import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.content_director_retrieval_service import ContentDirectorRetrievalService
from services.media_topic_compatibility_service import MediaTopicCompatibilityService
from smoke_tests.communications_officer_smoke import save_analysis, save_intelligence
from smoke_tests.sprint44_operational_activity_smoke import add_media, save_filesystem


def _seed(db):
    add_media(
        db,
        1,
        "daycare_spraydown.jpg",
        path="library/2026/Public Education/Daycare Spraydown/daycare_spraydown.jpg",
    )
    save_analysis(db, 1, "approved_real", "approved")
    save_intelligence(
        db,
        1,
        {
            "normalized_scene": "daycare spray down",
            "incident_type": "public education",
            "primary_activity": "daycare spray down",
            "content_tags": ["daycare", "spray down", "children"],
            "recommended_uses": ["community event", "public education"],
            "search_text": "daycare spray down children community visit",
            "communications_score": 88,
        },
    )
    save_filesystem(
        db,
        1,
        root_category="Public Education",
        subcategory="Daycare Spraydown",
        public_education_program="Daycare Visit",
        community_event="Daycare Spraydown",
        normalized_tags=["daycare", "spray down", "children"],
    )

    add_media(
        db,
        2,
        "fireworks_safety.jpg",
        path="library/2026/Public Education/Fireworks/fireworks_safety.jpg",
    )
    save_analysis(db, 2, "approved_real", "approved")
    save_intelligence(
        db,
        2,
        {
            "normalized_scene": "fireworks safety graphic",
            "incident_type": "public education",
            "primary_activity": "fireworks safety",
            "content_tags": ["fireworks", "public safety", "Canada Day"],
            "recommended_uses": ["fireworks safety"],
            "search_text": "fireworks safety Canada Day local rules",
            "communications_score": 84,
        },
    )
    save_filesystem(
        db,
        2,
        root_category="Public Education",
        subcategory="Fireworks Safety",
        campaign="Fireworks Safety",
        normalized_tags=["fireworks", "fireworks safety", "Canada Day"],
    )

    add_media(
        db,
        3,
        "smoke_alarm_check.jpg",
        path="library/2026/Fire Prevention/Smoke Alarms/smoke_alarm_check.jpg",
    )
    save_analysis(db, 3, "approved_real", "approved")
    save_intelligence(
        db,
        3,
        {
            "normalized_scene": "smoke alarm public education",
            "incident_type": "public education",
            "primary_activity": "smoke alarm reminder",
            "content_tags": ["smoke alarm", "fire prevention", "home safety"],
            "recommended_uses": ["fire prevention", "public education"],
            "search_text": "smoke alarm test replace escape planning",
            "communications_score": 86,
        },
    )
    save_filesystem(
        db,
        3,
        root_category="Fire Prevention",
        subcategory="Smoke Alarms",
        campaign="Fire Prevention",
        public_education_program="Smoke Alarms",
        normalized_tags=["smoke alarm", "fire prevention", "home fire safety"],
    )

    add_media(
        db,
        4,
        "wildfire_value_protection.jpg",
        path="library/2026/Wildfire/Value Protection/wildfire_value_protection.jpg",
    )
    save_analysis(db, 4, "approved_real", "approved")
    save_intelligence(
        db,
        4,
        {
            "normalized_scene": "wildfire value protection",
            "incident_type": "wildland",
            "primary_activity": "value protection",
            "content_tags": ["wildfire", "grass fire", "value protection"],
            "recommended_uses": ["wildfire prevention"],
            "search_text": "wildfire grass fire value protection",
            "communications_score": 92,
        },
    )
    save_filesystem(
        db,
        4,
        root_category="Wildfire",
        subcategory="Value Protection",
        incident_type="Wildfire",
        normalized_tags=["wildfire", "grass fire", "value protection"],
    )


def _assert_ready(package, expected_filename):
    assert package["package_status"] == "ready", package
    assert package["quality_gate"]["passed"], package
    assert package["options"], package
    option = package["options"][0]
    assert option["state"] == "ready", option
    assert option["media_package"]["verified_media_ids"], option
    captions = package["facebook_caption"] + "\n" + package["instagram_caption"]
    assert "No verified media available" not in captions, package
    assert "#MordenFireRescue" not in captions, package
    assert option["caption_quality"]["emoji_count"] > 0, option
    assert option["hashtags"][-1] == "#MordenMB", option
    matched = package["search_diagnostics"]["matched_media"]
    assert any(item["filename"] == expected_filename for item in matched), matched
    assert not any("wildfire_value_protection" in item["filename"] for item in matched), matched


def main():
    original = Path.cwd()
    with TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            db = DatabaseManager()
            db.initialize()
            _seed(db)

            service = ContentDirectorRetrievalService(database=db)
            _assert_ready(service.build_prompt_package("daycare"), "daycare_spraydown.jpg")
            _assert_ready(service.build_prompt_package("fireworks"), "fireworks_safety.jpg")
            _assert_ready(service.build_prompt_package("smoke alarm reminder"), "smoke_alarm_check.jpg")

            blocked = service.build_prompt_package("rope rescue")
            assert blocked["package_status"] == "blocked_no_verified_media", blocked
            assert not blocked["quality_gate"]["passed"], blocked
            assert blocked["facebook_caption"] == "No verified media available for this topic.", blocked

            compatibility = MediaTopicCompatibilityService()
            result = compatibility.evaluate(
                ["daycare"],
                {
                    "filename": "wildfire_value_protection.jpg",
                    "trust_state": "approved_real",
                    "filesystem_intelligence": {
                        "subcategory": "Value Protection",
                        "incident_type": "Wildfire",
                        "normalized_tags": ["wildfire", "value protection"],
                    },
                },
            )
            assert not result["compatible"], result
        finally:
            os.chdir(original)

    print("sprint49_1 editorial integrity smoke passed")


if __name__ == "__main__":
    main()
