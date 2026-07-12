import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.analysis_queue_schema import (
    analysis_queue_indexes,
    create_analysis_queue_tables
)
from database.analysis_queue_repository import AnalysisQueueRepository
from models.analysis_queue import AnalysisQueueState
from services.brain_service import BrainService


class SmokeDatabase:

    def __init__(self, path):

        self.db = Path(path)
        self._repo = AnalysisQueueRepository(self)
        self.initialize()

    def connection(self):

        return sqlite3.connect(self.db)

    def initialize(self):

        conn = self.connection()
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE media(
            id INTEGER PRIMARY KEY,
            filename TEXT,
            path TEXT,
            media_type TEXT
        );
        CREATE TABLE ai_analysis(
            media_id INTEGER PRIMARY KEY,
            description TEXT,
            provider TEXT,
            model TEXT,
            failure_reason TEXT
        );
        CREATE TABLE media_intelligence(
            media_id INTEGER PRIMARY KEY
        );
        CREATE TABLE media_corrections(
            id INTEGER PRIMARY KEY,
            media_id INTEGER,
            active INTEGER DEFAULT 1
        );
        """)
        create_analysis_queue_tables(cur)

        for statement in analysis_queue_indexes():
            cur.execute(statement)

        conn.commit()
        conn.close()

    def add_media(self, media_id, filename, path, media_type="image"):

        conn = self.connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO media(id, filename, path, media_type) VALUES(?,?,?,?)",
            (media_id, filename, path, media_type)
        )
        conn.commit()
        conn.close()

    def get_media_by_ids(self, media_ids):

        placeholders = ",".join("?" for _ in media_ids)
        conn = self.connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, filename, path, media_type
            FROM media
            WHERE id IN ({placeholders})
            ORDER BY id
            """,
            tuple(media_ids)
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_ai_analysis(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM ai_analysis WHERE media_id=?",
            (media_id,)
        )
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def save_ai_analysis(self, media_id, analysis):

        conn = self.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO ai_analysis(
            media_id,
            description,
            provider,
            model,
            failure_reason
        )
        VALUES(?,?,?,?,?)
        """,
        (
            media_id,
            analysis.get("description", ""),
            analysis.get("provider", ""),
            analysis.get("model", ""),
            analysis.get("failure_reason", "")
        ))
        conn.commit()
        conn.close()

    def save_ai_failure(self, media_id, failure):

        self.save_ai_analysis(
            media_id,
            {
                "description": "",
                "provider": failure.get("provider", ""),
                "model": failure.get("model", ""),
                "failure_reason": failure.get("failure_reason", "")
            }
        )

    def create_analysis_session(self, *args, **kwargs):
        return self._repo.create_session(*args, **kwargs)

    def enqueue_analysis_items(self, *args, **kwargs):
        return self._repo.enqueue_items(*args, **kwargs)

    def next_analysis_queue_batch(self, *args, **kwargs):
        return self._repo.next_batch(*args, **kwargs)

    def mark_analysis_queue_analyzing(self, *args, **kwargs):
        return self._repo.mark_analyzing(*args, **kwargs)

    def mark_analysis_queue_completed(self, *args, **kwargs):
        return self._repo.mark_completed(*args, **kwargs)

    def mark_analysis_queue_skipped(self, *args, **kwargs):
        return self._repo.mark_skipped(*args, **kwargs)

    def mark_analysis_queue_failed(self, *args, **kwargs):
        return self._repo.mark_failed(*args, **kwargs)

    def retry_failed_analysis_items(self, *args, **kwargs):
        return self._repo.retry_failed(*args, **kwargs)

    def cancel_analysis_session(self, *args, **kwargs):
        return self._repo.cancel_session(*args, **kwargs)

    def reset_stale_analysis_items(self, *args, **kwargs):
        return self._repo.reset_stale_analyzing(*args, **kwargs)

    def update_analysis_session(self, *args, **kwargs):
        return self._repo.update_session(*args, **kwargs)

    def refresh_analysis_session_counts(self, *args, **kwargs):
        return self._repo.refresh_session_counts(*args, **kwargs)

    def analysis_session_summary(self, *args, **kwargs):
        return self._repo.session_summary(*args, **kwargs)

    def latest_incomplete_analysis_session(self):
        return self._repo.latest_incomplete_session()


class ImmediateJobManager:

    def __init__(self):
        self.paused = False

    def submit(self, func, *args, callback=None, error_callback=None, **kwargs):

        class Done:
            def __init__(self):
                self._result = None

            def result(self, timeout=None):
                return self._result

        future = Done()

        try:
            future._result = func(*args, **kwargs)
            if callback:
                callback(future._result)
        except Exception as error:
            if error_callback:
                error_callback(error)
            raise

        return future

    def progress(self):
        return {
            "queued": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "canceled": 0,
            "paused": self.paused
        }

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def cancel_queued(self):
        return 0

    def clear_completed(self):
        return None

    def wait_if_paused(self):
        return None


class FakeVision:

    def __init__(self):
        self.fail_paths = {"timeout.jpg": TimeoutError("provider timeout")}

    def provider_key(self):
        return "ollama"

    def model_name(self):
        return "moondream:latest"

    def provider_settings(self):
        return {"timeout": 300}


class FakeAI:

    def analyze_image(self, image_path, vision):

        name = Path(image_path).name
        error = vision.fail_paths.get(name)

        if error:
            raise error

        return {
            "description": f"Analysis for {name}",
            "model": vision.model_name(),
            "overall_score": 80
        }


class NoopIntelligence:

    def generate_and_save(self, media_id, analysis):
        return analysis


def main():

    with tempfile.TemporaryDirectory() as temp_dir:
        db = SmokeDatabase(Path(temp_dir) / "queue.db")
        db.add_media(1, "one.jpg", str(Path(temp_dir) / "one.jpg"))
        db.add_media(2, "timeout.jpg", str(Path(temp_dir) / "timeout.jpg"))
        db.add_media(3, "three.jpg", str(Path(temp_dir) / "three.jpg"))
        db.add_media(4, "four.jpg", str(Path(temp_dir) / "four.jpg"))

        brain = BrainService(
            database=db,
            job_manager=ImmediateJobManager(),
            ai_service=FakeAI(),
            vision_service=FakeVision(),
            intelligence_service=NoopIntelligence(),
            config={
                "retry_attempts": 0,
                "retry_delay_seconds": 0,
                "batch_size": 2,
                "pause_between_batches": 0
            }
        )

        handle = brain.analyze_selected([1, 2, 3, 1])
        result = handle.future.result()
        session_id = result["session_id"]
        summary = db.analysis_session_summary(session_id)

        assert summary["completed_count"] == 2
        assert summary["failed_count"] == 1

        counts = db._repo.queue_counts(session_id)
        assert counts[AnalysisQueueState.COMPLETED] == 2
        assert counts[AnalysisQueueState.FAILED] == 1

        conn = db.connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analysis_queue WHERE session_id=?",
            (session_id,)
        )
        assert cur.fetchone()[0] == 3
        conn.close()

        brain.vision.fail_paths.clear()
        retry = brain.retry_failed_analysis(session_id)
        retry.result = retry.future.result()
        summary = db.analysis_session_summary(session_id)
        assert summary["completed_count"] == 3
        assert summary["failed_count"] == 0

        resume_session = db.create_analysis_session(
            "resume smoke",
            "ollama",
            "moondream:latest",
            total_items=1
        )
        db.enqueue_analysis_items(
            resume_session,
            [(4, "four.jpg", str(Path(temp_dir) / "four.jpg"), "image")],
            "ollama",
            "moondream:latest"
        )
        resumed = brain.resume_previous_analysis(resume_session)
        resumed.future.result()
        assert db.analysis_session_summary(resume_session)["completed_count"] == 1

        cancel_session = db.create_analysis_session(
            "cancel smoke",
            "ollama",
            "moondream:latest",
            total_items=1
        )
        db.enqueue_analysis_items(
            cancel_session,
            [(1, "one.jpg", str(Path(temp_dir) / "one.jpg"), "image")],
            "ollama",
            "moondream:latest"
        )
        assert db.cancel_analysis_session(cancel_session) == 1
        assert (
            db._repo.queue_counts(cancel_session)[AnalysisQueueState.CANCELED]
            == 1
        )

    print("production_analysis_engine_smoke passed")


if __name__ == "__main__":
    main()
