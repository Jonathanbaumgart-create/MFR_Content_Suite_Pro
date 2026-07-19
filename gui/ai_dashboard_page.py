import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path

from services.brain_service import BrainService
from services.analysis_review_service import AnalysisReviewService
from services.provider_diagnostics_service import ProviderDiagnosticsService
from services.time_service import TimeService
from services.writing_service import WritingService
from services.photo_review_workflow_service import PhotoReviewWorkflowService
from gui.window_placement import WindowPlacement
from gui.photo_viewer import PhotoViewer


class AIDashboardPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.brain = BrainService()
        self.review = AnalysisReviewService()
        self.review_workflow = PhotoReviewWorkflowService()
        self.diagnostics = ProviderDiagnosticsService()
        self.writing = WritingService()
        self.metric_labels = {}
        self.provider_var = ctk.StringVar(
            value=self.brain.vision.provider_key()
        )
        self.writing_provider_var = ctk.StringVar(
            value=self.writing.status().get("provider", "ollama")
        )

        self.build_page()
        self.refresh_metrics()

    ##########################################################

    def build_page(self):

        title = ctk.CTkLabel(
            self,
            text="AI Dashboard",
            font=("Segoe UI", 30, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        self.status = ctk.CTkLabel(
            self,
            text="Ready"
        )

        self.status.pack(
            anchor="w",
            padx=20,
            pady=(0, 5)
        )

        self.mock_notice = ctk.CTkLabel(
            self,
            text="",
            text_color="#f5c542"
        )

        self.mock_notice.pack(
            anchor="w",
            padx=20,
            pady=(0, 15)
        )

        self.create_metrics()
        self.create_provider_controls()
        self.create_diagnostics()
        self.create_controls()
        self.create_bulk_controls()

    ##########################################################

    def create_metrics(self):

        grid = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        grid.pack(
            fill="x",
            padx=10,
            pady=10
        )

        metrics = (
            ("queued", "Job Queued"),
            ("running", "Job Running"),
            ("completed", "Job Completed"),
            ("failed", "Job Failed"),
            ("provider", "Provider"),
            ("provider_model", "Vision Model"),
            ("average_analysis_time", "Avg Time"),
            ("total_analyzed", "Analyzed"),
            ("last_analyzed", "Last Analyzed"),
            ("legacy_mock_analysis", "Legacy Mock"),
            ("analysis_status", "Session"),
            ("analysis_worker_status", "Worker Status"),
            ("analysis_worker_active", "Worker Active"),
            ("analysis_heartbeat_age", "Heartbeat Age"),
            ("analysis_completed", "Session Done"),
            ("analysis_failed", "Session Failed"),
            ("analysis_skipped", "Session Skipped"),
            ("analysis_remaining", "Remaining"),
            ("analysis_current", "Current Image"),
            ("analysis_last_attempted", "Last Attempted"),
            ("analysis_speed", "Avg Speed"),
            ("analysis_eta", "ETA"),
            ("review_unreviewed", "Review Needed"),
            ("review_approved", "Approved"),
            ("review_corrected", "Corrected"),
            ("review_rejected", "Rejected"),
            ("review_failed", "Review Failed"),
            ("review_completion_percentage", "Review %"),
            ("new_media_today", "New Today"),
            ("new_photos_today", "New Photos"),
            ("new_videos_today", "New Videos"),
            ("new_unanalyzed_today", "New Unanalyzed"),
            ("new_review_required_today", "New Review"),
            ("new_approved_today", "New Approved"),
            ("new_failed_today", "New Failed")
        )

        for index, (key, label) in enumerate(metrics):

            row = index // 4
            column = index % 4

            grid.grid_columnconfigure(column, weight=1)

            card = ctk.CTkFrame(
                grid,
                height=120
            )

            card.grid(
                row=row,
                column=column,
                padx=10,
                pady=10,
                sticky="nsew"
            )

            heading = ctk.CTkLabel(
                card,
                text=label,
                font=("Segoe UI", 15, "bold")
            )

            heading.pack(
                pady=(16, 4)
            )

            value = ctk.CTkLabel(
                card,
                text="-",
                font=("Segoe UI", 24)
            )

            value.pack()

            self.metric_labels[key] = value

    ##########################################################

    def create_controls(self):

        row = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        row.pack(
            fill="x",
            padx=20,
            pady=(10, 5)
        )

        controls = (
            ("Pause Queue", self.pause_queue),
            ("Resume Queue", self.resume_queue),
            ("Resume Previous", self.resume_previous),
            ("Retry Failed", self.retry_failed),
            ("Cancel Queued Jobs", self.cancel_jobs),
            ("Clear Completed Jobs", self.clear_completed),
            ("Open Review Queue", self.open_review_queue),
            ("Review Next", self.review_next),
            ("Clear Legacy Mock Analysis", self.clear_mock_analysis)
        )

        for text, command in controls:

            button = ctk.CTkButton(
                row,
                text=text,
                command=command
            )

            button.pack(
                side="left",
                padx=(0, 10)
            )

    ##########################################################

    def create_provider_controls(self):

        panel = ctk.CTkFrame(self)

        panel.pack(
            fill="x",
            padx=20,
            pady=(5, 10)
        )

        heading = ctk.CTkLabel(
            panel,
            text="Provider Settings",
            font=("Segoe UI", 18, "bold")
        )

        heading.pack(
            anchor="w",
            padx=15,
            pady=(15, 8)
        )

        vision_label = ctk.CTkLabel(
            panel,
            text="Vision Provider",
            font=("Segoe UI", 14, "bold")
        )

        vision_label.pack(
            anchor="w",
            padx=15,
            pady=(0, 4)
        )

        row = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )

        row.pack(
            fill="x",
            padx=15,
            pady=(0, 12)
        )

        providers = self.brain.available_providers()

        self.provider_menu = ctk.CTkOptionMenu(
            row,
            values=providers,
            variable=self.provider_var,
            command=self.vision_provider_changed
        )

        self.provider_menu.pack(
            side="left",
            padx=(0, 10)
        )

        self.model_entry = ctk.CTkEntry(
            row,
            width=260,
            placeholder_text="Ollama vision model"
        )
        self.model_entry.insert(
            0,
            self.brain.vision.model_name()
        )

        self.model_entry.pack(
            side="left",
            padx=(0, 10)
        )

        apply_button = ctk.CTkButton(
            row,
            text="Apply Provider",
            command=self.apply_provider_settings
        )

        apply_button.pack(
            side="left",
            padx=(0, 10)
        )

        diagnostics_button = ctk.CTkButton(
            row,
            text="Run Diagnostics",
            command=self.run_provider_diagnostics
        )

        diagnostics_button.pack(
            side="left"
        )

        writing_label = ctk.CTkLabel(
            panel,
            text="Writing Provider",
            font=("Segoe UI", 14, "bold")
        )

        writing_label.pack(
            anchor="w",
            padx=15,
            pady=(4, 4)
        )

        writing_row = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )

        writing_row.pack(
            fill="x",
            padx=15,
            pady=(0, 12)
        )

        self.writing_provider_menu = ctk.CTkOptionMenu(
            writing_row,
            values=self.writing.available_providers(),
            variable=self.writing_provider_var,
            command=self.writing_provider_changed
        )

        self.writing_provider_menu.pack(
            side="left",
            padx=(0, 10)
        )

        self.writing_model_entry = ctk.CTkEntry(
            writing_row,
            width=260,
            placeholder_text="Ollama writing model"
        )
        self.writing_model_entry.insert(
            0,
            self.writing.model_name()
        )

        self.writing_model_entry.pack(
            side="left",
            padx=(0, 10)
        )

        writing_apply = ctk.CTkButton(
            writing_row,
            text="Apply Writing Provider",
            command=self.apply_writing_settings
        )

        writing_apply.pack(
            side="left"
        )

        guidance = ctk.CTkLabel(
            panel,
            text=(
                "If qwen2.5vl crashes with CUDA, try CPU mode, try a "
                "smaller vision model, or keep mock active for testing."
            ),
            justify="left",
            wraplength=1100,
            text_color="#f5c542"
        )

        guidance.pack(
            anchor="w",
            padx=15,
            pady=(0, 12)
        )

    ##########################################################

    def vision_provider_changed(self, provider):

        self.replace_entry_text(
            self.model_entry,
            self.provider_model(
                self.brain.vision.config,
                provider
            )
        )

    ##########################################################

    def writing_provider_changed(self, provider):

        self.replace_entry_text(
            self.writing_model_entry,
            self.provider_model(
                self.writing.config,
                provider
            )
        )

    ##########################################################

    def provider_model(self, config, provider):

        return config.get("providers", {}).get(
            provider,
            {}
        ).get("model", "")

    ##########################################################

    def replace_entry_text(self, entry, value):

        entry.delete(0, "end")
        entry.insert(
            0,
            value
        )

    ##########################################################

    def create_diagnostics(self):

        panel = ctk.CTkFrame(self)

        panel.pack(
            fill="x",
            padx=20,
            pady=(0, 10)
        )

        heading = ctk.CTkLabel(
            panel,
            text="Provider Diagnostics",
            font=("Segoe UI", 18, "bold")
        )

        heading.pack(
            anchor="w",
            padx=15,
            pady=(15, 8)
        )

        self.diagnostics_text = ctk.CTkTextbox(
            panel,
            height=150,
            wrap="word"
        )

        self.diagnostics_text.pack(
            fill="x",
            padx=15,
            pady=(0, 8)
        )
        actions = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        actions.pack(
            fill="x",
            padx=15,
            pady=(0, 15)
        )
        for label, command in (
            ("Run Production Schema Test", self.run_provider_diagnostics),
            ("View Last Failure Summary", self.view_last_provider_failure),
            ("Clear Provider Diagnostics", self.clear_provider_diagnostics)
        ):
            ctk.CTkButton(
                actions,
                text=label,
                width=190,
                command=command
            ).pack(
                side="left",
                padx=(0, 8)
            )
        self.set_diagnostics_text(
            "Diagnostics have not been run yet."
        )

    ##########################################################

    def apply_provider_settings(self):

        provider = self.provider_var.get()
        model = self.model_entry.get().strip()

        if provider == "ollama" and not model:
            self.status.configure(
                text="Enter an Ollama vision model before switching."
            )
            return

        result = self.brain.switch_provider(
            provider,
            model=model
        )
        self.diagnostics = ProviderDiagnosticsService()

        self.status.configure(
            text=(
                f"Provider set to {result['provider']} "
                f"({result['model']})"
            )
        )
        self.refresh_metrics()

    ##########################################################

    def apply_writing_settings(self):

        provider = self.writing_provider_var.get()
        model = self.writing_model_entry.get().strip()

        if not model:
            self.status.configure(
                text="Enter a writing model before switching."
            )
            return

        result = self.writing.switch_provider(
            provider,
            model=model
        )
        self.status.configure(
            text=(
                f"Writing provider set to {result['provider']} "
                f"({result['model']})"
            )
        )

    ##########################################################

    def run_provider_diagnostics(self):

        self.status.configure(
            text="Running provider diagnostics..."
        )
        self.set_diagnostics_text(
            "Checking provider. The app remains usable while diagnostics run..."
        )

        self.brain.jobs.submit(
            self.diagnostics.run,
            callback=self.diagnostics_complete,
            error_callback=self.diagnostics_failed
        )

    ##########################################################

    def diagnostics_complete(self, result):

        self.after(
            0,
            lambda: self.show_diagnostics_result(result)
        )

    ##########################################################

    def diagnostics_failed(self, error):

        self.after(
            0,
            lambda: self.set_diagnostics_text(
                f"Diagnostics failed: {error}"
            )
        )

    ##########################################################

    def view_last_provider_failure(self):

        folder = Path("logs") / "provider_diagnostics"
        files = sorted(
            folder.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True
        ) if folder.exists() else []

        if not files:
            self.set_diagnostics_text(
                "No provider failure diagnostics have been captured yet."
            )
            return

        self.set_diagnostics_text(
            files[0].read_text(
                encoding="utf-8",
                errors="replace"
            )[:6000]
        )

    def clear_provider_diagnostics(self):

        folder = Path("logs") / "provider_diagnostics"
        count = 0
        if folder.exists():
            for path in folder.glob("*.json"):
                try:
                    path.unlink()
                    count += 1
                except Exception:
                    pass

        self.set_diagnostics_text(
            f"Cleared {count:,} provider diagnostic file(s)."
        )

    ##########################################################

    def show_diagnostics_result(self, result):

        self.set_diagnostics_text(
            self.format_diagnostics(result)
        )
        self.status.configure(
            text=f"Diagnostics: {result.get('provider_status', '')}"
        )
        self.refresh_metrics()

    ##########################################################

    def set_diagnostics_text(self, text):

        self.diagnostics_text.configure(state="normal")
        self.diagnostics_text.delete("1.0", "end")
        self.diagnostics_text.insert("1.0", text)
        self.diagnostics_text.configure(state="disabled")

    ##########################################################

    def format_diagnostics(self, result):

        models = result.get("available_models") or []

        return "\n".join(
            [
                f"Active provider: {result.get('active_provider', '')}",
                f"Configured model: {result.get('configured_model', '')}",
                "Available Ollama models: " + (
                    ", ".join(models)
                    if models
                    else "None detected"
                ),
                f"Ollama reachable: {result.get('ollama_reachable')}",
                f"Configured model present: {result.get('configured_model_present')}",
                f"Simple text call: {result.get('simple_text_call')}",
                f"Vision model call: {result.get('vision_model_call')}",
                f"Image request accepted: {result.get('image_request_accepted', False)}",
                f"Raw response received: {result.get('raw_response_received', False)}",
                f"Response wrapper: {result.get('response_wrapper', '') or 'None'}",
                f"Wrapper recognized: {result.get('response_wrapper_recognized', False)}",
                f"JSON extracted: {result.get('json_extracted', False)}",
                f"Schema validated: {result.get('schema_validated', False)}",
                f"Production parser accepted: {result.get('production_parser_accepted', False)}",
                f"Persistence compatible: {result.get('persistence_compatible', False)}",
                f"Parser classification: {result.get('parser_classification', '') or 'None'}",
                f"Failure category: {result.get('failure_category', '') or 'None'}",
                f"Model loading: {result.get('model_loading', False)}",
                f"Status: {result.get('provider_status', '')}",
                f"Last error: {result.get('last_error', '') or 'None'}",
                f"GPU/CPU notes: {result.get('gpu_cpu_notes', '')}",
                f"Recommended fix: {result.get('recommended_action', '')}",
                result.get("mock_warning", "")
            ]
        )

    ##########################################################

    def create_bulk_controls(self):

        panel = ctk.CTkFrame(self)

        panel.pack(
            fill="x",
            padx=20,
            pady=15
        )

        heading = ctk.CTkLabel(
            panel,
            text="Bulk Analysis",
            font=("Segoe UI", 18, "bold")
        )

        heading.pack(
            anchor="w",
            padx=15,
            pady=(15, 8)
        )

        self.folder_entry = ctk.CTkEntry(
            panel,
            placeholder_text="Folder path"
        )

        self.folder_entry.pack(
            fill="x",
            padx=15,
            pady=(0, 10)
        )

        actions = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )

        actions.pack(
            fill="x",
            padx=15,
            pady=(0, 15)
        )

        folder_button = ctk.CTkButton(
            actions,
            text="Analyze Current Folder",
            command=self.analyze_folder
        )

        folder_button.pack(
            side="left",
            padx=(0, 10)
        )

        newest_button = ctk.CTkButton(
            actions,
            text="Analyze Newest Media",
            command=self.analyze_newest_media
        )

        newest_button.pack(
            side="left",
            padx=(0, 10)
        )

        last_year_button = ctk.CTkButton(
            actions,
            text="Analyze Last 12 Months",
            command=self.analyze_last_12_months
        )

        last_year_button.pack(
            side="left",
            padx=(0, 10)
        )

        library_button = ctk.CTkButton(
            actions,
            text="Analyze Entire Library",
            command=self.analyze_library
        )

        library_button.pack(
            side="left"
        )

        intelligence_button = ctk.CTkButton(
            actions,
            text="Build Intelligence Index",
            command=self.build_intelligence_index
        )

        intelligence_button.pack(
            side="left",
            padx=(10, 0)
        )

    ##########################################################

    def pause_queue(self):

        self.brain.pause_queue()
        self.refresh_metrics()

    ##########################################################

    def resume_queue(self):

        self.brain.resume_queue()
        self.refresh_metrics()

    ##########################################################

    def resume_previous(self):

        handle = self.brain.resume_previous_analysis(
            progress_callback=self.progress_update
        )

        self.status.configure(
            text=f"Resume requested for {len(handle):,} queued items"
        )

    ##########################################################

    def retry_failed(self):

        handle = self.brain.retry_failed_analysis(
            progress_callback=self.progress_update
        )

        self.status.configure(
            text=f"Retry requested for {len(handle):,} failed items"
        )

    ##########################################################

    def cancel_jobs(self):

        canceled = self.brain.cancel_queued_jobs()
        self.status.configure(
            text=f"Canceled {canceled:,} queued jobs"
        )
        self.refresh_metrics()

    ##########################################################

    def clear_completed(self):

        self.brain.clear_completed_jobs()
        self.refresh_metrics()

    ##########################################################

    def analyze_folder(self):

        folder = self.folder_entry.get().strip()

        if not folder:
            self.status.configure(
                text="Enter a folder path first."
            )
            return

        if not self.confirm_bulk_analysis():
            return

        futures = self.brain.analyze_folder(
            folder,
            progress_callback=self.progress_update
        )

        self.status.configure(
            text=f"Queued {len(futures):,} folder analysis jobs"
        )

    ##########################################################

    def analyze_library(self):

        if not self.confirm_bulk_analysis():
            return

        futures = self.brain.analyze_entire_library(
            progress_callback=self.progress_update
        )

        self.status.configure(
            text=f"Queued {len(futures):,} library analysis jobs"
        )

    ##########################################################

    def analyze_newest_media(self):

        if not self.confirm_bulk_analysis():
            return

        handle = self.brain.analyze_newest_media(
            preset="today",
            limit=200,
            include_photos=True,
            include_videos=True,
            only_unanalyzed=True,
            include_failed=False,
            progress_callback=self.progress_update
        )

        self.status.configure(
            text=f"Queued {len(handle):,} newest media item(s)"
        )

    ##########################################################

    def analyze_last_12_months(self):

        preview = self.brain.newest_media_preview("last_12_months")
        message = (
            "Last 12 months preview:\n\n"
            f"Total: {preview.get('total', 0):,}\n"
            f"Photos: {preview.get('photos', 0):,}\n"
            f"Videos: {preview.get('videos', 0):,}\n"
            f"Unanalyzed: {preview.get('unanalyzed', 0):,}\n"
            f"Review required: {preview.get('review_required', 0):,}\n"
            f"Approved: {preview.get('approved', 0):,}\n"
            f"Corrected: {preview.get('corrected', 0):,}\n"
            f"Failed: {preview.get('failed', 0):,}\n\n"
            "Queue the remaining unanalyzed media newest first?"
        )

        if not messagebox.askyesno(
            "Analyze Last 12 Months",
            message
        ):
            return

        if not self.confirm_bulk_analysis():
            return

        handle = self.brain.analyze_newest_media(
            preset="last_12_months",
            limit=1000,
            include_photos=True,
            include_videos=True,
            only_unanalyzed=True,
            include_failed=False,
            progress_callback=self.progress_update
        )

        self.status.configure(
            text=f"Queued {len(handle):,} last-12-month media item(s)"
        )

    ##########################################################

    def build_intelligence_index(self):

        self.brain.build_intelligence_index(
            progress_callback=self.intelligence_progress,
            callback=self.intelligence_complete,
            error_callback=self.intelligence_failed
        )

        self.status.configure(
            text="Building intelligence index..."
        )

    ##########################################################

    def open_review_queue(self):

        items = self.review.queue(limit=50)
        popup = ctk.CTkToplevel(self)
        popup.title("AI Analysis Review Queue")
        popup.transient(self.winfo_toplevel())
        WindowPlacement.center_window(popup, 900, 600, parent=self)

        heading = ctk.CTkLabel(
            popup,
            text=f"Review Queue ({len(items)} loaded)",
            font=("Segoe UI", 22, "bold")
        )
        heading.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        if not items:
            ctk.CTkLabel(
                popup,
                text="No analysis items currently require review."
            ).pack(
                anchor="w",
                padx=20,
                pady=20
            )
            return

        scroll = ctk.CTkScrollableFrame(popup)
        scroll.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )

        for item in items:
            self._review_queue_row(scroll, item)

    ##########################################################

    def _review_queue_row(self, parent, item):

        row = ctk.CTkFrame(parent)
        row.pack(
            fill="x",
            pady=5
        )

        text = (
            f"{item.get('filename', '')}\n"
            f"{item.get('provider', '')} / {item.get('model', '')} | "
            f"{item.get('trust_state', '') or 'unreviewed_real'} | "
            f"{item.get('parse_status', '')} | "
            f"confidence {item.get('confidence', 0):.2f}"
        )

        label = ctk.CTkLabel(
            row,
            text=text,
            justify="left",
            anchor="w",
            wraplength=620
        )
        label.pack(
            side="left",
            fill="x",
            expand=True,
            padx=10,
            pady=10
        )

        ctk.CTkButton(
            row,
            text="Open",
            command=lambda current=item: self.open_review_item(current)
        ).pack(
            side="right",
            padx=10
        )

    ##########################################################

    def open_review_item(self, item):

        queue = self.review.queue(limit=200)
        ids = [
            row["media_id"]
            for row in queue
        ]
        context = self.review_workflow.context_from_ids(
            ids,
            item["media_id"],
            label="AI Dashboard Review Queue",
            review_required_only=True
        )

        PhotoViewer(
            self,
            item["media_id"],
            item["filename"],
            item["path"],
            review_context=context,
            review_update_callback=self.review_item_updated
        )

    ##########################################################

    def review_item_updated(self, media_id, review_status):

        self.refresh_metrics()

    ##########################################################

    def review_next(self):

        items = self.review.queue(limit=1)

        if not items:
            self.status.configure(
                text="No analysis items currently require review."
            )
            return

        self.open_review_item(items[0])

    ##########################################################

    def clear_mock_analysis(self):

        summary = self.brain.legacy_mock_analysis_summary()

        if not summary.get("media_count"):
            messagebox.showinfo(
                "Clear Legacy Mock Analysis",
                "No successful legacy mock analysis rows were found."
            )
            return

        if not messagebox.askyesno(
            "Clear Legacy Mock Analysis",
            (
                "This will remove legacy mock test analysis only.\n\n"
                f"Media returned to unanalyzed: {summary.get('media_count', 0):,}\n"
                f"AI analysis rows: {summary.get('analysis_rows', 0):,}\n"
                f"Media Intelligence rows: {summary.get('media_intelligence_rows', 0):,}\n"
                f"Fire Service Intelligence rows: {summary.get('fire_service_rows', 0):,}\n"
                f"Editorial Strategy rows: {summary.get('editorial_strategy_rows', 0):,}\n"
                f"Editorial Comparison rows: {summary.get('editorial_comparison_rows', 0):,}\n\n"
                "Real Ollama analysis and human correction audit history will be preserved.\n\n"
                "Continue?"
            )
        ):
            return

        result = self.brain.clear_mock_analysis()

        self.status.configure(
            text=(
                f"Cleared {result.get('analysis_deleted', 0):,} mock "
                f"analysis rows and "
                f"{result.get('intelligence_deleted', 0):,} intelligence rows. "
                "Media is eligible for real analysis."
            )
        )

        self.refresh_metrics()

    ##########################################################

    def confirm_bulk_analysis(self):

        warning = self.brain.provider_bulk_warning()

        if not warning:
            return True

        return messagebox.askyesno(
            "Confirm AI Analysis",
            warning + "\n\nContinue?"
        )

    ##########################################################

    def intelligence_progress(self, progress):

        completed = progress.get("completed", 0)
        total = progress.get("total", 0)
        failed = progress.get("failed", 0)

        self.after(
            0,
            lambda: self.status.configure(
                text=(
                    "Building intelligence index: "
                    f"{completed:,} of {total:,} "
                    f"({failed:,} failed)"
                )
            )
        )

    ##########################################################

    def intelligence_complete(self, result):

        self.after(
            0,
            lambda: self.status.configure(
                text=(
                    "Intelligence index complete. "
                    f"{result.get('completed', 0):,} built, "
                    f"{result.get('failed', 0):,} failed."
                )
            )
        )

    ##########################################################

    def intelligence_failed(self, error):

        self.after(
            0,
            lambda: self.status.configure(
                text=f"Intelligence index failed: {error}"
            )
        )

    ##########################################################

    def progress_update(self, progress):

        bulk_total = progress.get("bulk_total", 0)
        bulk_processed = progress.get("bulk_processed", 0)

        if bulk_total:
            self.after(
                0,
                lambda: self.status.configure(
                    text=(
                        f"Bulk analysis: {bulk_processed:,} of "
                        f"{bulk_total:,} processed"
                    )
                )
            )

        self.after(
            0,
            self.refresh_metrics
        )

    ##########################################################

    def refresh_metrics(self):

        metrics = self.brain.dashboard_metrics()

        for key, label in self.metric_labels.items():

            value = metrics.get(key, "")

            if key == "average_analysis_time":
                value = f"{value:.2f}s"

            if key == "last_analyzed":
                value = TimeService.format_local(value) or "None"

            label.configure(
                text=str(value)
            )

        paused = metrics.get("paused")
        worker_status = metrics.get("analysis_worker_status", "Idle")
        session_status = metrics.get("analysis_status", "Idle")

        if metrics.get("provider") == "mock":
            self.mock_notice.configure(
                text="Mock provider active - test data only"
            )
        else:
            self.mock_notice.configure(
                text=""
            )

        if paused:
            self.status.configure(
                text="Queue paused"
            )
        elif (
            worker_status in ("Stale", "stale", "failed") or
            session_status in ("Recoverable", "Interrupted")
        ):
            self.status.configure(
                text=(
                    "Analysis session needs Resume Previous "
                    f"({session_status}, worker {worker_status})"
                )
            )
        elif session_status == "Paused":
            self.status.configure(
                text="Analysis session paused - Resume Previous to continue"
            )
        elif metrics.get("analysis_worker_active") == "Yes":
            self.status.configure(
                text=f"Analysis running ({worker_status})"
            )
        else:
            self.status.configure(
                text="Ready"
            )

        self.after(
            1000,
            self.refresh_metrics
        )
