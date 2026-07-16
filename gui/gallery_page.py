import customtkinter as ctk
from tkinter import BooleanVar, messagebox
from collections import deque

from gui.photo_card import PhotoCard
from services.brain_service import BrainService
from services.gallery_service import GalleryService
from services.thumbnail_service import ThumbnailService


class GalleryPage(ctk.CTkFrame):

    PAGE_SIZE = 200
    CARD_RENDER_CHUNK = 4
    CARD_RENDER_DELAY_MS = 50
    MAX_SELECTION_IDS = 10000

    def __init__(self, parent):

        super().__init__(parent)

        self.service = GalleryService()
        self.brain = None

        self.media = []

        self.loaded = 0
        self.total = 0
        self.selected = set()
        self.visible_media_ids = set()
        self.visible_media_types = {}
        self.cards_by_media_id = {}
        self.thumbnail_service = ThumbnailService()
        self.loading_cards = False
        self.pending_cards = deque()
        self.filter_var = ctk.StringVar(value="All Media")
        self.sort_var = ctk.StringVar(value="Added Date: Newest First")
        self.force_reanalysis_var = BooleanVar(value=False)
        self.retry_failed_var = BooleanVar(value=False)
        self.filter_map = {
            "All Media": "all",
            "Photos": "photos",
            "Videos": "videos",
            "Highest Reel Potential": "highest_reel_potential",
            "Training Videos": "training_videos",
            "Incident Videos": "incident_videos",
            "Community Videos": "community_videos",
            "Recruitment Videos": "recruitment_videos",
            "Reviewed Videos": "reviewed_videos",
            "Unreviewed Videos": "unreviewed_videos",
            "Filesystem: Training": "filesystem_training",
            "Filesystem: Incidents": "filesystem_incidents",
            "Filesystem: Apparatus": "filesystem_apparatus",
            "Filesystem: Programs": "filesystem_programs",
            "Filesystem: Campaigns": "filesystem_campaigns",
            "Filesystem: Community": "filesystem_community",
            "Filesystem: Conflicts": "filesystem_conflicts",
            "Has Filesystem Intelligence": "has_filesystem_intelligence",
            "Missing Filesystem Intelligence": "missing_filesystem_intelligence",
            "Added Today": "added_today",
            "Captured Today": "captured_today",
            "Last 7 Days": "last_7_days",
            "Last 30 Days": "last_30_days",
            "Last 12 Months": "last_12_months",
            "Not Analyzed": "not_analyzed",
            "Analyzed": "analyzed",
            "Real Analysis": "real_analysis",
            "Review Required": "review_required",
            "Approved": "approved",
            "Corrected": "corrected",
            "Rejected": "rejected",
            "Failed": "failed",
            "Mock/Test Data": "mock_test_data",
            "Photos Not Analyzed": "photos_not_analyzed",
            "Videos Not Analyzed": "videos_not_analyzed"
        }
        self.sort_map = {
            "Added Date: Newest First": "added_newest",
            "Added Date: Oldest First": "added_oldest",
            "Capture Date: Newest First": "capture_newest",
            "Capture Date: Oldest First": "capture_oldest",
            "Analysis Date: Newest First": "analysis_newest",
            "Analysis Date: Oldest First": "analysis_oldest",
            "Not Analyzed First": "not_analyzed_first",
            "Review Required First": "review_required_first",
            "Corrected First": "corrected_first",
            "Failed First": "failed_first",
            "Filename A-Z": "filename_az",
            "Filename Z-A": "filename_za"
        }

        self.build_page()

    ########################################################

    def brain_service(self):

        if self.brain is None:
            self.brain = BrainService()

        return self.brain

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

        self.filter_menu = ctk.CTkOptionMenu(
            actions,
            values=list(self.filter_map.keys()),
            variable=self.filter_var,
            command=self.filter_changed,
            width=170
        )

        self.filter_menu.pack(
            side="left",
            padx=(0, 10)
        )

        self.sort_menu = ctk.CTkOptionMenu(
            actions,
            values=list(self.sort_map.keys()),
            variable=self.sort_var,
            command=self.sort_changed,
            width=230
        )
        self.sort_menu.pack(
            side="left",
            padx=(0, 10)
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

        self.clear_selected_button = ctk.CTkButton(
            actions,
            text="Clear Selection",
            command=self.clear_selection
        )

        self.clear_selected_button.pack(
            side="left"
        )

        self.force_checkbox = ctk.CTkCheckBox(
            actions,
            text="Force reanalysis",
            variable=self.force_reanalysis_var
        )
        self.force_checkbox.pack(
            side="left",
            padx=(12, 0)
        )

        self.retry_failed_checkbox = ctk.CTkCheckBox(
            actions,
            text="Retry failed",
            variable=self.retry_failed_var
        )
        self.retry_failed_checkbox.pack(
            side="left",
            padx=(10, 0)
        )

        bulk_actions = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        bulk_actions.pack(
            fill="x",
            padx=20,
            pady=(8, 0)
        )

        self.select_all_visible_button = ctk.CTkButton(
            bulk_actions,
            text="Select All Visible",
            command=self.select_all_visible,
            width=140
        )
        self.select_all_visible_button.pack(
            side="left",
            padx=(0, 8)
        )

        self.select_all_filter_button = ctk.CTkButton(
            bulk_actions,
            text="Select All 0",
            command=self.select_all_current_filter,
            width=130
        )
        self.select_all_filter_button.pack(
            side="left",
            padx=(0, 8)
        )

        self.invert_selection_button = ctk.CTkButton(
            bulk_actions,
            text="Invert Selection",
            command=self.invert_selection,
            width=130
        )
        self.invert_selection_button.pack(
            side="left",
            padx=(0, 8)
        )

        self.select_all_photos_button = ctk.CTkButton(
            bulk_actions,
            text="Select All Photos",
            command=self.select_all_photos,
            width=135
        )
        self.select_all_photos_button.pack(
            side="left",
            padx=(0, 8)
        )

        self.select_all_videos_button = ctk.CTkButton(
            bulk_actions,
            text="Select All Videos",
            command=self.select_all_videos,
            width=135
        )
        self.select_all_videos_button.pack(
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

        self.total = self.service.media_count(
            self.current_filter()
        )
        self.refresh_selection_controls()

        self.load_more()

    ########################################################

    def load_more(self):

        if self.loading_cards:
            return

        media = self.service.get_media_page(
            self.PAGE_SIZE,
            self.loaded,
            self.current_filter(),
            self.current_sort()
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
            duration_seconds = item[5] if len(item) > 5 else 0
            date_label = item[7] if len(item) > 7 and item[7] else (
                item[6] if len(item) > 6 else ""
            )
            filesystem_badge = item[8] if len(item) > 8 else ""

            try:

                card = PhotoCard(
                    self.scroll,
                    media_id,
                    filename,
                    path,
                    thumbnail_service=self.thumbnail_service,
                    selection_callback=self.selection_changed,
                    analysis_status=analysis_status,
                    media_type=media_type,
                    duration_seconds=duration_seconds,
                    date_label=date_label,
                    filesystem_badge=filesystem_badge,
                    selected=media_id in self.selected
                )

                self.visible_media_ids.add(media_id)
                self.visible_media_types[media_id] = media_type
                self.cards_by_media_id[media_id] = card

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

        self.refresh_selection_controls()

    ########################################################

    def selection_changed(self, media_id, selected):

        if selected:
            self.selected.add(media_id)
        else:
            self.selected.discard(media_id)

        self.selected_label.configure(
            text=f"Selected: {len(self.selected):,}"
        )
        self.refresh_visible_selection_state()

    ########################################################

    def current_filter(self):

        return self.filter_map.get(
            self.filter_var.get(),
            "all"
        )

    ########################################################

    def current_sort(self):

        return self.sort_map.get(
            self.sort_var.get(),
            "added_newest"
        )

    ########################################################

    def filter_changed(self, _value=None):

        if self.loading_cards:
            return

        self.loaded = 0
        self.selected.clear()
        self.visible_media_ids.clear()
        self.visible_media_types.clear()
        self.cards_by_media_id.clear()
        self.pending_cards.clear()
        self.total = self.service.media_count(
            self.current_filter()
        )

        for child in self.scroll.winfo_children():
            child.destroy()

        self.selected_label.configure(
            text="Selected: 0"
        )
        self.refresh_selection_controls()
        self.more.configure(
            state="normal",
            text="Load More"
        )
        self.load_more()

    ########################################################

    def sort_changed(self, _value=None):

        self.filter_changed(_value)

    ########################################################

    def clear_selection(self):

        self.selected.clear()
        self.refresh_visible_selection_state()
        self.update_selected_label()

    ########################################################

    def select_all_visible(self):

        self.selected.update(self.visible_media_ids)
        self.refresh_visible_selection_state()
        self.update_selected_label()

    ########################################################

    def select_all_current_filter(self):

        ids = self.selection_ids_for_current_filter()
        self.selected.update(ids)
        self.refresh_visible_selection_state()
        self.update_selected_label()

    ########################################################

    def select_all_photos(self):

        ids = self.selection_ids_for_current_filter(media_type="image")
        self.selected.update(ids)
        self.refresh_visible_selection_state()
        self.update_selected_label()

    ########################################################

    def select_all_videos(self):

        ids = self.selection_ids_for_current_filter(media_type="video")
        self.selected.update(ids)
        self.refresh_visible_selection_state()
        self.update_selected_label()

    ########################################################

    def invert_selection(self):

        ids = set(
            self.selection_ids_for_current_filter()
        )

        for media_id in ids:
            if media_id in self.selected:
                self.selected.discard(media_id)
            else:
                self.selected.add(media_id)

        self.refresh_visible_selection_state()
        self.update_selected_label()

    ########################################################

    def selection_ids_for_current_filter(self, media_type=None):

        return self.service.get_media_ids_for_selection(
            filter_key=self.current_filter(),
            media_type=media_type,
            limit=self.MAX_SELECTION_IDS
        )

    ########################################################

    def refresh_visible_selection_state(self):

        for child in self.scroll.winfo_children():

            if isinstance(child, PhotoCard):
                child.set_selected(
                    child.media_id in self.selected
                )

    ########################################################

    def update_selected_label(self):

        self.selected_label.configure(
            text=f"Selected: {len(self.selected):,}"
        )

    ########################################################

    def refresh_selection_controls(self):

        filter_key = self.current_filter()
        total = self.total
        photos = self.service.media_count_for_selection(
            filter_key=filter_key,
            media_type="image"
        )
        videos = self.service.media_count_for_selection(
            filter_key=filter_key,
            media_type="video"
        )

        if total > self.MAX_SELECTION_IDS:
            select_text = (
                f"Select First {self.MAX_SELECTION_IDS:,} "
                f"of {total:,}"
            )
        else:
            select_text = f"Select All {total:,}"

        self.select_all_filter_button.configure(
            text=select_text
        )
        self.select_all_visible_button.configure(
            text=f"Select All Visible {len(self.visible_media_ids):,}"
        )
        self.select_all_photos_button.configure(
            text=f"Select All Photos {photos:,}"
        )
        self.select_all_videos_button.configure(
            text=f"Select All Videos {videos:,}"
        )

    ########################################################

    def analyze_selected(self):

        if not self.selected:
            self.info.configure(text="No media selected for analysis")
            return

        force = bool(self.force_reanalysis_var.get())
        retry_failed = bool(self.retry_failed_var.get())
        preview = self.service.analysis_selection_preview(
            list(self.selected),
            force=force,
            retry_failed=retry_failed
        )
        queueable = preview.get("queueable_ids", [])

        if not queueable:
            messagebox.showinfo(
                "Analyze Selected",
                self.analysis_preview_text(preview) +
                "\n\nNo selected media will be queued with the current options."
            )
            return

        if not messagebox.askyesno(
            "Analyze Selected",
            self.analysis_preview_text(preview) +
            "\n\nQueue the eligible media now?"
        ):
            return

        brain = self.brain_service()
        warning = brain.provider_bulk_warning()

        if warning:
            if not messagebox.askyesno(
                "Confirm AI Analysis",
                warning + "\n\nContinue?"
            ):
                return

        handle = brain.analyze_selected(
            queueable,
            force=force,
            progress_callback=self.analysis_progress
        )

        self.info.configure(
            text=f"Queued {len(queueable):,} selected media for analysis"
        )

    ########################################################

    def analysis_preview_text(self, preview):

        brain = self.brain_service()
        provider = brain.vision.provider_key()
        model = brain.vision.model_name()

        return "\n".join(
            [
                f"Selected: {preview.get('selected_count', 0):,}",
                f"Photos: {preview.get('photo_count', 0):,}",
                f"Videos: {preview.get('video_count', 0):,}",
                f"Genuinely unanalyzed: {preview.get('genuinely_unanalyzed_count', 0):,}",
                f"Completed real analysis: {preview.get('completed_real_analysis_count', 0):,}",
                f"Mock-only: {preview.get('mock_only_count', 0):,}",
                f"Failed: {preview.get('failed_count', 0):,}",
                f"Retryable failed: {preview.get('retryable_failed_count', 0):,}",
                f"Video metadata-only: {preview.get('video_metadata_only_count', 0):,}",
                f"Eligible to queue: {len(preview.get('queueable_ids', [])):,}",
                f"Provider: {provider}",
                f"Model: {model}",
                f"Force reanalysis: {preview.get('force_reanalysis', False)}",
                f"Retry failed: {preview.get('retry_failed', False)}",
                "Estimated Qwen time: depends on local model load and media complexity."
            ]
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
