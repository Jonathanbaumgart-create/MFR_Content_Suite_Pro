import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from database.db_manager import DatabaseManager
from media.thumbnail_cache import ThumbnailCache
from services.brain_service import BrainService
from services.content_director_service import ContentDirectorService
from services.media_priority_service import MediaPriorityService
from services.scan_service import ScanService
from services.time_service import TimeService
from services.video_metadata_service import VideoMetadataService


def create_image(path, size=(320, 180), color=(180, 40, 40)):

    Image.new(
        "RGB",
        size,
        color
    ).save(path)


def create_video(path, size=(160, 90), frames=24, fps=12):

    import cv2
    import numpy as np

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        size
    )

    if not writer.isOpened():
        raise RuntimeError("OpenCV could not create test video")

    for index in range(frames):
        frame = np.zeros(
            (size[1], size[0], 3),
            dtype=np.uint8
        )
        frame[:, :, 0] = min(255, 20 + index * 5)
        frame[:, :, 1] = 80
        frame[:, :, 2] = 180
        writer.write(frame)

    writer.release()


def set_media_dates(db, media_id, date_added, capture_time=""):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE media
        SET first_seen_at=?,
            date_added=?,
            capture_time=?,
            file_modified_at=?,
            file_created_at=?
        WHERE id=?
        """,
        (
            date_added,
            date_added,
            capture_time,
            date_added,
            date_added,
            media_id
        )
    )
    conn.commit()
    conn.close()


def media_id_by_name(db, filename):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM media WHERE filename=?",
        (filename,)
    )
    row = cur.fetchone()
    conn.close()

    assert row is not None, filename
    return row[0]


def media_dates_by_name(db, filename):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT first_seen_at, date_added, capture_time
        FROM media
        WHERE filename=?
        """,
        (filename,)
    )
    row = cur.fetchone()
    conn.close()

    assert row is not None, filename
    return row


class FakeVideoVisionService:

    def provider_key(self):

        return "fake_video"

    def model_name(self):

        return "fake-video-local"

    def provider_capabilities(self):

        return {
            "supports_images": True,
            "supports_video_frames": True,
            "supports_multi_image_prompt": False,
            "recommended_frame_count": 2,
            "timeout": 1,
            "maximum_resolution": 640,
            "production_approved": True,
            "cpu_safe": True,
            "gpu_dependent": False
        }


class FakeVideoAIService:

    def analyze_image(self, image_path, vision_provider, prompt_context=""):

        return {
            "description": "Training video frame with apparatus and firefighters visible.",
            "people_count": 2,
            "people": ["firefighters"],
            "apparatus": ["engine"],
            "equipment": ["training hose"],
            "activities": ["training"],
            "setting": "training ground",
            "visible_text": [],
            "uncertain_observations": [],
            "confidence": 0.72,
            "parse_status": "ok"
        }


