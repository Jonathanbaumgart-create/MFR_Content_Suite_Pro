from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.analysis_tier_service import AnalysisTierService
from services.daily_communications_officer_service import DailyCommunicationsOfficerService
from services.helmet_camera_service import HelmetCameraService


def create_image(path, color):

    Image.new("RGB", (640, 420), color).save(path)


def create_video(path):

    import cv2
    import numpy as np

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10,
        (320, 180)
    )

    for index in range(80):
        frame = np.zeros((180, 320, 3), dtype=np.uint8)
        frame[:, :, 1] = min(255, index * 3)
        frame[40:120, (index * 3) % 240:((index * 3) % 240) + 60, 2] = 255
        writer.write(frame)

    writer.release()


def add_media(db, path, index, media_type="image"):

    db.add_media({
        "filename": path.name,
        "path": str(path),
        "extension": path.suffix.lower(),
        "type": media_type,
        "size": path.stat().st_size,
        "sha256": f"sprint46-{index}",
        "width": 640 if media_type == "image" else 320,
        "height": 420 if media_type == "image" else 180,
        "duration_seconds": 0 if media_type == "image" else 8,
        "frame_rate": 0 if media_type == "image" else 10,
        "orientation": "landscape"
    })
    row = db.get_media_by_path(str(path))
    return row[0]


def save_reviewed_intelligence(db, media_id, title):

    db.save_ai_analysis(media_id, {
        "description": f"{title} Morden Fire Rescue training and community readiness.",
        "scene_type": "training",
        "activity": "training",
        "people_count": 2,
        "apparatus": ["engine"],
        "equipment": ["hose"],
        "keywords": ["training", "community", "recruitment"],
        "community_score": 80,
        "recruitment_score": 72,
        "education_score": 75,
        "technical_score": 70,
        "overall_score": 82,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": "test-real",
        "provider": "ollama",
        "review_status": "approved",
        "trust_state": "approved_real",
        "failure_reason": ""
    })
    db.save_media_intelligence(media_id, {
        "normalized_scene": "training",
        "incident_type": "training",
        "primary_activity": "training",
        "apparatus_tags": ["engine"],
        "equipment_tags": ["hose"],
        "ppe_tags": ["helmet"],
        "people_tags": ["firefighter"],
        "content_tags": ["training", "community", "recruitment"],
        "content_themes": ["readiness"],
        "recommended_uses": ["recruitment", "training"],
        "search_text": title,
        "intelligence_score": 82,
        "communications_score": 84,
        "source_model": "test-real"
    })


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            media_dir = Path(folder) / "Helmet Cam"
            media_dir.mkdir()
            photo_ids = []

            for index, color in enumerate(("red", "green", "blue"), start=1):
                path = media_dir / f"training_{index}.jpg"
                create_image(path, color)
                media_id = add_media(db, path, index, "image")
                save_reviewed_intelligence(db, media_id, f"Training {index}")
                photo_ids.append(media_id)

            video_path = media_dir / "helmet_training.mp4"
            create_video(video_path)
            video_id = add_media(db, video_path, 10, "video")

            tiers = AnalysisTierService(database=db)
            indexed = tiers.fast_index(photo_ids + [video_id])
            assert indexed["processed"] == 4, indexed
            assert indexed["provider_calls"] == 0, indexed
            assert db.media_analysis_tier(photo_ids[0], tiers.TIER_FAST_INDEX)

            screened = tiers.fast_screen(photo_ids, topic="training")
            assert screened["processed"] == 3, screened
            assert screened["provider_calls"] == 0, screened
            assert screened["items"][0]["score"] >= screened["items"][-1]["score"]

            daily = DailyCommunicationsOfficerService(database=db)
            brief = daily.generate(force=True)
            packages = brief.get("daily_post_packages", [])
            assert len(packages) == 3, packages
            for package in packages:
                assert package.get("facebook_caption"), package
                assert package.get("instagram_caption"), package
                assert len(package.get("instagram_hashtags") or []) <= 5, package
            assert brief.get("offline_ready") is True, brief

            helmet = HelmetCameraService(database=db)
            source = helmet.source_status(str(media_dir))
            assert source["available"] is True, source
            result = helmet.analyze_video(video_id, str(video_path))
            assert result["provider_calls"] == 0, result
            assert result["source_preserved"] is True, result
            assert result["permanent_frames_stored"] is False, result
            assert result["candidate_count"] > 0, result
            segment = result["top_segments"][0]
            assert 6 <= segment["duration_seconds"] <= 30, segment
            assert 0 <= segment["reel_score"] <= 100, segment
            reel = helmet.reel_package(video_id, segment)
            assert reel["review_required"] is True, reel
            assert reel["instagram_reel_caption"] == "", reel
            assert reel["semantic_status"] == "technical_candidate_semantic_pending", reel
            assert "semantic screen not completed" in reel["technical_candidate_status"].lower(), reel

        finally:
            os.chdir(original)

    print("sprint46_fast_officer_smoke passed")


if __name__ == "__main__":
    main()
