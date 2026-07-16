import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeVision:

    def provider_key(self):
        return "ollama"

    def model_name(self):
        return "qwen2.5vl:7b"

    def provider_settings(self):
        return {"timeout": 300}

    def request_metadata(self):
        return {
            "request": {"model": self.model_name()},
            "preprocessing": {},
            "attempts": []
        }


class FakeAI:

    def __init__(self):
        self.fail_names = set()

    def analyze_image(self, image_path, vision, prompt_context=""):
        filename = Path(image_path).name

        if filename in self.fail_names:
            raise TimeoutError("provider timeout")

        return {
            "description": f"Fire-service training image for {filename}",
            "scene_type": "training",
            "activity": "training",
            "people_count": 1,
            "people": ["firefighter"],
            "apparatus": [],
            "equipment": ["helmet", "hose"],
            "activities": ["training"],
            "setting": "training ground",
            "indoor_outdoor": "outdoor",
            "visible_text": [],
            "uncertain_observations": [],
            "keywords": ["training", "firefighter"],
            "community_score": 40,
            "recruitment_score": 70,
            "education_score": 60,
            "technical_score": 70,
            "overall_score": 82,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": vision.model_name(),
            "confidence": 0.82,
            "raw_response": "{\"description\":\"training\"}",
            "parse_status": "valid_structured_response",
            "parse_warnings": [],
            "structured_field_completeness": 0.9
        }


class NoopIntelligence:

    def generate_and_save(self, media_id, analysis):
        return analysis

    def rebuild_missing(self, limit=None, progress_callback=None):
        return {"processed": 0}


def add_media(db, media_id, filename, folder):
    path = folder / filename
    path.write_bytes(b"fake image bytes")
    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO media(
            id,
            filename,
            path,
            extension,
            media_type,
            filesize,
            sha256,
            date_added,
            first_seen_at
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            filename,
            str(path),
            path.suffix.lower(),
            "image",
            path.stat().st_size,
            f"hash-{media_id}",
            "2026-07-16T12:00:00+00:00",
            "2026-07-16T12:00:00+00:00"
        )
    )
    conn.commit()
    conn.close()


def queue_state_counts(db, session_id):
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


def duplicate_queue_rows(db):
    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT session_id, media_id, COUNT(*) AS count
            FROM analysis_queue
            GROUP BY session_id, media_id
            HAVING count > 1
        )
        """
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


def latest_media_status(db, media_id):
    return db._analysis_queue_repository().media_statuses([media_id])[media_id]


def main():
    original_cwd = os.getcwd()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        os.chdir(folder)

        try:
            from database.db_manager import DatabaseManager
            from models.analysis_queue import (
                AnalysisQueueState,
                AnalysisSessionStatus
            )
            from services.brain_service import BrainService
            from services.job_manager import JobManager

            db = DatabaseManager()
            media_folder = Path(folder) / "media"
            media_folder.mkdir()
            add_media(db, 1, "one.jpg", media_folder)
            add_media(db, 2, "two.jpg", media_folder)
            add_media(db, 3, "timeout.jpg", media_folder)

            jobs = JobManager()
            fake_ai = FakeAI()
            brain = BrainService(
                database=db,
                job_manager=jobs,
                ai_service=fake_ai,
                vision_service=FakeVision(),
                intelligence_service=NoopIntelligence(),
                config={
                    "retry_attempts": 0,
                    "retry_delay_seconds": 0,
                    "batch_size": 2,
                    "pause_between_batches": 0
                }
            )

            session_id = db.create_analysis_session(
                "worker recovery smoke",
                "ollama",
                "qwen2.5vl:7b",
                total_items=2
            )
            db.enqueue_analysis_items(
                session_id,
                [
                    (1, "one.jpg", str(media_folder / "one.jpg"), "image"),
                    (2, "two.jpg", str(media_folder / "two.jpg"), "image")
                ],
                "ollama",
                "qwen2.5vl:7b"
            )
            first = db.next_analysis_queue_batch(session_id, 1)[0]
            db.mark_analysis_queue_analyzing(first["queue_id"])
            db.update_analysis_session(
                session_id,
                status=AnalysisSessionStatus.RUNNING,
                current_media_id=1,
                current_filename="one.jpg"
            )

            recovered = brain.recover_interrupted_sessions()
            assert recovered, recovered
            summary = db.analysis_session_summary(session_id)
            assert summary["status"] == AnalysisSessionStatus.RECOVERABLE, summary
            assert summary["worker_status"] == "Recoverable", summary
            counts = queue_state_counts(db, session_id)
            assert counts[AnalysisQueueState.RETRY_PENDING] == 1, counts
            assert latest_media_status(db, 1) == "Interrupted"

            handle = brain.resume_previous_analysis(
                session_id,
                max_items=1
            )
            result = handle.future.result(timeout=10)
            assert result["session_id"] == session_id, result
            summary = db.analysis_session_summary(session_id)
            assert summary["status"] == AnalysisSessionStatus.PAUSED, summary
            assert summary["worker_heartbeat_at"], summary
            assert summary["worker_stopped_at"], summary
            assert summary["resume_count"] >= 1, summary
            counts = queue_state_counts(db, session_id)
            assert counts[AnalysisQueueState.COMPLETED] == 1, counts
            assert (
                counts.get(AnalysisQueueState.QUEUED, 0) +
                counts.get(AnalysisQueueState.RETRY_PENDING, 0)
            ) == 1, counts
            assert duplicate_queue_rows(db) == 0

            active_session = db.create_analysis_session(
                "duplicate worker smoke",
                "ollama",
                "qwen2.5vl:7b",
                total_items=1
            )
            db.enqueue_analysis_items(
                active_session,
                [(2, "two.jpg", str(media_folder / "two.jpg"), "image")],
                "ollama",
                "qwen2.5vl:7b"
            )
            jobs.pause()
            first_future = brain._submit_persistent_session(
                active_session,
                max_items=1
            )
            second_future = brain._submit_persistent_session(
                active_session,
                max_items=1
            )
            assert first_future is second_future
            jobs.resume()
            first_future.result(timeout=10)

            failed_session = db.create_analysis_session(
                "failure smoke",
                "ollama",
                "qwen2.5vl:7b",
                total_items=1
            )
            db.enqueue_analysis_items(
                failed_session,
                [
                    (
                        3,
                        "timeout.jpg",
                        str(media_folder / "timeout.jpg"),
                        "image"
                    )
                ],
                "ollama",
                "qwen2.5vl:7b"
            )
            fake_ai.fail_names.add("timeout.jpg")
            failed = brain.resume_previous_analysis(failed_session)
            failed.future.result(timeout=10)
            counts = queue_state_counts(db, failed_session)
            assert counts[AnalysisQueueState.FAILED] == 1, counts

            metrics = brain.dashboard_metrics()
            assert "analysis_worker_status" in metrics, metrics
            assert metrics.get("provider") == "ollama", metrics

            jobs.shutdown()

        finally:
            os.chdir(original_cwd)

    print("analysis_worker_recovery_smoke passed")


if __name__ == "__main__":
    main()
