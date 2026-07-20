from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.daily_communications_officer_service import DailyCommunicationsOfficerService
from services.event_collection_service import EventCollectionService
from services.helmet_camera_service import HelmetCameraService
from services.media_package_service import MediaPackageService
from services.package_review_service import PackageReviewService
from services.time_service import TimeService
from smoke_tests.sprint46_fast_officer_smoke import add_media, create_image, create_video


def save_intelligence(db, media_id, title, capture_time, review="review_required", trust="unreviewed_real"):

    db.save_ai_analysis(media_id, {
        "description": f"{title} firefighters training teamwork.",
        "scene_type": "training",
        "activity": "low angle rope rescue training",
        "people_count": 3,
        "keywords": ["training", "rope rescue", "teamwork"],
        "provider": "ollama",
        "model": "real-test",
        "review_status": review,
        "trust_state": trust,
        "failure_reason": "",
        "overall_score": 82,
        "last_analyzed": TimeService.utc_now_iso()
    })
    db.save_media_intelligence(media_id, {
        "normalized_scene": "training",
        "incident_type": "training",
        "primary_activity": "low angle rope rescue training",
        "equipment_tags": ["rope", "helmet"],
        "content_tags": ["training", "rope rescue", "teamwork"],
        "content_themes": ["training readiness"],
        "recommended_uses": ["training", "recruitment"],
        "search_text": title,
        "intelligence_score": 84,
        "communications_score": 88,
        "source_model": "real-test"
    })
    conn = db.connection()
    conn.execute(
        "UPDATE media SET capture_time=?, width=640, height=420 WHERE id=?",
        (capture_time.isoformat(timespec="seconds"), media_id)
    )
    conn.commit()
    conn.close()


