import os
import sys
import tempfile
from pathlib import Path

import customtkinter as ctk
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.content_director_page import ContentDirectorPage
from gui.home_page import HomePage
from gui.main_window import MainWindow
from gui.photo_card import PhotoCard
from gui.photo_viewer import PhotoViewer
from gui.window_placement import WindowPlacement
from media.preview_image_cache import PreviewImageCache


def make_image(path, size=(900, 600), color=(180, 40, 40)):
    Image.new("RGB", size, color).save(path)


def button_texts(widget):
    texts = []

    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkButton):
            texts.append(child.cget("text"))
        texts.extend(button_texts(child))

    return texts


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        image_paths = []

        for index in range(5):
            path = tmp / f"image-{index}.jpg"
            make_image(path, size=(900 + index * 20, 600))
            image_paths.append(path)

        missing = tmp / "missing.jpg"
        corrupt = tmp / "corrupt.jpg"
        corrupt.write_bytes(b"not an image")

        cache = PreviewImageCache(max_items=3, max_dimension=420)
        first = cache.get(1, image_paths[0])
        assert first["image"] is not None, first
        assert max(first["image"].size) <= 420, first["image"].size
        assert first["timings"]["file_read_seconds"] >= 0, first
        assert first["timings"]["image_decode_seconds"] >= 0, first
        assert first["timings"]["exif_transpose_seconds"] >= 0, first
        assert first["timings"]["preview_resize_seconds"] >= 0, first

        second = cache.get(1, image_paths[0])
        assert second["cache_hit"] is True, second

        cache.prefetch(2, image_paths[1])
        cache.prefetch(3, image_paths[2])
        cache.prefetch(4, image_paths[3])
        assert cache.size() <= 3, cache.size()

        missing_result = cache.get(20, missing)
        assert missing_result["image"] is None, missing_result
        assert missing_result["error"] is not None, missing_result

        corrupt_result = cache.get(21, corrupt)
        assert corrupt_result["image"] is None, corrupt_result
        assert corrupt_result["error"] is not None, corrupt_result

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        app = ctk.CTk()

        try:
            WindowPlacement.center_window(app, 800, 600)
            app.update()
            app.update_idletasks()
            geometry = app.geometry()
            size, x_text, y_text = geometry.split("+", 2)
            width, height = [int(part) for part in size.split("x")]
            x = int(x_text)
            y = int(y_text)
            assert width == 800 and height == 600, geometry
            assert x >= 0 and y >= 0, geometry
            assert x + width <= app.winfo_screenwidth(), geometry
            assert y + height <= app.winfo_screenheight(), geometry

            child = ctk.CTkToplevel(app)
            ctk.CTkLabel(child, text="placement").pack()
            WindowPlacement.center_window(child, 500, 360, parent=app)
            app.update()
            child.update_idletasks()
            child_geometry = child.geometry()
            assert "500x360" in child_geometry, child_geometry
            child.destroy()

            events = {
                "opened": 0,
                "approved": 0,
                "rejected": 0
            }

            card = PhotoCard(
                app,
                1,
                "review-required.jpg",
                str(image_paths[0]),
                analysis_status="Real - Review Required",
                media_type="image",
                open_callback=lambda _card: events.__setitem__("opened", events["opened"] + 1),
                quick_approve_callback=lambda _media_id: events.__setitem__("approved", events["approved"] + 1),
                quick_reject_callback=lambda _media_id: events.__setitem__("rejected", events["rejected"] + 1)
            )
            card.pack()
            app.update_idletasks()
            texts = set(button_texts(card))
            assert {"Review", "Correct", "Approve", "Reject"} <= texts, texts
            assert card.quick_review_allowed(), texts
            card.quick_approve()
            card.quick_reject()
            card.quick_review()
            assert events == {"opened": 1, "approved": 1, "rejected": 1}, events
            assert card.select_box.winfo_width() >= 28, card.select_box.winfo_width()
            card.destroy()

            approved_card = PhotoCard(
                app,
                2,
                "approved.jpg",
                str(image_paths[1]),
                analysis_status="Real - Approved",
                media_type="image"
            )
            approved_card.pack()
            app.update_idletasks()
            assert "Approve" not in set(button_texts(approved_card))
            approved_card.destroy()

            assert hasattr(PhotoViewer, "prefetch_neighbors")
            assert hasattr(PhotoViewer, "log_navigation_timings")
            assert hasattr(PhotoViewer, "shortcut_blocked")
            assert hasattr(PhotoViewer, "after_review_action")
            assert "PreviewImageCache" in Path(ROOT / "gui" / "photo_viewer.py").read_text(encoding="utf-8")
            assert "ImageLoader.load_pil_image" not in Path(ROOT / "gui" / "photo_viewer.py").read_text(encoding="utf-8")

            assert HomePage.LOAD_TIMEOUT_MS > 0
            assert hasattr(HomePage, "loading_timed_out")
            assert hasattr(HomePage, "render_empty")
            assert hasattr(HomePage, "render_error")
            assert hasattr(HomePage, "is_empty_brief")
            assert ContentDirectorPage.LOAD_TIMEOUT_MS > 0
            assert hasattr(ContentDirectorPage, "loading_timed_out")
            assert hasattr(ContentDirectorPage, "render_failure")
            assert hasattr(ContentDirectorPage, "cancel_load_timeout")

            assert "WindowPlacement.center_window" in Path(ROOT / "gui" / "main_window.py").read_text(encoding="utf-8")
            assert issubclass(MainWindow, ctk.CTk)
        finally:
            app.destroy()

    print("production_usability_repair_smoke passed")


if __name__ == "__main__":
    main()
