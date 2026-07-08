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
from services.context_providers import ContextProvider


class HighPriorityProvider(ContextProvider):

    def provider_name(self):

        return "high"

    def priority(self):

        return 5

    def get_context(self):

        context = self.base_context()
        context.update(
            {
                "active_themes": ["high_priority_theme", "shared_theme"],
                "suggested_opportunities": ["training_highlight"],
                "explanations": ["High priority provider ran."]
            }
        )

        return context


class LowPriorityProvider(ContextProvider):

    def provider_name(self):

        return "low"

    def priority(self):

        return 50

    def get_context(self):

        context = self.base_context()
        context.update(
            {
                "active_themes": ["low_priority_theme", "shared_theme"],
                "suggested_opportunities": ["general_engagement"],
                "explanations": ["Low priority provider ran."]
            }
        )

        return context


class DisabledProvider(ContextProvider):

    def enabled(self):

        return False

    def get_context(self):

        context = self.base_context()
        context["active_themes"] = ["disabled_theme"]

        return context


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
            "sha256": f"context-provider-hash-{index}"
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
            "content_tags": ["community", "summer", "safety"],
            "content_themes": ["community", "public_education"],
            "recommended_uses": ["community_outreach", "social_media"],
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
    assert "recruitment_friendly_period" in october.active_themes, october
    assert "fire_prevention_week" in october.suggested_opportunities, october

    prioritized = ContextEngine(
        providers=[
            LowPriorityProvider(today=date(2026, 7, 15)),
            HighPriorityProvider(today=date(2026, 7, 15)),
            DisabledProvider(today=date(2026, 7, 15))
        ]
    ).snapshot(date(2026, 7, 15))

    assert prioritized.active_themes[:3] == [
        "high_priority_theme",
        "shared_theme",
        "low_priority_theme"
    ], prioritized
    assert "disabled_theme" not in prioritized.active_themes, prioritized

    disabled_config = {
        "providers": {
            "calendar": {
                "enabled": True,
                "priority": 10
            },
            "season": {
                "enabled": False,
                "priority": 20
            },
            "campaign": {
                "enabled": False,
                "priority": 30
            }
        }
    }
    disabled = ContextEngine(config=disabled_config).snapshot(date(2026, 7, 15))
    assert disabled.season == "summer", disabled
    assert "summer_heat_safety" not in disabled.active_themes, disabled
    assert "heat_warning" not in disabled.suggested_opportunities, disabled

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            add_media(db, 1, "community_safety.jpg")
            save_intelligence(db, 1)

            from services.communications_director import CommunicationsDirector

            director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 10, 8))
            )
            brief = director.todays_brief()

            assert brief["context_snapshot"]["active_themes"], brief
            assert brief["recommendations"], brief
            assert not hasattr(director, "vision")
            assert not hasattr(director, "ai")

        finally:
            os.chdir(original)

    print("context_provider smoke passed")


if __name__ == "__main__":
    main()
