import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.cache_invalidation_service import CacheInvalidationService
from services.communications_memory_service import CommunicationsMemoryService
from services.communications_officer_service import CommunicationsOfficerService
from services.current_context_service import (
    CurrentContextService,
    LocalCalendarContextProvider,
    StaticContextProvider
)
from services.human_feedback_service import HumanFeedbackService
from services.media_topic_compatibility_service import MediaTopicCompatibilityService
from services.operational_activity_service import OperationalActivityService
from services.time_service import TimeService
from smoke_tests.communications_officer_smoke import (
    save_analysis,
    save_fire,
    save_intelligence
)


def add_media(
    db,
    media_id,
    filename,
    media_type="image",
    first_seen_at=None,
    capture_time=None,
    path=None
):
    extension = ".mp4" if media_type == "video" else ".jpg"
    db.add_media({
        "filename": filename,
        "path": path or str(Path("library") / filename),
        "extension": extension,
        "type": media_type,
        "size": 100 + media_id,
        "sha256": f"sprint44-{media_id}",
        "first_seen_at": first_seen_at or TimeService.utc_now_iso(),
        "capture_time": capture_time or "",
        "capture_time_source": "exif" if capture_time else "",
        "duration_seconds": 12 if media_type == "video" else 0
    })


def save_filesystem(db, media_id, **values):
    db.save_filesystem_intelligence(
        media_id,
        {
            "relative_path": values.get("relative_path", ""),
            "folder_hierarchy": values.get("folder_hierarchy", []),
            "root_category": values.get("root_category", ""),
            "subcategory": values.get("subcategory", ""),
            "normalized_tags": values.get("normalized_tags", []),
            "apparatus_identifier": values.get("apparatus_identifier", ""),
            "incident_type": values.get("incident_type", ""),
            "training_type": values.get("training_type", ""),
            "public_education_program": values.get("public_education_program", ""),
            "campaign": values.get("campaign", ""),
            "community_event": values.get("community_event", ""),
            "season": values.get("season", ""),
            "filesystem_confidence": values.get("filesystem_confidence", 90),
            "matching_rule": "sprint44_smoke",
            "source_folders": values.get("source_folders", []),
            "conflict_state": "",
            "enrichment_version": "smoke"
        }
    )


