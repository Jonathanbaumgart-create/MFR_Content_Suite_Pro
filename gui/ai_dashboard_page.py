import customtkinter as ctk
from tkinter import messagebox

from services.brain_service import BrainService
from services.provider_diagnostics_service import ProviderDiagnosticsService


class AIDashboardPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.brain = BrainService()
        self.diagnostics = ProviderDiagnosticsService()
        self.metric_labels = {}
        self.provider_var = ctk.StringVar(
            value=self.brain.vision.provider_key()
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
            ("queued", "Queued"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("provider", "Provider"),
            ("average_analysis_time", "Avg Time"),
            ("total_analyzed", "Analyzed"),
            ("last_analyzed", "Last Analyzed")
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
            ("Cancel Queued Jobs", self.cancel_jobs),
            ("Clear Completed Jobs", self.clear_completed),
            ("Clear Mock Analysis", self.clear_mock_analysis)
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
            variable=self.provider_var
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
            pady=(0, 15)
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

    def clear_mock_analysis(self):

        if not messagebox.askyesno(
            "Clear Mock Analysis",
            (
                "Clear all mock provider analysis and related "
                "Media Intelligence rows?"
            )
        ):
            return

        result = self.brain.clear_mock_analysis()

        self.status.configure(
            text=(
                f"Cleared {result.get('analysis_deleted', 0):,} mock "
                f"analysis rows and "
                f"{result.get('intelligence_deleted', 0):,} intelligence rows"
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

            label.configure(
                text=str(value)
            )

        paused = metrics.get("paused")

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

        self.after(
            1000,
            self.refresh_metrics
        )
