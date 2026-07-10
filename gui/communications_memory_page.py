import customtkinter as ctk
from tkinter import filedialog

from core.app_context import context
from services.communications_memory_service import CommunicationsMemoryService
from services.logging_service import LoggingService
from services.social_import_service import SocialImportService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationsMemoryPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.memory = CommunicationsMemoryService()
        self.importer = SocialImportService(
            self.memory
        )
        self.future = None
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
            text="Import JSON Export",
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
            title="Import Social Media JSON Export",
            filetypes=(
                ("JSON files", "*.json"),
                ("All files", "*.*")
            )
        )

        if not path:
            return

        self.status.configure(
            text="Importing communications memory..."
        )
        self.future = context.job_manager.submit(
            self.importer.import_file,
            path
        )
        logger.info(
            "Communications memory import queued path=%s",
            path
        )
        self.after(150, self.check_import)

    ##########################################################

    def check_import(self):

        if self._destroyed or self.future is None:
            return

        if not self.future.done():
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
                f"{summary['posts_imported']} posts, "
                f"{summary['duplicate_posts']} duplicates."
            )
        )
        self.refresh()

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
                f"Campaigns: {stats['campaigns']:,}",
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
