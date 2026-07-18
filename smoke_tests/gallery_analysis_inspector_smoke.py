import os
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import customtkinter as ctk
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.app_context import context
from database.db_manager import DatabaseManager
from gui.gallery_analysis_inspector import GalleryAnalysisInspector
from gui.gallery_page import GalleryPage
from gui.photo_card import PhotoCard
from services.gallery_service import GalleryService
from services.gallery_analysis_inspector_service import GalleryAnalysisInspectorService
from smoke_tests.communications_officer_smoke import save_analysis, save_intelligence
from smoke_tests.sprint44_operational_activity_smoke import add_media, save_filesystem


class FakeBrain:

    def __init__(self):
        self.queued = []

    def analyze_selected(self, media_ids, force=False):
        self.queued.append(
            {
                "media_ids": list(media_ids),
                "force": bool(force)
            }
        )


def seed(db):
    add_media(
        db,
        1,
        "review_one.jpg",
        path="library/Review Required/review_one.jpg"
    )
    add_media(
        db,
        2,
        "review_two.jpg",
        path="library/Review Required/review_two.jpg"
    )
    add_media(
        db,
        3,
        "review_video.mp4",
        media_type="video",
        path="library/Review Required/review_video.mp4"
    )

    for media_id in (1, 2, 3):
        save_analysis(db, media_id, "unreviewed_real", "review_required")
        save_intelligence(
            db,
            media_id,
            {
                "primary_activity": "training",
                "content_tags": ["training", "firefighter"],
                "recommended_uses": ["training"],
                "search_text": "training firefighter equipment",
                "communications_score": 80
            }
        )
        save_filesystem(
            db,
            media_id,
            root_category="Training",
            subcategory="Review Required",
            normalized_tags=["training", "review"],
            source_folders=["Training", "Review Required"]
        )


