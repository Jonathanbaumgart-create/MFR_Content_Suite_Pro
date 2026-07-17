import json
import customtkinter as ctk
from tkinter import filedialog

from core.app_context import context
from services.benchmark_communications_service import BenchmarkCommunicationsService
from services.logging_service import LoggingService
from gui.window_placement import WindowPlacement


logger = LoggingService.get_logger("content")


class BenchmarkLibraryPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)
        self.service = BenchmarkCommunicationsService(
            database=context.database
        )
        self.future = None
        self.pending_path = ""
        self.pending_preview = None
        self._destroyed = False
        self.department_var = ctk.StringVar(value="")
        self.platform_var = ctk.StringVar(value="")
        self.media_var = ctk.StringVar(value="")
        self.topic_var = ctk.StringVar(value="")
        self.applicability_var = ctk.StringVar(value="")
        self.reel_var = ctk.BooleanVar(value=False)
        self.engagement_var = ctk.BooleanVar(value=False)
        self.reviewed_var = ctk.BooleanVar(value=False)

        self.build_page()
        self.refresh()

    ##########################################################

    def build_page(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Benchmark Library",
            font=("Segoe UI", 30, "bold")
        )
        title.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Import Benchmark File",
            command=self.choose_import
        ).grid(row=0, column=1, padx=(10, 0))
        ctk.CTkButton(
            header,
            text="Refresh",
            command=self.refresh
        ).grid(row=0, column=2, padx=(10, 0))

        self.status = ctk.CTkLabel(
            self,
            text="Benchmark records are separate from MFR Communications Memory."
        )
        self.status.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 8))

        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))

        for column in range(8):
            filters.grid_columnconfigure(column, weight=1)

        self._entry(filters, "Department", self.department_var, 0)
        self._entry(filters, "Platform", self.platform_var, 1)
        self._entry(filters, "Media", self.media_var, 2)
        self._entry(filters, "Topic", self.topic_var, 3)
        self._entry(filters, "Applicability", self.applicability_var, 4)
        ctk.CTkCheckBox(filters, text="Reel", variable=self.reel_var).grid(row=0, column=5, padx=6)
        ctk.CTkCheckBox(filters, text="Engagement", variable=self.engagement_var).grid(row=0, column=6, padx=6)
        ctk.CTkCheckBox(filters, text="Reviewed", variable=self.reviewed_var).grid(row=0, column=7, padx=6)
        ctk.CTkButton(filters, text="Apply", command=self.refresh).grid(row=0, column=8, padx=6)

        self.content = ctk.CTkScrollableFrame(self)
        self.content.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content.grid_columnconfigure(0, weight=1)

    def _entry(self, parent, placeholder, variable, column):

        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            placeholder_text=placeholder,
            width=130
        )
        entry.grid(row=0, column=column, padx=6, pady=8, sticky="ew")

    ##########################################################

    def choose_import(self):

        path = filedialog.askopenfilename(
            title="Import Benchmark CSV, JSON, or XLSX",
            filetypes=(
                ("Benchmark files", "*.csv *.json *.xlsx"),
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*")
            )
        )

        if not path:
            return

        self.status.configure(text="Inspecting benchmark source...")
        self.pending_path = path
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
            self.status.configure(text=f"Benchmark preview failed: {ex}")
            logger.error("Benchmark preview failed", exc_info=(type(ex), ex, ex.__traceback__))
            return

        self.future = None
        self.show_preview()

    def show_preview(self):

        preview = self.pending_preview or {}
        window = ctk.CTkToplevel(self)
        window.title("Benchmark Import Preview")
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 960, 720, parent=self)
        window.lift()

        body = ctk.CTkTextbox(window, wrap="word")
        body.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        body.insert("1.0", json.dumps(preview, indent=2, default=str))
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

        self.status.configure(text="Importing benchmark records...")
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
                    f"Benchmark import complete: {summary.get('records_inserted', 0):,} "
                    f"inserted, {summary.get('duplicates_skipped', 0):,} duplicates."
                )
            )
        except Exception as ex:
            self.status.configure(text=f"Benchmark import failed: {ex}")
            logger.error("Benchmark import failed", exc_info=(type(ex), ex, ex.__traceback__))
        finally:
            self.future = None
            self.refresh()

    ##########################################################

    def refresh(self):

        for child in self.content.winfo_children():
            child.destroy()

        filters = self._filters()
        insights = self.service.insights()
        records = self.service.search(filters=filters, limit=50)
        patterns = context.database.benchmark_patterns(limit=10)

        self.status.configure(
            text=(
                f"Benchmark records: {insights.get('records', 0):,} | "
                f"departments: {insights.get('departments', 0):,} | "
                f"Reels/videos: {insights.get('reel_records', 0):,} | "
                f"engagement supplied: {insights.get('engagement_available', 0):,}"
            )
        )
        self._section("Insights", self._insight_text(insights))
        self._section("Patterns", self._pattern_text(patterns))

        for record in records:
            self._record(record)

    def _filters(self):

        filters = {
            "department": self.department_var.get().strip(),
            "platform": self.platform_var.get().strip().lower(),
            "media_type": self.media_var.get().strip().lower(),
            "topic": self.topic_var.get().strip().lower(),
            "applicability": self.applicability_var.get().strip()
        }
        filters["reel"] = self.reel_var.get()
        filters["engagement_available"] = self.engagement_var.get()
        filters["reviewed"] = self.reviewed_var.get()
        return {
            key: value
            for key, value in filters.items()
            if value
        }

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
            wraplength=1100
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

    def _record(self, record):

        frame = ctk.CTkFrame(self.content)
        frame.grid(sticky="ew", padx=4, pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)
        excerpt = record.get("original_text", "")[:280]
        if len(record.get("original_text", "")) > 280:
            excerpt += "..."
        details = (
            f"{record.get('source_department', '')} | {record.get('source_platform', '')} | "
            f"{record.get('source_date_text', '')} | {record.get('media_type', '')} | "
            f"{record.get('topic', '')} | {record.get('applicability', '')}\n"
            f"Engagement: {record.get('engagement_status', '')} | "
            f"Attribution: {record.get('copyright_status', '')}\n"
            f"{excerpt}"
        )
        ctk.CTkLabel(
            frame,
            text=details,
            justify="left",
            wraplength=1120
        ).grid(row=0, column=0, sticky="w", padx=12, pady=10)

    def _insight_text(self, insights):

        return "\n".join(
            [
                f"Platforms: {self._labels(insights.get('platforms', []))}",
                f"Topics: {self._labels(insights.get('topics', []))}",
                f"Media types: {self._labels(insights.get('media_types', []))}",
                f"Applicability: {self._labels(insights.get('applicability', []))}"
            ]
        )

    def _pattern_text(self, patterns):

        if not patterns:
            return "No benchmark patterns yet. Import local benchmark records to generate advisory patterns."

        return "\n".join(
            f"{item.get('title', '')}: {item.get('applicability', '')} "
            f"({item.get('evidence_count', 0)} source record(s))"
            for item in patterns[:8]
        )

    def _labels(self, items):

        if not items:
            return "none"

        return ", ".join(
            f"{item.get('label', '')} ({item.get('count', 0)})"
            for item in items[:6]
        )

    def destroy(self):

        self._destroyed = True
        super().destroy()
