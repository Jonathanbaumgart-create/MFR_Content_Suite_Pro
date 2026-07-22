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
from services.daily_communications_officer_service import DailyCommunicationsOfficerService
from services.media_topic_compatibility_service import MediaTopicCompatibilityService
from services.recommendation_freshness_service import RecommendationFreshnessService
from services.time_service import TimeService
from smoke_tests.communications_officer_smoke import save_analysis, save_intelligence
from smoke_tests.sprint44_operational_activity_smoke import add_media, save_filesystem


def seed_media(db):
    now = TimeService.utc_now_iso()
    records = [
        (
            1,
            "smoke_alarm_campaign_graphic.jpg",
            "library/Campaigns/Smoke Alarms/smoke_alarm_campaign_graphic.jpg",
            "approved_real",
            "approved",
            {
                "normalized_scene": "educational graphic",
                "incident_type": "home fire safety",
                "primary_activity": "smoke alarm testing",
                "content_tags": ["smoke alarm", "smoke detector", "home fire safety"],
                "content_themes": ["fire prevention"],
                "recommended_uses": ["smoke alarm", "public education"],
                "search_text": "smoke alarm test button battery replacement home fire safety graphic",
                "communications_score": 88
            },
            {
                "root_category": "Campaigns",
                "subcategory": "Smoke Alarms",
                "campaign": "Smoke Alarm Reminder",
                "public_education_program": "Home Fire Safety",
                "normalized_tags": ["smoke alarm", "smoke detector", "campaign graphic"],
                "source_folders": ["Campaigns", "Smoke Alarms"]
            }
        ),
        (
            2,
            "structure_fire_response.jpg",
            "library/Incidents/Structure Fire/structure_fire_response.jpg",
            "corrected_real",
            "corrected",
            {
                "normalized_scene": "emergency response",
                "incident_type": "structure fire",
                "primary_activity": "fire attack",
                "content_tags": ["structure fire", "incident response", "apparatus"],
                "content_themes": ["serious incident", "public information"],
                "recommended_uses": ["incident update", "community update"],
                "search_text": "confirmed incident structure fire apparatus public safe response",
                "communications_score": 91
            },
            {
                "root_category": "Incidents",
                "subcategory": "Structure Fire",
                "incident_type": "Structure Fire",
                "normalized_tags": ["structure fire", "incident update", "emergency response"],
                "source_folders": ["Incidents", "Structure Fire"]
            }
        ),
        (
            3,
            "daycare_spraydown.jpg",
            "library/Public Education/Daycare/daycare_spraydown.jpg",
            "approved_real",
            "approved",
            {
                "normalized_scene": "community visit",
                "incident_type": "public education",
                "primary_activity": "daycare spray-down",
                "content_tags": ["daycare", "spray down", "children"],
                "content_themes": ["community visit"],
                "recommended_uses": ["community event"],
                "search_text": "daycare spray down hose line children firefighters",
                "communications_score": 86
            },
            {
                "root_category": "Public Education",
                "subcategory": "Daycare",
                "community_event": "Daycare Visit",
                "normalized_tags": ["daycare", "spray down", "children"],
                "source_folders": ["Public Education", "Daycare"]
            }
        ),
        (
            4,
            "recruit_training.jpg",
            "library/Training/Recruitment/recruit_training.jpg",
            "approved_real",
            "approved",
            {
                "normalized_scene": "training",
                "incident_type": "training",
                "primary_activity": "firefighter training",
                "content_tags": ["recruitment", "training", "firefighter"],
                "content_themes": ["recruitment"],
                "recommended_uses": ["recruitment", "training"],
                "search_text": "volunteer recruitment firefighter training teamwork equipment checks",
                "communications_score": 84
            },
            {
                "root_category": "Training",
                "subcategory": "Recruitment",
                "training_type": "Recruitment",
                "normalized_tags": ["recruitment", "training", "teamwork"],
                "source_folders": ["Training", "Recruitment"]
            }
        ),
        (
            5,
            "unrelated_water.jpg",
            "library/Water Safety/unrelated_water.jpg",
            "approved_real",
            "approved",
            {
                "normalized_scene": "water",
                "incident_type": "public education",
                "primary_activity": "water background",
                "content_tags": ["water"],
                "content_themes": ["summer"],
                "recommended_uses": ["water safety"],
                "search_text": "water outdoor summer",
                "communications_score": 70
            },
            {
                "root_category": "Programs",
                "subcategory": "Water",
                "normalized_tags": ["water"],
                "source_folders": ["Water"]
            }
        )
    ]

    for media_id, filename, path, trust, review, intelligence, filesystem in records:
        add_media(
            db,
            media_id,
            filename,
            first_seen_at=now,
            capture_time=now,
            path=path
        )
        save_analysis(db, media_id, trust, review)
        save_intelligence(db, media_id, intelligence)
        save_filesystem(db, media_id, **filesystem)


def context_service():
    return CurrentContextService(
        providers=[
            StaticContextProvider(
                {
                    "season": "summer",
                    "month": "July",
                    "weekday": "Tuesday",
                    "active_themes": ["water safety", "recruitment", "community engagement"],
                    "alerts": [],
                    "weather": {},
                    "freshness": "fresh",
                    "data_freshness": "fixture"
                },
                is_enabled=True,
                provider_name="fixture_context"
            )
        ]
    )


