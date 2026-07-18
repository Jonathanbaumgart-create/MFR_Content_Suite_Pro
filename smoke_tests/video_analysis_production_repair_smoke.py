import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.brain_service import BrainService, VisionProviderError
from services.video_intelligence_service import VideoIntelligenceService
from services.video_metadata_service import VideoMetadataService
from smoke_tests.video_intelligence_smoke import create_video


class CapabilityVision:

    def __init__(self, supports_video_frames=True, provider="ollama"):
        self.supports_video_frames = supports_video_frames
        self.provider = provider

    def provider_key(self):
        return self.provider

    def model_name(self):
        return "test-vision-model"

    def provider_settings(self):
        return {
            "timeout": 20
        }

    def provider_capabilities(self):
        return {
            "provider": self.provider,
            "model": self.model_name(),
            "supports_images": True,
            "supports_video_frames": self.supports_video_frames,
            "supports_multi_image_prompt": False,
            "cpu_safe": True,
            "gpu_dependent": False,
            "recommended_frame_count": 2,
            "timeout": 20,
            "maximum_resolution": 640,
            "production_approved": self.provider != "mock"
        }


class LocalFrameAI:

    def analyze_image(self, image_path, vision, prompt_context=""):
        assert Path(image_path).exists()
        return {
            "description": "Firefighters are completing hose training in a video frame.",
            "people_count": 2,
            "people": ["firefighters"],
            "apparatus": ["engine"],
            "equipment": ["hose", "helmet"],
            "activities": ["training", "hose evolution"],
            "setting": "training ground",
            "visible_text": [],
            "uncertain_observations": [],
            "confidence": 0.82,
            "parse_status": "valid_structured_response"
        }


def add_video(db, media_id, path):
    db.add_media(
        {
            "filename": path.name,
            "path": str(path),
            "extension": path.suffix.lower(),
            "type": "video",
            "size": path.stat().st_size,
            "sha256": f"video-repair-{media_id}",
            "first_seen_at": "2026-07-17T12:00:00+00:00"
        }
    )


def main():
    original = os.getcwd()

    with TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            media_dir = Path(folder) / "media"
            media_dir.mkdir()
            video_path = media_dir / "training_video.mp4"
            create_video(video_path, seconds=8, fps=4, size=(160, 90))
            add_video(db, 1, video_path)

            preview = db.analysis_selection_preview([1])
            assert preview["video_count"] == 1, preview
            assert preview["queueable_ids"] == [1], preview

            unsupported = BrainService(
                database=db,
                vision_service=CapabilityVision(
                    supports_video_frames=False,
                    provider="mock"
                )
            )
            try:
                unsupported._analyze_video_and_save(1, str(video_path))
            except VisionProviderError as ex:
                assert ex.category == "unsupported_provider", ex
            else:
                raise AssertionError("Unsupported video provider did not fail visibly")

            failed = db.get_ai_analysis(1)
            assert failed["failure_category"] == "unsupported_provider", failed
            assert "Video analysis unavailable" in failed["failure_reason"], failed

            page = db.get_media_page(
                10,
                0,
                filter_key="all",
                sort_key="filename_az"
            )
            assert page[0][4] == "Unsupported Provider", page

            retry_preview = db.analysis_selection_preview(
                [1],
                retry_failed=True
            )
            assert retry_preview["queueable_ids"] == [1], retry_preview

            metadata_service = VideoMetadataService()
            metadata = metadata_service.inspect(video_path)
            supported_service = VideoIntelligenceService(
                database=db,
                ai_service=LocalFrameAI(),
                vision_service=CapabilityVision(
                    supports_video_frames=True,
                    provider="ollama"
                ),
                metadata_service=metadata_service,
                config={
                    "video_max_frames": 5,
                    "video_max_analyzed_frames": 4,
                    "video_sample_interval_seconds": 4
                }
            )
            result = supported_service.generate_and_save(
                1,
                str(video_path),
                metadata=metadata
            )
            assert result["analyzed_frame_count"] <= 2, result
            assert result["representative_frames"], result
            assert result["cover_recommendation"], result
            assert result["clip_recommendations"], result
            assert result["reel_potential"] > 0, result
            assert db.get_video_intelligence(1)["reel_potential"] == result["reel_potential"]
            assert not list(Path(folder).rglob("video_frame_*.jpg"))

            session_id = db.create_analysis_session(
                "video-smoke",
                "ollama",
                "test-vision-model",
                total_items=1
            )
            db.enqueue_analysis_items(
                session_id,
                db.get_media_by_ids([1]),
                "ollama",
                "test-vision-model",
                force=True
            )
            assert db.next_analysis_queue_batch(session_id, 5), "queue insertion failed"
            canceled = db.cancel_analysis_session(session_id, "Smoke cancellation")
            assert canceled == 1, canceled
            recovered = db.reset_stale_analysis_items(session_id)
            assert recovered == 0, recovered

        finally:
            os.chdir(original)

    print("video_analysis_production_repair_smoke passed")


if __name__ == "__main__":
    main()