def main():

    original_cwd = os.getcwd()

    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp_path = Path(tmp)
            os.chdir(tmp_path)

            media_dir = tmp_path / "media"
            media_dir.mkdir()
            create_image(media_dir / "today_photo.jpg", color=(180, 40, 40))
            create_image(media_dir / "old_photo.jpg", color=(40, 120, 180))
            create_image(media_dir / "older_capture_imported_today.jpg", color=(210, 210, 60))
            create_image(media_dir / "captured_today_old_import.jpg", color=(60, 180, 90))
            create_video(media_dir / "training_video.avi")
            (media_dir / "corrupt_video.avi").write_bytes(b"not a video")

            db = DatabaseManager()
            stats = ScanService(database=db).scan(str(media_dir))
            assert stats["inserted"] >= 4, stats

            today_photo = media_id_by_name(db, "today_photo.jpg")
            old_photo = media_id_by_name(db, "old_photo.jpg")
            older_capture_imported_today = media_id_by_name(
                db,
                "older_capture_imported_today.jpg"
            )
            captured_today = media_id_by_name(
                db,
                "captured_today_old_import.jpg"
            )
            video_id = media_id_by_name(db, "training_video.avi")
            corrupt_id = media_id_by_name(db, "corrupt_video.avi")

            now = TimeService.utc_now()
            older_capture = now - timedelta(days=90)
            set_media_dates(
                db,
                today_photo,
                now.isoformat(timespec="seconds")
            )
            set_media_dates(
                db,
                older_capture_imported_today,
                now.isoformat(timespec="seconds"),
                capture_time=older_capture.isoformat(timespec="seconds")
            )
            set_media_dates(
                db,
                old_photo,
                (now - timedelta(days=800)).isoformat(timespec="seconds")
            )
            set_media_dates(
                db,
                captured_today,
                (now - timedelta(days=800)).isoformat(timespec="seconds"),
                capture_time=now.isoformat(timespec="seconds")
            )
            set_media_dates(
                db,
                video_id,
                (now - timedelta(days=3)).isoformat(timespec="seconds")
            )
            set_media_dates(
                db,
                corrupt_id,
                (now - timedelta(days=3)).isoformat(timespec="seconds")
            )

            priority = MediaPriorityService(database=db, now=now)
            today = priority.candidates(
                preset="today",
                limit=10,
                include_photos=True,
                include_videos=True
            )
            assert any(item["id"] == today_photo for item in today), today
            assert any(
                item["id"] == older_capture_imported_today
                for item in today
            ), today
            assert all(item["id"] != old_photo for item in today), today
            assert all(item["id"] != captured_today for item in today), today

            captured = priority.candidates(
                preset="captured_today",
                limit=10,
                include_photos=True,
                include_videos=True,
                only_unanalyzed=True
            )
            assert any(item["id"] == captured_today for item in captured), captured
            assert all(
                item["id"] != older_capture_imported_today
                for item in captured
            ), captured
            assert db.media_count(filter_key="added_today") == 2
            assert db.media_count(filter_key="captured_today") == 1

            before_rescan = media_dates_by_name(
                db,
                "older_capture_imported_today.jpg"
            )
            rescan_stats = ScanService(database=db).scan(str(media_dir))
            assert rescan_stats["inserted"] == 0, rescan_stats
            after_rescan = media_dates_by_name(
                db,
                "older_capture_imported_today.jpg"
            )
            assert after_rescan[0] == before_rescan[0], after_rescan
            assert after_rescan[2] == before_rescan[2], after_rescan

            last_7 = priority.candidates(
                preset="last_7_days",
                limit=10,
                include_photos=True,
                include_videos=True,
                only_unanalyzed=True
            )
            assert last_7[0]["priority_score"] >= last_7[-1]["priority_score"], last_7
            assert any(item["id"] == video_id for item in last_7), last_7

            metadata = db.get_media_details(video_id)
            assert metadata["media_type"] == "video", metadata
            assert metadata["duration_seconds"] > 0, metadata
            assert metadata["width"] > 0 and metadata["height"] > 0, metadata

            video_service = VideoMetadataService()
            keyframes = video_service.keyframes(media_dir / "training_video.avi")
            assert 1 <= len(keyframes) <= 5, keyframes
            assert all("timestamp" in frame for frame in keyframes), keyframes

            cache = ThumbnailCache(cache_dir=tmp_path / "thumbs")
            thumb = cache.get_thumbnail(media_dir / "training_video.avi")
            assert thumb is not None and thumb.exists(), thumb
            assert cache.get_thumbnail(media_dir / "corrupt_video.avi") is None

            brain = BrainService(
                database=db,
                ai_service=FakeVideoAIService(),
                vision_service=FakeVideoVisionService()
            )
            analysis = brain._analyze_video_and_save(
                video_id,
                str(media_dir / "training_video.avi")
            )
            assert analysis["provider"] == "video_metadata", analysis
            assert analysis["trust_state"] == "unreviewed_real", analysis
            stored_video = db.get_video_intelligence(video_id)
            assert stored_video["analyzed_frame_count"] <= 5, stored_video
            assert stored_video["frame_timestamps"], stored_video

            candidates = db.content_director_candidates(limit=20)
            assert any(
                item["media_id"] == video_id and item["media_type"] == "video"
                for item in candidates
            ), candidates

            conn = db.connection()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE ai_analysis
                SET trust_state='rejected_real',
                    review_status='rejected'
                WHERE media_id=?
                """,
                (video_id,)
            )
            conn.commit()
            conn.close()

            recommendations = ContentDirectorService(database=db).recommend(
                prompt="training",
                limit=10
            )
            assert all(
                item["media_id"] != video_id
                for item in recommendations["recommendations"]
            ), recommendations

            preview = priority.preview("last_12_months")
            assert preview["videos"] >= 1, preview
            assert corrupt_id, "corrupt video should still be discoverable as media"
            os.chdir(original_cwd)

    finally:
        os.chdir(original_cwd)

    print("Sprint 29 recent media and video foundation smoke passed")


if __name__ == "__main__":
    main()
