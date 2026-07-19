import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from models.analysis_queue import AnalysisQueueState
from services.ai_service import AIService
from services.brain_service import BrainService
from services.job_manager import JobManager


VALID_JSON = json.dumps({
    "description": "Two firefighters are training with a hose line.",
    "people_count": 2,
    "people": ["firefighters"],
    "apparatus": [],
    "equipment": ["hose"],
    "activities": ["training"],
    "setting": "training ground",
    "indoor_outdoor": "outdoor",
    "visible_text": [],
    "training": True,
    "incident_scene": False,
    "public_education": False,
    "community_event": False,
    "safety_concerns": [],
    "public_use_risks": [],
    "uncertain_observations": [],
    "confidence": 0.82
})


class SequenceVision:

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def analyze(self, image_path, prompt_context=""):
        self.calls += 1
        if not self.responses:
            return VALID_JSON
        return self.responses.pop(0)

    def provider_key(self):
        return "ollama"

    def model_name(self):
        return "qwen2.5vl:7b"

    def provider_settings(self):
        return {"timeout": 30}

    def provider_capabilities(self):
        return {
            "supports_images": True,
            "supports_video_frames": True,
            "production_approved": True
        }

    def request_metadata(self):
        return {
            "request": {
                "wrapper": "response"
            },
            "preprocessing": {
                "path": r"C:\\sensitive\\photo.jpg",
                "base64": "A" * 240
            },
            "attempts": []
        }


class NoopIntelligence:

    def generate_and_save(self, media_id, analysis):
        return analysis


def add_media(db, media_id, path):
    db.add_media({
        "filename": path.name,
        "path": str(path),
        "extension": path.suffix,
        "type": "image",
        "size": path.stat().st_size,
        "sha256": f"invalid-response-{media_id}"
    })


def queue_counts(db, session_id):
    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT state, COUNT(*)
        FROM analysis_queue
        WHERE session_id=?
        GROUP BY state
        """,
        (session_id,)
    )
    counts = dict(cur.fetchall())
    conn.close()
    return counts


def parser_cases():
    parser = AIService()

    empty = parser.parse_analysis("", "test")
    assert empty["failure_category"] == "empty_response", empty
    assert empty["parser_classification"] == "invalid", empty

    malformed = parser.parse_analysis("not json", "test")
    assert malformed["failure_category"] == "malformed_json", malformed

    fenced = parser.parse_analysis(
        "```json\n" + VALID_JSON + "\n```",
        "test"
    )
    assert fenced["parser_classification"] == "normalized_valid", fenced
    assert "markdown_wrapped_json" in fenced["normalization_evidence"], fenced
    assert fenced["failure_category"] == "", fenced

    leading = parser.parse_analysis(
        "Here is the object:\n" + VALID_JSON,
        "test"
    )
    assert "extra_text_around_json" in leading["normalization_evidence"], leading
    assert leading["failure_category"] == "", leading
    assert leading["people_count"] == 2, leading

    trailing = parser.parse_analysis(
        VALID_JSON + "\nThat is the result.",
        "test"
    )
    assert "extra_text_around_json" in trailing["normalization_evidence"], trailing
    assert trailing["failure_category"] == "", trailing

    truncated = parser.parse_analysis(
        '{"description":"A firefighter using a hose","people_count":1,"confidence":0.7',
        "test"
    )
    assert "truncated_response" in truncated["normalization_evidence"], truncated
    assert truncated["failure_category"] == "", truncated
    assert truncated["parser_classification"] == "partial_valid", truncated

    invalid_confidence = parser.parse_analysis(
        json.dumps({
            "description": "A firefighter training with a hose.",
            "people_count": 1,
            "confidence": 150
        }),
        "test"
    )
    assert invalid_confidence["failure_category"] == "invalid_field_types"

    invalid_people = parser.parse_analysis(
        json.dumps({
            "description": "A firefighter training with a hose.",
            "people_count": -2,
            "confidence": 0.6
        }),
        "test"
    )
    assert invalid_people["failure_category"] == "invalid_field_types"


def brain_retry_and_queue_cases(folder):
    db = DatabaseManager()
    media_dir = Path(folder) / "media"
    media_dir.mkdir()
    first = media_dir / "first.jpg"
    second = media_dir / "second.jpg"
    third = media_dir / "third.jpg"
    first.write_bytes(b"fake image")
    second.write_bytes(b"fake image two")
    third.write_bytes(b"fake image three")
    add_media(db, 1, first)
    add_media(db, 2, second)
    add_media(db, 3, third)

    retry_vision = SequenceVision([
        "not json",
        VALID_JSON
    ])
    retry_brain = BrainService(
        database=db,
        job_manager=JobManager(),
        vision_service=retry_vision,
        intelligence_service=NoopIntelligence(),
        config={
            "retry_attempts": 0,
            "retry_delay_seconds": 0
        }
    )
    saved = retry_brain._analyze_and_save(1, str(first))
    assert saved["failure_reason"] == "", saved
    assert saved["retry_count"] == 1, saved
    retry_brain.jobs.shutdown()

    queue_vision = SequenceVision([
        "not json",
        "still not json",
        VALID_JSON
    ])
    jobs = JobManager()
    queue_brain = BrainService(
        database=db,
        job_manager=jobs,
        vision_service=queue_vision,
        intelligence_service=NoopIntelligence(),
        config={
            "retry_attempts": 0,
            "retry_delay_seconds": 0,
            "batch_size": 1,
            "pause_between_batches": 0
        }
    )
    handle = queue_brain.analyze_selected([2, 3], force=True)
    result = handle.future.result(timeout=20)
    counts = queue_counts(db, result["session_id"])
    assert counts[AnalysisQueueState.FAILED] == 1, counts
    assert counts[AnalysisQueueState.COMPLETED] == 1, counts
    failure = db.get_ai_analysis(2)
    assert failure["failure_category"] == "malformed_json", failure
    assert "invalid_response" not in failure["failure_category"], failure

    diagnostics = list((Path("logs") / "provider_diagnostics").glob("*.json"))
    assert diagnostics, "provider diagnostic was not written"
    text = diagnostics[-1].read_text(encoding="utf-8")
    assert "AAAAAAAAAAAAAAAAAAAAAAAA" not in text, text
    assert "C:\\\\sensitive" not in text, text
    jobs.shutdown()


def main():
    original = Path.cwd()
    with TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        os.chdir(folder)
        try:
            parser_cases()
            brain_retry_and_queue_cases(folder)
        finally:
            os.chdir(original)

    print("invalid_response_handling_smoke passed")


if __name__ == "__main__":
    main()
