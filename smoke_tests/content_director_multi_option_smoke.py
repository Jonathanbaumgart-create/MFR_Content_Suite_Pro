import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.content_director_retrieval_service import ContentDirectorRetrievalService
from services.current_context_service import CurrentContextService, StaticContextProvider
from smoke_tests.content_director_retrieval_smoke import seed as seed_retrieval
from smoke_tests.seasonal_communications_smoke import save_post
from smoke_tests.sprint44_operational_activity_smoke import add_media, save_filesystem
from smoke_tests.communications_officer_smoke import save_analysis, save_intelligence


def seed_extra(db):

    add_media(
        db,
        10,
        "water_rescue_training.jpg",
        path="library/2026/Training/Water Rescue/water_rescue_training.jpg"
    )
    water_id = media_id_by_filename(db, "water_rescue_training.jpg")
    save_analysis(db, water_id, "approved_real", "approved")
    save_intelligence(
        db,
        water_id,
        {
            "normalized_scene": "water rescue training",
            "incident_type": "training",
            "primary_activity": "water rescue",
            "content_tags": ["water safety", "water rescue", "life jacket"],
            "content_themes": ["training", "public education"],
            "recommended_uses": ["water safety", "public education"],
            "search_text": "water rescue training water safety life jacket",
            "communications_score": 88
        }
    )
    save_filesystem(
        db,
        water_id,
        root_category="Training",
        subcategory="Water Rescue",
        training_type="Water Rescue",
        normalized_tags=["water safety", "water rescue", "life jacket"]
    )

    add_media(
        db,
        11,
        "recruit_training_team.jpg",
        path="library/2026/Recruitment/recruit_training_team.jpg"
    )
    recruit_id = media_id_by_filename(db, "recruit_training_team.jpg")
    save_analysis(db, recruit_id, "corrected_real", "corrected")
    save_intelligence(
        db,
        recruit_id,
        {
            "normalized_scene": "firefighter training",
            "incident_type": "training",
            "primary_activity": "team training",
            "content_tags": ["recruitment", "training", "teamwork"],
            "content_themes": ["recruitment", "community service"],
            "recommended_uses": ["recruitment", "training"],
            "search_text": "volunteer recruitment firefighter training teamwork",
            "communications_score": 91
        }
    )
    save_filesystem(
        db,
        recruit_id,
        root_category="Recruitment",
        subcategory="Training",
        campaign="Volunteer Recruitment",
        normalized_tags=["volunteer recruitment", "training", "teamwork"]
    )

    add_media(
        db,
        13,
        "smoke_advisory.jpg",
        path="library/2026/Public Safety/Smoke Advisory/smoke_advisory.jpg"
    )
    smoke_advisory_id = media_id_by_filename(db, "smoke_advisory.jpg")
    save_analysis(db, smoke_advisory_id, "approved_real", "approved")
    save_intelligence(
        db,
        smoke_advisory_id,
        {
            "normalized_scene": "wildfire smoke public safety",
            "incident_type": "public education",
            "primary_activity": "smoke advisory",
            "content_tags": ["smoke advisory", "air quality", "wildfire smoke"],
            "content_themes": ["public safety", "air quality"],
            "recommended_uses": ["smoke advisory", "public education"],
            "search_text": "smoke advisory air quality wildfire smoke official alert",
            "communications_score": 86
        }
    )
    save_filesystem(
        db,
        smoke_advisory_id,
        root_category="Public Safety",
        subcategory="Smoke Advisory",
        campaign="Smoke Advisory",
        normalized_tags=["smoke advisory", "air quality", "wildfire smoke"]
    )

    add_media(
        db,
        14,
        "smoke_alarm_check.jpg",
        path="library/2026/Fire Prevention/Smoke Alarms/smoke_alarm_check.jpg"
    )
    smoke_alarm_id = media_id_by_filename(db, "smoke_alarm_check.jpg")
    save_analysis(db, smoke_alarm_id, "approved_real", "approved")
    save_intelligence(
        db,
        smoke_alarm_id,
        {
            "normalized_scene": "smoke alarm public education",
            "incident_type": "public education",
            "primary_activity": "smoke alarm reminder",
            "content_tags": ["smoke alarm", "fire prevention", "home safety"],
            "content_themes": ["public education", "fire prevention"],
            "recommended_uses": ["smoke alarm", "fire prevention"],
            "search_text": "smoke alarm test replace escape planning",
            "communications_score": 87
        }
    )
    save_filesystem(
        db,
        smoke_alarm_id,
        root_category="Fire Prevention",
        subcategory="Smoke Alarms",
        campaign="Fire Prevention",
        public_education_program="Smoke Alarms",
        normalized_tags=["smoke alarm", "fire prevention", "home fire safety"]
    )

    add_media(
        db,
        12,
        "mock_recruitment.jpg",
        path="library/2026/Recruitment/mock_recruitment.jpg"
    )
    mock_id = media_id_by_filename(db, "mock_recruitment.jpg")
    save_analysis(db, mock_id, "mock", "approved")
    save_intelligence(
        db,
        mock_id,
        {
            "content_tags": ["recruitment"],
            "recommended_uses": ["recruitment"],
            "search_text": "mock recruitment",
            "communications_score": 100
        }
    )

    save_post(
        db,
        "Water Safety Wednesday",
        "Water Safety Wednesday reminder: life jackets and supervision matter near the water.",
        "2025-07-16T15:00:00+00:00",
        topics=["water safety"],
        programs=["Water Safety Wednesday"],
        campaigns=["Water Safety Wednesday"],
        source_id="multi-water-2025"
    )
    save_post(
        db,
        "Water Safety Wednesday",
        "Water Safety Wednesday: mark your spot and keep kids within arm's reach.",
        "2024-07-18T15:00:00+00:00",
        topics=["water safety"],
        programs=["Water Safety Wednesday"],
        campaigns=["Water Safety Wednesday"],
        source_id="multi-water-2024"
    )
    save_post(
        db,
        "Recruitment",
        "Volunteer firefighters train together and serve neighbours when the call comes in.",
        "2025-07-20T15:00:00+00:00",
        topics=["volunteer recruitment"],
        campaigns=["Volunteer Recruitment"],
        source_id="multi-recruit-2025"
    )
    save_post(
        db,
        "Smoke Alarms",
        "Smoke alarm reminder: test alarms and talk about two ways out.",
        "2025-10-07T15:00:00+00:00",
        topics=["smoke alarm", "fire prevention"],
        campaigns=["Fire Prevention Week"],
        source_id="multi-smokealarm-2025"
    )


