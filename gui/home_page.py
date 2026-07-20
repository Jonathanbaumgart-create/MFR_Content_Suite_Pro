import customtkinter as ctk
import os
import subprocess
import time

from core.app_context import context
from gui.package_media_panel import PackageMediaPanel
from gui.photo_viewer import PhotoViewer
from services.communication_package_service import CommunicationPackageService
from services.communications_intelligence_service import CommunicationsIntelligenceService
from services.communications_officer_service import CommunicationsOfficerService
from services.content_generation_service import ContentGenerationService
from services.daily_communications_officer_service import DailyCommunicationsOfficerService
from services.decision_explainability_service import DecisionExplainabilityService
from services.logging_service import LoggingService
from services.package_review_service import PackageReviewService
from services.thumbnail_service import ThumbnailService
from services.time_service import TimeService
from gui.window_placement import WindowPlacement


logger = LoggingService.get_logger("application")


class HomePage(ctk.CTkFrame):

    LOAD_TIMEOUT_MS = 30000

    def __init__(self, parent):

        super().__init__(parent)

        self.service = DailyCommunicationsOfficerService()
        self.package_service = CommunicationPackageService()
        self.content_generation_service = ContentGenerationService()
        self.explainability_service = DecisionExplainabilityService()
        self.communications_intelligence_service = CommunicationsIntelligenceService()
        self.package_review_service = PackageReviewService()
        self.thumbnail_service = ThumbnailService()
        self.future = None
        self.package_future = None
        self.content_future = None
        self.explanation_future = None
        self.communications_intelligence_future = None
        self.communications_intelligence_profile = None
        self.brief = None
        self._refresh_after_id = None
        self._load_timeout_after_id = None
        self._load_token = 0
        self.loading_state = "idle"
        self._destroyed = False

        self.build_page()
        self._refresh_after_id = self.after(
            500,
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

        self.refresh_button = ctk.CTkButton(
            header,
            text="Refresh Brief",
            command=self.refresh_brief
        )

        self.refresh_button.grid(
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

        if self.loading_state == "loading":
            if self.future and not self.future.done():
                self.future.cancel()

        self._refresh_after_id = None
        self._load_token += 1
        token = self._load_token
        self.loading_state = "loading"
        self.refresh_button.configure(state="disabled")
        self.status.configure(
            text="Preparing today's communication priorities..."
        )
        self.render_loading()

        self.future = context.job_manager.submit(
            self.service.generate,
            force=True
        )
        self.communications_intelligence_future = None
        self.communications_intelligence_profile = None

        logger.info("Communications Officer Morning Brief refresh queued")
        self._load_timeout_after_id = self.after(
            self.LOAD_TIMEOUT_MS,
            lambda value=token: self.loading_timed_out(value)
        )
        self.after(150, lambda value=token: self.check_brief_future(value))

    ##########################################################

    def check_brief_future(self, token=None):

        if self._destroyed:
            return

        if token != self._load_token:
            return

        if self.future is None:
            return

        if not self.future.done():
            self.after(150, lambda value=token: self.check_brief_future(value))
            return

        self.cancel_load_timeout()
        self.refresh_button.configure(state="normal")

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
            self.loading_state = "failed"
            self.status.configure(
                text=f"Morning Brief error: {ex}"
            )
            self.render_error(str(ex))
            return

        if self.is_empty_brief(self.brief):
            self.loading_state = "empty"
            self.status.configure(
                text="Brief ready, but no reviewed recommendations qualify yet."
            )
            self.render_empty()
            return

        self.loading_state = "loaded"
        stage = self.brief.get("brief_stage", "complete")
        self.status.configure(
            text=(
                f"Brief {stage}: " +
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

    def loading_timed_out(self, token):

        if self._destroyed or token != self._load_token:
            return

        if self.future is not None and self.future.done():
            return

        if self.brief:
            self.loading_state = "partial"
            self.refresh_button.configure(state="normal")
            self.status.configure(
                text="Recent activity available; recommendations are still preparing."
            )
            self.render_brief()
            return

        self.loading_state = "timed out"
        self.refresh_button.configure(state="normal")
        self.status.configure(
            text="Morning Brief is taking longer than expected."
        )
        self.render_error(
            "The brief is still preparing in the background. You can keep using the app or retry the refresh."
        )

    ##########################################################

    def cancel_load_timeout(self):

        if self._load_timeout_after_id is not None:
            try:
                self.after_cancel(self._load_timeout_after_id)
            except Exception:
                pass
            self._load_timeout_after_id = None

    ##########################################################

    def is_empty_brief(self, brief):

        if not brief:
            return True

        return not (
            brief.get("top_story") or
            brief.get("top_three_communication_opportunities") or
            brief.get("editorial_recommendations") or
            brief.get("recent_mfr_activity")
        )

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

    def render_empty(self):

        self.clear_content()
        label = ctk.CTkLabel(
            self.content,
            text=(
                "No reviewed communication priorities qualify yet. "
                "Review or approve real analysis, then refresh the brief."
            ),
            wraplength=900,
            justify="left"
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

        retry = ctk.CTkButton(
            self.content,
            text="Retry",
            command=self.refresh_brief
        )
        retry.pack(
            anchor="w",
            padx=10,
            pady=(0, 20)
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
        self.render_daily_post_packages()
        self.render_context()
        self.render_recent_mfr_activity()
        self.render_communication_priorities()
        self.render_best_operational_opportunities()
        self.render_top_story()
        self.render_secondary_stories()
        self.render_review_queue()
        self.render_new_media()
        self.render_videos_awaiting_review()
        self.render_memory_status()
        self.render_communications_gaps()
        self.render_risks_and_limitations()
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
            signal = item.get("year_over_year_signal") or {}
            if signal.get("summary"):
                lines.append(
                    "  Around this time: " + signal.get("summary", "")
                )
            if signal.get("communications_gap_risk"):
                lines.append(
                    "  Timing risk: " +
                    signal.get("communications_gap_risk", "")
                )

        if not lines:
            lines.append("No reviewed communication priority is ready yet.")

        self.add_section(
            "Today's Communication Priorities",
            lines
        )

    ##########################################################

    def render_recent_mfr_activity(self):

        clusters = self.brief.get("recent_mfr_activity", [])
        lines = []

        for item in clusters[:6]:
            lines.append(
                (
                    f"{item.get('title', '')} - "
                    f"{item.get('recency_label', '').replace('_', ' ')} - "
                    f"{item.get('photo_count', 0)} photo(s), "
                    f"{item.get('video_count', 0)} video(s), "
                    f"{item.get('reviewed_media_count', 0)} reviewed - "
                    f"{item.get('confidence', 0)}% confidence."
                )
            )
            evidence = item.get("evidence", [])
            if evidence:
                lines.append("  Evidence: " + self.format_list(evidence[:3]))

        if not lines:
            lines.append("No recent operational activity clusters were found.")

        self.add_section(
            "Recent MFR Activity",
            lines
        )

    ##########################################################

    def render_best_operational_opportunities(self):

        opportunities = self.brief.get("best_communication_opportunities", [])
        lines = []

        for item in opportunities[:3]:
            lines.append(
                (
                    f"{item.get('title', '')} - "
                    f"{item.get('suitable_media_count', 0)} suitable media - "
                    f"{item.get('confidence', 0)}% confidence - "
                    f"{item.get('repetition_risk', 'unknown')} repetition risk."
                )
            )
            lines.append("  Why now: " + item.get("why_now", ""))
            if item.get("last_similar_mfr_post"):
                last = item["last_similar_mfr_post"]
                lines.append(
                    "  Last similar MFR post: " +
                    (TimeService.format_local(last.get("post_date", "")) or last.get("post_date", "") or "Unknown")
                )
            signal = item.get("year_over_year_signal") or {}
            if signal.get("summary"):
                lines.append(
                    "  Around this time: " + signal.get("summary", "")
                )

        if not lines:
            lines.append("No operational communication opportunity is ready yet.")

        self.add_section(
            "Best Communication Opportunities",
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
            (
                "Around this time: " +
                (story.get("year_over_year_signal", {}) or {}).get(
                    "summary",
                    "No same-period historical signal."
                )
            ),
            "Why the public would care: " + story.get("why_public_would_care", ""),
            "Why it should outperform: " + story.get("why_it_should_outperform", ""),
            "Trust: " + story.get("trust_label", "Trust state unknown"),
            story.get("trust_summary", ""),
            "Platforms: " + self.format_list(story.get("recommended_platforms", [])),
            (
                "Next action options: " +
                self.format_list(story.get("next_action_options", []))
            ),
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

        media_button = ctk.CTkButton(
            frame,
            text="View Media Package",
            width=160,
            command=lambda item=story: self.show_story_media_package(item)
        )
        media_button.pack(
            side="right",
            padx=(0, 8),
            pady=12
        )

        primary = self.primary_media_asset(
            story.get("media_package", {})
        )

        if primary:
            open_button = ctk.CTkButton(
                frame,
                text="Open Primary Photo",
                width=150,
                command=lambda item=primary: self.open_media_asset(item)
            )
            open_button.pack(
                side="right",
                padx=(0, 8),
                pady=12
            )

        why_button = ctk.CTkButton(
            frame,
            text="Why This?",
            width=120,
            command=lambda item=story: self.request_decision_explanation(
                item,
                "recommendation"
            )
        )
        why_button.pack(
            side="right",
            padx=(0, 8),
            pady=12
        )

    ##########################################################

    def render_daily_post_packages(self):

        packages = self.brief.get("daily_post_packages", [])

        if not packages:
            return

        section = ctk.CTkFrame(
            self.content,
            fg_color="#20242b",
            corner_radius=8
        )
        section.pack(
            fill="x",
            padx=10,
            pady=(0, 16)
        )

        title = ctk.CTkLabel(
            section,
            text="Today's Three Daily Post Packages",
            font=("Segoe UI", 18, "bold")
        )
        title.pack(
            anchor="w",
            padx=14,
            pady=(12, 6)
        )

        for package in packages[:3]:
            card = ctk.CTkFrame(
                section,
                fg_color="#252b34",
                corner_radius=8
            )
            card.pack(
                fill="x",
                padx=12,
                pady=(6, 10)
            )

            header = ctk.CTkLabel(
                card,
                text=(
                    f"Option {package.get('option_number', '')}: "
                    f"{package.get('option_title') or package.get('title', '')}"
                ),
                font=("Segoe UI", 15, "bold"),
                anchor="w"
            )
            header.pack(
                fill="x",
                padx=12,
                pady=(10, 2)
            )

            details = [
                f"Strategy: {package.get('strategy', '')}",
                f"Why today: {package.get('why_today', '')}",
                f"Confidence: {package.get('confidence', 0)}%",
                f"Media trust: {package.get('media_trust_state', '')}",
                f"Format: {package.get('recommended_format', '')}",
                (
                    "Historical evidence: " +
                    (package.get("historical_evidence_summary") or "No close historical match found.")
                )
            ]

            text = ctk.CTkLabel(
                card,
                text="\n".join(details),
                wraplength=1050,
                justify="left",
                anchor="w"
            )
            text.pack(
                fill="x",
                padx=12,
                pady=(0, 8)
            )

            media_package = package.get("media_package", {}) or {}
            if package.get("primary_media"):
                media_panel = PackageMediaPanel(
                    card,
                    media_package,
                    self.thumbnail_service,
                    open_callback=self.open_media_asset,
                    preview_callback=self.show_asset_preview,
                    compact=True
                )
                media_panel.pack(
                    anchor="w",
                    padx=12,
                    pady=(0, 8)
                )
            else:
                graphic = package.get("graphic_brief") or {}
                ctk.CTkLabel(
                    card,
                    text=(
                        "Text/graphic-first recommendation\n"
                        f"Graphic brief: {graphic.get('visual_direction', '')}"
                    ),
                    text_color="#d8e6ff",
                    fg_color="#1f2630",
                    corner_radius=6,
                    wraplength=900,
                    justify="left"
                ).pack(
                    fill="x",
                    padx=12,
                    pady=(0, 8)
                )

            captions = ctk.CTkTextbox(
                card,
                height=150,
                wrap="word"
            )
            captions.pack(
                fill="x",
                padx=12,
                pady=(0, 8)
            )
            captions.insert(
                "1.0",
                (
                    "Facebook\n"
                    f"{package.get('facebook_caption', '')}\n\n"
                    "Instagram\n"
                    f"{package.get('instagram_caption', '')}"
                )
            )
            captions.configure(state="disabled")

            warning_text = " | ".join(package.get("warnings") or [])
            if warning_text:
                warning = ctk.CTkLabel(
                    card,
                    text=warning_text,
                    text_color="#ffcf7a",
                    wraplength=1050,
                    justify="left"
                )
                warning.pack(
                    fill="x",
                    padx=12,
                    pady=(0, 8)
                )

            actions = ctk.CTkFrame(
                card,
                fg_color="transparent"
            )
            actions.pack(
                fill="x",
                padx=12,
                pady=(0, 10)
            )

            ctk.CTkButton(
                actions,
                text="Copy Facebook",
                width=130,
                command=lambda item=package: self.copy_daily_text(
                    item,
                    "facebook_caption"
                )
            ).pack(side="left", padx=(0, 8))
            ctk.CTkButton(
                actions,
                text="Copy Instagram",
                width=130,
                command=lambda item=package: self.copy_daily_text(
                    item,
                    "instagram_caption"
                )
            ).pack(side="left", padx=(0, 8))

            primary = package.get("primary_media") or {}
            if primary:
                ctk.CTkButton(
                    actions,
                    text="Open Media",
                    width=110,
                    command=lambda item=primary: self.open_media_asset(item)
                ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                actions,
                text="Media Package",
                width=130,
                command=lambda item=package: self.show_story_media_package(
                    {
                        "media_package": item.get("media_package", {})
                    }
                )
            ).pack(side="left")
            if package.get("event_diagnostics"):
                ctk.CTkButton(
                    actions,
                    text="Event Diagnostics",
                    width=145,
                    command=lambda item=package: self.show_event_diagnostics(item)
                ).pack(side="left", padx=(8, 0))
            ctk.CTkButton(
                actions,
                text="Approve Package",
                width=135,
                command=lambda item=package: self.record_package_decision(
                    item,
                    "approve_package"
                )
            ).pack(side="left", padx=(8, 0))
            ctk.CTkButton(
                actions,
                text="Reject Media",
                width=115,
                command=lambda item=package: self.record_package_decision(
                    item,
                    "reject_media"
                )
            ).pack(side="left", padx=(8, 0))
            for label, decision in (
                ("Correct Event", "correct_event"),
                ("Shorten", "shorten_caption"),
                ("More Community", "make_more_community_focused"),
                ("Lighter Tone", "make_more_light_hearted")
            ):
                ctk.CTkButton(
                    actions,
                    text=label,
                    width=120,
                    command=lambda item=package, kind=decision: self.record_package_decision(
                        item,
                        kind
                    )
                ).pack(side="left", padx=(8, 0))

            review = package.get("package_review") or {}
            quality = package.get("quality_gate") or {}
            review_label = ctk.CTkLabel(
                card,
                text=(
                    "Package review: required before publishing | "
                    f"Quality gate: {'passed' if quality.get('passed') else 'needs attention'} | "
                    "Actions: " + self.format_list(review.get("actions", [])[:4])
                ),
                text_color="#b9d7ff",
                wraplength=1050,
                justify="left"
            )
            review_label.pack(
                fill="x",
                padx=12,
                pady=(0, 10)
            )

    def copy_daily_text(self, package, key):

        self.clipboard_clear()
        self.clipboard_append((package or {}).get(key, ""))
        self.status.configure(text="Daily package text copied.")

    def record_package_decision(self, package, decision_type):

        result = self.package_review_service.record_decision(
            package,
            decision_type
        )
        self.status.configure(
            text=(
                "Package decision recorded: "
                f"{decision_type.replace('_', ' ')} "
                f"(#{result.get('decision_id')})."
            )
        )

    def show_event_diagnostics(self, package):

        diagnostics = (package or {}).get("event_diagnostics") or {}
        event = (package or {}).get("event_collection") or {}
        window = ctk.CTkToplevel(self)
        window.title("Event Diagnostics")
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 820, 620, parent=self)
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
            self.event_diagnostics_text(diagnostics, event)
        )
        textbox.configure(state="disabled")

        ctk.CTkButton(
            window,
            text="Close",
            command=window.destroy
        ).pack(
            anchor="e",
            padx=16,
            pady=(0, 16)
        )

    def event_diagnostics_text(self, diagnostics, event):

        integrity = (
            diagnostics.get("event_integrity")
            or event.get("event_integrity")
            or {}
        )
        lines = [
            "Event Diagnostics",
            "",
            f"Title: {diagnostics.get('event_title') or event.get('title', '')}",
            f"Title source: {diagnostics.get('title_source') or event.get('title_source', '')}",
            f"Title confidence: {diagnostics.get('title_confidence') or event.get('title_confidence', 0)}",
            f"Event confidence: {diagnostics.get('confidence') or event.get('confidence', 0)}",
            f"Usability: {diagnostics.get('event_usability_state') or integrity.get('event_usability_state', '')}",
            f"Coherence score: {integrity.get('coherence_score', 0)}",
            f"Date range: {diagnostics.get('date_range') or event.get('when_it_occurred', {})}",
            f"Source folders: {self.format_list(diagnostics.get('source_folders') or event.get('source_folders') or [])}",
            f"Media count: {diagnostics.get('media_count') or event.get('media_count', 0)}",
            "",
            "Grouping Evidence:",
            *[
                "- " + str(item)
                for item in (
                    diagnostics.get("grouping_evidence")
                    or integrity.get("grouping_evidence")
                    or []
                )
            ],
            "",
            "Conflicts:",
            *[
                "- " + str(item)
                for item in (
                    diagnostics.get("conflicts")
                    or integrity.get("conflicts")
                    or ["No blocking conflicts reported."]
                )
            ],
            "",
            "Excluded Items:",
            *[
                "- " + str(item.get("filename", "")) + ": " + str(item.get("reason", ""))
                for item in (
                    diagnostics.get("excluded_items")
                    or integrity.get("excluded_media")
                    or []
                )[:20]
            ],
            "",
            "Semantic Verification:",
            diagnostics.get("semantic_verification_status", "")
        ]
        return "\n".join(str(line) for line in lines)

    ##########################################################

    def show_story_media_package(self, story):

        package = story.get("media_package", {}) or {}
        window = ctk.CTkToplevel(self)
        window.title("Recommended Media Package")
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 900, 640, parent=self)
        window.lift()

        panel = PackageMediaPanel(
            window,
            package,
            self.thumbnail_service,
            open_callback=self.open_media_asset,
            reveal_callback=self.reveal_media_asset,
            copy_callback=self.copy_media_path,
            preview_callback=self.show_asset_preview
        )
        panel.pack(fill="x", padx=16, pady=(16, 8))

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
            self.media_package_text(package)
        )
        textbox.configure(state="disabled")

        footer = ctk.CTkFrame(window, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 16))
        primary = self.primary_media_asset(package)

        if primary:
            ctk.CTkButton(
                footer,
                text="Open Primary",
                command=lambda item=primary: self.open_media_asset(item)
            ).pack(side="left", padx=(0, 8))
            ctk.CTkButton(
                footer,
                text="Copy File Path",
                command=lambda item=primary: self.copy_media_path(item)
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            footer,
            text="Close",
            command=window.destroy
        ).pack(side="right")

    ##########################################################

    def media_package_text(self, package):

        package = package or {}
        lines = [
            "Primary Photo",
            self.media_asset_line(package.get("primary_photo") or package.get("best_photo")),
            "",
            "Primary Video",
            self.media_asset_line(package.get("primary_video") or package.get("best_video")),
            "",
            "Supporting Photos",
            self.media_asset_lines(package.get("gallery_photos") or package.get("supporting_photos")),
            "",
            "Supporting Videos",
            self.media_asset_lines(package.get("gallery_videos") or package.get("supporting_videos")),
            "",
            "Why These Assets",
            self.format_list(package.get("reasons", [])),
            "",
            "Diversity Reasoning",
            self.format_list(package.get("diversity_reasoning", [])),
            "",
            "Platform Guidance",
            self.platform_guidance_text(package.get("platform_media_guidance", {})),
            "",
            "Scores",
            (
                f"Story relevance {package.get('story_relevance', 0)} | "
                f"Media score {package.get('media_score', 0)} | "
                f"Platform fit {package.get('platform_fit', 0)} | "
                f"Recent-use risk {package.get('recent_use_risk', 0)}"
            )
        ]
        return "\n".join(str(line) for line in lines)

    def media_asset_lines(self, assets):

        lines = [
            self.media_asset_line(item)
            for item in (assets or [])
        ]
        return "\n".join(lines) if lines else "None"

    def media_asset_line(self, asset):

        asset = asset or {}

        if not asset:
            return "None"

        return (
            f"{asset.get('filename', '')} | "
            f"{asset.get('media_type', '')} | "
            f"trust {asset.get('trust_state', '')} | "
            f"score {asset.get('media_score', asset.get('communications_score', 0))} | "
            f"{asset.get('why_selected', '')}"
        )

    def platform_guidance_text(self, guidance):

        lines = []

        for platform, item in (guidance or {}).items():
            lines.append(
                (
                    f"{platform}: {item.get('primary_filename', '')} - "
                    f"{item.get('reason', '')}"
                )
            )

        return "\n".join(lines) if lines else "No platform-specific media guidance."

    def primary_media_asset(self, package):

        package = package or {}
        return (
            package.get("primary_photo")
            or package.get("best_photo")
            or package.get("primary_video")
            or package.get("best_video")
            or {}
        )

    def open_media_asset(self, asset):

        asset = asset or {}

        if not asset.get("media_id"):
            return

        if asset.get("media_type") == "video":
            path = asset.get("path", "")
            if path:
                os.startfile(path)
            return

        PhotoViewer(
            self,
            asset["media_id"],
            asset.get("filename", ""),
            asset.get("path", "")
        )

    def reveal_media_asset(self, asset):

        path = (asset or {}).get("path", "")

        if not path:
            return

        subprocess.Popen(
            ["explorer", "/select,", path]
        )

    def copy_media_path(self, asset):

        self.clipboard_clear()
        self.clipboard_append((asset or {}).get("path", ""))
        self.status.configure(text="Media file path copied.")

    def show_asset_preview(self, asset):

        window = ctk.CTkToplevel(self)
        window.title(asset.get("filename", "Media Preview"))
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 640, 520, parent=self)
        window.lift()
        panel = PackageMediaPanel(
            window,
            {
                "primary_video" if asset.get("media_type") == "video" else "primary_photo": asset
            },
            self.thumbnail_service,
            open_callback=self.open_media_asset,
            reveal_callback=self.reveal_media_asset,
            copy_callback=self.copy_media_path,
            preview_callback=None
        )
        panel.pack(fill="both", expand=True, padx=16, pady=16)

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
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 900, 720, parent=self)
        window.lift()

        visual_panel = PackageMediaPanel(
            window,
            package.get("media_package", {}),
            self.thumbnail_service,
            open_callback=self.open_media_asset,
            reveal_callback=self.reveal_media_asset,
            copy_callback=self.copy_media_path,
            preview_callback=self.show_asset_preview
        )
        visual_panel.pack(fill="x", padx=16, pady=(16, 8))

        textbox = ctk.CTkTextbox(
            window,
            wrap="word"
        )
        textbox.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(0, 8)
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
            text="Decision Audit",
            command=lambda item=package: self.show_decision_audit(
                item.get("decision_audit", {})
            )
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
                "Asset Selection\n" + "\n".join(
                    [
                        "Reasons: " + self.format_list(media.get("reasons", [])),
                        "Diversity: " + self.format_list(media.get("diversity_reasoning", [])),
                        "Platform media guidance:\n" + self.platform_guidance_text(
                            package.get("platform_media_guidance", {})
                            or media.get("platform_media_guidance", {})
                        )
                    ]
                ),
                "Suggested Hashtags\n" + " ".join(package.get("suggested_hashtags", [])),
                "Suggested CTA\n" + package.get("suggested_cta", ""),
                "Package Score\n" + str(scoring),
                "Decision Audit\n" + self.decision_audit_summary(
                    package.get("decision_audit", {})
                )
            ]
        )

    ##########################################################

    def request_decision_explanation(self, subject, decision_type="recommendation"):

        if self.explanation_future and not self.explanation_future.done():
            return

        alternatives = []

        if decision_type == "recommendation" and self.brief:
            alternatives = [
                item for item in self.brief.get("top_three_communication_opportunities", [])
                if item is not subject
            ]

        self.status.configure(text="Preparing decision explanation...")
        self.explanation_future = context.job_manager.submit(
            self.explainability_service.explain_recommendation,
            subject,
            alternatives
        )
        self.after(120, self.check_explanation_future)

    ##########################################################

    def check_explanation_future(self):

        if self._destroyed or self.explanation_future is None:
            return

        if not self.explanation_future.done():
            self.after(120, self.check_explanation_future)
            return

        try:
            explanation = self.explanation_future.result()
        except Exception as ex:
            logger.error(
                "Decision explanation failed",
                exc_info=(type(ex), ex, ex.__traceback__)
            )
            self.status.configure(text=f"Decision explanation error: {ex}")
            self.explanation_future = None
            return

        self.explanation_future = None
        self.status.configure(text="Decision explanation ready.")
        self.show_decision_audit(explanation)

    ##########################################################

    def show_decision_audit(self, explanation):

        explanation = explanation or {}
        window = ctk.CTkToplevel(self)
        window.title("Decision Audit")
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 900, 720, parent=self)
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
            self.explainability_service.format_explanation_text(explanation)
        )
        textbox.configure(state="disabled")

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

    def decision_audit_summary(self, explanation):

        if not explanation:
            return "No decision audit is attached yet."

        return "\n".join(
            [
                "Why selected: " + self.format_list(
                    explanation.get("why_selected", [])[:3]
                ),
                "Evidence count: " + str(explanation.get("evidence_count", 0)),
                "Trust: " + explanation.get("trust_label", "")
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
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 950, 760, parent=self)
        window.lift()

        selected = {"platform": "facebook"}
        source_package = package.get("source_package", {}) or {}
        media_panel = PackageMediaPanel(
            window,
            source_package.get("media_package", {}),
            self.thumbnail_service,
            open_callback=self.open_media_asset,
            reveal_callback=self.reveal_media_asset,
            copy_callback=self.copy_media_path,
            preview_callback=self.show_asset_preview,
            compact=True
        )
        media_panel.pack(fill="x", padx=16, pady=(16, 8))
        body = ctk.CTkTextbox(window, wrap="word")
        body.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(0, 8)
        )

        controls = ctk.CTkFrame(window, fg_color="transparent")
        controls.pack(
            fill="x",
            padx=16,
            pady=(8, 0)
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
                        "Internal media guidance: " + self.generated_media_guidance_text(
                            output.get("media_guidance", {})
                        ),
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
            text="Decision Audit",
            command=lambda item=package: self.show_decision_audit(
                item.get("generated_content_audit", {})
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

    def generated_media_guidance_text(self, guidance):

        guidance = guidance or {}
        support = guidance.get("supporting_media") or []
        support_names = [
            item.get("filename", "")
            for item in support
            if item.get("filename")
        ]
        return (
            f"Primary: {guidance.get('primary_filename', 'None')}. "
            f"Supporting: {self.format_list(support_names)}. "
            f"Why: {guidance.get('why', '')}"
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
                "Historical communications imported: "
                f"{memory.get('historical_communications_imported', 0):,}"
            ),
            f"Deliveries: {memory.get('communication_deliveries', 0):,}",
            (
                "Latest post: " +
                (
                    TimeService.format_local(memory.get("latest_post", ""))
                    or memory.get("latest_post", "")
                    or "Unknown"
                )
            ),
            (
                "Oldest communication: " +
                (
                    TimeService.format_local(memory.get("first_post", ""))
                    or memory.get("first_post", "")
                    or "Unknown"
                )
            ),
            (
                "Engagement records: "
                f"{memory.get('engagement_records', 0):,}"
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

    def render_communications_gaps(self):

        gaps = self.brief.get("communications_gaps", [])
        lines = list(gaps or [])

        if not lines:
            lines.append("No operational communications gaps were detected.")

        self.add_section(
            "Communications Gaps",
            lines[:8]
        )

    ##########################################################

    def render_risks_and_limitations(self):

        risks = self.brief.get("risks_and_limitations", [])
        lines = list(risks or [])

        if not lines:
            lines.append("No major limitations detected for this brief.")

        self.add_section(
            "Risks and Limitations",
            lines[:8]
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

        ctk.CTkButton(
            card,
            text="Why?",
            width=120,
            command=lambda item=recommendation: self.request_decision_explanation(
                item,
                "recommendation"
            )
        ).grid(
            row=2,
            column=1,
            sticky="e",
            padx=12,
            pady=(0, 10)
        )

    ##########################################################

    def show_recommendation_details(self, recommendation):

        window = ctk.CTkToplevel(self)
        window.title(recommendation.get("title", "Recommendation Details"))
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 900, 700, parent=self)
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

        if hasattr(self, "thumbnail_service"):
            self.thumbnail_service.shutdown()

        super().destroy()
