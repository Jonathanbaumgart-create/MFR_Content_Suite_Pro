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
            "sha256": f"program-timing-hash-{index}"
        }
    )


def seed_media(db):

    items = (
        (
            1,
            "fire_prevention.jpg",
            ["fire_prevention", "public_education", "safety"],
            ["public_education"],
            ["safety_message", "social_media"],
            "fire prevention public education safety"
        ),
        (
            2,
            "winter_hydrant.jpg",
            ["community", "winter", "public_education"],
            ["community_engagement"],
            ["community_outreach", "social_media"],
            "community winter hydrant public education"
        ),
        (
            3,
            "training.jpg",
            ["training", "recruitment", "crew"],
            ["recruitment", "technical_training"],
            ["recruitment", "training"],
            "training recruitment crew"
        )
    )

    for media_id, filename, tags, themes, uses, search_text in items:
        add_media(db, media_id, filename)
        db.save_ai_analysis(
            media_id,
            {
                "description": "Stored analysis for program timing smoke test.",
                "scene_type": "community",
                "activity": "public education",
                "people_count": 3,
                "apparatus": ["Engine"],
                "equipment": ["Hose"],
                "keywords": tags,
                "community_score": 88,
                "recruitment_score": 72,
                "education_score": 92,
                "technical_score": 60,
                "overall_score": 86,
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
            media_id,
            {
                "normalized_scene": "community",
                "incident_type": "public_education",
                "primary_activity": "community_outreach",
                "apparatus_tags": ["engine"],
                "equipment_tags": ["hose"],
                "ppe_tags": ["turnout_gear"],
                "people_tags": ["crew"],
                "content_tags": tags,
                "content_themes": themes,
                "recommended_uses": uses,
                "search_text": search_text,
                "intelligence_score": 90,
                "source_model": "mock"
            }
        )


def recommendation_text(recommendation):

    return " ".join(
        [
            recommendation.get("title", ""),
            recommendation.get("caption_strategy", ""),
            recommendation.get("call_to_action", ""),
            " ".join(recommendation.get("reasoning", []))
        ]
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed_media(db)

            from services.communications_director import CommunicationsDirector
            from services.communications_reasoning_service import (
                CommunicationsReasoningService
            )
            from services.daily_brief_service import DailyBriefService
            from services.knowledge_service import KnowledgeService

            knowledge = KnowledgeService(db)
            travelling = knowledge.explicit_program_from_prompt(
                "Travelling Sparky"
            )
            hydrant = knowledge.explicit_program_from_prompt(
                "Hydrant Heroes"
            )
            fire_prevention = knowledge.explicit_program_from_prompt(
                "Fire Prevention Week"
            )

            assert travelling, "Travelling Sparky default knowledge missing"
            assert hydrant, "Hydrant Heroes default knowledge missing"
            assert fire_prevention, "Fire Prevention Week default knowledge missing"

            assert not knowledge.program_status(
                travelling,
                date(2026, 7, 8)
            )["active"]
            assert knowledge.program_status(
                travelling,
                date(2026, 11, 8)
            )["active"]
            assert knowledge.program_status(
                hydrant,
                date(2026, 1, 8)
            )["active"]
            assert not knowledge.program_status(
                hydrant,
                date(2026, 7, 8)
            )["active"]
            assert knowledge.event_status(
                fire_prevention,
                date(2026, 9, 15)
            )["active"]
            assert knowledge.event_status(
                fire_prevention,
                date(2026, 10, 8)
            )["active"]
            assert knowledge.event_status(
                fire_prevention,
                date(2026, 7, 8)
            )["upcoming"]

            july_director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 7, 8))
            )
            july_reasoning = CommunicationsReasoningService(
                db,
                director=july_director,
                knowledge_service=knowledge
            )
            july_fire_prevention = july_reasoning.generate_recommendations(
                opportunity_keys=["fire_prevention_week"],
                limit=1
            )[0]
            july_text = recommendation_text(july_fire_prevention)

            assert "Travelling Sparky Fire Prevention Week" not in july_text, july_text
            assert "outside its active window" in july_text, july_text

            explicit = july_reasoning.generate_recommendations(
                prompt="Travelling Sparky school visit",
                limit=1
            )[0]
            explicit_text = recommendation_text(explicit)

            assert "Travelling Sparky" in explicit_text, explicit_text
            assert "explicitly requested" in explicit_text, explicit_text

            winter_director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 1, 8))
            )
            winter_reasoning = CommunicationsReasoningService(
                db,
                director=winter_director,
                knowledge_service=knowledge
            )
            winter = winter_reasoning.generate_recommendations(
                opportunity_keys=["community_appreciation"],
                limit=1
            )[0]
            assert "Hydrant Heroes" in recommendation_text(winter), winter

            daily = DailyBriefService(
                db,
                reasoning_service=july_reasoning,
                knowledge_service=knowledge
            ).generate(
                now=datetime(2026, 7, 8, 8, 0)
            )
            top_text = " ".join(
                [
                    daily["top_recommendation"]["title"],
                    " ".join(daily["top_recommendation"]["reasoning"])
                ]
            )
            assert "Travelling Sparky Fire Prevention Week" not in top_text, top_text
            assert not hasattr(july_reasoning, "vision")
            assert not hasattr(july_reasoning, "ai")

        finally:
            os.chdir(original)

    print("program_timing smoke passed")


if __name__ == "__main__":
    main()