def main():
    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)
        try:
            db = DatabaseManager()
            seed_media(db)

            freshness = RecommendationFreshnessService(database=db)
            package = {
                "title": "Smoke Alarm Reminder",
                "communication_objective": "Educate",
                "narrative_angle": {"angle_name": "Working alarms buy time"},
                "narrative_focus": "test smoke alarms and replace expired units",
                "recommended_platforms": ["Facebook", "Instagram"],
                "media_package": {
                    "verified_media_ids": [1],
                    "primary_photo": {"media_id": 1, "filename": "smoke_alarm_campaign_graphic.jpg"},
                    "gallery_photos": []
                },
                "quality_gate": {"passed": True},
                "confidence": 85,
                "caption_quality": {"specificity_score": 92}
            }
            first = freshness.fingerprint(package)
            second = freshness.fingerprint(dict(package))
            assert first == second, (first, second)

            ranked = freshness.apply_to_packages(
                [dict(package)],
                page="Home",
                limit=1,
                record=True
            )
            assert ranked[0]["package_state"] == "Publish Ready", ranked
            assert ranked[0]["exposure_count"] == 0, ranked

            ranked_again = freshness.apply_to_packages(
                [dict(package)],
                page="Home",
                limit=1,
                record=False
            )
            assert ranked_again[0]["freshness"]["prior_exposure_count"] >= 1, ranked_again
            assert ranked_again[0]["freshness_penalty"] > 0, ranked_again

            different_angle = dict(package)
            different_angle["narrative_angle"] = {"angle_name": "Check the date on every alarm"}
            different_angle["narrative_focus"] = "check the date on each alarm"
            mixed = freshness.apply_to_packages(
                [dict(package), different_angle],
                page="Home",
                limit=2,
                record=False
            )
            assert mixed[0]["recommendation_fingerprint"] != first, mixed

            freshness.update_status(
                first,
                "Dismissed",
                page="Home",
                timestamp_field="dismissed_at"
            )
            dismissed = freshness.apply_to_packages(
                [dict(package)],
                page="Home",
                limit=1,
                record=False
            )[0]
            assert dismissed["freshness"]["dismissed"] is True, dismissed
            assert dismissed["freshness_penalty"] >= 80, dismissed

            retrieval = ContentDirectorRetrievalService(
                database=db,
                context_service=context_service()
            )
            smoke = retrieval.build_prompt_package(
                "smoke alarms",
                limit=5,
                option_count=3
            )
            assert smoke["search_result_status"] == "Publish Ready", smoke
            selected_filenames = [
                item.get("filename", "")
                for item in smoke["media_package"].get("carousel_order", [])
            ]
            assert "smoke_alarm_campaign_graphic.jpg" in selected_filenames, smoke
            assert "unrelated_water.jpg" not in selected_filenames, smoke
            rejected_names = [
                item.get("filename", "")
                for item in smoke["search_diagnostics"].get("rejected_media", [])
            ]
            assert "unrelated_water.jpg" in rejected_names, smoke
            assert smoke["recommendation_fingerprint"], smoke

            serious = retrieval.build_prompt_package(
                "serious incident",
                limit=5,
                option_count=3
            )
            assert serious["search_result_status"] == "Publish Ready", serious
            assert "Community Safety" not in serious["facebook_caption"], serious
            assert "structure_fire_response.jpg" in str(serious["media_package"]), serious

            empty = retrieval.build_prompt_package(
                "unknown parade mascot",
                limit=5,
                option_count=3
            )
            assert empty["search_diagnostics"]["search_result_status"] in (
                "Needs Media",
                "No Relevant Content",
                "No Matching Event",
                "Needs Media Review"
            ), empty
            assert empty["search_diagnostics"]["user_guidance"], empty

            compatibility = MediaTopicCompatibilityService()
            reusable = compatibility.evaluate(
                ["smoke alarm"],
                {
                    "filename": "smoke_alarm_campaign_graphic.jpg",
                    "trust_state": "approved_real",
                    "review_status": "approved",
                    "search_text": "smoke alarm test button home fire safety campaign graphic",
                    "content_tags": ["smoke alarm", "home fire safety"],
                    "filesystem_intelligence": {
                        "campaign": "Smoke Alarm Reminder",
                        "normalized_tags": ["smoke alarm", "campaign graphic"]
                    }
                }
            )
            assert reusable["compatible"], reusable

            unrelated = compatibility.evaluate(
                ["smoke alarm"],
                {
                    "filename": "unrelated_water.jpg",
                    "trust_state": "approved_real",
                    "review_status": "approved",
                    "search_text": "water outdoor summer",
                    "content_tags": ["water"]
                }
            )
            assert not unrelated["compatible"], unrelated

            daily = DailyCommunicationsOfficerService(
                database=db,
                context_service=context_service()
            )
            brief = daily.generate(force=True)
            packages = brief["daily_post_packages"]
            assert packages, brief
            fingerprints = [
                item.get("recommendation_fingerprint")
                for item in packages
            ]
            assert len(fingerprints) == len(set(fingerprints)), fingerprints
            objectives = {
                item.get("opportunity_type") or item.get("content_family")
                for item in packages
            }
            assert len(objectives) >= 2 or len(packages) < 3, packages

            director = retrieval.build_prompt_package(
                "recruitment",
                limit=5,
                option_count=3
            )
            home_order = [
                item.get("title")
                for item in packages
            ]
            director_order = [
                item.get("title")
                for item in director.get("options", [])
            ]
            assert home_order != director_order, (home_order, director_order)

        finally:
            os.chdir(original)

    print("sprint49_3 recommendation freshness smoke passed")


if __name__ == "__main__":
    main()
