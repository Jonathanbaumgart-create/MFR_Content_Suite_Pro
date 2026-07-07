from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys
import time

from PIL import Image
import customtkinter as ctk


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager


def create_image(path, color):

    image = Image.new(
        "RGB",
        (64, 64),
        color=color
    )
    image.save(path)


def add_media(db, index, path):

    db.add_media(
        {
            "filename": path.name,
            "path": str(path),
            "extension": ".jpg",
            "type": "image",
            "size": path.stat().st_size,
            "sha256": f"image-{index}"
        }
    )


def save_intelligence(db, media_id, incident, equipment, use, score):

    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": "emergency_response",
            "incident_type": incident,
            "primary_activity": "interior_attack",
            "apparatus_tags": ["engine"],
            "equipment_tags": equipment,
            "ppe_tags": ["turnout_gear"],
            "people_tags": ["crew"],
            "content_tags": [
                incident,
                "interior_attack"
            ] + equipment,
            "content_themes": ["recruitment"],
            "recommended_uses": use,
            "search_text": " ".join(
                [incident, "interior_attack"] + equipment + use
            ),
            "intelligence_score": score,
            "source_model": "mock"
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        root = Path(folder)
        os.chdir(root)

        try:
            db = DatabaseManager()
            library = root / "library"
            library.mkdir()

            first = library / "alpha.jpg"
            second = library / "bravo.jpg"
            create_image(first, "red")
            create_image(second, "blue")

            add_media(db, 1, first)
            save_intelligence(
                db,
                1,
                "structure_fire",
                ["scba"],
                ["recruitment"],
                95
            )

            add_media(db, 2, second)
            save_intelligence(
                db,
                2,
                "grass_fire",
                ["hose"],
                ["public_education"],
                70
            )

            from gui.main_window import MainWindow
            from gui.photo_card import PhotoCard

            ctk.set_appearance_mode("Dark")
            ctk.set_default_color_theme("blue")

            app = MainWindow()

            try:
                app.update()
                app.show_intelligence()
                app.update()

                page = app.current_page
                assert page.total == 2, page.total

                page.toggle_filter(
                    "incident_type",
                    "structure_fire"
                )
                page.toggle_filter(
                    "equipment_tags",
                    "scba"
                )
                page.sort_changed("Intelligence Score")

                end = time.time() + 3

                while time.time() < end:
                    app.update()
                    cards = [
                        child
                        for child in page.scroll.winfo_children()
                        if isinstance(child, PhotoCard)
                    ]

                    if cards:
                        break

                    time.sleep(0.05)

                assert page.total == 1, page.total
                assert cards, "No intelligence result cards rendered"
                assert cards[0].filename == "alpha.jpg", cards[0].filename

                cards[0].open_viewer()
                app.update()

                viewers = [
                    child
                    for child in app.winfo_children()
                    if child.winfo_class() == "Toplevel"
                ]

                assert viewers is not None

            finally:
                app.destroy()

        finally:
            os.chdir(original)

    print("intelligence_page smoke passed")


if __name__ == "__main__":
    main()
