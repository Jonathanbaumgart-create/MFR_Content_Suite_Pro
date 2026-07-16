import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communication_package_service import CommunicationPackageService
from services.communications_officer_service import CommunicationsOfficerService
from services.decision_explainability_service import DecisionExplainabilityService
from services.media_package_service import MediaPackageService
from services.video_intelligence_service import VideoIntelligenceService
from services.video_metadata_service import VideoMetadataService


class FakeVision:

    def __init__(self, fail=False):
        self.fail = fail

    def provider_key(self):
        return "ollama"

    def model_name(self):
        return "qwen2.5vl:7b"


class FakeAI:

    def analyze_image(self, image_path, vision, prompt_context=""):
        if vision.fail:
            raise TimeoutError("provider timeout")

        assert "C:\\" not in prompt_context
        assert "\\" not in prompt_context

        return {
            "description": "A firefighter in helmet and turnout gear is handling hose during training.",
            "people_count": 1,
            "people": ["firefighter"],
            "apparatus": ["engine"],
            "equipment": ["hose", "helmet"],
            "activities": ["training", "hose evolution"],
            "setting": "training ground",
            "visible_text": [],
            "uncertain_observations": [],
            "confidence": 0.86,
            "parse_status": "valid_structured_response"
        }


def create_video(path, seconds=12, fps=4, size=(160, 90)):
    import cv2
    import numpy as np

    path = str(path)
    writer = cv2.VideoWriter(
        path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        size
    )
    assert writer.isOpened(), "Could not create synthetic video"

    colors = [
        (30, 30, 190),
        (30, 160, 30),
        (190, 120, 30),
        (220, 220, 220)
    ]
    total = int(seconds * fps)

    for index in range(total):
        color = colors[(index * len(colors)) // max(1, total)]
        frame = np.full((size[1], size[0], 3), color, dtype=np.uint8)
        cv2.putText(
            frame,
            f"{index // fps:02d}s",
            (10, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )
        writer.write(frame)

    writer.release()


def add_media(db, media_id, path, media_type="video"):
    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO media(
            id,
            filename,
            path,
            extension,
            media_type,
            filesize,
            sha256,
            date_added,
            first_seen_at
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            path.name,
            str(path),
            path.suffix.lower(),
            media_type,
            path.stat().st_size,
            f"hash-{media_id}",
            "2026-07-16T12:00:00+00:00",
            "2026-07-16T12:00:00+00:00"
        )
    )
    conn.commit()
    conn.close()


def save_real_analysis(db, media_id):
    db.save_ai_analysis(
        media_id,
        {
            "description": "Training video with firefighter hose handling.",
            "scene_type": "training",
            "activity": "training",
            "people_count": 1,
            "people": ["firefighter"],
            "apparatus": ["engine"],
            "equipment": ["hose", "helmet"],
            "activities": ["training"],
            "setting": "training ground",
            "indoor_outdoor": "outdoor",
            "keywords": ["training", "hose"],
            "community_score": 40,
            "recruitment_score": 70,
            "education_score": 75,
            "technical_score": 80,
            "overall_score": 82,
            "model": "qwen2.5vl:7b",
            "provider": "ollama",
            "retry_count": 0,
            "failure_reason": "",
            "raw_response": "{}",
            "parse_status": "valid_structured_response",
            "parse_warnings": [],
            "confidence": 0.86,
            "quality_state": "review_required",
            "trust_state": "approved_real",
            "review_status": "approved",
            "media_context": "video"
        }
    )


def save_media_intelligence(db, media_id):
    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": "training",
            "incident_type": "training",
            "primary_activity": "training",
            "apparatus_tags": ["engine"],
            "equipment_tags": ["hose", "helmet"],
            "ppe_tags": ["helmet"],
            "people_tags": ["firefighter"],
            "content_tags": ["training", "recruitment"],
            "content_themes": ["Training"],
            "recommended_uses": ["Training Tuesday", "Recruitment"],
            "search_text": "training firefighter hose engine recruitment",
            "intelligence_score": 82,
            "communications_score": 84,
            "source_model": "qwen2.5vl:7b"
        }
    )


