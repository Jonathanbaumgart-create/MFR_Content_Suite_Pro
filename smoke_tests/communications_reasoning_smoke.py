from datetime import date
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
            "sha256": f"communications-reasoning-hash-{index}"
        }
    )


def save_analysis(db, media_id, scores):

    db.save_ai_analysis(
        media_id,
        {
            "description": "Stored analysis for reasoning smoke test.",
            "scene_type": "community",
            "activity": "public education",
            "people_count": 3,
            "apparatus": ["Engine"],
            "equipment": ["Hose", "SCBA"],
            "keywords": ["community", "safety", "summer"],
            "community_score": scores.get("community", 80),
            "recruitment_score": scores.get("recruitment", 60),
            "education_score": scores.get("education", 80),
            "technical_score": scores.get("technical", 60),
            "overall_score": scores.get("overall", 80),
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
            "equipment_tags": values.get("equipment_tags", []),
            "ppe_tags": values.get("ppe_tags", ["turnout_gear"]),
            "people_tags": values.get("people_tags", ["crew"]),
            "content_tags": values.get("content_tags", []),
            "content_themes": values.get("content_themes", []),
            "recommended_uses": values.get("recommended_uses", []),
            "search_text": values.get("search_text", ""),
            "intelligence_score": values.get("intelligence_score", 80),
            "source_model": "mock"
        }
    )


def seed(db):

    add_media(db, 1, "heat_safety_best.jpg")
    save_analysis(
        db,
        1,
        {
            "community": 92,
            "education": 94,
            "recruitment": 50,
            "overall": 92
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
            "intelligence_score": 95
        }
    )

    add_media(db, 2, "heat_safety_backup.jpg")
    save_analysis(
        db,
        2,
        {
            "community": 88,
            "education": 90,
            "recruitment": 45,
            "overall": 88
        }
    )
    save_intelligence(
        db,
        2,
        {
            "content_tags": ["heat", "summer", "hydration", "safety"],
            "content_themes": ["public_education"],
            "recommended_uses": ["safety_message"],
            "search_text": "heat hydration summer safety",
            "intelligence_score": 89
        }
    )

    add_media(db, 3, "recruitment_training.jpg")
    save_analysis(
        db,
        3,
        {
            "community": 78,
            "education": 70,
            "recruitment": 96,
            "technical": 88,
            "overall": 91
        }
    )
    save_intelligence(
        db,
        3,
        {
            "normalized_scene": "training",
            "incident_type": "training",
            "primary_activity": "training",
            "content_tags": ["training", "recruitment", "crew", "scba"],
            "content_themes": ["recruitment", "technical_training"],
            "recommended_uses": ["recruitment", "training", "social_media"],
            "search_text": "training recruitment crew scba",
            "intelligence_score": 93
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

            director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 7, 15))
            )
            service = CommunicationsReasoningService(
                db,
                director=director
            )

            brief = service.todays_communications_brief()
            assert brief["title"] == "Today's Communications Brief", brief
            assert brief["top_recommendation"], brief
            assert brief["additional_opportunities"], brief
            assert brief["library_health"]["total_media"] == 3, brief
            assert brief["content_gaps"], brief
            assert brief["seasonal_context"]["season"] == "summer", brief

            top = brief["top_recommendation"]
            assert top["reasoning"], top
            assert top["recommended_media"], top
            assert top["caption_strategy"], top
            assert top["engagement_prediction"], top
            assert top["call_to_action"], top

            history = db.recent_recommended_media_ids(days=30)
            assert history, history

            first = service.generate_recommendations(
                opportunity_keys=["heat_warning"],
                limit=1,
                persist_history=True
            )[0]
            first_media = first["recommended_media"][0]["media_id"]

            second = service.generate_recommendations(
                opportunity_keys=["heat_warning"],
                limit=1,
                persist_history=False
            )[0]
            second_media = second["recommended_media"][0]["media_id"]

            assert first_media != second_media, (first, second)
            assert "recently" in second["recommended_media"][0]["reason"], second
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")

        finally:
            os.chdir(original)

    print("communications_reasoning smoke passed")


if __name__ == "__main__":
    main()