class FakeHelmetProvider:

    def __init__(self):

        self.calls = 0

    def provider_key(self):

        return "fake_helmet_semantic"

    def model_name(self):

        return "fake-local"

    def analyze(self, image_path, prompt_context=""):

        self.calls += 1
        assert Path(image_path).exists()
        return """
        {
          "visible_activity": "firefighters moving through a training evolution with helmet-camera perspective",
          "likely_context": "training",
          "action_sequence": "movement into the task, steady work, and a clear finish",
          "opening_hook": "A firefighter's-eye view of training.",
          "payoff": "shows practical readiness",
          "operational_interest": 78,
          "public_interest": 70,
          "firefighter_interest": 82,
          "behind_the_scenes_value": 76,
          "light_hearted_value": 20,
          "educational_value": 65,
          "risks": [],
          "confidence": 81,
          "recommended_tone": "Action-focused"
        }
        """


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            base_time = TimeService.to_local(TimeService.utc_now())
            event_dir = Path(folder) / "2026" / "Training" / "Low Angle Rope Rescue Training"
            event_dir.mkdir(parents=True)
            event_ids = []

            for index in range(4):
                path = event_dir / f"IMG_10{index}.jpg"
                create_image(path, ("red", "green", "blue", "yellow")[index])
                media_id = add_media(db, path, index + 1)
                save_intelligence(
                    db,
                    media_id,
                    "Low Angle Rope Rescue Training",
                    base_time + timedelta(minutes=index * 4),
                    review="approved" if index == 0 else "review_required",
                    trust="approved_real" if index == 0 else "unreviewed_real"
                )
                event_ids.append(media_id)

            graphic = event_dir / "11.png"
            create_image(graphic, "purple")
            graphic_id = add_media(db, graphic, 50)
            save_intelligence(
                db,
                graphic_id,
                "Low Angle Rope Rescue Training",
                base_time + timedelta(minutes=5)
            )

            old_dir = Path(folder) / "2024" / "Archive" / "Anniversary Graphics"
            old_dir.mkdir(parents=True)
            old = old_dir / "15 Year.jpg"
            create_image(old, "orange")
            old_id = add_media(db, old, 51)
            save_intelligence(
                db,
                old_id,
                "Anniversary graphic training",
                base_time - timedelta(days=500)
            )

            event_service = EventCollectionService(database=db)
            all_events = event_service.build_collections(limit=100)
            usable = event_service.top_collections(limit=10, source_limit=100)
            assert usable, all_events
            assert all(item["title"] != "Unknown" for item in usable), usable
            assert all(
                item["event_integrity"]["event_usability_state"] in ("coherent", "coherent_with_review")
                for item in usable
            ), usable

            rope = next(item for item in usable if item["title"] == "Low Angle Rope Rescue Training")
            assert rope["title_source"] == "exact_event_folder", rope
            assert rope["title_confidence"] >= 80, rope
            assert rope["event_integrity"]["coherence_score"] >= 65, rope
            ranked = event_service.rank_event_photos(rope, limit=8)
            ranked_ids = [item["media_id"] for item in ranked]
            assert graphic_id not in ranked_ids, ranked
            assert old_id not in ranked_ids, ranked
            assert set(ranked_ids).issubset(set(event_ids)), ranked_ids

            contact = event_service.contact_sheet_classification(rope)
            assert contact["provider_calls"] == 0, contact
            assert contact["temporary_contact_sheet_stored"] is False, contact

            package_service = MediaPackageService(database=db)
            package = package_service.build_package({
                "title": rope["title"],
                "topic": "rope rescue training",
                "best_asset_ids": event_ids[:2],
                "supporting_asset_ids": event_ids[2:] + [graphic_id, old_id],
                "allowed_media_ids": event_ids,
                "recommended_platforms": ["Facebook", "Instagram"],
                "strict_asset_ids": True
            }, persist=False)
            package_ids = [
                (package.get("primary_photo") or {}).get("media_id"),
                *[item.get("media_id") for item in package.get("gallery_photos", [])]
            ]
            assert graphic_id not in package_ids, package
            assert old_id not in package_ids, package

            daily = DailyCommunicationsOfficerService(database=db)
            brief = daily.generate(force=True)
            packages = brief.get("daily_post_packages") or []
            assert len(packages) == 3, packages
            assert all(pkg["title"] != "Unknown" for pkg in packages), packages
            assert packages[0]["quality_gate"]["passed"], packages[0]
            assert packages[0].get("event_diagnostics"), packages[0]
            media_backed = [pkg for pkg in packages if not pkg.get("text_graphic_first")]
            assert len(media_backed) >= 1, packages

            review = PackageReviewService(database=db)
            correction = review.record_decision(
                packages[0],
                "correct_event",
                metadata={"event_title": "Confirmed Low Angle Rope Rescue Training"}
            )
            assert correction["event_anchor_recorded"] is True, correction
            assert correction["raw_analysis_overwritten"] is False, correction

            video_path = Path(folder) / "helmet.mp4"
            create_video(video_path)
            video_id = add_media(db, video_path, 99, media_type="video")
            helmet = HelmetCameraService(database=db)
            analysis = helmet.analyze_video(video_id, str(video_path))
            segment = analysis["top_segments"][0]
            technical_package = helmet.reel_package(video_id, segment)
            assert technical_package["facebook_reel_caption"] == "", technical_package
            assert "semantic screen not completed" in technical_package["technical_candidate_status"].lower()

            provider = FakeHelmetProvider()
            screened = helmet.semantic_screen_segments(
                video_id,
                segments=[segment],
                limit=1,
                semantic_provider=provider
            )[0]
            assert provider.calls == 1, screened
            assert screened["semantic_status"] == "completed_provider", screened
            assert "firefighters moving" in screened["visible_activity_summary"], screened
            semantic_package = helmet.reel_package(video_id, screened)
            assert semantic_package["facebook_reel_caption"], semantic_package
            assert "firefighters moving" in semantic_package["facebook_reel_caption"], semantic_package

            cached = helmet.semantic_screen_segments(
                video_id,
                segments=[segment],
                limit=1,
                semantic_provider=provider
            )[0]
            assert provider.calls == 1, cached
            assert cached["semantic_cached"] is True, cached

        finally:
            os.chdir(original)

    print("sprint47_event_integrity_smoke passed")


if __name__ == "__main__":
    main()