def main():
    original = os.getcwd()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            media_dir = Path(folder) / "media"
            media_dir.mkdir()
            short_video = media_dir / "training_reel.mp4"
            long_video = media_dir / "long_training.mp4"
            create_video(short_video, seconds=12)
            create_video(long_video, seconds=48)
            add_media(db, 1, short_video)
            add_media(db, 2, long_video)
            save_real_analysis(db, 1)
            save_media_intelligence(db, 1)

            metadata_service = VideoMetadataService()
            short_metadata = metadata_service.inspect(short_video)
            long_metadata = metadata_service.inspect(long_video)
            service = VideoIntelligenceService(
                database=db,
                ai_service=FakeAI(),
                vision_service=FakeVision(),
                metadata_service=metadata_service,
                config={
                    "video_max_frames": 6,
                    "video_max_analyzed_frames": 3,
                    "video_sample_interval_seconds": 10
                }
            )

            short_times = service.sample_timestamps(short_metadata)
            long_times = service.sample_timestamps(long_metadata)
            assert len(short_times) == 6, short_times
            assert len(long_times) <= 6, long_times
            assert short_times[-1] <= short_metadata["duration"], short_times

            intelligence = service.generate_and_save(
                1,
                short_video,
                metadata=short_metadata
            )
            assert intelligence["reel_potential"] > 0, intelligence
            assert intelligence["story_category"] == "Training", intelligence
            assert intelligence["clip_recommendations"], intelligence
            assert intelligence["cover_recommendation"], intelligence
            assert intelligence["estimated_scene_count"] >= 1, intelligence
            assert len(intelligence["representative_frames"]) <= 6, intelligence
            assert intelligence["analyzed_frame_count"] <= 3, intelligence
            assert "C:\\" not in str(intelligence["raw_frame_outputs"])
            assert "\\" not in str(intelligence["raw_frame_outputs"])

            stored = db.get_video_intelligence(1)
            assert stored["reel_potential"] == intelligence["reel_potential"], stored
            assert stored["clip_recommendations"], stored

            failing = VideoIntelligenceService(
                database=db,
                ai_service=FakeAI(),
                vision_service=FakeVision(fail=True),
                metadata_service=metadata_service,
                config={"video_max_analyzed_frames": 2}
            )
            failed_result = failing.generate(
                2,
                long_video,
                metadata=long_metadata
            )
            assert failed_result["raw_frame_outputs"], failed_result
            assert any(
                item.get("failure") == "TimeoutError"
                for item in failed_result["raw_frame_outputs"]
            ), failed_result

            assert db.media_count("highest_reel_potential") == 1
            assert db.media_count("training_videos") == 1
            page = db.get_media_page(
                10,
                0,
                filter_key="highest_reel_potential",
                sort_key="filename_az"
            )
            assert page and page[0][0] == 1, page

            recommendation = {
                "recommendation_id": "video-training",
                "title": "Training Highlight",
                "summary": "Show a bounded training story.",
                "editorial_angle": "Training",
                "recommended_platforms": ["Facebook", "Instagram"],
                "best_asset_ids": [1],
                "supporting_asset_ids": []
            }
            media_package = MediaPackageService(database=db).build_package(
                recommendation,
                platforms=["Facebook", "Instagram"],
                persist=False
            )
            assert media_package["primary_video"], media_package
            assert media_package["primary_video"]["reel_potential"] > 0, media_package
            assert media_package["primary_video"]["clip_recommendations"], media_package

            communication_package = CommunicationPackageService(
                database=db
            ).generate_package(
                recommendation,
                package_type="Instagram"
            )
            assert communication_package["best_video"], communication_package

            explanation = DecisionExplainabilityService(
                database=db
            ).audit_package(
                communication_package,
                recommendation=recommendation,
                persist=False
            )
            assets = explanation.get("supporting_assets", [])
            assert assets and assets[0].get("reel_potential") > 0, explanation

            brief = CommunicationsOfficerService(database=db).generate(force=True)
            assert "recommended_videos" in brief, brief

        finally:
            os.chdir(original)

    print("video_intelligence_smoke passed")


if __name__ == "__main__":
    main()