def main():
    original = os.getcwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            fixture_dir = Path("library") / "Review Required"
            fixture_dir.mkdir(parents=True, exist_ok=True)
            for name in ("review_one.jpg", "review_two.jpg"):
                Image.new("RGB", (320, 180), (90, 120, 160)).save(
                    fixture_dir / name
                )
            db = DatabaseManager()
            seed(db)

            fake_brain = FakeBrain()
            service = GalleryAnalysisInspectorService(
                database=db,
                brain_service=fake_brain
            )
            payload = service.inspector_payload(1)
            display = payload["display"]
            assert display["filename"] == "review_one.jpg", display
            assert display["review_state"] == "Review Required", display
            assert display["provider"] == "ollama", display
            assert display["raw_description"], display
            assert "training" in display["filesystem"].lower(), display

            approved = service.approve(1)
            assert approved["status"] == "approved", approved
            assert db.get_ai_analysis(1)["review_status"] == "approved"
            assert db.analysis_review_history(1), "approval audit missing"

            corrected = service.save_corrections(
                2,
                {
                    "description": "Corrected gallery inspector description",
                    "content_tags": "training, recruitment",
                    "primary_activity": "hose training",
                    "apparatus": "Engine",
                    "equipment": "Hose, Helmet",
                    "people_count": "2",
                    "notes": "Gallery inspector smoke correction"
                }
            )
            assert corrected["status"] == "corrected", corrected
            effective = service.feedback.effective_media_intelligence(2)
            assert effective["description"] == "Corrected gallery inspector description", effective
            assert effective["people_count"] == 2, effective
            assert effective["trust_state"] == "corrected_real", effective
            assert service.feedback.history_for_media(2), "correction audit missing"

            rejected = service.reject(2)
            assert rejected["status"] == "rejected", rejected
            assert db.get_ai_analysis(2)["review_status"] == "rejected"

            reanalysis = service.request_reanalysis(3)
            assert reanalysis["status"] == "reanalyze_requested", reanalysis
            assert db.get_ai_analysis(3)["review_status"] == "reanalyze_requested"
            assert fake_brain.queued == [{"media_ids": [3], "force": True}]

            ids = db.get_media_ids_for_selection(
                filter_key="review_required",
                limit=10
            )
            assert 1 not in ids
            assert 2 not in ids

            assert hasattr(GalleryAnalysisInspector, "inspect_media")
            assert hasattr(GalleryAnalysisInspector, "save_correction_next")
            assert hasattr(GalleryAnalysisInspector, "handle_key")
            assert hasattr(GalleryPage, "inspect_card")
            assert hasattr(GalleryPage, "select_next_inspector_item")
            assert hasattr(GalleryPage, "next_context_media_id")
            assert hasattr(PhotoCard, "inspect")

            card = PhotoCard.__new__(PhotoCard)
            called = []
            card.inspect_callback = lambda value: called.append(value)
            result = PhotoCard.inspect(card)
            assert result is None
            assert called == [card]

            context.database = db
            session_id = db.create_analysis_session(
                "gallery inspector smoke",
                "ollama",
                "qwen2.5vl:7b",
                total_items=3,
                settings={}
            )
            db.enqueue_analysis_items(
                session_id,
                [
                    {
                        "id": 1,
                        "filename": "review_one.jpg",
                        "path": "library/Review Required/review_one.jpg",
                        "media_type": "image"
                    },
                    {
                        "id": 2,
                        "filename": "review_two.jpg",
                        "path": "library/Review Required/review_two.jpg",
                        "media_type": "image"
                    }
                ],
                "ollama",
                "qwen2.5vl:7b"
            )
            summary = GalleryService().analysis_queue_summary()
            assert summary["has_session"] is True, summary
            assert summary["queued"] == 2, summary
            assert summary["progress_percent"] == 0, summary
            assert summary["eta"] == "Estimated time unavailable", summary

            ctk.set_appearance_mode("Dark")
            app = ctk.CTk()
            app.geometry("1200x780")

            try:
                GalleryAnalysisInspector.collapsed_state = False
                inspector = GalleryAnalysisInspector(
                    app,
                    service=service
                )
                inspector.grid(
                    row=0,
                    column=0,
                    sticky="ns"
                )
                app.update()
                assert inspector.header.grid_info(), "fixed header missing"
                assert inspector.content.grid_info(), "scrollable content missing"
                assert inspector.footer.grid_info(), "fixed footer missing"
                assert inspector.winfo_width() >= 360, inspector.winfo_width()

                inspector.inspect_media(
                    1,
                    "review_one.jpg",
                    "library/Review Required/review_one.jpg",
                    "image"
                )
                deadline = time.time() + 5
                while time.time() < deadline and not hasattr(inspector, "raw_text"):
                    app.update()
                    time.sleep(0.05)
                app.update()
                assert hasattr(inspector, "raw_text"), inspector.status.cget("text")
                assert inspector.action_buttons["approve"].winfo_ismapped()
                assert inspector.action_buttons["correct"].winfo_ismapped()
                assert inspector.action_buttons["reject"].winfo_ismapped()
                assert inspector.action_buttons["reanalyze"].winfo_ismapped()
                assert not inspector.raw_text.winfo_ismapped(), "raw analysis should be collapsed by default"
                assert inspector.readable("unreviewed_real") == "Real - Review Required"
                assert inspector.readable("water_rescue_equipment") == "Water rescue equipment"

                inspector.enter_correction_mode()
                app.update()
                assert inspector.correction_frame.winfo_ismapped()
                assert inspector.action_buttons["save"].winfo_ismapped()
                assert inspector.action_buttons["save_next"].winfo_ismapped()
                assert inspector.action_buttons["cancel"].winfo_ismapped()

                inspector.toggle_collapsed()
                app.update()
                assert not inspector.content.grid_info()
                inspector.toggle_collapsed()
                app.update()
                assert inspector.content.grid_info()

                page = GalleryPage(app)
                page.grid(row=0, column=1, sticky="nsew")
                app.update()
                assert page.analysis_panel.winfo_ismapped()
                assert page.queue_summary.get("queued") == 2, page.queue_summary
                assert page.session_panel.winfo_ismapped()
                assert hasattr(page, "poll_analysis_queue")
                assert page.ACTIVE_QUEUE_POLL_MS >= 750
                page.destroy()
                inspector.destroy()
            finally:
                app.destroy()

        finally:
            os.chdir(original)

    print("gallery_analysis_inspector_smoke passed")


if __name__ == "__main__":
    main()
