from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.context_engine import ContextEngine


class FixedContextEngine:

    def __init__(self, fixed_date):

        self.fixed_date = fixed_date
        self.engine = ContextEngine()

    def snapshot(self):

        return self.engine.snapshot(self.fixed_date)


def add_media(db, index, filename):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"daily-brief-hash-{index}"
        }
    )


def save_analysis(db, media_id, values):

    db.save_ai_analysis(
        media_id,
        {
            "description": "Stored analysis for daily brief smoke test.",
            "scene_type": values.get("scene_type", "community"),
            "activity": values.get("activity", "community outreach"),
            "people_count": 3,
            "apparatus": values.get("apparatus", ["Engine"]),
            "equipment": values.get("equipment", ["Hose"]),
            "keywords": values.get("keywords", ["community", "safety"]),
            "community_score": values.get("community_score", 86),
            "recruitment_score": values.get("recruitment_score", 68),
            "education_score": values.get("education_score", 82),
            "technical_score": values.get("technical_score", 55),
            "overall_score": values.get("overall_score", 84),
            "facebook_caption": "",
            "instagram_caption": "",
            "model": "mock",
            "analysis_duration": 0.1,
            "provider": "mock",
            "retry_count": 0,
            "failure_reason": ""
        }
    )


def save_intelligence(db, media_id, values):

    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": values.get("normalized_scene", "community"),
            "incident_type": values.get("incident_type", "public_education"),
            "primary_activity": values.get("primary_activity", "community_outreach"),
            "apparatus_tags": values.get("apparatus_tags", ["engine"]),
            "equipment_tags": values.get("equipment_tags", ["hose"]),
            "ppe_tags": values.get("ppe_tags", ["turnout_gear"]),
            "people_tags": values.get("people_tags", ["crew"]),
            "content_tags": values.get("content_tags", []),
            "content_themes": values.get("content_themes", []),
            "recommended_uses": values.get("recommended_uses", []),
            "search_text": values.get("search_text", ""),
            "intelligence_score": values.get("intelligence_score", 82),
            "source_model": "mock"
        }
    )


def seed(db):

    add_media(db, 1, "summer_heat_safety.jpg")
    save_analysis(
        db,
        1,
        {
            "community_score": 90,
            "education_score": 92,
            "overall_score": 91
        }
    )
    save_intelligence(
        db,
        1,
        {
            "content_tags": ["heat", "summer", "safety", "public_education"],
            "content_themes": ["public_education", "community"],
            "recommended_uses": ["safety_message", "social_media"],
            "search_text": "heat summer safety public education",
            "intelligence_score": 94
        }
    )

    add_media(db, 2, "recruitment_training.jpg")
    save_analysis(
        db,
        2,
        {
            "scene_type": "training",
            "activity": "training",
            "community_score": 76,
            "recruitment_score": 93,
            "technical_score": 84,
            "overall_score": 90
        }
    )
    save_intelligence(
        db,
        2,
        {
            "normalized_scene": "training",
            "incident_type": "training",
            "primary_activity": "training",
            "apparatus_tags": ["engine"],
            "equipment_tags": ["scba", "hose"],
            "content_tags": ["training", "recruitment", "crew"],
            "content_themes": ["recruitment", "technical_training"],
            "recommended_uses": ["recruitment", "training", "social_media"],
            "search_text": "training recruitment crew scba hose",
            "intelligence_score": 91
        }
    )

    add_media(db, 3, "community_open_house.jpg")
    save_analysis(
        db,
        3,
        {
            "community_score": 95,
            "education_score": 75,
            "overall_score": 88
        }
    )
    save_intelligence(
        db,
        3,
        {
            "incident_type": "community_event",
            "primary_activity": "community_outreach",
            "content_tags": ["community", "public_education"],
            "content_themes": ["community_engagement"],
            "recommended_uses": ["community_outreach", "social_media"],
            "search_text": "community open house public education",
            "intelligence_score": 89
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed(db)

            from services.communications_director import CommunicationsDirector
            from services.communications_reasoning_service import (
                CommunicationsReasoningService
            )
            from services.daily_brief_service import DailyBriefService
            from services.knowledge_service import KnowledgeService
            from services.recommendation_learning_service import (
                RecommendationLearningService
            )
            from gui.home_page import HomePage

            director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 7, 15))
            )
            learning = RecommendationLearningService(db)
            reasoning = CommunicationsReasoningService(
                db,
                director=director,
                learning_service=learning
            )
            service = DailyBriefService(
                db,
                reasoning_service=reasoning,
                knowledge_service=KnowledgeService(db)
            )

            brief = service.generate(
                now=datetime(2026, 7, 15, 8, 30)
            )

            assert brief["title"] == "Daily Communications Brief", brief
            assert brief["greeting"].startswith("Good morning"), brief
            assert brief["current_date"] == "Wednesday, July 15, 2026", brief
            assert brief["current_context"]["season"] == "summer", brief
            assert brief["top_recommendation"]["title"], brief
            assert brief["top_recommendation"]["recommended_media"], brief
            assert brief["top_recommendation"]["facebook_caption"], brief
            assert brief["top_recommendation"]["instagram_caption"], brief
            assert len(brief["additional_opportunities"]) == 3, brief
            assert brief["library_health_summary"]["media_scanned"] == 3, brief
            assert brief["library_health_summary"]["media_analyzed"] == 3, brief
            assert brief["library_health_summary"]["knowledge_completeness"] > 0, brief
            assert brief["processing_status"], brief
            assert brief["recent_learning"], brief
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")
            assert HomePage is not None

        finally:
            os.chdir(original)

    print("daily_brief smoke passed")


if __name__ == "__main__":
    main()
