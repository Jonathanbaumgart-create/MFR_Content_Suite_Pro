import json
import customtkinter as ctk
from tkinter import filedialog

from core.app_context import context
from services.communications_learning_service import CommunicationsLearningService
from services.logging_service import LoggingService
from gui.window_placement import WindowPlacement


logger = LoggingService.get_logger("content")


class CommunicationsLearningPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)
        self.service = CommunicationsLearningService(
            database=context.database
        )
        self.future = None
        self.pending_path = ""
        self.pending_preview = None
        self._destroyed = False

        self.build_page()
        self.refresh()

    ##########################################################

    def build_page(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Communications Learning",
            font=("Segoe UI", 30, "bold")
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Import Performance File",
            command=self.choose_import
        ).grid(row=0, column=1, padx=(10, 0))
        ctk.CTkButton(
            header,
            text="Refresh",
            command=self.refresh
        ).grid(row=0, column=2, padx=(10, 0))

        self.status = ctk.CTkLabel(
            self,
            text="Loading communications learning..."
        )
        self.status.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        self.content = ctk.CTkScrollableFrame(self)
        self.content.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content.grid_columnconfigure(0, weight=1)

    ##########################################################

    def choose_import(self):

        path = filedialog.askopenfilename(
            title="Import MFR Performance CSV, JSON, or XLSX",
            filetypes=(
                ("Performance files", "*.csv *.json *.xlsx"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*")
            )
        )

        if not path:
            return

        self.pending_path = path
        self.status.configure(text="Inspecting performance source...")
        self.future = context.job_manager.submit(
            self.service.preview_file,
            path
        )
        self.after(150, self.check_preview)

    def check_preview(self):

        if self._destroyed or self.future is None:
            return

        if not self.future.done():
            self.after(150, self.check_preview)
            return

        try:
            self.pending_preview = self.future.result()
        except Exception as ex:
            self.status.configure(text=f"Learning preview failed: {ex}")
            logger.error("Learning preview failed", exc_info=(type(ex), ex, ex.__traceback__))
            return

        self.future = None
        self.show_preview()

    def show_preview(self):

        window = ctk.CTkToplevel(self)
        window.title("Communications Learning Import Preview")
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 960, 720, parent=self)
        window.lift()

        body = ctk.CTkTextbox(window, wrap="word")
        body.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        body.insert(
            "1.0",
            json.dumps(self.pending_preview or {}, indent=2, default=str)
        )
        body.configure(state="disabled")

        actions = ctk.CTkFrame(window, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            actions,
            text="Apply Import",
            command=lambda: self.apply_import(window)
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Discard",
            command=window.destroy
        ).pack(side="right")

    def apply_import(self, window):

        if window:
            window.destroy()

        self.status.configure(text="Importing performance records...")
        self.future = context.job_manager.submit(
            self.service.import_file,
            self.pending_path
        )
        self.after(200, self.check_import)

    def check_import(self):

        if self._destroyed or self.future is None:
            return

        if not self.future.done():
            self.after(200, self.check_import)
            return

        try:
            summary = self.future.result()
            self.status.configure(
                text=(
                    f"Learning import complete: {summary.get('records_inserted', 0):,} "
                    f"inserted, {summary.get('duplicates_skipped', 0):,} duplicates."
                )
            )
        except Exception as ex:
            self.status.configure(text=f"Learning import failed: {ex}")
            logger.error("Learning import failed", exc_info=(type(ex), ex, ex.__traceback__))
        finally:
            self.future = None
            self.refresh()

    ##########################################################

    def refresh(self):

        for child in self.content.winfo_children():
            child.destroy()

        summary = self.service.dashboard()
        records = self.service.records(limit=12)
        experiments = context.database.communication_experiments(limit=8)

        self.status.configure(
            text=(
                f"Learning records: {summary.get('sample_count', 0):,} | "
                f"confidence: {summary.get('learning_confidence', 0)} | "
                f"baseline engagement: {summary.get('baseline_engagement_score', 0)}"
            )
        )
        self._section(
            "Performance Intelligence",
            self._summary_text(summary)
        )
        self._section(
            "Recent Experiments",
            self._experiments_text(experiments)
        )

        for record in records:
            self._record(record)

    def _section(self, title, text):

        frame = ctk.CTkFrame(self.content)
        frame.grid(sticky="ew", padx=4, pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text=title,
            font=("Segoe UI", 18, "bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            frame,
            text=text,
            justify="left",
            wraplength=1120
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

    def _record(self, record):

        derived = record.get("derived_metrics", {})
        details = (
            f"{record.get('platform', '')} | {record.get('publication_date', '')} "
            f"{record.get('publication_time', '')} | {record.get('topic', '')} | "
            f"{record.get('campaign', '')}\n"
            f"Engagement score: {derived.get('engagement_score', 0)} | "
            f"CTA: {derived.get('cta_style', '')} | "
            f"Media: {record.get('linked_context', {}).get('media_type', '')}\n"
            f"Limitations: {', '.join(derived.get('limitations', [])[:2])}"
        )
        self._section("Performance Record", details)

    def _summary_text(self, summary):

        return "\n".join(
            [
                f"Top performers: {self._items(summary.get('top_performers', []), 'topic')}",
                f"Trending topics: {self._items(summary.get('topics_trending', []), 'topic')}",
                f"Topics cooling down: {json.dumps(summary.get('topics_cooling_down', [])[:4])}",
                f"Best weekdays: {self._dict_keys(summary.get('best_weekdays', {}))}",
                f"Best hours: {self._dict_keys(summary.get('best_hours', {}))}",
                f"Media performance: {self._dict_keys(summary.get('media_performance', {}))}",
                f"Learning limitations: {'; '.join(summary.get('learning_limitations', []))}"
            ]
        )

    def _experiments_text(self, experiments):

        if not experiments:
            return "No communications experiments yet."

        return "\n".join(
            f"{item.get('hypothesis', '')} | {item.get('status', '')}"
            for item in experiments
        )

    def _items(self, items, key):

        if not items:
            return "none"

        return ", ".join(str(item.get(key, "")) for item in items[:5])

    def _dict_keys(self, item):

        if not item:
            return "none"

        return ", ".join(list(item.keys())[:6])

    def destroy(self):

        self._destroyed = True
        super().destroy()
