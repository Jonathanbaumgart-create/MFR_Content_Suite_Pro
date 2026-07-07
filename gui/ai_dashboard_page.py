import customtkinter as ctk

from services.brain_service import BrainService


class AIDashboardPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.brain = BrainService()
        self.metric_labels = {}

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
            pady=(0, 15)
        )

        self.create_metrics()
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
            ("Clear Completed Jobs", self.clear_completed)
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

        futures = self.brain.analyze_folder(
            folder,
            progress_callback=self.progress_update
        )

        self.status.configure(
            text=f"Queued {len(futures):,} folder analysis jobs"
        )

    ##########################################################

    def analyze_library(self):

        futures = self.brain.analyze_entire_library(
            progress_callback=self.progress_update
        )

        self.status.configure(
            text=f"Queued {len(futures):,} library analysis jobs"
        )

    ##########################################################

    def progress_update(self, progress):

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

        if paused:
            self.status.configure(
                text="Queue paused"
            )

        self.after(
            1000,
            self.refresh_metrics
        )
