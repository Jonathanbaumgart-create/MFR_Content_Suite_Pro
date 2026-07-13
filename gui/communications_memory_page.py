import customtkinter as ctk
from tkinter import filedialog

from core.app_context import context
from services.communication_import_service import CommunicationImportService
from services.communications_memory_service import CommunicationsMemoryService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationsMemoryPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.memory = CommunicationsMemoryService()
        self.importer = CommunicationImportService(
            database=context.database
        )
        self.future = None
        self.import_progress = None
        self.pending_import_path = ""
        self.pending_preview = None
        self._destroyed = False

        self.build_page()
        self.refresh()

    ##########################################################

    def build_page(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(20, 10)
        )
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Communications Memory",
            font=("Segoe UI", 30, "bold")
        )

        title.grid(
            row=0,
            column=0,
            sticky="w"
        )

        import_button = ctk.CTkButton(
            header,
            text="Import Communications",
            command=self.choose_import
        )

        import_button.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(10, 0)
        )

        refresh = ctk.CTkButton(
            header,
            text="Refresh",
            command=self.refresh
        )

        refresh.grid(
            row=0,
            column=2,
            sticky="e",
            padx=(10, 0)
        )

        self.status = ctk.CTkLabel(
            self,
            text="Loading communications memory..."
        )

        self.status.grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 10)
        )

        self.content = ctk.CTkScrollableFrame(self)

        self.content.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 20)
        )
        self.content.grid_columnconfigure(0, weight=1)

    ##########################################################

    def choose_import(self):

        path = filedialog.askopenfilename(
            title="Import Communications CSV or JSON",
            filetypes=(
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            )
        )

        if not path:
            return

        self.status.configure(
            text="Inspecting communication import source..."
        )

        self.future = context.job_manager.submit(
            self.importer.preview_file,
            path
        )
        self.pending_import_path = path
        logger.info(
            "Communications memory import preview queued path=%s",
            path
        )
        self.after(150, self.check_preview)

    ##########################################################

    def check_preview(self):

        if self._destroyed or self.future is None:
            return

        if not self.future.done():
            self.after(150, self.check_preview)
            return

        try:
            self.pending_preview = self.future.result()

        except Exception as ex:
            logger.error(
                "Communications memory import preview failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Import preview failed: {ex}"
            )
            return

        self.future = None
        self.status.configure(
            text="Import preview ready."
        )
        self.show_import_preview()

    ##########################################################

    def show_import_preview(self):

        preview = self.pending_preview or {}
        window = ctk.CTkToplevel(self)
        window.title("Communication Import Preview")
        window.geometry("950x720")
        window.transient(self.winfo_toplevel())
        window.lift()

        body = ctk.CTkTextbox(
            window,
            wrap="word"
        )
        body.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(16, 8)
        )
        body.insert(
            "1.0",
            self.import_preview_text(preview)
        )
        body.configure(state="disabled")

        controls = ctk.CTkFrame(
            window,
            fg_color="transparent"
        )
        controls.pack(
            fill="x",
            padx=16,
            pady=(0, 16)
        )

        ctk.CTkButton(
            controls,
            text="Start Import",
            command=lambda: self.start_import_from_preview(window)
        ).pack(
            side="left",
            padx=(0, 8)
        )
        ctk.CTkButton(
            controls,
            text="Close",
            command=window.destroy
        ).pack(
            side="right"
        )

    ##########################################################

    def start_import_from_preview(self, window):

        window.destroy()

        self.status.configure(
            text="Importing communications memory..."
        )
        self.future = context.job_manager.submit(
            self.importer.import_file,
            self.pending_import_path,
            progress_callback=self._on_import_progress
        )
        logger.info(
            "Communications memory import queued path=%s",
            self.pending_import_path
        )
        self.after(150, self.check_import)

    ##########################################################

    def check_import(self):

        if self._destroyed or self.future is None:
            return

        if not self.future.done():
            if self.import_progress:
                self.status.configure(
                    text=(
                        "Importing communications memory: "
                        f"{self.import_progress['records_processed']} processed, "
                        f"{self.import_progress['records_inserted']} inserted, "
                        f"{self.import_progress['duplicates_skipped']} duplicates, "
                        f"{self.import_progress['records_failed']} failed."
                    )
                )
            self.after(150, self.check_import)
            return

        try:
            summary = self.future.result()

        except Exception as ex:
            logger.error(
                "Communications memory import failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Import failed: {ex}"
            )
            return

        self.status.configure(
            text=(
                "Import complete: "
                f"{summary['records_inserted']} records, "
                f"{summary['deliveries_inserted']} deliveries, "
                f"{summary['duplicates_skipped']} duplicates."
            )
        )
        self.refresh()

    ##########################################################

    def _on_import_progress(self, progress):

        self.import_progress = progress

    ##########################################################

    def refresh(self):

        self.clear_content()

        try:
            stats = self.memory.statistics()
            posts = self.memory.search(
                "",
                limit=10
            )

        except Exception as ex:
            logger.error(
                "Communications memory refresh failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Communications memory error: {ex}"
            )
            return

        self.status.configure(
            text="Communications memory loaded."
        )
        self.render_stats(
            stats,
            posts
        )

    ##########################################################

    def render_stats(self, stats, posts):

        row = 0

        self.section(
            row,
            "Overview",
            [
                f"Total Posts: {stats['total_posts']:,}",
                f"Communication Records: {stats['communication_records']:,}",
                f"Deliveries: {stats['communication_deliveries']:,}",
                f"Campaigns: {stats['campaigns']:,}",
                f"Communication Campaigns: {stats['communication_campaigns']:,}",
                f"Communication Programs: {stats['communication_programs']:,}",
                f"Topics: {stats['communication_topics']:,}",
                f"Import Runs: {stats['communication_import_runs']:,}",
                f"Platforms: {stats['platforms']:,}",
                f"Linked Media Uses: {stats['media_usage']:,}"
            ]
        )
        row += 1

        writing = stats["writing_statistics"]
        self.section(
            row,
            "Writing Statistics",
            [
                f"Average Caption Length: {writing['average_caption_length']:.1f}",
                f"Average Hashtags: {writing['average_hashtags']:.1f}",
                f"Average Emojis: {writing['average_emojis']:.1f}",
                f"Question Rate: {writing['question_rate']:.0%}",
                f"Storytelling Rate: {writing['storytelling_rate']:.0%}",
                f"Safety Message Rate: {writing['safety_message_rate']:.0%}"
            ]
        )
        row += 1

        self.section(
            row,
            "Most Used Hashtags",
            [
                f"{tag} ({count})"
                for tag, count in stats["top_hashtags"]
            ] or ["No hashtags imported yet."]
        )
        row += 1

        self.section(
            row,
            "Most Common Writing Styles",
            [
                f"{style} ({count})"
                for style, count in stats["writing_styles"]
            ] or ["No writing styles detected yet."]
        )
        row += 1

        self.section(
            row,
            "Posting Timeline",
            [
                f"{period}: {count} posts"
                for period, count in stats["posting_frequency"]
            ] or ["No timeline data imported yet."]
        )
        row += 1

        self.section(
            row,
            "Recent Campaigns",
            [
                f"{campaign} ({count})"
                for campaign, count in stats["recent_campaigns"]
            ] or ["No campaigns discovered yet."]
        )
        row += 1

        self.section(
            row,
            "Memory Statistics",
            [
                f"Normalized Records: {stats['engine']['records']:,}",
                f"Delivery Records: {stats['engine']['deliveries']:,}",
                f"Campaign Objects: {stats['engine']['campaigns']:,}",
                f"Program Objects: {stats['engine']['programs']:,}",
                f"Topic Links: {stats['engine']['topics']:,}"
            ] + [
                f"Topic: {item['topic']} ({item['count']})"
                for item in stats["engine"].get("top_topics", [])[:5]
            ] or ["No normalized communication memory imported yet."]
        )
        row += 1

        self.section(
            row,
            "Import Runs",
            [
                (
                    f"Run {item['import_run_id']}: {item['status']} | "
                    f"{item['records_processed']} processed | "
                    f"{item['records_inserted']} inserted | "
                    f"{item['duplicates_skipped']} duplicates"
                )
                for item in self.import_runs()
            ] or ["No import runs yet."]
        )
        row += 1

        self.section(
            row,
            "Intelligence Review",
            [
                "Imported communication intelligence is saved as automated analysis.",
                "Corrections are additive and preserve raw imported records.",
                "Use bounded imports and review warnings before production import."
            ]
        )
        row += 1

        self.section(
            row,
            "Import History",
            [
                (
                    f"{self.format_post_time(post)} | {post['platform']} | "
                    f"{post['campaign'] or 'No campaign'} | "
                    f"{post['caption'][:140]}"
                )
                for post in posts
            ] or ["No posts imported yet."]
        )

    ##########################################################

    def import_preview_text(self, preview):

        samples = preview.get("sample_normalized_records", [])
        lines = [
            "Source type: " + preview.get("source_type", ""),
            "Confidence: " + str(preview.get("confidence", 0)),
            (
                "Record count estimate: " +
                f"{preview.get('record_count_estimate', 0):,}"
            ),
            "Detected fields: " + ", ".join(preview.get("detected_fields", [])),
            "Mapped fields: " + str(preview.get("mapped_fields", {})),
            (
                "Potential duplicates: "
                f"{preview.get('potential_duplicate_count', 0):,}"
            ),
            (
                "Probable duplicates needing review: "
                f"{preview.get('probable_duplicate_count', 0):,}"
            ),
            f"Invalid records: {preview.get('invalid_record_count', 0):,}",
            f"Warnings: {preview.get('warning_count', 0):,}",
            "",
            "Samples"
        ]

        for index, sample in enumerate(samples[:5], start=1):
            lines.extend(
                [
                    "",
                    f"{index}. {sample.get('sample_title', '')}",
                    "Date: " + sample.get("sample_date", ""),
                    "Platform: " + sample.get("sample_platform", ""),
                    "Campaign: " + ", ".join(sample.get("campaign", [])),
                    "Program: " + ", ".join(sample.get("program", [])),
                    "Topics: " + ", ".join(sample.get("topics", [])),
                    "Media references: " + ", ".join(sample.get("media_references", [])),
                    "Text: " + sample.get("sample_text", "")[:400]
                ]
            )

        if preview.get("warnings"):
            lines.extend(["", "Warnings"])
            lines.extend(preview.get("warnings", [])[:20])

        return "\n".join(lines)

    ##########################################################

    def import_runs(self):

        try:
            return context.database.communication_import_runs(limit=10)
        except Exception:
            return []

    ##########################################################

    def format_post_time(self, post):

        value = " ".join(
            item
            for item in (
                post.get("post_date", ""),
                post.get("post_time", "")
            )
            if item
        )

        if post.get("post_time"):
            return TimeService.format_local(value) or value

        return value

    ##########################################################

    def section(self, row, title, lines):

        frame = ctk.CTkFrame(
            self.content,
            corner_radius=8
        )

        frame.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=10,
            pady=10
        )
        frame.grid_columnconfigure(0, weight=1)

        heading = ctk.CTkLabel(
            frame,
            text=title,
            font=("Segoe UI", 20, "bold")
        )

        heading.grid(
            row=0,
            column=0,
            sticky="w",
            padx=15,
            pady=(12, 5)
        )

        label = ctk.CTkLabel(
            frame,
            text="\n".join(lines),
            justify="left",
            wraplength=1050
        )

        label.grid(
            row=1,
            column=0,
            sticky="w",
            padx=15,
            pady=(0, 12)
        )

    ##########################################################

    def clear_content(self):

        for child in self.content.winfo_children():
            child.destroy()

    ##########################################################

    def destroy(self):

        self._destroyed = True
        super().destroy()
