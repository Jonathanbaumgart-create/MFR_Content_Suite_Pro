from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager


class FakeJobManager:

    def progress(self):

        return {
            "queued": 2,
            "running": 1,
            "completed": 3,
            "failed": 1,
            "canceled": 0,
            "paused": False
        }


def add_media(db, index, filename):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"operations-center-hash-{index}"
        }
    )


def seed(db):

    add_media(db, 1, "ready.jpg")
    add_media(db, 2, "provider_failure.jpg")
    add_media(db, 3, "unanalyzed.jpg")

    db.save_ai_analysis(
        1,
        {
            "description": "Stored analysis for operations smoke test.",
            "scene_type": "community",
            "activity": "public education",
            "people_count": 3,
            "apparatus": ["Engine"],
            "equipment": ["Hose"],
            "keywords": ["community", "safety", "public_education"],
            "community_score": 90,
            "recruitment_score": 60,
            "education_score": 90,
            "technical_score": 45,
            "overall_score": 88,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": "mock",
            "analysis_duration": 0.1,
            "provider": "mock",
            "retry_count": 0,
            "failure_reason": ""
        }
    )
    db.save_media_intelligence(
        1,
        {
            "normalized_scene": "community",
            "incident_type": "public_education",
            "primary_activity": "community_outreach",
            "apparatus_tags": ["engine"],
            "equipment_tags": ["hose"],
            "ppe_tags": ["turnout_gear"],
            "people_tags": ["crew"],
            "content_tags": ["community", "public_education"],
            "content_themes": ["community"],
            "recommended_uses": ["community_outreach", "social_media"],
            "search_text": "community public education safety",
            "intelligence_score": 90,
            "source_model": "mock"
        }
    )
    db.save_ai_failure(
        2,
        {
            "model": "qwen2.5vl:7b",
            "provider": "ollama",
            "retry_count": 2,
            "analysis_duration": 0.5,
            "failure_reason": "CUDA provider failure"
        }
    )
    db.save_recommendation_history(
        {
            "media_id": 1,
            "reason": "smoke test",
            "opportunity": "community_appreciation",
            "score": 88,
            "platform": "Facebook"
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed(db)

            from services.operations_service import OperationsService
            from gui.operations_page import OperationsPage

            service = OperationsService(
                database=db,
                job_manager=FakeJobManager()
            )
            report = service.snapshot()

            library = report["library_processing"]
            assert library["total_media_scanned"] == 3, library
            assert library["media_intelligence_count"] == 1, library
            assert library["unanalyzed_count"] == 1, library
            assert library["intelligence_missing_count"] == 0, library
            assert library["analysis_coverage_percentage"] >= 60, library

            queue = report["queue_health"]
            assert queue["queued_jobs"] == 2, queue
            assert queue["running_jobs"] == 1, queue
            assert queue["failed_jobs"] == 1, queue
            assert queue["status"] == "Running", queue

            provider = report["provider_health"]
            assert provider["active_provider"] == "mock", provider
            assert provider["mock_warning"] == "Mock provider active - test data only", provider
            assert provider["last_provider_failure"], provider

            knowledge = report["knowledge_health"]
            assert knowledge["programs_count"] >= 2, knowledge
            assert knowledge["knowledge_completeness_score"] > 0, knowledge

            communications = report["communications_readiness"]
            assert communications["recommendation_history_count"] == 1, communications
            assert communications["content_gaps"], communications

            attention = " ".join(report["attention_items"])
            assert "Mock provider active" in attention, attention
            assert "Provider failures detected" in attention, attention
            assert "Travelling Sparky" in attention, attention
            assert OperationsPage is not None
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")

        finally:
            os.chdir(original)

    print("operations_center smoke passed")


if __name__ == "__main__":
    main()
