import os
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.ai_service import AIService
from services.analysis_quality_service import AnalysisQualityService
from services.analysis_review_service import AnalysisReviewService
from services.content_director_service import ContentDirectorService
from services.vision_preprocessing_service import VisionPreprocessingService
from services.vision_service import OllamaVisionProvider, VisionProviderError


class FakeResponse:

    def __init__(self, status_code=200, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeRequests:

    def __init__(self):
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout
            }
        )
        if len(self.calls) == 1:
            return FakeResponse(
                status_code=400,
                text="payload rejected"
            )
        return FakeResponse(
            status_code=200,
            payload={
                "response": """
{
  "description": "One firefighter in turnout gear is handling a hose near a training tower.",
  "people_count": 1,
  "people": ["firefighter"],
  "apparatus": [],
  "equipment": ["hose", "training tower", "helmet"],
  "activities": ["training"],
  "setting": "training ground",
  "indoor_outdoor": "outdoor",
  "visible_text": [],
  "training": true,
  "incident_scene": false,
  "public_education": false,
  "community_event": false,
  "safety_concerns": [],
  "public_use_risks": [],
  "uncertain_observations": [],
  "confidence": 0.86
}
"""
            }
        )


def image(path, mode="RGB", size=(300, 200)):
    img = Image.new(mode, size, (200, 30, 30, 180) if "A" in mode else (200, 30, 30))
    img.save(path)


def add_media(db, media_id, filename):
    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO media(id, filename, path, extension, media_type, filesize, sha256)
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            media_id,
            filename,
            str(Path(filename).resolve()),
            ".jpg",
            "image",
            123,
            f"hash-{media_id}"
        )
    )
    conn.commit()
    conn.close()


def sample_analysis(provider="ollama", trust_state="unreviewed_real"):
    return {
        "description": "One firefighter in turnout gear is handling a hose near a training tower.",
        "scene_type": "training ground",
        "activity": "training",
        "people_count": 1,
        "people": ["firefighter"],
        "apparatus": [],
        "equipment": ["hose", "helmet"],
        "activities": ["training"],
        "setting": "training ground",
        "indoor_outdoor": "outdoor",
        "visible_text": [],
        "uncertain_observations": [],
        "keywords": ["training", "hose"],
        "community_score": 20,
        "recruitment_score": 60,
        "education_score": 50,
        "technical_score": 70,
        "overall_score": 86,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": "qwen2.5vl:7b" if provider == "ollama" else "mock",
        "provider": provider,
        "retry_count": 0,
        "failure_reason": "",
        "raw_response": "{\"description\":\"ok\"}",
        "parse_status": "valid_structured_response",
        "parse_warnings": [],
        "confidence": 0.86,
        "structured_field_completeness": 0.9,
        "quality_state": "approved_automatically",
        "trust_state": trust_state,
        "review_status": "review_required",
        "quality_warnings": [],
        "media_context": "physical_scene"
    }


def save_intelligence(db, media_id):
    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": "training",
            "incident_type": "training",
            "primary_activity": "training",
            "apparatus_tags": [],
            "equipment_tags": ["hose"],
            "ppe_tags": ["helmet"],
            "people_tags": ["people"],
            "content_tags": ["training", "recruitment"],
            "content_themes": ["training"],
            "recommended_uses": ["recruitment", "training"],
            "search_text": "training firefighter hose",
            "intelligence_score": 80,
            "communications_score": 80,
            "source_model": "qwen2.5vl:7b"
        }
    )


