import customtkinter as ctk
from tkinter import messagebox

from gui.photo_card import PhotoCard
from media.thumbnail_cache import ThumbnailCache
from services.brain_service import BrainService
from services.gallery_service import GalleryService


class GalleryPage(ctk.CTkFrame):

    PAGE_SIZE = 200

    def __init__(self, parent):

        super().__init__(parent)

        self.service = GalleryService()
        self.brain = BrainService()

        self.media = []

        self.loaded = 0
        self.total = 0
        self.selected = set()
        self.thumbnail_cache = ThumbnailCache()

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

        end = min(
            self.loaded + self.PAGE_SIZE,
            self.total
        )

        media = self.service.get_media_page(
            self.PAGE_SIZE,
            self.loaded
        )

        for page_index, item in enumerate(media):

            media_id, filename, path, media_type = item
            index = self.loaded + page_index

            try:

                card = PhotoCard(
                    self.scroll,
                    media_id,
                    filename,
                    path,
                    thumbnail_cache=self.thumbnail_cache,
                    selection_callback=self.selection_changed
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

        self.loaded = end

        self.info.configure(
            text=f"Showing {self.loaded:,} of {self.total:,} media"
        )

        if self.loaded >= self.total:

            self.more.configure(
                state="disabled",
                text="All Media Loaded"
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

        if self.brain.is_mock_provider():

            if not messagebox.askyesno(
                "Mock Provider Active",
                (
                    "Mock provider active - test data only.\n\n"
                    "Selected-photo analysis will save the same test "
                    "analysis for each photo that does not already have "
                    "real analysis. Continue?"
                )
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

        self.after(
            0,
            lambda: self.info.configure(
                text=(
                    f"AI queue: {progress.get('queued', 0):,} queued, "
                    f"{progress.get('running', 0):,} running"
                )
            )
        )
