import customtkinter as ctk
from tkinter import BooleanVar, messagebox
from collections import deque

import gui.photo_card as photo_card_module
from gui.gallery_analysis_inspector import GalleryAnalysisInspector
from gui.photo_card import PhotoCard
from services.brain_service import BrainService
from services.gallery_service import GalleryService
from services.gallery_analysis_inspector_service import GalleryAnalysisInspectorService
from services.photo_review_workflow_service import PhotoReviewWorkflowService
from services.thumbnail_service import ThumbnailService


class GalleryPage(ctk.CTkFrame):

    PAGE_SIZE = 200
    CARD_RENDER_CHUNK = 1
    CARD_RENDER_DELAY_MS = 150
    MAX_SELECTION_IDS = 10000
    ACTIVE_QUEUE_POLL_MS = 1000
    IDLE_QUEUE_POLL_MS = 4000
    session_panel_collapsed = False

    def __init__(self, parent):

        super().__init__(parent)

        self.service = GalleryService()
        self.review_workflow = PhotoReviewWorkflowService()
        self.brain = None

        self.media = []

        self.loaded = 0
        self.total = 0
        self.selected = set()
        self.visible_media_ids = set()
        self.visible_media_types = {}
        self.cards_by_media_id = {}
        self.selected_inspector_media_id = None
        self.viewer = None
        self.thumbnail_service = ThumbnailService()
        self.inspector_service = GalleryAnalysisInspectorService()
        self.loading_cards = False
        self._destroyed = False
        self._queue_poll_after_id = None
        self._queue_poll_token = 0
        self.queue_summary = {}
        self.selected_eligible_count = 0
        self.selection_preview = {}
        self.session_panel_collapsed = self.__class__.session_panel_collapsed
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

        self.approve_selected_button = ctk.CTkButton(
            actions,
            text="Approve Selected",
            command=self.approve_selected_review_items
        )

        self.approve_selected_button.pack(
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
            variable=self.force_reanalysis_var,
            command=self.analysis_options_changed
        )
        self.force_checkbox.pack(
            side="left",
            padx=(12, 0)
        )

        self.retry_failed_checkbox = ctk.CTkCheckBox(
            actions,
            text="Retry failed",
            variable=self.retry_failed_var,
            command=self.analysis_options_changed
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

        self.build_analysis_status_panel()

        self.content = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.content.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_columnconfigure(1, weight=0)
        self.content.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self.content)

        self.scroll.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 12)
        )

        self.inspector = GalleryAnalysisInspector(
            self.content,
            service=self.inspector_service,
            next_callback=self.select_next_inspector_item,
            previous_callback=self.select_previous_inspector_item,
            review_callback=self.review_state_changed,
            reanalyze_callback=self.reanalyze_media_from_inspector
        )
        self.inspector.grid(
            row=0,
            column=1,
            sticky="ns"
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
        self.refresh_queue_summary()
        self.start_queue_polling()

    ########################################################

    def build_analysis_status_panel(self):

        self.analysis_panel = ctk.CTkFrame(
            self,
            fg_color="#20242b",
            corner_radius=8
        )
        self.analysis_panel.pack(
            fill="x",
            padx=20,
            pady=(10, 0)
        )
        self.analysis_panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(
            self.analysis_panel,
            fg_color="transparent"
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=(8, 4)
        )
        header.grid_columnconfigure(0, weight=1)

        self.queue_title = ctk.CTkLabel(
            header,
            text="Analysis Queue",
            font=("Segoe UI", 15, "bold"),
            anchor="w"
        )
        self.queue_title.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.session_toggle_button = ctk.CTkButton(
            header,
            text="Session Details",
            width=130,
            height=28,
            command=self.toggle_session_panel
        )
        self.session_toggle_button.grid(
            row=0,
            column=1,
            padx=(8, 0)
        )

        self.queue_summary_label = ctk.CTkLabel(
            self.analysis_panel,
            text="Selected: 0 | Queue idle",
            anchor="w",
            justify="left",
            wraplength=900
        )
        self.queue_summary_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 4)
        )

        self.queue_detail_label = ctk.CTkLabel(
            self.analysis_panel,
            text="Estimated time unavailable",
            anchor="w",
            justify="left",
            wraplength=900,
            font=("Segoe UI", 11)
        )
        self.queue_detail_label.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 6)
        )

        controls = ctk.CTkFrame(
            self.analysis_panel,
            fg_color="transparent"
        )
        controls.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 8)
        )

        self.pause_resume_button = ctk.CTkButton(
            controls,
            text="Pause Queue",
            width=120,
            command=self.pause_or_resume_queue
        )
        self.pause_resume_button.pack(
            side="left",
            padx=(0, 8)
        )

        self.cancel_queue_button = ctk.CTkButton(
            controls,
            text="Cancel Queue",
            width=120,
            fg_color="#7a3434",
            hover_color="#963f3f",
            command=self.cancel_queue
        )
        self.cancel_queue_button.pack(
            side="left",
            padx=(0, 8)
        )

        self.retry_failed_button = ctk.CTkButton(
            controls,
            text="Retry Failed",
            width=120,
            command=self.retry_failed_queue
        )
        self.retry_failed_button.pack(
            side="left",
            padx=(0, 8)
        )

        self.open_ai_dashboard_button = ctk.CTkButton(
            controls,
            text="Open AI Dashboard",
            width=150,
            command=self.open_ai_dashboard
        )
        self.open_ai_dashboard_button.pack(
            side="left"
        )

        self.session_panel = ctk.CTkFrame(
            self.analysis_panel,
            fg_color="#171a20",
            corner_radius=8
        )
        self.session_panel.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 10)
        )

        self.session_detail_label = ctk.CTkLabel(
            self.session_panel,
            text="No current analysis session.",
            anchor="w",
            justify="left",
            wraplength=900,
            font=("Segoe UI", 11)
        )
        self.session_detail_label.pack(
            fill="x",
            padx=10,
            pady=8
        )

        self.apply_session_panel_state()

    ########################################################

    def refresh_queue_summary(self):

        if self._destroyed:
            return

        try:
            summary = self.service.analysis_queue_summary()
        except Exception as ex:
            self.queue_summary_label.configure(
                text=f"Analysis Queue: status unavailable ({ex})"
            )
            return

        self.queue_summary = summary
        brain = self.brain_service()
        selected_count = len(self.selected)
        eligible_count = self.selected_eligible_count
        provider = summary.get("provider") or brain.vision.provider_key()
        model = summary.get("model") or brain.vision.model_name()
        total = int(summary.get("total") or 0)
        completed = int(summary.get("completed") or 0)
        failed = int(summary.get("failed") or 0)
        cancelled = int(summary.get("cancelled") or 0)
        queued = int(summary.get("queued") or 0)
        running = int(summary.get("running") or 0)
        progress = int(summary.get("progress_percent") or 0)
        current = summary.get("current_filename") or "No active media"
        status = summary.get("status", "Idle")
        session_id = summary.get("session_id")
        active_workers = (
            1
            if session_id and brain.session_has_active_worker(session_id)
            else 0
        )

        if total:
            headline = (
                f"Selected: {selected_count:,} | Eligible: {eligible_count:,} | "
                f"{completed:,} of {total:,} complete | Progress: {progress}%"
            )
        else:
            headline = (
                f"Selected: {selected_count:,} | Eligible: {eligible_count:,} | "
                "Queue idle"
            )

        if summary.get("recoverable"):
            headline += " | Previous analysis session found"

        self.queue_summary_label.configure(text=headline)
        selection_reason = self.selection_reason_summary()
        self.queue_detail_label.configure(
            text=(
                f"Running: {running:,} | Queued: {queued:,} | "
                f"Failed: {failed:,} | Cancelled: {cancelled:,} | "
                f"Current: {current} | Provider: {provider} | Model: {model} | "
                f"Elapsed: {summary.get('elapsed', '0s')} | "
                f"{summary.get('eta', 'Estimated time unavailable')}"
                f"{selection_reason}"
            )
        )
        self.session_detail_label.configure(
            text=(
                f"Status: {status}\n"
                f"Session: {summary.get('session_id', '') or 'None'} | "
                f"Created: {summary.get('created_at', '') or 'Unknown'}\n"
                f"Total: {total:,} | Completed: {completed:,} | "
                f"Failed: {failed:,} | Remaining: {summary.get('remaining', 0):,}\n"
                f"Active workers: {active_workers:,} | Worker status: "
                f"{summary.get('worker_status', '') or 'Idle'} | "
                f"Resume count: {summary.get('resume_count', 0)}\n"
                f"{self.session_action_text(summary, active_workers)}"
            )
        )
        button_text, button_state = self.session_primary_control(summary, active_workers)
        self.pause_resume_button.configure(
            text=button_text,
            state=button_state
        )

    ########################################################

    def refresh_visible_analysis_statuses(self):

        if self._destroyed or not self.visible_media_ids:
            return

        try:
            statuses = self.service.analysis_media_statuses(
                list(self.visible_media_ids)
            )
        except Exception:
            return

        selected_status_changed = False
        for media_id, status in statuses.items():
            card = self.cards_by_media_id.get(int(media_id))
            if not card:
                continue
            if status and card.analysis_status != status:
                card.set_analysis_status(status)
                if int(media_id) == int(self.selected_inspector_media_id or 0):
                    selected_status_changed = True

        if selected_status_changed:
            card = self.cards_by_media_id.get(
                int(self.selected_inspector_media_id or 0)
            )
            if card:
                self.inspector.inspect_media(
                    card.media_id,
                    card.filename,
                    card.filepath,
                    media_type=card.media_type
                )

    ########################################################

    def start_queue_polling(self):

        self._queue_poll_token += 1
        self.schedule_queue_poll(active=False)

    def schedule_queue_poll(self, active=False):

        if self._destroyed:
            return

        delay = self.ACTIVE_QUEUE_POLL_MS if active else self.IDLE_QUEUE_POLL_MS
        token = self._queue_poll_token
        self._queue_poll_after_id = self.after(
            delay,
            lambda: self.poll_analysis_queue(token)
        )

    def poll_analysis_queue(self, token):

        if self._destroyed or token != self._queue_poll_token:
            return

        self.refresh_queue_summary()
        self.refresh_visible_analysis_statuses()
        active = bool(
            self.queue_summary.get("queued")
            or self.queue_summary.get("running")
            or self.queue_summary.get("status") in (
                "Queued",
                "Starting",
                "Running",
                "Recoverable",
                "Interrupted"
            )
        )
        self.schedule_queue_poll(active=active)

    ########################################################

    def current_eligible_selection_count(self):

        if not self.selected:
            return 0

        try:
            preview = self.service.analysis_selection_preview(
                list(self.selected),
                force=bool(self.force_reanalysis_var.get()),
                retry_failed=bool(self.retry_failed_var.get())
            )
            self.selection_preview = preview
            return len(preview.get("queueable_ids", []))
        except Exception:
            self.selection_preview = {}
            return 0

    def update_selected_eligible_count(self):

        self.selected_eligible_count = self.current_eligible_selection_count()
        return self.selected_eligible_count

    def analysis_options_changed(self):

        self.update_selected_eligible_count()
        self.refresh_queue_summary()

    ########################################################

    def toggle_session_panel(self):

        self.session_panel_collapsed = not self.session_panel_collapsed
        self.__class__.session_panel_collapsed = self.session_panel_collapsed
        self.apply_session_panel_state()

    def apply_session_panel_state(self):

        if self.session_panel_collapsed:
            self.session_panel.grid_remove()
            self.session_toggle_button.configure(text="Show Session")
        else:
            self.session_panel.grid()
            self.session_toggle_button.configure(text="Hide Session")

    ########################################################

    def session_primary_control(self, summary, active_workers):

        status = summary.get("status", "Idle")

        if status in ("Recoverable", "Interrupted"):
            return "Resume Session", "normal"

        if status == "Paused":
            return "Resume Queue", "normal"

        if status in ("Running", "Starting", "Queued") or active_workers:
            return "Pause Queue", "normal"

        return "Pause Queue", "disabled"

    def session_action_text(self, summary, active_workers):

        status = summary.get("status", "Idle")
        reason = summary.get("worker_stop_reason") or ""

        if status in ("Recoverable", "Interrupted"):
            lines = [
                "Processing is stopped. Use Resume Session to validate the provider and restart the worker."
            ]
            if reason:
                lines.append("Last stop reason: " + reason)
            return "\n".join(lines)

        if status == "Paused":
            return "Processing is paused. Use Resume Queue to continue."

        if active_workers:
            return "Worker is active; Gallery will update on the next polling interval."

        return "No live worker is attached to this session."

    ########################################################

    def pause_or_resume_queue(self):

        summary = self.queue_summary or {}
        brain = self.brain_service()
        status = summary.get("status")
        session_id = summary.get("session_id")
        active_worker = (
            brain.session_has_active_worker(session_id)
            if session_id
            else False
        )

        if status in ("Recoverable", "Interrupted"):
            handle = brain.resume_previous_analysis(
                session_id,
                progress_callback=self.analysis_progress
            )
            self.info.configure(text=self.resume_handle_text(handle))
            self.start_queue_polling()
        elif status == "Paused":
            if active_worker:
                brain.resume_queue()
                self.info.configure(text="Analysis queue resumed")
            else:
                handle = brain.resume_previous_analysis(
                    session_id,
                    progress_callback=self.analysis_progress
                )
                self.info.configure(text=self.resume_handle_text(handle))
            self.start_queue_polling()
        elif status in ("Running", "Starting", "Queued"):
            brain.pause_queue()
            self.info.configure(text="Analysis queue paused")
        else:
            self.info.configure(text="No active analysis queue to control")
        self.refresh_queue_summary()

    def resume_handle_text(self, handle):

        future = getattr(handle, "future", None)
        if future and future.done():
            try:
                result = future.result(timeout=0)
            except Exception as error:
                return f"Resume failed: {error}"
            if result.get("resumed") is False:
                return "Resume blocked: " + result.get("reason", "preflight failed")

        return f"Resume requested for {len(handle):,} queued item(s)"

    def cancel_queue(self):

        if not messagebox.askyesno(
            "Cancel Queue",
            "Cancel queued analysis items? Running work may finish or fail safely."
        ):
            return

        canceled = self.brain_service().cancel_queued_jobs()
        self.info.configure(text=f"Cancelled {canceled:,} queued item(s)")
        self.refresh_queue_summary()
        self.refresh_visible_analysis_statuses()

    def retry_failed_queue(self):

        handle = self.brain_service().retry_failed_analysis(
            progress_callback=self.analysis_progress
        )
        self.info.configure(text=f"Retrying {len(handle):,} failed item(s)")
        self.refresh_queue_summary()
        self.start_queue_polling()

    def open_ai_dashboard(self):

        root = self.winfo_toplevel()
        if hasattr(root, "show_ai_dashboard"):
            root.show_ai_dashboard()

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
                    selected=media_id in self.selected,
                    open_callback=self.open_card_viewer,
                    inspect_callback=self.inspect_card,
                    quick_approve_callback=self.quick_approve_media,
                    quick_reject_callback=self.quick_reject_media
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
        self.refresh_visible_analysis_statuses()
        self.refresh_queue_summary()

    ########################################################

    def open_card_viewer(self, card):

        context = self.review_workflow.context_from_ids(
            self.current_context_ids(),
            card.media_id,
            label=self.filter_var.get(),
            review_required_only=self.current_filter() == "review_required"
        )

        self.viewer = photo_card_module.PhotoViewer(
            self,
            card.media_id,
            card.filename,
            card.filepath,
            review_context=context,
            review_update_callback=self.review_state_changed
        )

    ########################################################

    def inspect_card(self, card):

        self.selected_inspector_media_id = int(card.media_id)
        self.inspector.inspect_media(
            card.media_id,
            card.filename,
            card.filepath,
            media_type=card.media_type
        )
        self.highlight_inspected_card()

    ########################################################

    def highlight_inspected_card(self):

        for media_id, card in self.cards_by_media_id.items():
            if int(media_id) == int(self.selected_inspector_media_id or 0):
                card.configure(border_width=2, border_color="#4ea1ff")
            else:
                card.configure(border_width=0)

    ########################################################

    def select_next_inspector_item(self):

        next_id = self.next_context_media_id()
        if next_id:
            self.select_inspector_media(next_id)

    ########################################################

    def select_previous_inspector_item(self):

        previous_id = self.previous_context_media_id()
        if previous_id:
            self.select_inspector_media(previous_id)

    ########################################################

    def next_context_media_id(self):

        ids = self.current_context_ids()
        if not ids:
            return None

        try:
            position = ids.index(int(self.selected_inspector_media_id))
        except Exception:
            return ids[0]

        for candidate in ids[position + 1:]:
            if self.current_filter() == "review_required":
                card = self.cards_by_media_id.get(candidate)
                if card and card.analysis_status != "Real - Review Required":
                    continue
            return candidate

        return None

    ########################################################

    def previous_context_media_id(self):

        ids = self.current_context_ids()
        if not ids:
            return None

        try:
            position = ids.index(int(self.selected_inspector_media_id))
        except Exception:
            return ids[-1]

        if position <= 0:
            return None

        return ids[position - 1]

    ########################################################

    def select_inspector_media(self, media_id):

        card = self.cards_by_media_id.get(int(media_id))

        if card is None:
            return

        self.inspect_card(card)

    ########################################################

    def reanalyze_media_from_inspector(self, media_id):

        card = self.cards_by_media_id.get(int(media_id))

        if card is not None:
            card.set_analysis_status("Queued")

    ########################################################

    def current_context_ids(self):

        ids = [
            int(media_id)
            for media_id in self.visible_media_ids
        ]

        if self.selected:
            ids = [
                media_id
                for media_id in ids
                if media_id in self.selected
            ] or list(self.selected)

        return sorted(
            ids,
            key=lambda media_id: self.loaded_position(media_id)
        )

    ########################################################

    def loaded_position(self, media_id):

        for index, child in enumerate(self.scroll.winfo_children()):
            if isinstance(child, PhotoCard) and child.media_id == media_id:
                return index

        return 999999

    ########################################################

    def quick_approve_media(self, media_id):

        self.review_workflow.review.approve(
            media_id,
            notes="Quick approved from Gallery"
        )
        self.review_state_changed(media_id, "approved")

    ########################################################

    def quick_reject_media(self, media_id):

        self.review_workflow.review.reject(
            media_id,
            notes="Quick rejected from Gallery"
        )
        self.review_state_changed(media_id, "rejected")

    ########################################################

    def approve_selected_review_items(self):

        if not self.selected:
            self.info.configure(
                text="No media selected for approval"
            )
            return

        preview = self.review_workflow.approve_selected_preview(
            list(self.selected)
        )

        if not preview["eligible_count"]:
            messagebox.showinfo(
                "Approve Selected",
                (
                    f"Selected: {preview['selected_count']:,}\n"
                    "Eligible review-required items: 0\n"
                    f"Ineligible skipped: {preview['ineligible_count']:,}"
                )
            )
            return

        if not messagebox.askyesno(
            "Approve Selected",
            (
                "Approve selected review-required media?\n\n"
                f"Selected: {preview['selected_count']:,}\n"
                f"Eligible: {preview['eligible_count']:,}\n"
                f"Ineligible skipped: {preview['ineligible_count']:,}\n\n"
                "Failed, rejected, corrected, mock, and unanalyzed items "
                "will not be approved."
            )
        ):
            return

        result = self.review_workflow.approve_selected(
            list(self.selected),
            notes="Bulk approved from Gallery"
        )

        for media_id in result["approved_ids"]:
            self.review_state_changed(media_id, "approved")

        self.info.configure(
            text=(
                f"Approved {result['approved_count']:,}; "
                f"skipped {result['ineligible_count']:,} ineligible"
            )
        )

    ########################################################

    def review_state_changed(self, media_id, review_status):

        status_map = {
            "approved": "Real - Approved",
            "corrected": "Real - Corrected",
            "rejected": "Real - Rejected",
            "reanalyze_requested": "Real - Review Required"
        }
        card = self.cards_by_media_id.get(int(media_id))

        if card is not None:
            card.set_analysis_status(
                status_map.get(review_status, card.analysis_status)
            )

        if self.current_filter() == "review_required" and review_status in (
            "approved",
            "corrected",
            "rejected"
        ):
            self.total = max(0, self.total - 1)
            self.info.configure(
                text=f"Showing {self.loaded:,} of {self.total:,} media"
            )

        self.refresh_selection_controls()
        self.highlight_inspected_card()
        self.refresh_queue_summary()

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
        self.update_selected_eligible_count()
        self.refresh_queue_summary()

        if selected:
            card = self.cards_by_media_id.get(int(media_id))
            if card:
                self.inspect_card(card)

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
        self.selected_inspector_media_id = None
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
        self.update_selected_eligible_count()
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
        self.refresh_queue_summary()

    ########################################################

    def select_all_visible(self):

        self.selected.update(self.visible_media_ids)
        self.refresh_visible_selection_state()
        self.update_selected_label()
        self.refresh_queue_summary()

    ########################################################

    def select_all_current_filter(self):

        ids = self.selection_ids_for_current_filter()
        self.selected.update(ids)
        self.refresh_visible_selection_state()
        self.update_selected_label()
        self.refresh_queue_summary()

    ########################################################

    def select_all_photos(self):

        ids = self.selection_ids_for_current_filter(media_type="image")
        self.selected.update(ids)
        self.refresh_visible_selection_state()
        self.update_selected_label()
        self.refresh_queue_summary()

    ########################################################

    def select_all_videos(self):

        ids = self.selection_ids_for_current_filter(media_type="video")
        self.selected.update(ids)
        self.refresh_visible_selection_state()
        self.update_selected_label()
        self.refresh_queue_summary()

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
        self.refresh_queue_summary()

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
        self.update_selected_eligible_count()
        self.refresh_queue_summary()

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

        for media_id in queueable:
            card = self.cards_by_media_id.get(int(media_id))
            if card is not None:
                card.set_analysis_status("Queued")

        self.info.configure(
            text=(
                f"Queued {len(queueable):,} selected media for analysis. "
                "Selection preserved."
            )
        )
        self.refresh_queue_summary()
        self.refresh_visible_analysis_statuses()
        self.start_queue_polling()

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
                f"Already queued: {preview.get('already_queued_count', 0):,}",
                f"Queued in recoverable session: {preview.get('queued_in_recoverable_count', 0):,}",
                f"Queued in running session: {preview.get('queued_in_running_count', 0):,}",
                f"Missing file/path: {preview.get('missing_file_count', 0):,}",
                f"Failed requiring Retry Failed: {preview.get('failed_requires_retry_count', 0):,}",
                f"Eligible to queue: {len(preview.get('queueable_ids', [])):,}",
                self.analysis_reason_text(preview),
                f"Provider: {provider}",
                f"Model: {model}",
                f"Force reanalysis: {preview.get('force_reanalysis', False)}",
                f"Retry failed: {preview.get('retry_failed', False)}",
                "Estimated Qwen time: depends on local model load and media complexity."
            ]
        )

    def analysis_reason_text(self, preview):

        reasons = preview.get("reason_counts") or {}

        if not reasons:
            return "Skipped reasons: none"

        lines = [
            "Skipped reasons:"
        ]
        for reason, count in sorted(reasons.items()):
            lines.append(f"- {reason}: {count:,}")

        return "\n".join(lines)

    def selection_reason_summary(self):

        if not self.selected or self.selected_eligible_count:
            return ""

        reasons = self.selection_preview.get("reason_counts") or {}
        if not reasons:
            return " | Selection blocked: no queueable reason available"

        reason, count = sorted(
            reasons.items(),
            key=lambda item: item[1],
            reverse=True
        )[0]
        return f" | Selection blocked: {reason} ({count:,})"

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
            lambda: self.analysis_progress_update(text)
        )

    ########################################################

    def analysis_progress_update(self, text):

        if self._destroyed:
            return

        self.info.configure(text=text)
        self.refresh_queue_summary()
        self.refresh_visible_analysis_statuses()

    ########################################################

    def destroy(self):

        self._destroyed = True
        self._queue_poll_token += 1
        if self._queue_poll_after_id:
            try:
                self.after_cancel(self._queue_poll_after_id)
            except Exception:
                pass

        if hasattr(self, "thumbnail_service"):
            self.thumbnail_service.shutdown()

        super().destroy()
