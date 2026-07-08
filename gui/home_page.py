import customtkinter as ctk

from core.app_context import context
from services.daily_brief_service import DailyBriefService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("application")


class HomePage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.service = DailyBriefService()
        self.future = None
        self.brief = None
        self._refresh_after_id = None
        self._destroyed = False

        self.build_page()
        self._refresh_after_id = self.after(
            100,
            self.refresh_brief
        )

        logger.info("Daily Brief viewed from Home page")

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
            text="Home",
            font=("Segoe UI", 30, "bold")
        )

        title.grid(
            row=0,
            column=0,
            sticky="w"
        )

        refresh = ctk.CTkButton(
            header,
            text="Refresh Brief",
            command=self.refresh_brief
        )

        refresh.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.status = ctk.CTkLabel(
            self,
            text="Preparing today's communications brief..."
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

        self.render_loading()

    ##########################################################

    def refresh_brief(self):

        if self._destroyed:
            return

        self._refresh_after_id = None
        self.status.configure(
            text="Preparing today's communications brief..."
        )
        self.render_loading()

        self.future = context.job_manager.submit(
            self.service.generate
        )

        logger.info("Daily Brief refresh queued")
        self.after(150, self.check_brief_future)

    ##########################################################

    def check_brief_future(self):

        if self._destroyed:
            return

        if self.future is None:
            return

        if not self.future.done():
            self.after(150, self.check_brief_future)
            return

        try:
            self.brief = self.future.result()

        except Exception as ex:
            logger.error(
                "Daily Brief refresh failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Daily Brief error: {ex}"
            )
            self.render_error(str(ex))
            return

        self.status.configure(
            text=f"Brief ready: {self.brief.get('generated_at', '')}"
        )
        self.render_brief()

    ##########################################################

    def render_loading(self):

        self.clear_content()

        label = ctk.CTkLabel(
            self.content,
            text="Preparing proactive recommendations from stored intelligence..."
        )

        label.pack(
            anchor="w",
            padx=10,
            pady=20
        )

    ##########################################################

    def render_error(self, message):

        self.clear_content()

        label = ctk.CTkLabel(
            self.content,
            text=message,
            wraplength=900,
            justify="left"
        )

        label.pack(
            anchor="w",
            padx=10,
            pady=20
        )

    ##########################################################

    def render_brief(self):

        self.clear_content()

        if not self.brief:
            self.render_loading()
            return

        self.add_section(
            self.brief.get("title", "Daily Communications Brief"),
            [
                self.brief.get("greeting", ""),
                self.brief.get("current_date", "")
            ]
        )
        self.render_context()
        self.render_top_recommendation()
        self.render_additional_opportunities()
        self.render_library_health()
        self.render_learning()
        self.render_gaps()

    ##########################################################

    def render_context(self):

        current = self.brief.get("current_context", {})

        lines = [
            "Season: " + self.format_label(current.get("season", "")),
            "Active Themes: " + self.format_list(current.get("active_themes", [])),
            "Upcoming Themes: " + self.format_list(current.get("upcoming_themes", [])),
            "Priority Context: " + self.format_list(current.get("priority_context", []))
        ]

        if current.get("explanation"):
            lines.append(current["explanation"])

        self.add_section(
            "Current Context",
            lines
        )

    ##########################################################

    def render_top_recommendation(self):

        top = self.brief.get("top_recommendation", {})
        media = top.get("recommended_media") or []
        lines = [
            top.get("summary", ""),
            (
                f"Confidence {top.get('confidence', 0)}% | "
                f"Posting Time {top.get('suggested_posting_time', '')} | "
                f"Engagement {top.get('estimated_engagement', '')}"
            ),
            "Platforms: " + ", ".join(top.get("suggested_platforms", [])),
            "Media: " + self.media_summary(media),
            "Reasoning: " + " | ".join(top.get("reasoning", [])[:4]),
            "Facebook: " + top.get("facebook_caption", ""),
            "Instagram: " + top.get("instagram_caption", "")
        ]

        self.add_section(
            "Top Recommendation: " + top.get("title", ""),
            lines
        )

    ##########################################################

    def render_additional_opportunities(self):

        opportunities = self.brief.get("additional_opportunities", [])
        lines = []

        for item in opportunities:
            lines.append(
                (
                    f"{item.get('title', '')}: "
                    f"{item.get('confidence', 0)}% confidence, "
                    f"{item.get('suggested_posting_time', '')}, "
                    f"{item.get('estimated_engagement', '')}"
                )
            )

        if not lines:
            lines.append("No additional opportunities are available yet.")

        self.add_section(
            "Three Additional Opportunities",
            lines
        )

    ##########################################################

    def render_library_health(self):

        health = self.brief.get("library_health_summary", {})
        processing = self.brief.get("processing_status", {})
        lines = [
            f"Media scanned: {health.get('media_scanned', 0):,}",
            f"Media analyzed: {health.get('media_analyzed', 0):,}",
            (
                "Media intelligence coverage: "
                f"{health.get('media_intelligence_coverage', 0)}%"
            ),
            (
                "Knowledge completeness: "
                f"{health.get('knowledge_completeness', 0)}%"
            ),
            (
                "Recommendation confidence: "
                f"{health.get('recommendation_confidence', 0)}%"
            ),
            (
                "Awaiting analysis: "
                f"{health.get('items_awaiting_analysis', 0):,}"
            ),
            (
                "Awaiting intelligence: "
                f"{health.get('items_awaiting_intelligence', 0):,}"
            ),
            (
                "Queue: "
                f"{processing.get('media_requiring_analysis', 0):,} need analysis, "
                f"{processing.get('media_requiring_intelligence', 0):,} need intelligence"
            )
        ]

        self.add_section(
            "Library Health",
            lines
        )

    ##########################################################

    def render_learning(self):

        self.add_section(
            "Recent Learning",
            self.brief.get("recent_learning", [])
        )

    ##########################################################

    def render_gaps(self):

        campaigns = self.brief.get("upcoming_campaigns", [])
        gaps = self.brief.get("content_gaps", [])
        lines = []

        if campaigns:
            lines.append(
                "Upcoming Campaigns: " +
                ", ".join(item.get("title", "") for item in campaigns[:5])
            )
        else:
            lines.append("Upcoming Campaigns: None detected yet.")

        if gaps:
            lines.append(
                "Content Gaps: " +
                ", ".join(item.get("name", "") for item in gaps[:6])
            )
        else:
            lines.append("Content Gaps: None detected.")

        self.add_section(
            "Upcoming Campaigns and Content Gaps",
            lines
        )

    ##########################################################

    def add_section(self, title, lines):

        frame = ctk.CTkFrame(
            self.content,
            corner_radius=8
        )

        frame.pack(
            fill="x",
            padx=10,
            pady=8
        )

        heading = ctk.CTkLabel(
            frame,
            text=title,
            font=("Segoe UI", 20, "bold")
        )

        heading.pack(
            anchor="w",
            padx=15,
            pady=(12, 5)
        )

        label = ctk.CTkLabel(
            frame,
            text="\n".join(line for line in lines if line),
            wraplength=1050,
            justify="left"
        )

        label.pack(
            anchor="w",
            padx=15,
            pady=(0, 12)
        )

    ##########################################################

    def clear_content(self):

        for child in self.content.winfo_children():
            child.destroy()

    ##########################################################

    def media_summary(self, media):

        if not media:
            return "No media selected"

        return ", ".join(
            item.get("filename", "")
            for item in media[:3]
            if item.get("filename")
        )

    ##########################################################

    def format_list(self, values):

        if not values:
            return "None"

        return ", ".join(
            self.format_label(value)
            for value in values[:6]
        )

    ##########################################################

    def format_label(self, value):

        return str(value or "").replace(
            "_",
            " "
        ).title()

    ##########################################################

    def destroy(self):

        self._destroyed = True

        if self._refresh_after_id:
            try:
                self.after_cancel(self._refresh_after_id)
            except Exception:
                pass

        if self.future and not self.future.done():
            self.future.cancel()

        super().destroy()
