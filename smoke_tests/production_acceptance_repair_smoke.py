import os
import sys
import time
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communications_memory_service import CommunicationsMemoryService
from services.communications_officer_service import CommunicationsOfficerService
from services.content_director_retrieval_service import ContentDirectorRetrievalService
from services.media_topic_compatibility_service import MediaTopicCompatibilityService
from services.time_service import TimeService
from smoke_tests.communications_officer_smoke import save_analysis, save_intelligence
from smoke_tests.sprint44_operational_activity_smoke import add_media, save_filesystem


def seed(db):
    now = TimeService.utc_now()
    captured = (now - timedelta(hours=4)).isoformat(timespec="seconds")
    imported = (now - timedelta(hours=2)).isoformat(timespec="seconds")

    add_media(
        db,
        1,
        "recruit_training_team.jpg",
        first_seen_at=imported,
        capture_time=captured,
        path="library/2026/Recruitment/Training/recruit_training_team.jpg"
    )
    save_analysis(db, 1, "approved_real", "approved")
    save_intelligence(
        db,
        1,
        {
            "primary_activity": "firefighter recruitment training",
            "content_tags": ["recruitment", "firefighter training", "teamwork"],
            "content_themes": ["recruitment", "training"],
            "recommended_uses": ["recruitment"],
            "search_text": "recruitment firefighter training teamwork station orientation",
            "communications_score": 88
        }
    )
    save_filesystem(
        db,
        1,
        root_category="Recruitment",
        subcategory="Recruit Training",
        training_type="Recruit Class",
        normalized_tags=["recruitment", "recruit class", "firefighter training"],
        source_folders=["Recruitment", "Recruit Training"]
    )

    add_media(
        db,
        2,
        "daycare_spray_event.jpg",
        first_seen_at=imported,
        capture_time=captured,
        path="library/2026/Public Education/Daycare Spray/daycare_spray_event.jpg"
    )
    save_analysis(db, 2, "approved_real", "approved")
    save_intelligence(
        db,
        2,
        {
            "primary_activity": "daycare spray event",
            "content_tags": ["children", "water play", "public education", "firefighters"],
            "content_themes": ["community", "public education"],
            "recommended_uses": ["community engagement"],
            "search_text": "daycare children water spray firefighters public education",
            "communications_score": 96
        }
    )
    save_filesystem(
        db,
        2,
        root_category="Public Education",
        subcategory="Daycare Spray",
        community_event="Daycare Spray",
        normalized_tags=["daycare", "spraydown", "children"],
        source_folders=["Public Education", "Daycare Spray"]
    )

    add_media(
        db,
        3,
        "water_safety_folder.jpg",
        first_seen_at=imported,
        capture_time=captured,
        path="library/2026/Social Media/Water Safety/water_safety_folder.jpg"
    )
    save_analysis(db, 3, "approved_real", "approved")
    save_intelligence(
        db,
        3,
        {
            "primary_activity": "water safety education",
            "content_tags": ["water safety", "life jacket", "shoreline safety"],
            "content_themes": ["water safety"],
            "recommended_uses": ["water safety"],
            "search_text": "Water Safety Wednesday life jacket shoreline boating safety",
            "communications_score": 82
        }
    )
    save_filesystem(
        db,
        3,
        root_category="Social Media",
        subcategory="Water Safety",
        campaign="Water Safety Wednesday",
        normalized_tags=["water safety", "life jacket", "shoreline safety"],
        source_folders=["Social Media", "Water Safety"]
    )

    add_media(
        db,
        4,
        "lake_background_rescue.jpg",
        first_seen_at=imported,
        capture_time=captured,
        path="library/2026/Training/Low Angle/lake_background_rescue.jpg"
    )
    save_analysis(db, 4, "approved_real", "approved")
    save_intelligence(
        db,
        4,
        {
            "primary_activity": "low angle rescue",
            "content_tags": ["rescue training", "lake", "outdoor"],
            "content_themes": ["training"],
            "recommended_uses": ["training"],
            "search_text": "low angle rescue training lake visible in background",
            "communications_score": 90
        }
    )
    save_filesystem(
        db,
        4,
        root_category="Training",
        subcategory="Low Angle Rescue",
        training_type="Low Angle Rescue",
        normalized_tags=["low angle rescue", "training", "lake"],
        source_folders=["Training", "Low Angle Rescue"]
    )

    memory = CommunicationsMemoryService(db)
    memory.remember_post({
        "platform": "facebook",
        "post_date": "2024-07-04",
        "caption": "Water Safety Wednesday: wear a life jacket and stay close to your group near the water.",
        "campaign": "Water Safety Wednesday",
        "opportunity_type": "water safety",
        "media_ids": [3],
        "imported": True
    })
    memory.remember_post({
        "platform": "facebook",
        "post_date": "2025-09-01",
        "caption": "Volunteer recruitment is open for people who want to train, serve, and be part of the team.",
        "campaign": "Recruitment",
        "opportunity_type": "recruitment",
        "media_ids": [1],
        "imported": True
    })


