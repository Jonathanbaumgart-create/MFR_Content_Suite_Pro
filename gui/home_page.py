import customtkinter as ctk
import time

from core.app_context import context
from services.communication_package_service import CommunicationPackageService
from services.communications_intelligence_service import CommunicationsIntelligenceService
from services.communications_officer_service import CommunicationsOfficerService
from services.content_generation_service import ContentGenerationService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("application")


class HomePage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.service = CommunicationsOfficerService()
        self.package_service = CommunicationPackageService()
        self.content_generation_service = ContentGenerationService()
        self.communications_intelligence_service = CommunicationsIntelligenceService()
        self.future = None
        self.package_future = None
        self.content_future = None
        self.communications_intelligence_future = None
        self.communications_intelligence_profile = None
        self.brief = None
        self._refresh_after_id = None
        self._destroyed = False

        self.build_page()
        self._refresh_after_id = self.after(
            100,
            self.refresh_brief
        )

        logger.info("Communications Officer Morning Brief viewed from Home page")

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
            text="Preparing today's communication priorities..."
        )
        self.render_loading()

        self.future = context.job_manager.submit(
            self.service.generate
        )
        self.communications_intelligence_future = None
        self.communications_intelligence_profile = None

        logger.info("Communications Officer Morning Brief refresh queued")
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
                "Communications Officer Morning Brief refresh failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Morning Brief error: {ex}"
            )
            self.render_error(str(ex))
            return

        self.status.configure(
            text=(
                "Brief ready: " +
                (
                    TimeService.format_local(
                        self.brief.get("generated_at", "")
                    ) or
                    self.brief.get("generated_at", "")
                )
            )
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

        render_started = time.perf_counter()
        self.clear_content()

        if not self.brief:
            self.render_loading()
            return

        self.add_section(
            self.brief.get("title", "AI Communications Officer Morning Brief"),
            [
                self.brief.get("current_date", ""),
                "Why today matters: " + self.brief.get("why_today_matters", ""),
                (
                    "Confidence: "
                    f"{self.brief.get('confidence', 0)}%"
                )
            ]
        )
        self.render_communication_priorities()
        self.render_top_story()
        self.render_secondary_stories()
        self.render_review_queue()
        self.render_new_media()
        self.render_videos_awaiting_review()
        self.render_memory_status()
        self.render_communications_intelligence_status()
        profile = getattr(self.service, "last_metrics", {}).setdefault(
            "profile",
            {}
        )
        profile["tk_render_seconds"] = round(
            time.perf_counter() - render_started,
            3
        )

    ##########################################################

    def render_communication_priorities(self):

        opportunities = self.brief.get(
            "top_three_communication_opportunities",
            []
        )
        lines = []

        for index, item in enumerate(opportunities, start=1):
            lines.append(
                (
                    f"{index}. {item.get('title', '')} - "
                    f"{item.get('confidence', 0)}% confidence - "
                    f"{item.get('trust_label', 'Trust state unknown')} - "
                    f"{item.get('why_today_matters', '')}"
                )
            )

        if not lines:
            lines.append("No reviewed communication priority is ready yet.")

        self.add_section(
            "Today's Communication Priorities",
            lines
        )

    ##########################################################

    def render_top_story(self):

        story = self.brief.get("top_story", {})
        package = story.get("media_package", {})
        best_photo = package.get("best_photo", {})
        best_video = package.get("best_video", {})
        lines = [
            story.get("summary", ""),
            "Why today: " + story.get("why_today_matters", ""),
            "Why the public would care: " + story.get("why_public_would_care", ""),
            "Why it should outperform: " + story.get("why_it_should_outperform", ""),
            "Trust: " + story.get("trust_label", "Trust state unknown"),
            story.get("trust_summary", ""),
            "Platforms: " + self.format_list(story.get("recommended_platforms", [])),
            "Estimated audience: " + self.format_list(story.get("estimated_audience", [])),
            (
                "Best photo: " +
                (best_photo.get("filename") or "None")
            ),
            (
                "Best video: " +
                (best_video.get("filename") or "None")
            ),
            (
                "Media package score: "
                f"{package.get('communications_score', 0)}"
            ),
            (
                "Positive factors: " +
                self.format_list(story.get("positive_factors", []))
            ),
            (
                "Limitations: " +
                self.format_list(story.get("confidence_limitations", []))
            )
        ]

        self.add_section(
            "Top Story: " + story.get("title", ""),
            lines
        )
        self.render_top_story_package_action(story)

    ##########################################################

    def render_top_story_package_action(self, story):

        frame = ctk.CTkFrame(
            self.content,
            corner_radius=8
        )
        frame.pack(
            fill="x",
            padx=10,
            pady=(0, 8)
        )

        label = ctk.CTkLabel(
            frame,
            text="Prepare a complete communication package from this Top Story.",
            wraplength=850,
            justify="left"
        )
        label.pack(
            side="left",
            padx=15,
            pady=12
        )

        button = ctk.CTkButton(
            frame,
            text="Generate Package",
            width=170,
            command=lambda item=story: self.request_communication_package(item)
        )
        button.pack(
            side="right",
            padx=15,
            pady=12
        )

    ##########################################################

    def request_communication_package(self, story):

        if self.package_future and not self.package_future.done():
            return

        self.status.configure(
            text="Preparing communication package preview..."
        )
        self.package_future = context.job_manager.submit(
            self.package_service.generate_package,
            story,
            package_type="Facebook"
        )
        self.after(150, self.check_package_future)

    ##########################################################

    def check_package_future(self):

        if self._destroyed:
            return

        if self.package_future is None:
            return

        if not self.package_future.done():
            self.after(150, self.check_package_future)
            return

        try:
            package = self.package_future.result()
        except Exception as ex:
            logger.error(
                "Communication package preview failed",
                exc_info=(type(ex), ex, ex.__traceback__)
            )
            self.status.configure(
                text=f"Package preview error: {ex}"
            )
            return

        self.status.configure(
            text="Communication package preview ready."
        )
        self.show_package_preview(package)

    ##########################################################

    def show_package_preview(self, package):

        window = ctk.CTkToplevel(self)
        window.title("Communication Package Preview")
        window.geometry("900x720")
        window.transient(self.winfo_toplevel())
        window.lift()

        textbox = ctk.CTkTextbox(
            window,
            wrap="word"
        )
        textbox.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(16, 8)
        )
        textbox.insert(
            "1.0",
            self.package_preview_text(package)
        )
        textbox.configure(state="disabled")

        ctk.CTkButton(
            window,
            text="Generate Content",
            command=lambda item=package: self.request_generated_content(item)
        ).pack(
            anchor="e",
            padx=16,
            pady=(0, 8)
        )

        ctk.CTkButton(
            window,
            text="Close",
            command=window.destroy
        ).pack(
            anchor="e",
            padx=16,
            pady=(0, 16)
        )

    ##########################################################

    def package_preview_text(self, package):

        strategy = package.get("writing_strategy", {}) or {}
        media = package.get("media_package", {}) or {}
        scoring = package.get("package_scoring", {}) or {}

        return "\n\n".join(
            [
                "Top Story\n" + package.get("headline", ""),
                "Audience\n" + self.format_list(package.get("audience", [])),
                "Trust Level\n" + package.get("trust_label", ""),
                "Platforms\n" + self.format_list(package.get("recommended_platforms", [])),
                "Publishing Strategy\n" + str(package.get("publishing_strategy", {}).get("decision_note", "")),
                "Writing Strategy\n" + "\n".join(
                    [
                        f"Purpose: {strategy.get('purpose', '')}",
                        f"Tone: {strategy.get('tone', '')}",
                        f"Length: {strategy.get('length', '')}",
                        f"CTA: {strategy.get('call_to_action_strategy', '')}",
                        f"Visual: {strategy.get('visual_strategy', '')}",
                        f"Notes: {strategy.get('platform_notes', '')}"
                    ]
                ),
                "Supporting Media\n" + "\n".join(
                    [
                        "Primary photo: " + (media.get("primary_photo", {}).get("filename") or "None"),
                        "Primary video: " + (media.get("primary_video", {}).get("filename") or "None"),
                        "Gallery photos: " + self.media_summary(media.get("gallery_photos", [])),
                        "Gallery videos: " + self.media_summary(media.get("gallery_videos", []))
                    ]
                ),
                "Suggested Hashtags\n" + " ".join(package.get("suggested_hashtags", [])),
                "Suggested CTA\n" + package.get("suggested_cta", ""),
                "Package Score\n" + str(scoring)
            ]
        )

    ##########################################################

    def request_generated_content(self, package):

        if self.content_future and not self.content_future.done():
            return

        self.status.configure(
            text="Generating multi-platform content..."
        )
        self.content_future = context.job_manager.submit(
            self.content_generation_service.generate_from_package,
            package
        )
        self.after(150, self.check_generated_content_future)

    ##########################################################

    def check_generated_content_future(self):

        if self._destroyed:
            return

        if self.content_future is None:
            return

        if not self.content_future.done():
            self.after(150, self.check_generated_content_future)
            return

        try:
            generated = self.content_future.result()
        except Exception as ex:
            logger.error(
                "Multi-platform content generation failed",
                exc_info=(type(ex), ex, ex.__traceback__)
            )
            self.status.configure(
                text=f"Content generation error: {ex}"
            )
            return

        self.status.configure(
            text="Multi-platform content ready."
        )
        self.show_generated_content_preview(generated)

    ##########################################################

    def show_generated_content_preview(self, package):

        window = ctk.CTkToplevel(self)
        window.title("Generated Content Preview")
        window.geometry("950x760")
        window.transient(self.winfo_toplevel())
        window.lift()

        selected = {"platform": "facebook"}
        body = ctk.CTkTextbox(window, wrap="word")
        body.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(8, 8)
        )

        controls = ctk.CTkFrame(window, fg_color="transparent")
        controls.pack(
            fill="x",
            padx=16,
            pady=(16, 0)
        )

        def render(platform):
            selected["platform"] = platform
            output = package.get(platform, {}) or {}
            body.configure(state="normal")
            body.delete("1.0", "end")
            warning = package.get("internal_warning", "")

            if warning:
                body.insert("end", "INTERNAL WARNING\n" + warning + "\n\n")

            body.insert(
                "end",
                "\n\n".join(
                    [
                        output.get("title", self.format_label(platform)),
                        output.get("copy_text", ""),
                        "Word count: " + str(output.get("word_count", "")),
                        (
                            "Reading time: " +
                            str(output.get("estimated_reading_time", ""))
                        )
                    ]
                )
            )
            body.configure(state="disabled")

        for platform in (
            "facebook",
            "instagram",
            "linkedin",
            "website",
            "news_release",
            "newsletter"
        ):
            ctk.CTkButton(
                controls,
                text=self.format_label(platform),
                width=120,
                command=lambda item=platform: render(item)
            ).pack(side="left", padx=(0, 8), pady=(0, 8))

        footer = ctk.CTkFrame(window, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            footer,
            text="Copy Current",
            command=lambda: self.copy_generated_text(
                package,
                selected["platform"]
            )
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            footer,
            text="Close",
            command=window.destroy
        ).pack(side="right")
        render("facebook")

    ##########################################################

    def copy_generated_text(self, package, platform):

        self.clipboard_clear()
        self.clipboard_append(
            package.get("copy_buttons", {}).get(platform, "")
        )
        self.status.configure(
            text=f"{self.format_label(platform)} copied."
        )

    ##########################################################

    def render_secondary_stories(self):

        stories = self.brief.get("secondary_stories", [])
        lines = []

        for story in stories:
            lines.append(
                (
                    f"{story.get('title', '')}: "
                    f"{story.get('confidence', 0)}% confidence. "
                    f"{story.get('trust_label', 'Trust state unknown')}. "
                    f"{story.get('why_it_should_outperform', '')}"
                )
            )

        if not lines:
            lines.append("No secondary reviewed stories are ready yet.")

        self.add_section(
            "Secondary Stories",
            lines
        )

    ##########################################################

    def render_review_queue(self):

        summary = self.brief.get("summary", {})
        lines = [
            f"Review queue size: {summary.get('review_queue_size', 0):,}",
            f"Approved media: {summary.get('approved_media_count', 0):,}",
            f"Corrected media: {summary.get('corrected_media_count', 0):,}",
            f"Failed analysis: {summary.get('failed_analysis_count', 0):,}",
            (
                "Analyzed since last Home session: "
                f"{summary.get('media_analyzed_since_last_session', 0):,}"
            ),
            (
                "Session source: " +
                self.format_label(summary.get("media_analyzed_since_source", ""))
            )
        ]

        self.add_section(
            "Review Queue",
            lines
        )

    ##########################################################

    def render_new_media(self):

        summary = self.brief.get("summary", {})
        today = self.brief.get("todays_new_media", {})
        lines = [
            (
                "New media added yesterday: "
                f"{summary.get('new_media_added_yesterday', 0):,}"
            ),
            f"Added today: {today.get('added_today', 0):,}",
            f"Photos added today: {today.get('photos', 0):,}",
            f"Videos added today: {today.get('videos', 0):,}",
            f"Unanalyzed new media: {today.get('unanalyzed', 0):,}"
        ]

        self.add_section(
            "Today's New Media",
            lines
        )

    ##########################################################

    def render_videos_awaiting_review(self):

        self.add_section(
            "Videos Awaiting Review",
            [
                (
                    "Videos awaiting human review: "
                    f"{self.brief.get('videos_awaiting_review', 0):,}"
                )
            ]
        )

    ##########################################################

    def render_memory_status(self):

        memory = self.brief.get("communications_memory_status", {})
        lines = [
            "Status: " + memory.get("status", ""),
            f"Stored posts: {memory.get('total_posts', 0):,}",
            (
                "Latest post: " +
                (
                    TimeService.format_local(memory.get("latest_post", ""))
                    or memory.get("latest_post", "")
                    or "Unknown"
                )
            ),
            (
                "Recommendation history: "
                f"{memory.get('recommendation_history_count', 0):,}"
            )
        ]

        self.add_section(
            "Communications Memory Status",
            lines
        )

    ##########################################################

    def render_communications_intelligence_status(self):

        profile = self.communications_intelligence_profile or {}

        if profile:
            lines = [
                (
                    "Learning from approved communications: "
                    f"{profile.get('approved_communication_count', 0):,}"
                ),
                (
                    "Approved edit learning samples: "
                    f"{profile.get('approved_edit_count', 0):,}"
                ),
                (
                    "Department voice confidence: "
                    f"{profile.get('learning_confidence', 0)}%"
                ),
                (
                    "Voice: " +
                    (profile.get("department_voice", "") or "Insufficient history")
                ),
                (
                    "Last updated: " +
                    (
                        TimeService.format_local(
                            profile.get("last_profile_update", "")
                        ) or
                        profile.get("last_profile_update", "") or
                        "Not built yet"
                    )
                )
            ]
        else:
            lines = [
                "Preparing Department Communications Profile...",
                "Home remains usable while communication intelligence loads."
            ]

        self.add_section(
            "Communications Intelligence Status",
            lines
        )

        if profile or self.communications_intelligence_future:
            return

        self.communications_intelligence_future = context.job_manager.submit(
            self.communications_intelligence_service.profile
        )
        self.after(150, self.check_communications_intelligence_future)

    ##########################################################

    def check_communications_intelligence_future(self):

        if self._destroyed:
            return

        if self.communications_intelligence_future is None:
            return

        if not self.communications_intelligence_future.done():
            self.after(150, self.check_communications_intelligence_future)
            return

        try:
            self.communications_intelligence_profile = (
                self.communications_intelligence_future.result()
            )

        except Exception as ex:
            logger.error(
                "Communications Intelligence status failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.communications_intelligence_profile = {
                "department_voice": f"Unavailable: {ex}",
                "learning_confidence": 0,
                "approved_communication_count": 0,
                "approved_edit_count": 0
            }

        self.communications_intelligence_future = None

        if self.brief:
            self.render_brief()

    ##########################################################

    def render_editorial_recommendations(self):

        recommendations = self.brief.get("editorial_recommendations", [])

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
            text="Today's Top Communication Opportunities",
            font=("Segoe UI", 20, "bold")
        )
        heading.pack(
            anchor="w",
            padx=15,
            pady=(12, 5)
        )

        if not recommendations:
            ctk.CTkLabel(
                frame,
                text=(
                    "No ranked editorial recommendations are available yet. "
                    "Analyze media and build Media Intelligence to unlock this section."
                ),
                wraplength=1050,
                justify="left"
            ).pack(
                anchor="w",
                padx=15,
                pady=(0, 12)
            )
            return

        for recommendation in recommendations[:5]:
            self.add_recommendation_card(
                frame,
                recommendation
            )

    ##########################################################

    def add_recommendation_card(self, parent, recommendation):

        card = ctk.CTkFrame(
            parent,
            corner_radius=6
        )
        card.pack(
            fill="x",
            padx=15,
            pady=6
        )
        card.grid_columnconfigure(0, weight=1)

        title = (
            f"{recommendation.get('title', '')} "
            f"({recommendation.get('priority_score', 0)} priority, "
            f"{recommendation.get('confidence_score', 0)} confidence)"
        )
        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 15, "bold"),
            wraplength=950,
            justify="left"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(10, 2)
        )

        details = [
            recommendation.get("primary_reason", ""),
            (
                f"Support: {recommendation.get('supporting_photo_count', 0)} photo(s), "
                f"{recommendation.get('supporting_video_count', 0)} video(s)"
            ),
            (
                "Strongest angle: " +
                self.format_list(recommendation.get("editorial_angles", [])[:1])
            ),
            (
                "Platforms: " +
                self.format_list(recommendation.get("recommended_platforms", []))
            ),
            (
                "Window: " +
                recommendation.get("recommended_posting_window", "")
            )
        ]

        ctk.CTkLabel(
            card,
            text="\n".join(line for line in details if line),
            wraplength=950,
            justify="left"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=12,
            pady=(0, 10)
        )

        ctk.CTkButton(
            card,
            text="Details",
            width=120,
            command=lambda item=recommendation: self.show_recommendation_details(item)
        ).grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e",
            padx=12,
            pady=10
        )

    ##########################################################

    def show_recommendation_details(self, recommendation):

        window = ctk.CTkToplevel(self)
        window.title(recommendation.get("title", "Recommendation Details"))
        window.geometry("900x700")
        window.transient(self.winfo_toplevel())
        window.lift()

        frame = ctk.CTkFrame(window)
        frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text=recommendation.get("title", "Recommendation Details"),
            font=("Segoe UI", 22, "bold")
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=12,
            pady=(12, 6)
        )

        text = ctk.CTkTextbox(frame)
        text.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=12,
            pady=8
        )
        text.insert(
            "1.0",
            self.recommendation_detail_text(recommendation)
        )
        text.configure(state="disabled")

        ctk.CTkButton(
            frame,
            text="Close",
            command=window.destroy
        ).grid(
            row=2,
            column=0,
            sticky="e",
            padx=12,
            pady=(4, 12)
        )

    ##########################################################

    def recommendation_detail_text(self, recommendation):

        positive = [
            factor
            for factor in recommendation.get("reasoning_factors", [])
            if factor.get("direction") == "positive"
        ]
        negative = [
            factor
            for factor in recommendation.get("reasoning_factors", [])
            if factor.get("direction") == "negative"
        ]

        lines = [
            recommendation.get("summary", ""),
            "",
            f"Headline: {recommendation.get('headline', recommendation.get('title', ''))}",
            f"Category: {recommendation.get('category', '')}",
            f"Topic: {recommendation.get('topic', '')}",
            f"Priority score: {recommendation.get('priority_score', 0)}",
            f"Confidence score: {recommendation.get('confidence_score', 0)}",
            f"Scoring version: {recommendation.get('scoring_version', '')}",
            f"Primary reason: {recommendation.get('primary_reason', '')}",
            f"Editorial angle: {recommendation.get('editorial_angle', '')}",
            "Supporting topics: " + self.format_list(
                recommendation.get("supporting_topics", [])
            ),
            "Supporting programs: " + self.format_list(
                recommendation.get("supporting_programs", [])
            ),
            f"Communications gap: {recommendation.get('communications_gap', '')}",
            f"Repetition risk: {recommendation.get('repetition_risk', '')}",
            "Story strength: " + self.story_strength_text(
                recommendation.get("story_strength", {})
            ),
            "",
            "Positive Factors:"
        ]

        lines.extend(
            self.factor_lines(positive)
        )
        lines.append("")
        lines.append("Negative Factors:")
        lines.extend(
            self.factor_lines(negative)
        )
        lines.extend(
            [
                "",
                "Supporting Assets:",
                "All: " + self.format_list(recommendation.get("supporting_asset_ids", [])),
                "Best: " + self.format_list(recommendation.get("best_asset_ids", [])),
                "",
                "Editorial Angles: " + self.format_list(recommendation.get("editorial_angles", [])),
                "Platforms: " + self.format_list(recommendation.get("recommended_platforms", [])),
                "Audiences: " + self.format_list(recommendation.get("recommended_audiences", [])),
                "Formats: " + self.format_list(recommendation.get("recommended_content_formats", [])),
                "Posting Window: " + recommendation.get("recommended_posting_window", ""),
                "",
                "Known Confidence Limitations:"
            ]
        )
        limitations = recommendation.get("confidence_limitations", [])
        lines.extend(
            limitations if limitations else ["None"]
        )
        lines.extend(
            [
                "",
                "Source Signals:"
            ]
        )
        lines.extend(
            recommendation.get("source_signals", [])
        )

        return "\n".join(str(line) for line in lines if line is not None)

    ##########################################################

    def factor_lines(self, factors):

        if not factors:
            return ["None"]

        return [
            f"{factor.get('score', 0):+}: {factor.get('label', '')}"
            for factor in factors
        ]

    ##########################################################

    def story_strength_text(self, story):

        if not story:
            return "Unknown"

        strongest = self.format_list(story.get("strongest", []))

        return (
            f"{story.get('overall', 0)} overall; "
            f"strongest dimensions: {strongest}"
        )

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