def main():
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            rgb_path = Path(tmp) / "rgb.jpg"
            rgba_path = Path(tmp) / "rgba.png"
            large_path = Path(tmp) / "large.jpg"
            image(rgb_path)
            image(rgba_path, mode="RGBA")
            image(large_path, size=(4000, 2500))

            preprocessor = VisionPreprocessingService()
            rgb = preprocessor.preprocess(rgb_path, max_dimension=1536)
            rgba = preprocessor.preprocess(rgba_path, max_dimension=1536)
            large = preprocessor.preprocess(large_path, max_dimension=1536)

            assert rgb["metadata"]["submitted_dimensions"] == [300, 200], rgb
            assert rgba["metadata"]["submitted_mode"] == "RGB", rgba
            assert max(large["metadata"]["submitted_dimensions"]) <= 1536, large
            assert rgb["base64"], rgb

            import services.vision_service as vision_module

            fake = FakeRequests()
            original_requests = vision_module.requests
            vision_module.requests = fake
            try:
                provider = OllamaVisionProvider(
                    {
                        "url": "http://localhost:11434/api/generate",
                        "model": "qwen2.5vl:7b",
                        "timeout": 5,
                        "analysis_max_dimension": 1536,
                        "analysis_retry_max_dimension": 1024
                    }
                )
                output = provider.analyze(str(rgb_path))
                assert "firefighter" in output, output
                metadata = provider.request_metadata()
                assert len(fake.calls) == 2, fake.calls
                assert metadata["attempts"][0]["failure_category"] == "provider_http_400", metadata
                assert metadata["attempts"][1]["status_code"] == 200, metadata
            finally:
                vision_module.requests = original_requests

            parser = AIService()
            parsed = parser.parse_analysis(output, model="qwen2.5vl:7b")
            assert parsed["parse_status"] == parser.STATUS_VALID, parsed
            assert parsed["people_count"] == 1, parsed
            assert parsed["visible_text"] == [], parsed

            quality = AnalysisQualityService()
            gate = quality.evaluate(parsed | {"provider": "ollama"})
            assert gate["trust_state"] == "unreviewed_real", gate
            assert gate["review_status"] == "review_required", gate

            screenshot = quality.evaluate(
                parsed | {
                    "description": "A Facebook screenshot with Morden Fire Rescue text.",
                    "visible_text": ["Morden Fire Rescue", "Like", "Share", "Comment", "Home"],
                    "provider": "ollama"
                }
            )
            assert screenshot["media_context"] == "screenshot", screenshot
            assert screenshot["quality_state"] == quality.REVIEW_REQUIRED, screenshot

            db = DatabaseManager()
            db.initialize()
            add_media(db, 1, "approved.jpg")
            add_media(db, 2, "rejected.jpg")
            db.save_ai_analysis(1, sample_analysis())
            db.save_ai_analysis(2, sample_analysis(trust_state="rejected_real"))
            save_intelligence(db, 1)
            save_intelligence(db, 2)

            saved = db.get_ai_analysis(1)
            assert saved["raw_response"], saved
            assert saved["trust_state"] == "unreviewed_real", saved

            review = AnalysisReviewService(database=db)
            approved = review.approve(1, notes="Looks accurate")
            assert approved["trust_state"] == "approved_real", approved
            corrected = review.correct(1, {"people_count": 2}, notes="Adjusted count")
            assert corrected["trust_state"] == "corrected_real", corrected
            rejected = review.reject(2, notes="Wrong media interpretation")
            assert rejected["trust_state"] == "rejected_real", rejected
            metrics = review.metrics()
            assert metrics["review_corrected"] == 1, metrics
            assert metrics["review_rejected"] == 1, metrics
            reanalysis = review.request_reanalysis(1, notes="Try improved prompt")
            assert reanalysis["review_status"] == "reanalyze_requested", reanalysis
            history = db.analysis_review_history(1)
            assert len(history) == 3, history
            assert history[0]["decision"] == "reanalyze", history

            queue = review.queue(limit=10)
            assert any(item["media_id"] == 1 for item in queue), queue
            assert all(item["media_id"] != 2 for item in queue), queue

            candidates = db.content_director_candidates(limit=10)
            ids = {item["media_id"] for item in candidates}
            assert 1 in ids, candidates
            assert 2 not in ids, candidates

            result = ContentDirectorService(database=db).recommend(
                "training",
                limit=5
            )
            result_ids = {
                item["media_id"]
                for item in result["recommendations"]
            }
            assert 2 not in result_ids, result

            failed = VisionProviderError(
                "bad request",
                category="provider_http_400"
            )
            assert failed.category == "provider_http_400"
        finally:
            os.chdir(original_cwd)

    print("sprint28_analysis_workflow smoke passed")


if __name__ == "__main__":
    main()