def main():
    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed(db)

            officer = CommunicationsOfficerService(database=db)
            started = time.perf_counter()
            brief = officer.generate_fast(force=True)
            elapsed = time.perf_counter() - started
            assert elapsed < 4.0, officer.last_metrics
            assert brief["brief_stage"] == "partial", brief
            assert brief["recent_mfr_activity"], brief
            assert "editorial_recommendations" in brief["pending_stages"], brief

            service = ContentDirectorRetrievalService(database=db)
            recruitment = service.build_prompt_package("volunteer recruitment", limit=5)
            selected_recruitment = str(recruitment["media_package"]["carousel_order"])
            excluded_recruitment = str(recruitment["media_package"]["excluded_conflicts"])
            assert "recruit_training_team" in selected_recruitment, recruitment
            assert "daycare_spray_event" not in selected_recruitment, recruitment
            assert "daycare_spray_event" in excluded_recruitment, recruitment
            assert recruitment["historical_references"], recruitment
            assert "Matched topic evidence" not in recruitment["facebook_draft"]["copy_text"], recruitment
            assert "Tier A" not in recruitment["facebook_draft"]["copy_text"], recruitment
            assert "recruit_training_team.jpg" not in recruitment["facebook_draft"]["copy_text"], recruitment
            assert "Suggested media:" not in recruitment["facebook_draft"]["copy_text"], recruitment

            water = service.build_prompt_package("water safety", limit=5)
            selected_water = str(water["media_package"]["carousel_order"])
            excluded_water = str(water["media_package"]["excluded_conflicts"])
            assert "water_safety_folder" in selected_water, water
            assert "lake_background_rescue" not in selected_water, water
            assert "lake_background_rescue" in excluded_water, water
            assert water["historical_references"], water

            smoke = service.build_prompt_package("smoke advisory", limit=5)
            assert smoke["media_package"]["no_suitable_media"], smoke
            assert "official alert" in " ".join(smoke["validation_warnings"]).lower(), smoke

            compatibility = MediaTopicCompatibilityService()
            weak = compatibility.evaluate(
                ["water safety"],
                {
                    "media_id": 10,
                    "trust_state": "approved_real",
                    "review_status": "approved",
                    "content_tags": ["lake", "outdoor", "people"],
                    "primary_activity": "low angle rescue"
                },
                activity={}
            )
            assert not weak["compatible"], weak
            assert weak["evidence_tier"] == "C_or_none", weak

            from gui.content_director_page import ContentDirectorPage
            from gui.home_page import HomePage

            assert hasattr(ContentDirectorPage, "cancel_current_request")
            assert hasattr(ContentDirectorPage, "render_fast_brief_summary")
            assert hasattr(HomePage, "render_recent_mfr_activity")

        finally:
            os.chdir(original)

    print("production_acceptance_repair_smoke passed")


if __name__ == "__main__":
    main()
