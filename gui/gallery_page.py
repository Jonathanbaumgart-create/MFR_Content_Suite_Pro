import customtkinter as ctk
from tkinter import messagebox
from collections import deque

from gui.photo_card import PhotoCard
from services.brain_service import BrainService
from services.gallery_service import GalleryService
from services.thumbnail_service import ThumbnailService


class GalleryPage(ctk.CTkFrame):

    PAGE_SIZE = 200
    CARD_RENDER_CHUNK = 4
    CARD_RENDER_DELAY_MS = 50

    def __init__(self, parent):

        super().__init__(parent)

        self.service = GalleryService()
        self.brain = BrainService()

        self.media = []

        self.loaded = 0
        self.total = 0
        self.selected = set()
        self.thumbnail_service = ThumbnailService()
        self.loading_cards = False
        self.pending_cards = deque()

        self.build_page()

    ########################################################

    def build_page(self):

        title = ctk.CTkLabel(
            self,
            text="Gallery",
            font=("Segoe UI", 30, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        self.info = ctk.CTkLabel(
            self,
            text=""
        )

        self.info.pack(
            anchor="w",
            padx=20
        )

        actions = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        actions.pack(
            fill="x",
            padx=20,
            pady=(10, 0)
        )

        self.selected_label = ctk.CTkLabel(
            actions,
            text="Selected: 0"
        )

        self.selected_label.pack(
            side="left",
            padx=(0, 15)
        )

        analyze_selected = ctk.CTkButton(
            actions,
            text="Analyze Selected",
            command=self.analyze_selected
        )

        analyze_selected.pack(
            side="left",
            padx=(0, 10)
        )

        clear_selected = ctk.CTkButton(
            actions,
            text="Clear Selection",
            command=self.clear_selection
        )

        clear_selected.pack(
            side="left"
        )

        self.scroll = ctk.CTkScrollableFrame(self)

        self.scroll.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.more = ctk.CTkButton(
            self,
            text="Load More",
            command=self.load_more
        )

        self.more.pack(pady=10)

        self.total = self.service.media_count()

        self.load_more()

    ########################################################

    def load_more(self):

        if self.loading_cards:
            return

        media = self.service.get_media_page(
            self.PAGE_SIZE,
            self.loaded
        )

        self.pending_cards = deque(
            (
                self.loaded + page_index,
                item
            )
            for page_index, item in enumerate(media)
        )
        self.loading_cards = True
        self.more.configure(
            state="disabled",
            text="Loading..."
        )

        self.render_card_chunk()

    ########################################################

    def render_card_chunk(self):

        rendered = 0

        while self.pending_cards and rendered < self.CARD_RENDER_CHUNK:

            index, item = self.pending_cards.popleft()

            media_id, filename, path, media_type = item[:4]
            analysis_status = (
                item[4]
                if len(item) > 4
                else "Not analyzed"
            )

            try:

                card = PhotoCard(
                    self.scroll,
                    media_id,
                    filename,
                    path,
                    thumbnail_service=self.thumbnail_service,
                    selection_callback=self.selection_changed,
                    analysis_status=analysis_status
                )

                row = index // 4
                column = index % 4

                card.grid(
                    row=row,
                    column=column,
                    padx=12,
                    pady=12
                )

            except Exception as ex:

                print(path)
                print(ex)

            rendered += 1

        self.loaded += rendered

        self.info.configure(
            text=f"Showing {self.loaded:,} of {self.total:,} media"
        )

        if self.pending_cards:

            self.after(
                self.CARD_RENDER_DELAY_MS,
                self.render_card_chunk
            )
            return

        self.loading_cards = False

        if self.loaded >= self.total:

            self.more.configure(
                state="disabled",
                text="All Media Loaded"
            )

        else:
            self.more.configure(
                state="normal",
                text="Load More"
            )

    ########################################################

    def selection_changed(self, media_id, selected):

        if selected:
            self.selected.add(media_id)
        else:
            self.selected.discard(media_id)

        self.selected_label.configure(
            text=f"Selected: {len(self.selected):,}"
        )

    ########################################################

    def clear_selection(self):

        self.selected.clear()

        for child in self.scroll.winfo_children():

            if hasattr(child, "selected"):
                child.selected.set(False)

        self.selected_label.configure(
            text="Selected: 0"
        )

    ########################################################

    def analyze_selected(self):

        warning = self.brain.provider_bulk_warning()

        if warning:
            if not messagebox.askyesno(
                "Confirm AI Analysis",
                warning + "\n\nContinue?"
            ):
                return

        futures = self.brain.analyze_selected(
            list(self.selected),
            progress_callback=self.analysis_progress
        )

        self.info.configure(
            text=f"Queued {len(futures):,} selected photos for analysis"
        )

    ########################################################

    def analysis_progress(self, progress):

        bulk_total = progress.get("bulk_total", 0)
        bulk_processed = progress.get("bulk_processed", 0)

        if bulk_total:
            text = (
                f"AI bulk: {bulk_processed:,} of "
                f"{bulk_total:,} processed"
            )
        else:
            text = (
                f"AI queue: {progress.get('queued', 0):,} queued, "
                f"{progress.get('running', 0):,} running"
            )

        self.after(
            0,
            lambda: self.info.configure(
                text=text
            )
        )

    ########################################################

    def destroy(self):

        if hasattr(self, "thumbnail_service"):
            self.thumbnail_service.shutdown()

        super().destroy()
