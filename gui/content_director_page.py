import customtkinter as ctk

from gui.photo_card import PhotoCard
from gui.photo_viewer import PhotoViewer
from services.communications_director import CommunicationsDirector
from services.communications_reasoning_service import CommunicationsReasoningService
from services.content_generation_service import ContentGenerationService
from services.logging_service import LoggingService
from services.thumbnail_service import ThumbnailService


logger = LoggingService.get_logger("content")


class ContentDirectorPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.director = CommunicationsDirector()
        self.reasoning_service = CommunicationsReasoningService(
            director=self.director
        )
        self.content_generation_service = ContentGenerationService()
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

        status_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        status_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 8)
        )
        status_frame.grid_columnconfigure(0, weight=1)

        self.status = ctk.CTkLabel(
            status_frame,
            text="Opportunity type: none selected"
        )

        self.status.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.provider_status = ctk.CTkLabel(
            status_frame,
            text=self.writing_provider_status_text()
        )

        self.provider_status.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(12, 0)
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
            self.brief = self.reasoning_service.todays_communications_brief()

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
            text=self.brief.get(
                "title",
                "Today's Communications Brief"
            ),
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

        top_recommendation = self.brief.get(
            "top_recommendation"
        )
        top_text = (
            f"{top_recommendation['title']} - "
            f"{top_recommendation['priority']} Priority - "
            f"{top_recommendation['confidence']}% Confidence"
            if top_recommendation
            else "No recommendation available"
        )

        top_label = ctk.CTkLabel(
            self.brief_frame,
            text="Top Recommendation: " + top_text,
            justify="left"
        )

        top_label.grid(
            row=2,
            column=0,
            sticky="w",
            padx=15,
            pady=(0, 12)
        )

        if top_recommendation:
            reasoning = " | ".join(
                top_recommendation.get(
                    "reasoning",
                    []
                )[:3]
            )
            reasoning_label = ctk.CTkLabel(
                self.brief_frame,
                text="Reasoning: " + reasoning,
                wraplength=1100,
                justify="left"
            )

            reasoning_label.grid(
                row=3,
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
            row=4,
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
                    "opportunities": self.reasoning_service.generate_recommendations(
                        opportunity_keys=opportunity_types,
                        limit=5
                    )
                }
            else:
                result = {
                    "opportunity_types": self.director.interpret_prompt(prompt),
                    "opportunities": self.reasoning_service.generate_recommendations(
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
        self.render_learning_insights(parent=self.results)

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
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=1)

        media = opportunity["recommended_media"]
        self.record_viewed(opportunity)

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
                rowspan=15,
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
            font=("Segoe UI", 18, "bold"),
            wraplength=900,
            justify="left"
        )

        title.grid(
            row=0,
            column=1,
            sticky="ew",
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
            sticky="ew",
            padx=(0, 12),
            pady=3
        )

        self.add_caption_line(
            frame,
            2,
            "Reasoning",
            " | ".join(opportunity["reasoning"])
        )

        package = self.generate_package(
            opportunity
        )

        if package:
            self.render_package(
                frame,
                package,
                start_row=3
            )
        else:
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
            row=12,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=(3, 12)
        )
        footer.grid_columnconfigure(0, weight=1)

        cta = ctk.CTkLabel(
            footer,
            text=(
                f"CTA: {opportunity['call_to_action']} | "
                f"Engagement: {opportunity['estimated_engagement']} | "
                f"Platforms: {', '.join(opportunity['recommended_platforms'])}"
            ),
            wraplength=760,
            justify="left"
        )

        cta.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        if media:
            open_button = ctk.CTkButton(
                footer,
                text="Open in Viewer",
                command=lambda item=media[0], opp=opportunity: self.open_viewer(
                    item,
                    opp
                )
            )

            open_button.grid(
                row=0,
                column=1,
                sticky="e",
                padx=(12, 0)
            )

        feedback = ctk.CTkFrame(
            frame,
            fg_color="transparent"
        )

        feedback.grid(
            row=13,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=(0, 12)
        )

        buttons = (
            ("👍 Useful", "accepted"),
            ("👎 Not Useful", "dismissed"),
            ("⭐ Save for Later", "saved"),
            ("🔄 Show Another Suggestion", "regenerated")
        )

        for label, feedback_type in buttons:

            button = ctk.CTkButton(
                feedback,
                text=label,
                width=145,
                command=lambda opp=opportunity, kind=feedback_type: self.handle_feedback(
                    opp,
                    kind
                )
            )

            button.pack(
                side="left",
                padx=(0, 8)
            )

        for index, item in enumerate(media[1:], start=14):
            self.add_caption_line(
                frame,
                index,
                "Additional Media",
                f"{item['filename']} - {item['reason']}"
            )

    ##########################################################

    def generate_package(self, opportunity):

        try:
            return self.content_generation_service.generate_package(
                opportunity,
                context_snapshot=(
                    self.brief.get("context_snapshot", {})
                    if self.brief
                    else None
                )
            )

        except Exception as ex:
            logger.error(
                "Communication package generation failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Package generation error: {ex}"
            )
            return None

        finally:
            self.update_writing_provider_status()

    ##########################################################

    def render_package(self, parent, package, start_row=3):

        self.update_writing_provider_status(package)

        self.add_caption_line(
            parent,
            start_row,
            "Complete Communication Package",
            package.get("headline", "")
        )
        self.add_caption_line(
            parent,
            start_row + 1,
            "Facebook",
            package.get("facebook_caption", "")
        )
        self.add_caption_line(
            parent,
            start_row + 2,
            "Instagram",
            package.get("instagram_caption", "")
        )
        self.add_caption_line(
            parent,
            start_row + 3,
            "LinkedIn",
            package.get("linkedin_caption", "")
        )
        self.add_caption_line(
            parent,
            start_row + 4,
            "Facebook Hashtags",
            " ".join(package.get("facebook_hashtags", package.get("hashtags", [])))
        )
        self.add_caption_line(
            parent,
            start_row + 5,
            "Instagram Hashtags",
            " ".join(package.get("instagram_hashtags", package.get("hashtags", [])))
        )
        self.add_caption_line(
            parent,
            start_row + 6,
            "CTA",
            package.get("call_to_action", "")
        )
        self.add_caption_line(
            parent,
            start_row + 7,
            "Package Reasoning",
            " | ".join(package.get("reasoning", [])[:5])
        )
        self.render_copy_controls(
            parent,
            package,
            start_row + 8
        )

    ##########################################################

    def render_copy_controls(self, parent, package, row):

        controls = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        controls.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=3
        )
        for column in range(3):
            controls.grid_columnconfigure(column, weight=0)

        hashtags = " ".join(
            dict.fromkeys(
                (package.get("facebook_hashtags") or []) +
                (package.get("instagram_hashtags") or []) +
                (package.get("hashtags") or [])
            )
        )

        buttons = (
            (
                "Copy Facebook",
                package.get("facebook_caption", "")
            ),
            (
                "Copy Instagram",
                package.get("instagram_caption", "")
            ),
            (
                "Copy Hashtags",
                hashtags
            ),
            (
                "Copy CTA",
                package.get("call_to_action", "")
            ),
            (
                "Copy All",
                self.package_text(package)
            )
        )

        for index, (label, value) in enumerate(buttons):
            button = ctk.CTkButton(
                controls,
                text=label,
                width=118,
                command=lambda text=value, name=label: self.copy_text(
                    name,
                    text
                )
            )

            button.grid(
                row=index // 3,
                column=index % 3,
                sticky="w",
                padx=(0, 8),
                pady=(0, 6)
            )

    ##########################################################

    def copy_text(self, label, value):

        self.clipboard_clear()
        self.clipboard_append(value)
        self.status.configure(
            text=f"{label} copied."
        )

    ##########################################################

    def package_text(self, package):

        return "\n\n".join(
            [
                package.get("headline", ""),
                "Facebook:\n" + package.get("facebook_caption", ""),
                "Instagram:\n" + package.get("instagram_caption", ""),
                "LinkedIn:\n" + package.get("linkedin_caption", ""),
                (
                    "Facebook Hashtags:\n" +
                    " ".join(package.get("facebook_hashtags", []))
                ),
                (
                    "Instagram Hashtags:\n" +
                    " ".join(package.get("instagram_hashtags", []))
                ),
                "CTA:\n" + package.get("call_to_action", ""),
                "Reasoning:\n" + "\n".join(package.get("reasoning", []))
            ]
        )

    ##########################################################

    def record_viewed(self, opportunity):

        try:
            self.reasoning_service.learning.record_viewed(opportunity)

        except Exception as ex:
            logger.error(
                "Recommendation viewed feedback failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )

    ##########################################################

    def handle_feedback(self, opportunity, feedback_type):

        try:
            self.reasoning_service.learning.record_feedback(
                opportunity,
                feedback_type
            )

            if feedback_type == "regenerated":
                self.show_another_suggestion(opportunity)
                return

            self.status.configure(
                text=f"Feedback saved: {self.format_label(feedback_type)}"
            )
            self.render_results()

        except Exception as ex:
            logger.error(
                "Recommendation feedback failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Feedback error: {ex}"
            )

    ##########################################################

    def show_another_suggestion(self, opportunity):

        try:
            replacements = self.reasoning_service.generate_recommendations(
                opportunity_keys=[
                    opportunity["opportunity_type"]
                ],
                limit=1
            )

            if replacements:
                self.current_results = [
                    replacements[0]
                    if item is opportunity
                    else item
                    for item in self.current_results
                ]

            self.status.configure(
                text="Showing another learned suggestion"
            )
            self.render_results()

        except Exception as ex:
            logger.error(
                "Recommendation regeneration failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Regeneration error: {ex}"
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

    def render_learning_insights(self, parent):

        try:
            preferences = self.reasoning_service.learning.preferences()
            analytics = self.reasoning_service.learning.analytics()

        except Exception as ex:
            logger.error(
                "Learning insights render failed",
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
            pady=(5, 10)
        )

        heading = ctk.CTkLabel(
            frame,
            text="Your Communication Preferences",
            font=("Segoe UI", 20, "bold")
        )

        heading.pack(
            anchor="w",
            padx=15,
            pady=(12, 6)
        )

        summary = preferences.get("summary") or []

        if summary:
            preference_line = "You prefer: " + ", ".join(summary)
        else:
            preference_line = "Preferences will appear as recommendations are used."

        lines = [
            preference_line,
            (
                f"Acceptance {analytics['acceptance_rate']}% | "
                f"Dismissal {analytics['dismissal_rate']}% | "
                f"Average confidence {analytics['average_confidence']}%"
            )
        ]

        if analytics.get("most_accepted_opportunity_type"):
            lines.append(
                "Most accepted: " +
                analytics["most_accepted_opportunity_type"]
            )

        if analytics.get("most_rejected_opportunity_type"):
            lines.append(
                "Most rejected: " +
                analytics["most_rejected_opportunity_type"]
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

        line = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        line.grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=3
        )
        line.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            line,
            text=f"{label}:",
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )

        title.grid(
            row=0,
            column=0,
            sticky="w"
        )

        text = str(value or "")

        if self.is_long_text(label, text):
            box = ctk.CTkTextbox(
                line,
                height=self.text_area_height(label, text),
                wrap="word"
            )

            box.grid(
                row=1,
                column=0,
                sticky="ew",
                pady=(2, 0)
            )
            box.insert("1.0", text)
            box.configure(state="disabled")
            return

        caption = ctk.CTkLabel(
            line,
            text=text,
            wraplength=820,
            justify="left",
            anchor="w"
        )

        caption.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(2, 0)
        )

    ##########################################################

    def is_long_text(self, label, value):

        return (
            len(value) > 160 or
            "\n" in value or
            label in (
                "Facebook",
                "Instagram",
                "LinkedIn",
                "Package Reasoning",
                "Reasoning"
            )
        )

    ##########################################################

    def text_area_height(self, label, value):

        if label in ("Facebook", "Instagram", "LinkedIn"):
            return 125

        if label in ("Reasoning", "Package Reasoning"):
            return 95

        lines = max(2, len(value) // 95)
        return min(130, 42 + lines * 20)

    ##########################################################

    def open_viewer(self, recommendation, opportunity=None):

        logger.info(
            "Content Director opened viewer media_id=%s",
            recommendation["media_id"]
        )

        if opportunity:
            try:
                self.reasoning_service.learning.record_feedback(
                    opportunity,
                    "opened",
                    media=recommendation
                )

            except Exception as ex:
                logger.error(
                    "Recommendation opened feedback failed",
                    exc_info=(
                        type(ex),
                        ex,
                        ex.__traceback__
                    )
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

    def update_writing_provider_status(self, package=None):

        if package:
            provider = package.get("writing_provider", "")
            model = package.get("writing_model", "")
            fallback = package.get("writing_fallback_used", False)
            error = package.get("writing_provider_error", "")
        else:
            status = self.content_generation_service.writing.status()
            provider = status.get("active_provider", "")
            model = status.get("active_model", "")
            fallback = status.get("fallback_used", False)
            error = status.get("last_error", "")

        text = self.writing_provider_status_text(
            provider,
            model,
            fallback,
            error
        )

        if hasattr(self, "provider_status"):
            self.provider_status.configure(
                text=text
            )

    ##########################################################

    def writing_provider_status_text(
        self,
        provider=None,
        model=None,
        fallback=False,
        error=""
    ):

        if provider is None:
            status = self.content_generation_service.writing.status()
            provider = status.get("active_provider", "")
            model = status.get("active_model", "")
            fallback = status.get("fallback_used", False)
            error = status.get("last_error", "")

        label = f"Writing: {provider or 'unknown'}"

        if model:
            label += f" ({model})"

        if fallback:
            label += " - fallback"

        if error:
            label += " - local Ollama unavailable"

        return label

    ##########################################################

    def destroy(self):

        if hasattr(self, "thumbnail_service"):
            self.thumbnail_service.shutdown()

        super().destroy()