def media_id_by_filename(db, filename):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM media WHERE filename=? ORDER BY id DESC LIMIT 1",
        (filename,)
    )
    row = cur.fetchone()
    conn.close()
    assert row, filename
    return row[0]


def assert_options(package, expected=3):

    options = package.get("options", [])
    assert len(options) >= expected, package
    assert len(options) <= 5, package
    families = {item.get("strategy_family") for item in options}
    formats = {item.get("recommended_format") for item in options}
    assert len(families) >= expected, options
    assert len(formats) >= 2, options
    captions = [item.get("facebook_caption", "") for item in options]
    assert len(set(captions)) == len(captions), captions
    for item in options:
        assert item.get("option_id"), item
        assert item.get("strategic_angle"), item
        assert item.get("facebook_caption"), item
        assert item.get("instagram_caption"), item
        assert len(item.get("hashtags", [])) <= 5, item
        assert item.get("year_over_year_evidence") is not None, item
        assert item.get("current_context_evidence"), item
        assert item.get("explainability_evidence"), item
        assert item.get("state") == "ready", item
        public = item.get("facebook_caption", "") + item.get("instagram_caption", "")
        banned = [
            "source_record_id",
            "media_id",
            "library/",
            "selected media is supported",
            "incident type:",
            "activity:"
        ]
        assert not any(term in public.lower() for term in banned), public


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)
        try:
            db = DatabaseManager()
            seed_retrieval(db)
            seed_extra(db)
            context = CurrentContextService(
                providers=[
                    StaticContextProvider(
                        {
                            "season": "summer",
                            "month": "July",
                            "weekday": "Friday",
                            "active_themes": ["water safety", "wildfire awareness"],
                            "alerts": [],
                            "weather": {},
                            "freshness": "fresh",
                            "data_freshness": "Local deterministic context."
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

            water = service.build_prompt_package("water safety", option_count=3)
            assert_options(water, expected=3)
            assert any(
                item["strategy_family"] == "historical_campaign_refresh"
                for item in water["options"]
            ), water
            assert water["around_this_time"]["matches"], water
            assert water["around_this_time"]["current_year_already_communicated"] is False, water

            maxed = service.build_prompt_package("water safety", option_count=8)
            assert len(maxed["options"]) <= 5, maxed

            recruitment = service.build_prompt_package("need a volunteer recruitment post")
            assert_options(recruitment, expected=3)
            selected_recruitment_media = [
                item.get("filename", "")
                for option in recruitment["options"]
                for item in option.get("media_package", {}).get("carousel_order", [])
            ]
            assert "mock_recruitment.jpg" not in selected_recruitment_media, recruitment
            assert {
                "recruitment_appeal",
                "training_story",
                "community_service_story"
            } & {item["strategy_family"] for item in recruitment["options"]}, recruitment

            smoke = service.build_prompt_package("smoke advisory")
            assert_options(smoke, expected=3)
            assert any(
                "official alert" in " ".join(item["validation_warnings"]).lower()
                or "official" in item["facebook_caption"].lower()
                for item in smoke["options"]
            ), smoke

            smoke_alarm = service.build_prompt_package("smoke alarm reminder")
            assert_options(smoke_alarm, expected=3)
            assert any(item["strategy_family"] == "checklist" for item in smoke_alarm["options"]), smoke_alarm

            one = service.build_prompt_package("water safety", option_count=1)
            assert len(one["options"]) == 1, one

            original_titles = [item["title"] for item in water["options"]]
            regenerated = service.regenerate_option(
                water,
                water["options"][0]["option_id"]
            )
            assert regenerated["status"] == "ready", regenerated
            assert len(regenerated["package"]["options"]) == len(water["options"]), regenerated
            assert regenerated["package"]["options"][1]["title"] == original_titles[1], regenerated

            draft = service.create_publication_draft(
                water,
                water["options"][0]["option_id"]
            )
            assert draft.get("source_option_id") == water["options"][0]["option_id"], draft
            assert draft.get("media_ids") is not None, draft

            from gui.content_director_page import ContentDirectorPage

            for name in (
                "render_prompt_options",
                "render_prompt_option_card",
                "package_for_option",
                "regenerate_prompt_option",
                "create_option_publication_draft"
            ):
                assert hasattr(ContentDirectorPage, name), name

        finally:
            os.chdir(original)

    print("content_director_multi_option_smoke passed")


if __name__ == "__main__":
    main()
