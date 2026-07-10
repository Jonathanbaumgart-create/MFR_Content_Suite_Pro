from collections import deque

import customtkinter as ctk

from gui.photo_card import PhotoCard
from services.intelligence_explorer_service import IntelligenceExplorerService
from services.logging_service import LoggingService
from services.thumbnail_service import ThumbnailService


logger = LoggingService.get_logger("intelligence")


class IntelligenceExplorerPage(ctk.CTkFrame):

    PAGE_SIZE = 200
    CARD_RENDER_CHUNK = 10

    SECTIONS = (
        ("incident_type", "INCIDENT TYPES"),
        ("apparatus_tags", "APPARATUS"),
        ("equipment_tags", "EQUIPMENT"),
        ("primary_activity", "ACTIVITIES"),
        ("recommended_uses", "RECOMMENDED USES"),
        ("content_themes", "THEMES"),
        ("content_tags", "CONTENT TAGS"),
        ("review_status", "REVIEW")
    )

    SORT_OPTIONS = {
        "Filename": "filename",
        "Date": "date",
        "Intelligence Score": "intelligence_score",
        "Communications Score": "communications_score",
        "Storytelling": "storytelling",
        "Educational": "educational",
        "Recruitment": "recruitment",
        "Community Engagement": "community_engagement",
        "Trust Building": "trust_building",
        "Correction Count": "correction_count",
        "Newest": "newest",
        "Oldest": "oldest"
    }

    def __init__(self, parent):

        super().__init__(parent)

        self.service = IntelligenceExplorerService()
        self.thumbnail_service = ThumbnailService()
        self.filters = {}
        self.section_frames = {}
        self.section_buttons = {}
        self.collapsed = set()
        self.pending_cards = deque()
        self.loaded = 0
        self.total = 0
        self.loading_cards = False
        self.sort_label = "Filename"

        self.build_page()
        self.refresh_counts()
        self.reload_results()

    ##########################################################

    def build_page(self):

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkScrollableFrame(
            self,
            width=310
        )

        sidebar.grid(
            row=0,
            column=0,
            sticky="ns",
            padx=(0, 15),
            pady=0
        )

        title = ctk.CTkLabel(
            sidebar,
            text="Intelligence Explorer",
            font=("Segoe UI", 22, "bold")
        )

        title.pack(
            anchor="w",
            padx=15,
            pady=(15, 10)
        )

        clear = ctk.CTkButton(
            sidebar,
            text="Clear Filters",
            command=self.clear_filters
        )

        clear.pack(
            fill="x",
            padx=15,
            pady=(0, 15)
        )

        for key, label in self.SECTIONS:
            self.create_section(
                sidebar,
                key,
                label
            )

        main = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        main.grid(
            row=0,
            column=1,
            sticky="nsew"
        )
        main.grid_rowconfigure(2, weight=1)
        main.grid_columnconfigure(0, weight=1)

        heading = ctk.CTkLabel(
            main,
            text="Browse by Media Intelligence",
            font=("Segoe UI", 30, "bold")
        )

        heading.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 8)
        )

        controls = ctk.CTkFrame(
            main,
            fg_color="transparent"
        )

        controls.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 10)
        )

        self.info = ctk.CTkLabel(
            controls,
            text=""
        )

        self.info.pack(
            side="left",
            padx=(0, 20)
        )

        sort_label = ctk.CTkLabel(
            controls,
            text="Sort"
        )

        sort_label.pack(
            side="left",
            padx=(0, 8)
        )

        self.sort_menu = ctk.CTkOptionMenu(
            controls,
            values=list(self.SORT_OPTIONS.keys()),
            command=self.sort_changed
        )

        self.sort_menu.set(self.sort_label)
        self.sort_menu.pack(
            side="left"
        )

        self.selected_filters = ctk.CTkLabel(
            controls,
            text=""
        )

        self.selected_filters.pack(
            side="left",
            padx=20
        )

        self.scroll = ctk.CTkScrollableFrame(main)

        self.scroll.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=20,
            pady=10
        )

        self.more = ctk.CTkButton(
            main,
            text="Load More",
            command=self.load_more
        )

        self.more.grid(
            row=3,
            column=0,
            pady=(0, 15)
        )

    ##########################################################

    def create_section(self, parent, key, label):

        header = ctk.CTkButton(
            parent,
            text=label,
            command=lambda: self.toggle_section(key)
        )

        header.pack(
            fill="x",
            padx=15,
            pady=(8, 3)
        )

        frame = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        frame.pack(
            fill="x",
            padx=15,
            pady=(0, 5)
        )

        self.section_frames[key] = frame
        self.section_buttons[key] = []

    ##########################################################

    def refresh_counts(self):

        counts = self.service.filter_counts(self.filters)

        for key, label in self.SECTIONS:
            self.render_section(
                key,
                counts.get(key, [])
            )

    ##########################################################

    def render_section(self, key, rows):

        frame = self.section_frames[key]

        for child in frame.winfo_children():
            child.destroy()

        self.section_buttons[key] = []

        if key in self.collapsed:
            return

        for value, count in rows[:50]:

            text = f"{self.format_label(value)} ({count:,})"
            selected = value in self.filters.get(key, [])

            button = ctk.CTkButton(
                frame,
                text=text,
                height=30,
                fg_color=(
                    "#1f6aa5"
                    if selected
                    else "transparent"
                ),
                command=lambda k=key, v=value: self.toggle_filter(k, v)
            )

            button.pack(
                fill="x",
                pady=2
            )

            self.section_buttons[key].append(button)

    ##########################################################

    def toggle_section(self, key):

        if key in self.collapsed:
            self.collapsed.remove(key)
        else:
            self.collapsed.add(key)

        self.refresh_counts()

    ##########################################################

    def toggle_filter(self, key, value):

        selected = self.filters.setdefault(
            key,
            []
        )

        if value in selected:
            selected.remove(value)
        else:
            selected.append(value)

        if not selected:
            self.filters.pop(key, None)

        logger.info(
            "Intelligence filter changed filters=%s",
            self.filters
        )

        self.refresh_counts()
        self.reload_results()

    ##########################################################

    def clear_filters(self):

        self.filters = {}
        logger.info("Intelligence filters cleared")
        self.refresh_counts()
        self.reload_results()

    ##########################################################

    def sort_changed(self, label):

        self.sort_label = label
        logger.info(
            "Intelligence sort changed sort=%s",
            label
        )
        self.reload_results()

    ##########################################################

    def reload_results(self):

        for child in self.scroll.winfo_children():
            child.destroy()

        self.loaded = 0
        self.total = self.service.media_count(self.filters)
        self.pending_cards.clear()
        self.loading_cards = False
        self.update_filter_summary()
        self.load_more()

    ##########################################################

    def load_more(self):

        if self.loading_cards:
            return

        media = self.service.media_page(
            filters=self.filters,
            sort_by=self.SORT_OPTIONS.get(
                self.sort_label,
                "filename"
            ),
            limit=self.PAGE_SIZE,
            offset=self.loaded
        )

        self.pending_cards = deque(
            (
                self.loaded + index,
                item
            )
            for index, item in enumerate(media)
        )
        self.loading_cards = True
        self.more.configure(
            state="disabled",
            text="Loading..."
        )
        self.render_card_chunk()

    ##########################################################

    def render_card_chunk(self):

        rendered = 0

        while self.pending_cards and rendered < self.CARD_RENDER_CHUNK:

            index, item = self.pending_cards.popleft()
            media_id, filename, path, media_type = item

            try:
                card = PhotoCard(
                    self.scroll,
                    media_id,
                    filename,
                    path,
                    thumbnail_service=self.thumbnail_service
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
                logger.error(
                    "Intelligence card render failed path=%s",
                    path,
                    exc_info=(
                        type(ex),
                        ex,
                        ex.__traceback__
                    )
                )

            rendered += 1

        self.loaded += rendered
        self.update_info()

        if self.pending_cards:
            self.after(
                50,
                self.render_card_chunk
            )
            return

        self.loading_cards = False

        if self.loaded >= self.total:
            self.more.configure(
                state="disabled",
                text="All Matching Media Loaded"
            )
        else:
            self.more.configure(
                state="normal",
                text="Load More"
            )

    ##########################################################

    def update_info(self):

        self.info.configure(
            text=f"Showing {self.loaded:,} of {self.total:,} matching media"
        )

    ##########################################################

    def update_filter_summary(self):

        parts = []

        for key, label in self.SECTIONS:

            values = self.filters.get(key, [])

            if values:
                parts.append(
                    f"{label}: {', '.join(self.format_label(v) for v in values)}"
                )

        self.selected_filters.configure(
            text=" | ".join(parts)
        )

    ##########################################################

    def format_label(self, value):

        return str(value).replace(
            "_",
            " "
        ).title()

    ##########################################################

    def destroy(self):

        if hasattr(self, "thumbnail_service"):
            self.thumbnail_service.shutdown()

        super().destroy()
