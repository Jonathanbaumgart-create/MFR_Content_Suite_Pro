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
            "sha256": f"knowledge-service-hash-{index}"
        }
    )


def save_analysis(db, media_id):

    db.save_ai_analysis(
        media_id,
        {
            "description": "Stored public education analysis.",
            "scene_type": "community",
            "activity": "public education",
            "people_count": 3,
            "apparatus": ["Engine"],
            "equipment": ["Hose"],
            "keywords": ["community", "safety", "public_education"],
            "community_score": 90,
            "recruitment_score": 60,
            "education_score": 95,
            "technical_score": 45,
            "overall_score": 90,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": "mock",
            "analysis_duration": 0.1,
            "provider": "mock",
            "retry_count": 0,
            "failure_reason": ""
        }
    )


def save_intelligence(db, media_id):

    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": "community",
            "incident_type": "public_education",
            "primary_activity": "community_outreach",
            "apparatus_tags": ["engine"],
            "equipment_tags": ["hose"],
            "ppe_tags": ["turnout_gear"],
            "people_tags": ["crew"],
            "content_tags": ["community", "safety", "public_education", "fire_prevention"],
            "content_themes": ["community", "public_education"],
            "recommended_uses": ["community_outreach", "social_media", "safety_message"],
            "search_text": "community safety public education fire prevention",
            "intelligence_score": 92,
            "source_model": "mock"
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()

            from services.knowledge_service import KnowledgeService

            knowledge = KnowledgeService(db)
            profile = knowledge.profile()

            assert profile["department_name"] == "Morden Fire & Rescue", profile
            assert any(
                item["name"] == "Hydrant Heroes"
                for item in knowledge.items("programs")
            )
            assert any(
                item["name"] == "Travelling Sparky"
                for item in knowledge.items("programs")
            )
            assert knowledge.program_for_opportunity(
                "community_appreciation",
                today=date(2026, 1, 8)
            )["name"] == "Hydrant Heroes"
            assert knowledge.program_for_opportunity(
                "fire_prevention_week",
                today=date(2026, 11, 8)
            )["name"] == "Travelling Sparky"
            assert knowledge.program_for_opportunity(
                "fire_prevention_week",
                today=date(2026, 7, 8)
            ) is None

            knowledge.save_profile(
                {
                    "department_name": "Morden Fire & Rescue",
                    "community": "Morden"
                }
            )
            item_id = knowledge.save_item(
                "community_partners",
                {
                    "name": "Morden Schools",
                    "category": "education",
                    "description": "School partner for public education.",
                    "tags": ["school", "public_education"],
                    "active": True
                }
            )
            assert item_id, item_id

            add_media(db, 1, "travelling_sparky.jpg")
            save_analysis(db, 1)
            save_intelligence(db, 1)

            from services.communications_director import CommunicationsDirector
            from services.communications_reasoning_service import (
                CommunicationsReasoningService
            )

            director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 11, 8))
            )
            service = CommunicationsReasoningService(
                db,
                director=director,
                knowledge_service=knowledge
            )
            recommendation = service.generate_recommendations(
                opportunity_keys=["fire_prevention_week"],
                limit=1
            )[0]

            text = " ".join(
                [
                    recommendation["title"],
                    recommendation["caption_strategy"],
                    recommendation["call_to_action"],
                    " ".join(recommendation["reasoning"])
                ]
            )

            assert "Travelling Sparky" in text, recommendation
            assert "Morden Fire & Rescue" in text, recommendation
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")

        finally:
            os.chdir(original)

    print("knowledge_service smoke passed")


if __name__ == "__main__":
    main()
