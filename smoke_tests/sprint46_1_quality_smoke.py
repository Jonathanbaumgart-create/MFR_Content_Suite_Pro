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
from services.helmet_camera_service import HelmetCameraService
from smoke_tests.sprint46_fast_officer_smoke import (
    add_media,
    create_image,
    create_video,
    save_reviewed_intelligence
)


BANNED = (
    "Review media before publishing",
    "Review the selected media before publishing",
    "selected media",
    "media trust",
    "provider",
    "model",
    "review status",
    "technical warnings",
    "#MordenFireRescue"
)


def assert_public_caption(caption):

    assert len(caption) > 80, caption
    for phrase in BANNED:
        assert phrase.lower() not in caption.lower(), caption


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            media_dir = Path(folder) / "Helmet Cam"
            media_dir.mkdir()
            photo_ids = []

            for index, name in enumerate(("training", "community", "recruitment"), start=1):
                path = media_dir / f"{name}_{index}.jpg"
                create_image(path, ("red", "green", "blue")[index - 1])
                media_id = add_media(db, path, index, "image")
                save_reviewed_intelligence(db, media_id, f"{name} teamwork readiness")
                photo_ids.append(media_id)

            video_path = media_dir / "helmet_action.mp4"
            create_video(video_path)
            video_id = add_media(db, video_path, 10, "video")

            daily = DailyCommunicationsOfficerService(database=db)
            brief = daily.generate(force=True)
            packages = brief.get("daily_post_packages", [])
            assert len(packages) == 3, packages

            families = {
                package.get("content_family")
                for package in packages
                if package.get("content_family")
            }
            assert len(families) >= 3, families
            assert any(package.get("primary_media") for package in packages), packages
            assert any(package.get("text_graphic_first") for package in packages), packages

            for package in packages:
                assert_public_caption(package.get("facebook_caption", ""))
                assert_public_caption(package.get("instagram_caption", ""))
                assert package.get("facebook_caption") != package.get("instagram_caption"), package
                assert "#MordenFireRescue" not in " ".join(package.get("instagram_hashtags") or []), package
                assert len(package.get("instagram_hashtags") or []) <= 5, package
                assert package.get("tone_options"), package
                assert package.get("content_angle"), package

            helmet = HelmetCameraService(database=db)
            assert helmet.effective_rotation(video_path, override=180) == 180

            image = Image.new("RGB", (4, 2), "black")
            image.putpixel((0, 0), (255, 0, 0))
            rotated = helmet.apply_rotation(image, 180)
            assert rotated.getpixel((3, 1)) == (255, 0, 0)

            result = helmet.analyze_video(video_id, str(video_path))
            segment = result["top_segments"][0]
            assert segment.get("visual_summary"), segment
            assert "Technically selected" not in segment.get("visual_summary", ""), segment
            assert segment.get("reason_selected"), segment

            screened = helmet.semantic_screen_segments(
                video_id,
                result["top_segments"],
                limit=3
            )
            assert screened, screened
            first = screened[0]
            assert first.get("classification"), first
            assert first.get("visible_activity_summary"), first
            assert first.get("recommended_tone"), first
            assert first.get("suggested_hook"), first
            assert first.get("why_this_clip_works"), first

            sheet = helmet.create_contact_sheet(str(video_path), segment)
            assert sheet is not None, segment
            preview = helmet.create_preview_clip(str(video_path), segment)
            assert preview.get("source_preserved") is True, preview
            assert preview.get("temporary") is True, preview
            if preview.get("success"):
                assert Path(preview.get("preview_path", "")).exists(), preview
                os.remove(preview["preview_path"])

            reel = helmet.reel_package(video_id, first)
            assert "Review before publishing" not in str(reel), reel
            assert reel.get("content_family"), reel
            assert reel.get("posting_angle"), reel
            assert reel.get("orientation_correction") in (0, 90, 180, 270), reel

        finally:
            os.chdir(original)

    print("sprint46_1_quality_smoke passed")


if __name__ == "__main__":
    main()
