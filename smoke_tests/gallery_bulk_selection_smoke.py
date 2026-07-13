import os
import sys
import tempfile
import time
from pathlib import Path

import customtkinter as ctk
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def create_image(path, color):

    Image.new(
        "RGB",
        (120, 80),
        color
    ).save(path)


def add_media(db, path, media_type, index):

    db.add_media({
        "filename": path.name,
        "path": str(path),
        "extension": path.suffix.lower(),
        "type": media_type,
        "size": path.stat().st_size,
        "sha256": f"selection-smoke-{index}",
        "thumbnail_status": "pending"
    })


def wait_for_cards(app, page, expected, timeout=5):

    deadline = time.time() + timeout

    while time.time() < deadline:
        app.update()

        if len(page.cards_by_media_id) >= expected:
            return

        time.sleep(0.02)

    raise AssertionError(
        f"Expected {expected} cards, got {len(page.cards_by_media_id)}"
    )


def rendered_cards(page):

    return list(page.cards_by_media_id.values())


def main():

    original_cwd = os.getcwd()

    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tmp_path = Path(tmp)
            os.chdir(tmp_path)

            media_dir = tmp_path / "media"
            media_dir.mkdir()

            from database.db_manager import DatabaseManager

            db = DatabaseManager()

            for index in range(5):
                image_path = media_dir / f"photo_{index}.jpg"
                create_image(
                    image_path,
                    (40 + index * 20, 80, 160)
                )
                add_media(
                    db,
                    image_path,
                    "image",
                    index
                )

            for index in range(3):
                video_path = media_dir / f"video_{index}.mov"
                video_path.write_bytes(b"selection smoke video")
                add_media(
                    db,
                    video_path,
                    "video",
                    100 + index
                )

            import gui.photo_card as photo_card_module
            from gui.gallery_page import GalleryPage

            viewer_launches = {
                "count": 0
            }

            def fake_viewer(*_args, **_kwargs):

                viewer_launches["count"] += 1

            photo_card_module.PhotoViewer = fake_viewer

            GalleryPage.PAGE_SIZE = 4
            GalleryPage.CARD_RENDER_CHUNK = 8
            GalleryPage.CARD_RENDER_DELAY_MS = 1

            ctk.set_appearance_mode("Dark")
            ctk.set_default_color_theme("blue")

            app = ctk.CTk()
            app.geometry("900x700")

            try:
                page = GalleryPage(app)
                page.pack(
                    fill="both",
                    expand=True
                )
                app.update()
                wait_for_cards(app, page, 4)

                first_card = rendered_cards(page)[0]
                checkbox = first_card.select_box
                app.update()

                assert checkbox.winfo_ismapped(), "checkbox is not visible"
                assert checkbox.winfo_width() >= 28, checkbox.winfo_width()
                assert checkbox.winfo_height() >= 28, checkbox.winfo_height()
                assert checkbox.winfo_x() >= 0, checkbox.winfo_x()
                assert checkbox.winfo_y() >= 0, checkbox.winfo_y()
                assert (
                    checkbox.winfo_x() + checkbox.winfo_width()
                    <= first_card.image_area.winfo_width()
                )
                assert (
                    checkbox.winfo_y() + checkbox.winfo_height()
                    <= first_card.image_area.winfo_height()
                )

                before_viewer_count = viewer_launches["count"]
                first_card.toggle_selection_from_keyboard()
                app.update()
                assert viewer_launches["count"] == before_viewer_count
                assert first_card.media_id in page.selected
                assert "Selected: 1" in page.selected_label.cget("text")

                first_card.open_viewer()
                assert viewer_launches["count"] == before_viewer_count + 1

                page.load_more()
                wait_for_cards(app, page, 8)
                assert first_card.media_id in page.selected
                assert first_card.selected.get() is True

                page.clear_selection()
                app.update()
                assert len(page.selected) == 0
                assert "Selected: 0" in page.selected_label.cget("text")

                page.filter_var.set("Added Today")
                page.filter_changed("Added Today")
                wait_for_cards(app, page, 4)
                app.update()
                assert page.select_all_filter_button.cget("text") == "Select All 8"

                page.select_all_current_filter()
                app.update()
                assert len(page.selected) == 8, page.selected
                assert "Selected: 8" in page.selected_label.cget("text")

                page.invert_selection()
                app.update()
                assert len(page.selected) == 0, page.selected

                page.select_all_photos()
                app.update()
                assert len(page.selected) == 5, page.selected
                assert "Photos 5" in page.select_all_photos_button.cget("text")

                page.clear_selection()
                page.select_all_videos()
                app.update()
                assert len(page.selected) == 3, page.selected
                assert "Videos 3" in page.select_all_videos_button.cget("text")

                page.filter_var.set("Videos")
                page.filter_changed("Videos")
                wait_for_cards(app, page, 3)
                app.update()
                assert page.select_all_filter_button.cget("text") == "Select All 3"
                page.select_all_current_filter()
                assert len(page.selected) == 3, page.selected

                page.clear_selection()
                visible_ids = set(page.visible_media_ids)
                page.select_all_visible()
                assert page.selected == visible_ids, page.selected

            finally:
                app.destroy()

    finally:
        os.chdir(original_cwd)

    print("gallery bulk selection smoke passed")


if __name__ == "__main__":
    main()
