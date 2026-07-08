import customtkinter as ctk

from gui.photo_card import PhotoCard
from gui.photo_viewer import PhotoViewer
from services.communications_director import CommunicationsDirector
from services.logging_service import LoggingService
from services.thumbnail_service import ThumbnailService


logger = LoggingService.get_logger("content")


class ContentDirectorPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.director = CommunicationsDirector()
        self.thumbnail_service = ThumbnailService()
        self.current_results = []
        self.brief = None

        self.build_page()
        self.refresh_brief()
        self.render_daily_opportunities()

    ##########################################################

    def build_page(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        heading = ctk.CTkLabel(
            self,
            text="Content Director",
            font=("Segoe UI", 30, "bold")
        )

        heading.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 8)
        )

        prompt_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        prompt_frame.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12)
        )
        prompt_frame.grid_columnconfigure(0, weight=1)

        self.prompt_entry = ctk.CTkEntry(
            prompt_frame,
            placeholder_text="Describe a content opportunity"
        )

        self.prompt_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 10)
        )

        generate = ctk.CTkButton(
            prompt_frame,
            text="Generate Suggestions",
            command=self.generate_suggestions
        )

        generate.grid(
            row=0,
            column=1
        )

        self.status = ctk.CTkLabel(
            self,
            text="Opportunity type: none selected"
        )

        self.status.grid(
            row=2,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 8)
        )

        self.brief_frame = ctk.CTkFrame(self)

        self.brief_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12)
        )

        content = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        content.grid(
            row=4,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 20)
        )
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(
            content,
            width=280
        )

        left.grid(
            row=0,
            column=0,
            sticky="ns",
            padx=(0, 15)
        )
        left.grid_propagate(False)

        daily_label = ctk.CTkLabel(
            left,
            text="Today's Opportunities",
            font=("Segoe UI", 18, "bold")
        )

        daily_label.pack(
            anchor="w",
            padx=15,
            pady=(15, 10)
        )

        self.daily_frame = ctk.CTkFrame(
            left,
            fg_color="transparent"
        )

        self.daily_frame.pack(
            fill="x",
            padx=15,
            pady=(0, 15)
        )

        self.results = ctk.CTkScrollableFrame(content)

        self.results.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.empty_label = ctk.CTkLabel(
            self.results,
            text="Enter a prompt or choose an opportunity."
        )

        self.empty_label.pack(
            pady=30
        )

    ##########################################################

    def refresh_brief(self):

        try:
            self.brief = self.director.todays_brief()

        except Exception as ex:
            logger.error(
                "Today's Brief render failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.brief = None
            self.status.configure(
                text=f"Today's Brief error: {ex}"
            )
            return

        self.render_brief()
        self.current_results = self.brief.get(
            "recommendations",
            []
        )
        self.render_results()

    ##########################################################

    def render_brief(self):

        for child in self.brief_frame.winfo_children():
            child.destroy()

        if not self.brief:
            return

        title = ctk.CTkLabel(
            self.brief_frame,
            text="Today's Brief",
            font=("Segoe UI", 18, "bold")
        )

        title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=15,
            pady=(12, 3)
        )

        health = self.brief["library_health"]
        status = self.brief["processing_status"]
        summary = (
            f"{health['media_with_intelligence']:,} media with intelligence | "
            f"{health['community_content_percentage']}% community | "
            f"{health['training_percentage']}% training | "
            f"{status['media_requiring_analysis']:,} need analysis | "
            f"{status['media_requiring_intelligence']:,} need intelligence"
        )

        label = ctk.CTkLabel(
            self.brief_frame,
            text=summary,
            justify="left"
        )

        label.grid(
            row=1,
            column=0,
            sticky="w",
            padx=15,
            pady=(0, 12)
        )

        top = [
            opportunity["title"]
            for opportunity in self.brief["top_opportunities"]
        ]

        top_label = ctk.CTkLabel(
            self.brief_frame,
            text="Top Opportunities: " + ", ".join(top),
            justify="left"
        )

        top_label.grid(
            row=2,
            column=0,
            sticky="w",
            padx=15,
            pady=(0, 12)
        )

        context = self.brief.get(
            "context_snapshot",
            {}
        )

        context_lines = [
            "Current Context",
            f"Season: {self.format_label(context.get('season', ''))}",
            (
                "Active Themes: " +
                self.format_context_list(context.get("active_themes", []))
            ),
            (
                "Upcoming Themes: " +
                self.format_context_list(context.get("upcoming_themes", []))
            ),
            (
                "Priority Context: " +
                self.format_context_list(context.get("priority_context", []))
            )
        ]

        context_label = ctk.CTkLabel(
            self.brief_frame,
            text="\n".join(context_lines),
            justify="left"
        )

        context_label.grid(
            row=3,
            column=0,
            sticky="w",
            padx=15,
            pady=(0, 12)
        )

    ##########################################################

    def render_daily_opportunities(self):

        for child in self.daily_frame.winfo_children():
            child.destroy()

        opportunities = (
            self.brief.get("recommendations", [])
            if self.brief
            else []
        )

        for opportunity in opportunities:

            button = ctk.CTkButton(
                self.daily_frame,
                text=opportunity["title"],
                command=lambda item=opportunity: self.use_daily_opportunity(item)
            )

            button.pack(
                fill="x",
                pady=4
            )

    ##########################################################

    def use_daily_opportunity(self, opportunity):

        self.prompt_entry.delete(0, "end")
        self.prompt_entry.insert(
            0,
            opportunity["title"]
        )
        self.generate_suggestions(
            opportunity_types=[opportunity["opportunity_type"]]
        )

    ##########################################################

    def generate_suggestions(self, opportunity_types=None):

        prompt = self.prompt_entry.get().strip()

        try:
            if opportunity_types:
                result = {
                    "opportunity_types": opportunity_types,
                    "opportunities": [
                        self.director.generate_opportunity(item)
                        for item in opportunity_types
                    ]
                }
            else:
                result = {
                    "opportunity_types": self.director.interpret_prompt(prompt),
                    "opportunities": self.director.generate_opportunities(
                        prompt,
                        limit=5
                    )
                }

        except Exception as ex:
            logger.error(
                "Communications Director request failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Communications Director error: {ex}"
            )
            return

        self.current_results = result["opportunities"]
        labels = [
            self.format_label(item)
            for item in result["opportunity_types"]
        ]
        self.status.configure(
            text=f"Opportunity type: {', '.join(labels)}"
        )
        self.render_results()

    ##########################################################

    def render_results(self):

        for child in self.results.winfo_children():
            child.destroy()

        heading = ctk.CTkLabel(
            self.results,
            text="Recommended Opportunities",
            font=("Segoe UI", 20, "bold")
        )

        heading.pack(
            anchor="w",
            padx=10,
            pady=(10, 4)
        )

        if not self.current_results:
            label = ctk.CTkLabel(
                self.results,
                text="No communication opportunities found."
            )

            label.pack(
                pady=30
            )
            self.render_library_insights(parent=self.results)
            return

        for opportunity in self.current_results:
            self.render_opportunity(opportunity)

        self.render_library_insights(parent=self.results)

    ##########################################################

    def render_opportunity(self, opportunity):

        frame = ctk.CTkFrame(
            self.results,
            corner_radius=8
        )

        frame.pack(
            fill="x",
            padx=10,
            pady=10
        )
        frame.grid_columnconfigure(1, weight=1)

        media = opportunity["recommended_media"]

        if media:
            card = PhotoCard(
                frame,
                media[0]["media_id"],
                media[0]["filename"],
                media[0]["path"],
                thumbnail_service=self.thumbnail_service
            )

            card.grid(
                row=0,
                column=0,
                rowspan=7,
                padx=12,
                pady=12,
                sticky="nw"
            )

        title = ctk.CTkLabel(
            frame,
            text=(
                f"{opportunity['title']} "
                f"- {opportunity['priority']} Priority "
                f"- {opportunity['confidence']}% Confidence"
            ),
            font=("Segoe UI", 18, "bold")
        )

        title.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=(12, 3)
        )

        reason = ctk.CTkLabel(
            frame,
            text=opportunity["description"],
            wraplength=850,
            justify="left"
        )

        reason.grid(
            row=1,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=3
        )

        self.add_caption_line(
            frame,
            2,
            "Reasoning",
            " | ".join(opportunity["reasoning"])
        )
        self.add_caption_line(
            frame,
            3,
            "Caption Theme",
            opportunity["caption_theme"]
        )
        self.add_caption_line(
            frame,
            4,
            "Hashtags",
            " ".join(opportunity["hashtags"])
        )
        self.add_caption_line(
            frame,
            5,
            "Best Time",
            opportunity["best_posting_time"]
        )

        footer = ctk.CTkFrame(
            frame,
            fg_color="transparent"
        )

        footer.grid(
            row=6,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=(3, 12)
        )

        cta = ctk.CTkLabel(
            footer,
            text=(
                f"CTA: {opportunity['call_to_action']} | "
                f"Engagement: {opportunity['estimated_engagement']} | "
                f"Platforms: {', '.join(opportunity['recommended_platforms'])}"
            ),
            wraplength=700,
            justify="left"
        )

        cta.pack(
            side="left",
            fill="x",
            expand=True
        )

        if media:
            open_button = ctk.CTkButton(
                footer,
                text="Open in Viewer",
                command=lambda item=media[0]: self.open_viewer(item)
            )

            open_button.pack(
                side="right",
                padx=(12, 0)
            )

        for index, item in enumerate(media[1:], start=7):
            self.add_caption_line(
                frame,
                index,
                "Additional Media",
                f"{item['filename']} - {item['reason']}"
            )

    ##########################################################

    def render_library_insights(self, parent=None):

        parent = parent or self.brief_frame

        if parent is self.brief_frame:
            return

        try:
            insights = self.director.library_insights()
            gaps = self.director.content_gaps()

        except Exception as ex:
            logger.error(
                "Library insights render failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            return

        frame = ctk.CTkFrame(
            parent,
            corner_radius=8
        )

        frame.pack(
            fill="x",
            padx=10,
            pady=(15, 10)
        )

        heading = ctk.CTkLabel(
            frame,
            text="Library Insights",
            font=("Segoe UI", 20, "bold")
        )

        heading.pack(
            anchor="w",
            padx=15,
            pady=(12, 6)
        )

        lines = [
            (
                "Most Common Incident: "
                f"{insights['most_common_incident']['name']} "
                f"({insights['most_common_incident']['count']:,})"
            ),
            (
                "Least Photographed Apparatus: "
                f"{insights['least_photographed_apparatus']['name']} "
                f"({insights['least_photographed_apparatus']['count']:,})"
            ),
            (
                "Most Photographed Activity: "
                f"{insights['most_photographed_activity']['name']} "
                f"({insights['most_photographed_activity']['count']:,})"
            ),
            (
                f"Community {insights['community_content_percentage']}% | "
                f"Training {insights['training_percentage']}% | "
                f"Recruitment {insights['recruitment_percentage']}%"
            ),
            (
                f"Need Analysis {insights['media_requiring_analysis']:,} | "
                f"Need Intelligence {insights['media_requiring_intelligence']:,}"
            )
        ]

        if gaps:
            lines.append(
                "Content Gaps: " +
                ", ".join(gap["name"] for gap in gaps[:6])
            )

        label = ctk.CTkLabel(
            frame,
            text="\n".join(lines),
            justify="left"
        )

        label.pack(
            anchor="w",
            padx=15,
            pady=(0, 12)
        )

    ##########################################################

    def add_caption_line(self, parent, row, label, value):

        caption = ctk.CTkLabel(
            parent,
            text=f"{label}: {value}",
            wraplength=850,
            justify="left"
        )

        caption.grid(
            row=row,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=3
        )

    ##########################################################

    def open_viewer(self, recommendation):

        logger.info(
            "Content Director opened viewer media_id=%s",
            recommendation["media_id"]
        )

        PhotoViewer(
            self,
            recommendation["media_id"],
            recommendation["filename"],
            recommendation["path"]
        )

    ##########################################################

    def format_label(self, value):

        return str(value).replace(
            "_",
            " "
        ).title()

    ##########################################################

    def format_context_list(self, values):

        if not values:
            return "None"

        return ", ".join(
            self.format_label(value)
            for value in values[:6]
        )

    ##########################################################

    def destroy(self):

        if hasattr(self, "thumbnail_service"):
            self.thumbnail_service.shutdown()

        super().destroy()