def seed(db):
    now = TimeService.utc_now()
    recent_capture = (now - timedelta(hours=8)).isoformat(timespec="seconds")
    same_day = (now - timedelta(hours=6)).isoformat(timespec="seconds")
    old_capture = (now - timedelta(days=400)).isoformat(timespec="seconds")
    imported_today = (now - timedelta(hours=2)).isoformat(timespec="seconds")

    add_media(
        db,
        1,
        "fire_chief_day_hero.jpg",
        first_seen_at=imported_today,
        capture_time=recent_capture,
        path="library/2026/Fire Chief of the Day/fire_chief_day_hero.jpg"
    )
    save_analysis(db, 1, "approved_real", "approved")
    save_intelligence(
        db,
        1,
        {
            "normalized_scene": "public education",
            "incident_type": "public education",
            "primary_activity": "Fire Chief of the Day",
            "content_tags": ["fire chief of the day", "children", "public education"],
            "content_themes": ["community", "public education"],
            "recommended_uses": ["community education"],
            "search_text": "Fire Chief of the Day child public education station visit",
            "communications_score": 91
        }
    )
    save_fire(db, 1)
    save_filesystem(
        db,
        1,
        root_category="Programs",
        subcategory="Public Education",
        public_education_program="Fire Chief of the Day",
        normalized_tags=["fire chief of the day", "public education"],
        source_folders=["Fire Chief of the Day"]
    )

    add_media(
        db,
        2,
        "water_rescue_training.jpg",
        first_seen_at=imported_today,
        capture_time=same_day,
        path="library/2026/Training/Water Rescue/water_rescue_training.jpg"
    )
    save_analysis(db, 2, "corrected_real", "corrected")
    save_intelligence(
        db,
        2,
        {
            "normalized_scene": "training",
            "incident_type": "water rescue training",
            "primary_activity": "water rescue training",
            "equipment_tags": ["life jacket", "rescue rope"],
            "content_tags": ["water rescue", "life jacket", "training"],
            "content_themes": ["water safety", "training"],
            "recommended_uses": ["water safety", "training_tuesday"],
            "search_text": "water rescue training life jacket shoreline safety",
            "communications_score": 88
        }
    )
    save_fire(db, 2)
    save_filesystem(
        db,
        2,
        root_category="Training",
        subcategory="Water Rescue",
        training_type="Water Rescue",
        normalized_tags=["water rescue", "life jacket", "shoreline"],
        source_folders=["Training", "Water Rescue"]
    )

    add_media(
        db,
        3,
        "old_open_house_imported_today.jpg",
        first_seen_at=imported_today,
        capture_time=old_capture,
        path="library/archive/2019/Open House/old_open_house_imported_today.jpg"
    )
    save_analysis(db, 3, "approved_real", "approved")
    save_intelligence(
        db,
        3,
        {
            "primary_activity": "community open house",
            "content_tags": ["community", "open house"],
            "recommended_uses": ["community engagement"],
            "search_text": "older open house archive community",
            "communications_score": 72
        }
    )
    save_filesystem(
        db,
        3,
        root_category="Community",
        community_event="Open House",
        normalized_tags=["community", "open house"],
        source_folders=["archive", "Open House"]
    )

    add_media(
        db,
        4,
        "same_day_extrication.jpg",
        first_seen_at=imported_today,
        capture_time=same_day,
        path="library/2026/Training/Extrication/same_day_extrication.jpg"
    )
    save_analysis(db, 4, "approved_real", "approved")
    save_intelligence(
        db,
        4,
        {
            "incident_type": "vehicle extrication",
            "primary_activity": "vehicle extrication",
            "equipment_tags": ["extrication tools"],
            "content_tags": ["extrication", "training"],
            "recommended_uses": ["training_tuesday"],
            "search_text": "vehicle extrication tools training",
            "communications_score": 84
        }
    )
    save_filesystem(
        db,
        4,
        root_category="Training",
        subcategory="Extrication",
        training_type="Vehicle Extrication",
        normalized_tags=["extrication", "training"],
        source_folders=["Training", "Extrication"]
    )

    add_media(db, 5, "rejected_water.jpg", first_seen_at=imported_today, capture_time=same_day)
    save_analysis(db, 5, "rejected_real", "rejected")
    save_intelligence(
        db,
        5,
        {
            "content_tags": ["water rescue"],
            "recommended_uses": ["water safety"],
            "search_text": "water rescue rejected",
            "communications_score": 99
        }
    )

    add_media(db, 6, "mock_water.jpg", first_seen_at=imported_today, capture_time=same_day)
    save_analysis(db, 6, "mock", "review_required")
    save_intelligence(
        db,
        6,
        {
            "content_tags": ["water rescue"],
            "recommended_uses": ["water safety"],
            "search_text": "water rescue mock",
            "communications_score": 99
        }
    )

    feedback = HumanFeedbackService(database=db)
    feedback.save_correction(
        2,
        "operational_context",
        "water rescue training",
        notes="Corrected by smoke test."
    )

    memory = CommunicationsMemoryService(db)
    memory.remember_post({
        "platform": "facebook",
        "post_date": (datetime.now(timezone.utc) - timedelta(days=12)).date().isoformat(),
        "caption": "Water rescue training helps our crews stay ready for shoreline emergencies.",
        "campaign": "Water Safety",
        "opportunity_type": "water safety",
        "media_ids": [2],
        "imported": True
    })
    memory.remember_post({
        "platform": "facebook",
        "post_date": (datetime.now(timezone.utc) - timedelta(days=75)).date().isoformat(),
        "caption": "Fire Chief of the Day brought smiles and public education to the hall.",
        "campaign": "Public Education",
        "opportunity_type": "fire chief of the day",
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

            summer = datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc)
            context_service = CurrentContextService(
                providers=[
                    LocalCalendarContextProvider(),
                    StaticContextProvider(
                        {
                            "alerts": [
                                {
                                    "type": "heat",
                                    "summary": "Fixture heat alert",
                                    "source": "smoke_fixture"
                                }
                            ],
                            "freshness": "fresh"
                        },
                        is_enabled=True,
                        provider_name="fixture_weather"
                    )
                ]
            )
            current = context_service.current_context(now=summer, force=True)
            assert current["season"] == "summer", current
            assert "water safety" in [item.lower() for item in current["active_themes"]], current
            assert current["alerts"], current

            offline = CurrentContextService(
                providers=[StaticContextProvider(is_enabled=False)]
            ).current_context(now=summer, force=True)
            assert offline["freshness"] == "unavailable", offline
            assert "unavailable" in offline["data_freshness"].lower(), offline

            service = OperationalActivityService(
                database=db,
                memory_service=CommunicationsMemoryService(db),
                context_service=context_service
            )
            clusters = service.clusters_for_window(days=30, limit=20, now=summer)
            titles = [item["title"] for item in clusters]
            assert "Fire Chief of the Day" in titles, titles
            assert "Water Rescue Training" in titles, titles
            assert "Vehicle Extrication" in titles, titles
            assert len([item for item in clusters if item["title"] in ("Water Rescue Training", "Vehicle Extrication")]) == 2, clusters

            old = next(item for item in clusters if item["title"] == "Community Open House")
            assert old["recency_label"] == "recently_imported_old_media", old

            water = service.media_for_topic("water safety", clusters=clusters, limit=10)
            accepted_names = " ".join(item["filename"] for item in water["accepted"])
            excluded_names = " ".join(item["filename"] for item in water["excluded"])
            assert "water_rescue_training" in accepted_names, water
            assert "fire_chief_day_hero" not in accepted_names, water
            assert "fire_chief_day_hero" in excluded_names, water
            assert "rejected_water" not in accepted_names, water
            assert "mock_water" not in accepted_names, water

            no_media = service.media_for_topic("hazmat", clusters=clusters, limit=5)
            assert no_media["no_suitable_media"] is True, no_media

            opportunities = service.communication_opportunities(
                limit=3,
                clusters=clusters,
                current_context=current
            )
            assert opportunities, opportunities
            assert opportunities[0]["source_signals"], opportunities[0]
            assert opportunities[0]["positive_factors"], opportunities[0]
            assert any(item.get("historical_matches") for item in opportunities), opportunities

            gaps = service.communications_gaps(clusters=clusters, current_context=current)
            assert isinstance(gaps, list), gaps

            compatibility = MediaTopicCompatibilityService()
            fire_chief = next(item for item in clusters if item["title"] == "Fire Chief of the Day")
            result = compatibility.evaluate(
                "water safety",
                fire_chief["top_media_candidates"][0],
                activity=fire_chief
            )
            assert result["compatible"] is False and result["hard_reject"], result

            officer = CommunicationsOfficerService(database=db)
            officer.context_service = context_service
            officer.operational = service
            brief = officer.generate(now=summer, force=True)
            assert brief["current_context"]["season"] == "summer", brief
            assert brief["recent_mfr_activity"], brief
            assert brief["best_communication_opportunities"], brief
            assert brief["communications_gaps"] is not None, brief
            assert brief["risks_and_limitations"], brief
            assert "Benchmark" not in " ".join(brief["source_signals"]), brief
            assert "Learning" not in " ".join(brief["source_signals"]), brief
            assert officer.last_metrics["profile"]["operational_activity_seconds"] >= 0, officer.last_metrics

            CacheInvalidationService.invalidate(
                reason="sprint44_smoke",
                scopes=["current_context"]
            )
            assert CacheInvalidationService.changed_since(
                0,
                scopes=["current_context"]
            )

            from gui.home_page import HomePage

            assert hasattr(HomePage, "render_recent_mfr_activity")
            assert hasattr(HomePage, "render_best_operational_opportunities")
            assert hasattr(HomePage, "render_risks_and_limitations")

        finally:
            os.chdir(original)

    print("sprint44 operational activity smoke passed")


if __name__ == "__main__":
    main()
