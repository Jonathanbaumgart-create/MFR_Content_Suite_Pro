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
            "sha256": f"context-engine-hash-{index}"
        }
    )


def save_analysis(db, media_id):

    db.save_ai_analysis(
        media_id,
        {
            "description": "Stored summer safety and recruitment analysis.",
            "scene_type": "community",
            "activity": "public education",
            "people_count": 3,
            "apparatus": ["Engine"],
            "equipment": ["Hose"],
            "keywords": ["community", "safety", "summer"],
            "community_score": 90,
            "recruitment_score": 80,
            "education_score": 88,
            "technical_score": 50,
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
            "content_tags": ["community", "summer", "safety", "public_education"],
            "content_themes": ["community", "public_education"],
            "recommended_uses": ["community_outreach", "social_media", "safety_message"],
            "search_text": "community summer safety public education",
            "intelligence_score": 90,
            "source_model": "mock"
        }
    )


def main():

    engine = ContextEngine()

    october = engine.snapshot(date(2026, 10, 8))
    assert october.month == 10, october
    assert october.season == "fall", october
    assert "fire_prevention_week" in october.active_themes, october
    assert "fire_prevention_week" in october.suggested_opportunities, october

    summer = engine.snapshot(date(2026, 7, 15))
    assert summer.season == "summer", summer
    assert "summer_heat_safety" in summer.active_themes, summer
    assert "heat_warning" in summer.suggested_opportunities, summer
    assert "water_safety" in summer.suggested_opportunities, summer

    winter = engine.snapshot(date(2026, 1, 15))
    assert winter.season == "winter", winter
    assert "winter_safety_season" in winter.active_themes, winter
    assert "holiday_safety" in winter.suggested_opportunities, winter

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            add_media(db, 1, "summer_safety.jpg")
            save_analysis(db, 1)
            save_intelligence(db, 1)

            from services.communications_director import CommunicationsDirector

            director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 7, 15))
            )

            brief = director.todays_brief()
            context = brief["context_snapshot"]

            assert context["season"] == "summer", context
            assert "summer_heat_safety" in context["active_themes"], context
            assert brief["recommendations"], brief
            assert brief["recommendations"][0]["opportunity_type"] in (
                "heat_warning",
                "water_safety"
            ), brief

            generated = director.generate_opportunities(
                "general update",
                limit=2
            )
            assert generated, generated
            assert any(
                "local calendar context" in " ".join(item["reasoning"]).lower()
                for item in generated
            ), generated
            assert not hasattr(director, "vision")
            assert not hasattr(director, "ai")

        finally:
            os.chdir(original)

    print("context_engine smoke passed")


if __name__ == "__main__":
    main()
