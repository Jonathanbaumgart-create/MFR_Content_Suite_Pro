import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communications_memory_service import CommunicationsMemoryService
from services.content_director_retrieval_service import ContentDirectorRetrievalService
from services.current_context_service import CurrentContextService, StaticContextProvider
from services.media_topic_compatibility_service import MediaTopicCompatibilityService
from services.time_service import TimeService
from smoke_tests.communications_officer_smoke import save_analysis, save_intelligence
from smoke_tests.sprint44_operational_activity_smoke import add_media, save_filesystem


def seed(db):
    now = TimeService.utc_now()
    captured = (now - timedelta(hours=5)).isoformat(timespec="seconds")
    imported = (now - timedelta(hours=3)).isoformat(timespec="seconds")

    add_media(
        db,
        1,
        "wildfire_smoke_haze.jpg",
        first_seen_at=imported,
        capture_time=captured,
        path="library/2026/Public Safety/Wildfire Smoke/wildfire_smoke_haze.jpg"
    )
    save_analysis(db, 1, "corrected_real", "corrected")
    save_intelligence(
        db,
        1,
        {
            "normalized_scene": "outdoor haze",
            "incident_type": "wildfire smoke",
            "primary_activity": "air quality safety",
            "content_tags": ["smoke", "haze", "wildfire smoke", "air quality"],
            "content_themes": ["air quality", "community safety"],
            "recommended_uses": ["smoke advisory", "public education"],
            "search_text": "wildfire smoke haze air quality visibility outdoor safety",
            "communications_score": 90
        }
    )
    save_filesystem(
        db,
        1,
        root_category="Campaigns",
        subcategory="Air Quality",
        campaign="Smoke Advisory",
        normalized_tags=["wildfire smoke", "air quality", "haze"],
        source_folders=["Public Safety", "Wildfire Smoke"]
    )

    add_media(
        db,
        2,
        "fire_chief_day.jpg",
        first_seen_at=imported,
        capture_time=captured,
        path="library/2026/Fire Chief of the Day/fire_chief_day.jpg"
    )
    save_analysis(db, 2, "approved_real", "approved")
    save_intelligence(
        db,
        2,
        {
            "normalized_scene": "public education",
            "incident_type": "public education",
            "primary_activity": "Fire Chief of the Day",
            "content_tags": ["fire chief of the day", "children"],
            "content_themes": ["community"],
            "recommended_uses": ["public education"],
            "search_text": "Fire Chief of the Day public education child",
            "communications_score": 95
        }
    )
    save_filesystem(
        db,
        2,
        root_category="Programs",
        public_education_program="Fire Chief of the Day",
        normalized_tags=["fire chief of the day"],
        source_folders=["Fire Chief of the Day"]
    )

    add_media(
        db,
        3,
        "rejected_smoke.jpg",
        first_seen_at=imported,
        capture_time=captured
    )
    save_analysis(db, 3, "rejected_real", "rejected")
    save_intelligence(
        db,
        3,
        {
            "content_tags": ["smoke", "air quality"],
            "recommended_uses": ["smoke advisory"],
            "search_text": "smoke advisory rejected",
            "communications_score": 99
        }
    )

    memory = CommunicationsMemoryService(db)
    memory.remember_post({
        "platform": "facebook",
        "post_date": (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat(),
        "caption": "Wildfire smoke can affect air quality. Check current conditions and take breaks indoors when needed.",
        "campaign": "Smoke Advisory",
        "opportunity_type": "air quality",
        "media_ids": [1],
        "imported": True
    })
    memory.remember_post({
        "platform": "facebook",
        "post_date": (datetime.now(timezone.utc) - timedelta(days=3)).date().isoformat(),
        "caption": "Fire Chief of the Day was a great public education visit at the hall.",
        "campaign": "Fire Chief of the Day",
        "opportunity_type": "public education",
        "media_ids": [2],
        "imported": True
    })


def main():
    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed(db)
            context = CurrentContextService(
                providers=[
                    StaticContextProvider(
                        {
                            "season": "summer",
                            "month": "July",
                            "weekday": "Friday",
                            "active_themes": ["heat safety", "water safety", "wildfire awareness"],
                            "alerts": [],
                            "weather": {},
                            "freshness": "fresh",
                            "data_freshness": "Local context fresh; no official alert fixture."
                        },
                        is_enabled=True,
                        provider_name="fixture_context"
                    )
                ]
            )
            service = ContentDirectorRetrievalService(
                database=db,
                context_service=context
            )

            interpreted = service.interpret_query("smoke advisory")
            assert interpreted["primary_topic"] == "smoke_advisory", interpreted
            assert "air quality" in interpreted["secondary_topics"], interpreted
            assert interpreted["urgency"] == "elevated", interpreted

            air = service.interpret_query("air quality warning")
            assert air["primary_topic"] == "smoke_advisory", air

            package = service.build_prompt_package("smoke advisory", limit=5)
            assert package["interpreted_topic"]["primary_topic"] == "smoke_advisory", package
            assert package["historical_references"], package
            assert "Wildfire smoke" in package["historical_references"][0]["caption_excerpt"], package
            assert package["media_package"]["primary_image"]["filename"] == "wildfire_smoke_haze.jpg", package
            assert "fire_chief_day" not in str(package["media_package"]["primary_image"]), package
            selected_text = str(package["media_package"]["carousel_order"])
            assert "rejected_smoke" not in selected_text, package
            assert package["facebook_draft"]["copy_text"], package
            assert package["instagram_draft"]["copy_text"], package
            assert len(package["instagram_draft"]["hashtags"]) <= 5, package
            assert "source_record_id" not in package["facebook_draft"]["copy_text"], package
            assert "Matched topic evidence" not in package["facebook_draft"]["copy_text"], package
            assert "Tier A" not in package["facebook_draft"]["copy_text"], package
            assert "wildfire_smoke_haze.jpg" not in package["facebook_draft"]["copy_text"], package
            assert "Suggested media:" not in package["facebook_draft"]["copy_text"], package
            assert "No fresh official alert" in " ".join(package["validation_warnings"]), package
            assert "official alert" in package["facebook_draft"]["copy_text"].lower(), package

            compatibility = MediaTopicCompatibilityService()
            excluded = package["media_package"]["excluded_conflicts"]
            assert any("fire_chief_day" in item["filename"] for item in excluded), excluded
            assert any("rejected_smoke" in item["filename"] for item in excluded), excluded

            water = service.build_prompt_package("water safety", limit=5)
            assert water["media_package"]["no_suitable_media"] is True, water
            assert "No suitable current media" in " ".join(water["validation_warnings"]), water

            from gui.content_director_page import ContentDirectorPage

            assert hasattr(ContentDirectorPage, "render_prompt_progress")
            assert hasattr(ContentDirectorPage, "render_prompt_package")
            assert hasattr(ContentDirectorPage, "cancel_current_request")

        finally:
            os.chdir(original)

    print("content_director_retrieval_smoke passed")


if __name__ == "__main__":
    main()
