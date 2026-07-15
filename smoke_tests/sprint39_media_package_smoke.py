import os
import inspect
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.post = lambda *args, **kwargs: (_ for _ in ()).throw(
        RuntimeError("requests unavailable in smoke test")
    )
    requests_stub.get = requests_stub.post
    sys.modules["requests"] = requests_stub

from database.db_manager import DatabaseManager
from gui.package_media_panel import PackageMediaPanel
from services.communication_package_service import CommunicationPackageService
from services.content_generation_service import ContentGenerationService
from services.media_package_service import MediaPackageService
from services.time_service import TimeService
from smoke_tests.communications_officer_smoke import (
    add_media,
    save_analysis,
    save_fire,
    save_intelligence
)


def set_media_metadata(db, media_id, width, height, duration=0, orientation="landscape"):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE media
        SET width=?,
            height=?,
            duration_seconds=?,
            orientation=?,
            capture_time=?,
            first_seen_at=?
        WHERE id=?
        """,
        (
            width,
            height,
            duration,
            orientation,
            TimeService.utc_now_iso(),
            TimeService.utc_now_iso(),
            media_id
        )
    )
    conn.commit()
    conn.close()


def seed(db):

    rows = (
        (1, "ladder_training_hero.jpg", "image", "approved_real", "approved", 96, 3600, 2400, 0, "landscape"),
        (2, "ladder_training_corrected.jpg", "image", "corrected_real", "corrected", 92, 2400, 3600, 0, "portrait"),
        (3, "ladder_training_support.jpg", "image", "approved_real", "approved", 84, 1800, 1200, 0, "landscape"),
        (4, "ladder_training_video.mp4", "video", "approved_real", "approved", 88, 1920, 1080, 18, "landscape"),
        (5, "ladder_training_unreviewed.jpg", "image", "unreviewed_real", "review_required", 99, 4000, 2600, 0, "landscape"),
        (6, "ladder_training_rejected.jpg", "image", "rejected_real", "rejected", 100, 4000, 2600, 0, "landscape"),
        (7, "ladder_training_failed.jpg", "image", "failed", "failed", 100, 4000, 2600, 0, "landscape"),
        (8, "ladder_training_mock.jpg", "image", "mock", "mock", 100, 4000, 2600, 0, "landscape"),
        (9, "engine_apparatus_alt.jpg", "image", "approved_real", "approved", 78, 2200, 1400, 0, "landscape"),
    )

    for media_id, filename, media_type, trust, review, score, width, height, duration, orientation in rows:
        add_media(db, media_id, filename, media_type=media_type)
        save_analysis(db, media_id, trust, review, failure_reason="provider timeout" if trust == "failed" else "")

        if trust == "mock":
            db.save_ai_analysis(
                media_id,
                {
                    "description": "MOCK TEST ANALYSIS",
                    "scene_type": "training",
                    "activity": "ladder training",
                    "people_count": 1,
                    "keywords": ["training", "ladder"],
                    "overall_score": score,
                    "provider": "mock",
                    "model": "mock",
                    "trust_state": "mock",
                    "review_status": "mock",
                    "last_analyzed": TimeService.utc_now_iso()
                }
            )

        save_intelligence(
            db,
            media_id,
            {
                "normalized_scene": "training",
                "incident_type": "training",
                "primary_activity": "ladder_operations",
                "content_tags": ["training", "ladder_operations", "recruitment"],
                "content_themes": ["training", "technical_education"],
                "recommended_uses": ["training_tuesday", "recruitment"],
                "search_text": "training ladder operations recruitment firefighter",
                "communications_score": score,
                "storytelling_score": max(60, score - 5),
                "recruitment_value_score": max(55, score - 4),
                "educational_value_score": max(55, score - 3),
                "platform_suitability": {
                    "facebook": score,
                    "instagram": score - 4,
                    "linkedin": score - 12,
                    "website": score - 8,
                    "news_release": 52,
                    "newsletter": score - 10
                }
            }
        )
        save_fire(db, media_id)
        set_media_metadata(db, media_id, width, height, duration, orientation)

    db.save_media_usage(
        {
            "media_id": 3,
            "post_id": 1,
            "platform": "facebook",
            "used_at": TimeService.utc_now_iso(),
            "campaign": "Training"
        }
    )


def recommendation():

    return {
        "recommendation_id": "sprint39-training",
        "title": "Training Tuesday Ladder Operations",
        "headline": "Training Tuesday Ladder Operations",
        "summary": "Ladder training has strong reviewed visual evidence.",
        "topic": "ladder_operations",
        "category": "Training",
        "editorial_angle": "Training Highlight",
        "priority_score": 91,
        "confidence_score": 88,
        "best_asset_ids": [5, 1, 2, 6, 8],
        "supporting_asset_ids": [3, 4, 7, 9],
        "supporting_topics": ["Ladder Operations", "Training", "Recruitment"],
        "supporting_programs": ["Training Tuesday"],
        "recommended_platforms": [
            "Facebook",
            "Instagram",
            "LinkedIn",
            "Website",
            "News Release",
            "Newsletter"
        ],
        "recommended_audiences": ["Morden residents", "Prospective firefighters"],
        "story_strength": {"overall": 90},
        "positive_factors": ["Reviewed ladder operations media", "Strong training value"],
        "negative_factors": [],
        "confidence_limitations": []
    }


def all_package_media(package):

    media = package.get("media_package", {})
    values = []
    for key in ("primary_photo", "primary_video"):
        if media.get(key):
            values.append(media[key])
    for key in ("gallery_photos", "gallery_videos", "supporting_photos", "supporting_videos"):
        values.extend(media.get(key) or [])
    return values


def assert_media_package(package):

    media = package["media_package"]
    assert media["primary_photo"], media
    assert media["primary_video"], media
    assert media["media_count"] >= 3, media
    assert media["primary_photo"]["media_id"] in (1, 2), media
    assert media["primary_photo"]["trust_state"] in ("approved_real", "corrected_real"), media
    assert media["primary_video"]["media_id"] == 4, media
    assert media["platform_media_guidance"], media
    assert media["reasons"], media
    assert media["diversity_reasoning"], media
    assert media["version"] == MediaPackageService.PACKAGE_VERSION, media

    ids = {item["media_id"] for item in all_package_media(package)}
    assert 5 not in ids, "unreviewed should not beat reviewed alternatives"
    assert 6 not in ids, "rejected analysis must be excluded"
    assert 7 not in ids, "failed analysis must be excluded"
    assert 8 not in ids, "mock analysis must be excluded"
    assert media["recent_use_risk"] >= 0, media
    assert media["duplicate_scene_risk"] >= 0, media


def assert_visual_hooks():

    source = inspect.getsource(PackageMediaPanel)
    assert "thumbnail_service.load_thumbnail" in source, "background thumbnail loading hook missing"
    assert "Loading thumbnail" in source, "placeholder state missing"
    assert "No Preview" in source, "corrupt/missing thumbnail state missing"
    assert "ImageDimensions.fit_size" in source, "aspect-ratio fit helper missing"
    assert "MAX_SUPPORTING = 8" in source, "bounded thumbnail count missing"
    assert "CTkImage" in source, "thumbnail display hook missing"
    assert "subprocess.Popen" in source, "reveal in file explorer hook missing"


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            assert_visual_hooks()
            db = DatabaseManager()
            seed(db)
            package_service = CommunicationPackageService(database=db)
            package = package_service.generate_package(
                recommendation(),
                package_type="Facebook"
            )
            assert_media_package(package)

            history = db.communication_package_history(
                package_id=package["media_package"]["package_id"]
            )
            assert history, "package history should be append-only"

            alternatives = package_service.alternatives_for_package(
                package,
                media_type="image",
                limit=10
            )
            assert alternatives, "bounded alternatives should be available"

            replacement = alternatives[0]
            replaced = package_service.replace_package_asset(
                package,
                replacement,
                "primary_photo",
                reason="Smoke test replacement"
            )
            assert replaced["media_package"]["replacement_history"], replaced
            actions = db.communication_package_asset_actions(
                replaced["media_package"]["package_id"]
            )
            assert actions, "replacement action should be persisted"
            regenerated = package_service.generate_package(
                recommendation(),
                package_type="Facebook"
            )
            assert (
                regenerated["media_package"]["primary_photo"]["media_id"]
                == replacement["media_id"]
            ), regenerated["media_package"]

            primary_id = replaced["media_package"]["primary_photo"]["media_id"]
            excluded = package_service.exclude_package_asset(
                replaced,
                primary_id,
                reason="Smoke test unsuitable asset"
            )
            assert primary_id in excluded["media_package"]["excluded_asset_ids"], excluded
            assert db.get_ai_analysis(primary_id), "asset exclusion must not delete analysis"

            generated = ContentGenerationService(database=db).generate_from_package(
                package
            )
            for platform in (
                "facebook",
                "instagram",
                "linkedin",
                "website",
                "news_release",
                "newsletter"
            ):
                output = generated[platform]
                assert output["media_guidance"]["primary_media_id"], output
                assert output["media_guidance"]["internal_only"] is True, output
                copied = generated["copy_buttons"][platform]
                assert "Internal media guidance" not in copied, copied
                assert package["media_package"]["primary_photo"]["filename"] not in copied, copied

        finally:
            os.chdir(original)

    print("sprint39 media package smoke passed")


if __name__ == "__main__":
    main()
