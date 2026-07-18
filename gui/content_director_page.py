from concurrent.futures import ThreadPoolExecutor
import os
import queue
import subprocess

import customtkinter as ctk

from gui.package_media_panel import PackageMediaPanel
from gui.photo_card import PhotoCard
from gui.photo_viewer import PhotoViewer
from services.communications_director import CommunicationsDirector
from services.communications_memory_service import CommunicationsMemoryService
from services.communications_officer_service import CommunicationsOfficerService
from services.communications_reasoning_service import CommunicationsReasoningService
from services.communication_package_service import CommunicationPackageService
from services.content_director_retrieval_service import ContentDirectorRetrievalService
from services.content_generation_service import ContentGenerationService
from services.decision_explainability_service import DecisionExplainabilityService
from services.editorial_comparison_service import EditorialComparisonService
from services.logging_service import LoggingService
from services.thumbnail_service import ThumbnailService
from gui.window_placement import WindowPlacement


logger = LoggingService.get_logger("content")


class ContentDirectorPage(ctk.CTkFrame):

    LOAD_TIMEOUT_MS = 30000

    def __init__(self, parent):

        super().__init__(parent)

        self.director = CommunicationsDirector()
        self.reasoning_service = CommunicationsReasoningService(
            director=self.director
        )
        self.officer_service = CommunicationsOfficerService()
        self.communication_package_service = CommunicationPackageService()
        self.retrieval_service = ContentDirectorRetrievalService()
        self.content_generation_service = ContentGenerationService()
        self.explainability_service = DecisionExplainabilityService()
        self.editorial_comparison_service = EditorialComparisonService()
        self.memory_service = CommunicationsMemoryService()
        self.thumbnail_service = ThumbnailService()
        self.current_results = []
        self.brief = None
        self.brief_cache = None
        self.package_cache = {}
        self.package_jobs = {}
        self.package_preview_cache = {}
        self.package_preview_jobs = {}
        self.strategy_cache = {}
        self.strategy_jobs = {}
        self.strategy_views = set()
        self.ui_queue = queue.Queue()
        self.loading_state = "idle"
        self._load_token = 0
        self._load_timeout_after_id = None
        self.brief_future = None
        self.suggestion_future = None
        self.active_request_id = ""
        self.executor = ThreadPoolExecutor(
            max_workers=2
        )
        self._destroyed = False

        self.build_page()
        self.after(
            100,
            self.process_ui_queue
        )
        self.refresh_brief()

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

        self.generate_button = ctk.CTkButton(
            prompt_frame,
            text="Generate Suggestions",
            command=self.generate_suggestions
        )

        self.generate_button.grid(
            row=0,
            column=1
        )

        self.cancel_button = ctk.CTkButton(
            prompt_frame,
            text="Cancel",
            width=90,
            command=self.cancel_current_request,
            state="disabled"
        )

        self.cancel_button.grid(
            row=0,
            column=2,
            padx=(8, 0)
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

    def enqueue_ui(self, callback, *args):

        if self._destroyed:
            return

        self.ui_queue.put(
            (
                callback,
                args
            )
        )

    ##########################################################

    def process_ui_queue(self):

        if self._destroyed:
            return

        while True:
            try:
                callback, args = self.ui_queue.get_nowait()

            except queue.Empty:
                break

            callback(
                *args
            )

        self.after(
            100,
            self.process_ui_queue
        )

    ##########################################################

    def refresh_brief(self):

        if self.loading_state == "loading":
            return

        if self.brief_cache:
            self.loading_state = "loaded"
            self.brief = self.brief_cache
            self.render_brief()
            self.current_results = self.brief.get(
                "recommendations",
                []
            )
            self.render_results()
            self.render_daily_opportunities()
            return

        self.loading_state = "loading"
        self._load_token += 1
        token = self._load_token
        self.active_request_id = f"brief-{token}"
        self.generate_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status.configure(
            text="Loading today's communications brief..."
        )
        self.render_loading_results(
            "Preparing today's recommendations..."
        )
        self.brief_future = self.executor.submit(
            self.officer_service.generate_fast,
            force=True
        )
        self.brief_future.add_done_callback(
            lambda item: self.enqueue_ui(
                self.finish_refresh_brief,
                item,
                token
            )
        )
        self._load_timeout_after_id = self.after(
            self.LOAD_TIMEOUT_MS,
            lambda value=token: self.loading_timed_out(value)
        )

    ##########################################################

    def finish_refresh_brief(self, future, token=None):

        if self._destroyed:
            return

        if token != self._load_token:
            return

        self.cancel_load_timeout()
        self.generate_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

        try:
            self.brief = future.result()
            self.brief_cache = self.brief

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
            self.loading_state = "failed"
            self.status.configure(
                text=f"Today's Brief error: {ex}"
            )
            self.render_failure(str(ex))
            return

        self.loading_state = "loaded"
        self.render_brief()
        self.current_results = self.brief.get(
            "recommendations",
            []
        )
        if not self.current_results:
            self.loading_state = "empty"
        self.render_results()
        self.render_daily_opportunities()

    ##########################################################

    def loading_timed_out(self, token):

        if self._destroyed or token != self._load_token:
            return

        self.loading_state = "timed out"
        self.generate_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.status.configure(
            text="Content Director is taking longer than expected."
        )
        self.render_failure(
            "Recommendations are still preparing in the background. You can retry without restarting the app."
        )

    ##########################################################

    def cancel_current_request(self):

        self._load_token += 1
        self.loading_state = "cancelled"
        self.cancel_load_timeout()
        self.generate_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

        for future in (self.brief_future, self.suggestion_future):
            if future and not future.done():
                future.cancel()

        self.status.configure(
            text="Request cancelled."
        )
        self.render_failure(
            "Request cancelled. Enter a prompt and retry when ready."
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

    def render_brief(self):

        for child in self.brief_frame.winfo_children():
            child.destroy()

        if not self.brief:
            return

        if "library_health" not in self.brief:
            self.render_fast_brief_summary()
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

    def render_fast_brief_summary(self):

        summary = self.brief.get("summary", {}) or {}
        context = self.brief.get("current_context", {}) or {}
        stage = self.brief.get("brief_stage", "partial")
        lines = [
            f"Stage: {stage}",
            "Recent activity loaded: " +
            str(len(self.brief.get("recent_mfr_activity", []))),
            "Historical memory: " +
            (self.brief.get("communications_memory_status", {}) or {}).get(
                "status",
                "Unavailable"
            ),
            "Review queue: " + str(summary.get("review_queue_size", 0)),
            "Season: " + self.format_label(context.get("season", "")),
            "Active themes: " + self.format_context_list(
                context.get("active_themes", [])
            ),
            "Recommendations still preparing or deferred."
        ]
        label = ctk.CTkLabel(
            self.brief_frame,
            text="\n".join(lines),
            justify="left",
            wraplength=1100
        )
        label.grid(
            row=1,
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

        if self.loading_state == "loading":
            return

        prompt = self.prompt_entry.get().strip()
        self.loading_state = "loading"
        self._load_token += 1
        token = self._load_token
        self.active_request_id = f"prompt-{token}"
        self.generate_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status.configure(
            text="Generating communication opportunities..."
        )
        if not opportunity_types:
            interpreted = self.retrieval_service.interpret_query(prompt)
            self.render_prompt_progress(
                interpreted,
                "Searching MFR history, operational activity, and compatible media..."
            )
        else:
            self.render_loading_results(
                "Finding recommendations..."
            )
        self.suggestion_future = self.executor.submit(
            self.load_suggestions,
            prompt,
            opportunity_types
        )
        self.suggestion_future.add_done_callback(
            lambda item: self.enqueue_ui(
                self.finish_generate_suggestions,
                item,
                token
            )
        )
        self._load_timeout_after_id = self.after(
            self.LOAD_TIMEOUT_MS,
            lambda value=token: self.loading_timed_out(value)
        )

    ##########################################################

    def load_suggestions(self, prompt, opportunity_types=None):

        if opportunity_types:
            return {
                "opportunity_types": opportunity_types,
                "opportunities": self.reasoning_service.generate_recommendations(
                    opportunity_keys=opportunity_types,
                    limit=5
                )
            }

        package = self.retrieval_service.build_prompt_package(
            prompt,
            limit=5
        )
        return {
            "opportunity_types": [
                package.get("interpreted_topic", {}).get(
                    "primary_topic",
                    "general_engagement"
                )
            ],
            "opportunities": [],
            "production_package": package,
            "request_id": package.get("request_id", "")
        }

    ##########################################################

    def finish_generate_suggestions(self, future, token=None):

        if self._destroyed:
            return

        if token != self._load_token:
            return

        self.cancel_load_timeout()
        self.generate_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")

        try:
            result = future.result()

        except Exception as ex:
            logger.error(
                "Communications Director request failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.loading_state = "failed"
            self.status.configure(
                text=f"Communications Director error: {ex}"
            )
            self.render_failure(str(ex))
            return

        if result.get("production_package"):
            self.current_results = []
            self.loading_state = "loaded"
            topic = result["production_package"].get("interpreted_topic", {})
            self.status.configure(
                text=(
                    "Opportunity type: " +
                    self.format_label(topic.get("primary_topic", ""))
                )
            )
            self.render_prompt_package(
                result["production_package"]
            )
            return

        self.current_results = result["opportunities"]
        self.loading_state = "loaded" if self.current_results else "empty"
        labels = [
            self.format_label(item)
            for item in result["opportunity_types"]
        ]
        self.status.configure(
            text=f"Opportunity type: {', '.join(labels)}"
        )
        self.render_results()

    ##########################################################

    def render_failure(self, message):

        for child in self.results.winfo_children():
            child.destroy()

        label = ctk.CTkLabel(
            self.results,
            text=message,
            wraplength=900,
            justify="left"
        )
        label.pack(
            pady=(30, 10),
            padx=10,
            anchor="w"
        )

        retry = ctk.CTkButton(
            self.results,
            text="Retry",
            command=self.refresh_brief
        )
        retry.pack(
            padx=10,
            anchor="w"
        )

    ##########################################################

    def render_loading_results(self, message):

        for child in self.results.winfo_children():
            child.destroy()

        label = ctk.CTkLabel(
            self.results,
            text=message
        )

        label.pack(
            pady=30
        )

    ##########################################################

    def render_prompt_progress(self, interpreted, message):

        for child in self.results.winfo_children():
            child.destroy()

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

        heading = ctk.CTkLabel(
            frame,
            text="Preparing Production Package",
            font=("Segoe UI", 20, "bold")
        )
        heading.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=(12, 3)
        )
        self.add_caption_line(
            frame,
            1,
            "Interpreted Topic",
            interpreted.get("label", "")
        )
        self.add_caption_line(
            frame,
            2,
            "Secondary Topics",
            self.format_values(interpreted.get("secondary_topics", []))
        )
        self.add_caption_line(
            frame,
            3,
            "Retrieval Status",
            message
        )

    ##########################################################

    def render_prompt_package(self, package):

        if package.get("options") and not package.get("selected_option_id"):
            self.render_prompt_options(package)
            return

        for child in self.results.winfo_children():
            child.destroy()

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
        topic = package.get("interpreted_topic", {})
        summary = package.get("opportunity_summary", {})
        media = package.get("media_package", {}) or {}
        primary = (
            media.get("primary_image")
            or media.get("primary_video")
            or {}
        )

        if primary:
            card = PhotoCard(
                frame,
                primary.get("media_id"),
                primary.get("filename", ""),
                primary.get("path", ""),
                thumbnail_service=self.thumbnail_service
            )
            card.grid(
                row=0,
                column=0,
                rowspan=18,
                padx=12,
                pady=12,
                sticky="nw"
            )

        title = ctk.CTkLabel(
            frame,
            text=(
                f"{summary.get('what', topic.get('label', 'Communication Package'))} "
                f"- {summary.get('confidence', 0)}% Confidence"
            ),
            font=("Segoe UI", 20, "bold"),
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
        self.add_caption_line(
            frame,
            1,
            "Why Now",
            summary.get("why_now", "")
        )
        self.add_caption_line(
            frame,
            2,
            "Current Context Evidence",
            self.current_context_text(summary.get("current_context_evidence", {}))
        )
        self.add_caption_line(
            frame,
            3,
            "Historical MFR Evidence",
            self.historical_reference_text(package.get("historical_references", []))
        )
        self.add_caption_line(
            frame,
            4,
            "Around This Time in Previous Years",
            self.around_this_time_text(package.get("around_this_time", {}))
        )
        self.add_caption_line(
            frame,
            5,
            "Media Package",
            self.production_media_text(media)
        )
        self.add_caption_line(
            frame,
            6,
            "Facebook",
            package.get("facebook_draft", {}).get("copy_text", "")
        )
        self.add_caption_line(
            frame,
            7,
            "Instagram",
            package.get("instagram_draft", {}).get("copy_text", "")
        )
        self.add_caption_line(
            frame,
            8,
            "Validation Warnings",
            self.format_values(package.get("validation_warnings", []))
        )
        self.add_caption_line(
            frame,
            9,
            "Why Selected",
            self.format_values(package.get("trust_explanation", []))
        )

        controls = ctk.CTkFrame(
            frame,
            fg_color="transparent"
        )
        controls.grid(
            row=10,
            column=1,
            sticky="w",
            padx=(0, 12),
            pady=(6, 12)
        )

        buttons = (
            ("Copy Facebook", package.get("facebook_draft", {}).get("copy_text", "")),
            ("Copy Instagram", package.get("instagram_draft", {}).get("copy_text", "")),
            ("Retry", None),
        )

        for label, value in buttons:
            command = (
                self.generate_suggestions
                if value is None
                else lambda name=label, text=value: self.copy_text(name, text)
            )
            button = ctk.CTkButton(
                controls,
                text=label,
                width=135,
                command=command
            )
            button.pack(
                side="left",
                padx=(0, 8)
            )

        if primary:
            open_button = ctk.CTkButton(
                controls,
                text="Open Media",
                width=135,
                command=lambda item=primary: self.open_package_asset(item)
            )
            open_button.pack(
                side="left",
                padx=(0, 8)
            )

        if package.get("around_this_time", {}).get("matches"):
            memory_controls = ctk.CTkFrame(
                frame,
                fg_color="transparent"
            )
            memory_controls.grid(
                row=11,
                column=1,
                sticky="w",
                padx=(0, 12),
                pady=(0, 12)
            )
            for label, command in (
                (
                    "Use as Reference",
                    lambda item=package: self.copy_text(
                        "Around This Time Reference",
                        self.around_this_time_text(item.get("around_this_time", {}))
                    )
                ),
                (
                    "Generate Updated Version",
                    lambda item=package: self.generate_updated_from_memory(item)
                ),
                (
                    "View in Communications Memory",
                    lambda item=package: self.show_around_this_time_memory(item)
                )
            ):
                ctk.CTkButton(
                    memory_controls,
                    text=label,
                    width=170,
                    command=command
                ).pack(
                    side="left",
                    padx=(0, 8)
                )

    ##########################################################

    def render_prompt_options(self, package):

        for child in self.results.winfo_children():
            child.destroy()

        frame = ctk.CTkFrame(
            self.results,
            corner_radius=8
        )
        frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        topic = package.get("interpreted_topic", {}) or {}
        heading = ctk.CTkLabel(
            frame,
            text=(
                "Content Options - " +
                topic.get("label", "Communication Opportunity")
            ),
            font=("Segoe UI", 20, "bold"),
            anchor="w"
        )
        heading.pack(
            fill="x",
            padx=12,
            pady=(12, 4)
        )

        if package.get("option_limit_reason"):
            ctk.CTkLabel(
                frame,
                text=package.get("option_limit_reason", ""),
                wraplength=980,
                justify="left",
                text_color="#d4b483"
            ).pack(
                fill="x",
                padx=12,
                pady=(0, 8)
            )

        ctk.CTkLabel(
            frame,
            text=(
                "Around This Time in Previous Years\n" +
                self.around_this_time_text(package.get("around_this_time", {}))
            ),
            wraplength=980,
            justify="left",
            anchor="w"
        ).pack(
            fill="x",
            padx=12,
            pady=(0, 8)
        )

        options_frame = ctk.CTkFrame(
            frame,
            fg_color="transparent"
        )
        options_frame.pack(
            fill="x",
            padx=12,
            pady=(6, 12)
        )

        for option in package.get("options", [])[:5]:
            self.render_prompt_option_card(
                options_frame,
                package,
                option
            )

    def render_prompt_option_card(self, parent, package, option):

        card = ctk.CTkFrame(
            parent,
            corner_radius=8
        )
        card.pack(
            fill="x",
            pady=(0, 10)
        )
        card.grid_columnconfigure(1, weight=1)

        media = option.get("media_package", {}) or {}
        primary = media.get("primary_image") or media.get("primary_video") or {}
        if primary:
            thumb = PhotoCard(
                card,
                primary.get("media_id"),
                primary.get("filename", ""),
                primary.get("path", ""),
                thumbnail_service=self.thumbnail_service
            )
            thumb.grid(
                row=0,
                column=0,
                rowspan=4,
                padx=10,
                pady=10,
                sticky="nw"
            )

        title = ctk.CTkLabel(
            card,
            text=(
                f"{option.get('title', '')} - "
                f"{option.get('confidence', 0)}% - "
                f"{option.get('recommended_format', '')}"
            ),
            font=("Segoe UI", 16, "bold"),
            wraplength=850,
            justify="left"
        )
        title.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=10,
            pady=(10, 2)
        )
        summary = ctk.CTkLabel(
            card,
            text=(
                option.get("strategic_angle", "") +
                "\nAudience: " +
                self.format_values(option.get("target_audience", [])) +
                "\nTiming: " +
                (option.get("year_over_year_evidence", {}) or {}).get(
                    "summary",
                    ""
                )
            ),
            wraplength=850,
            justify="left",
            anchor="w"
        )
        summary.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=10,
            pady=(0, 4)
        )
        warning_text = self.format_values(option.get("validation_warnings", [])[:2])
        if warning_text:
            ctk.CTkLabel(
                card,
                text="Warnings: " + warning_text,
                wraplength=850,
                justify="left",
                text_color="#d4b483"
            ).grid(
                row=2,
                column=1,
                sticky="ew",
                padx=10,
                pady=(0, 4)
            )

        controls = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        controls.grid(
            row=3,
            column=1,
            sticky="w",
            padx=10,
            pady=(4, 10)
        )

        buttons = (
            (
                "View Full Option",
                lambda item=option: self.render_prompt_package(
                    self.package_for_option(package, item)
                )
            ),
            (
                "Use This Option",
                lambda item=option: self.use_prompt_option(package, item)
            ),
            (
                "Copy Facebook",
                lambda item=option: self.copy_text(
                    "Facebook",
                    item.get("facebook_caption", "")
                )
            ),
            (
                "Copy Instagram",
                lambda item=option: self.copy_text(
                    "Instagram",
                    item.get("instagram_caption", "")
                )
            ),
            (
                "Change Media",
                lambda item=option: self.render_prompt_package(
                    self.package_for_option(package, item)
                )
            ),
            (
                "Regenerate This Option",
                lambda item=option: self.regenerate_prompt_option(
                    package,
                    item
                )
            ),
            (
                "Create Publication Draft",
                lambda item=option: self.create_option_publication_draft(
                    package,
                    item
                )
            )
        )
        for label, command in buttons:
            ctk.CTkButton(
                controls,
                text=label,
                width=150,
                command=command
            ).pack(
                side="left",
                padx=(0, 6)
            )

    def package_for_option(self, package, option):

        selected = dict(package or {})
        selected["selected_option_id"] = option.get("option_id", "")
        selected["opportunity_summary"] = dict(
            package.get("opportunity_summary", {}) or {}
        )
        selected["opportunity_summary"]["what"] = option.get("title", "")
        selected["opportunity_summary"]["why_now"] = option.get(
            "why_relevant_now",
            ""
        )
        selected["opportunity_summary"]["confidence"] = option.get(
            "confidence",
            0
        )
        selected["facebook_draft"] = option.get("facebook_draft", {})
        selected["instagram_draft"] = option.get("instagram_draft", {})
        selected["facebook_caption"] = option.get("facebook_caption", "")
        selected["instagram_caption"] = option.get("instagram_caption", "")
        selected["media_package"] = option.get("media_package", {})
        selected["historical_references"] = option.get(
            "historical_references",
            []
        )
        selected["validation_warnings"] = option.get(
            "validation_warnings",
            []
        )
        selected["selected_option"] = option
        return selected

    def use_prompt_option(self, package, option):

        self.status.configure(
            text="Selected option: " + option.get("title", "")
        )
        self.render_prompt_package(
            self.package_for_option(package, option)
        )

    def create_option_publication_draft(self, package, option):

        draft = self.retrieval_service.create_publication_draft(
            package,
            option.get("option_id", "")
        )
        if draft.get("persisted"):
            self.status.configure(
                text="Publication draft saved for " + option.get("title", "")
            )
        else:
            self.status.configure(
                text="Publication draft was prepared but not saved."
            )

    def regenerate_prompt_option(self, package, option):

        result = self.retrieval_service.regenerate_option(
            package,
            option.get("option_id", "")
        )
        if result.get("status") != "ready":
            self.status.configure(
                text=result.get("reason", "Option could not be regenerated.")
            )
            return
        self.status.configure(
            text="Regenerated option: " + option.get("title", "")
        )
        self.render_prompt_options(result["package"])

    ##########################################################

    def current_context_text(self, evidence):

        evidence = evidence or {}
        lines = [
            "Season: " + str(evidence.get("season", "")),
            "Active themes: " + self.format_values(evidence.get("active_themes", [])),
            "Alerts: " + self.format_values(
                [
                    item.get("summary") or item.get("type") or ""
                    for item in evidence.get("alerts", [])
                ]
            ),
            "Freshness: " + str(evidence.get("data_freshness", ""))
        ]
        return "\n".join(lines)

    def historical_reference_text(self, references):

        lines = []
        for item in (references or [])[:5]:
            lines.append(
                (
                    f"{item.get('post_date', 'Unknown date')} - "
                    f"{item.get('similarity_score', 0)}% - "
                    f"{item.get('caption_excerpt', '')}"
                )
            )
        return "\n".join(lines) if lines else "No close historical MFR reference found."

    def around_this_time_text(self, seasonal):

        seasonal = seasonal or {}
        lines = []
        if seasonal.get("summary"):
            lines.append(seasonal["summary"])
        if seasonal.get("matching_years"):
            lines.append(
                "Matching years: " +
                self.format_values(seasonal.get("matching_years", []))
            )
        if seasonal.get("last_related_post"):
            lines.append(
                "Last related post: " +
                str(seasonal.get("last_related_post", ""))
            )
        if seasonal.get("current_year_already_communicated"):
            lines.append("Current year coverage: already communicated.")
        if seasonal.get("communications_gap_risk"):
            lines.append(
                "Gap/repetition signal: " +
                seasonal.get("communications_gap_risk", "")
            )
        for item in seasonal.get("matches", [])[:4]:
            lines.append(
                (
                    f"{item.get('date', 'Unknown date')} - "
                    f"{item.get('similarity_score', 0)}% - "
                    f"{item.get('topic') or item.get('program') or item.get('campaign') or 'MFR memory'} - "
                    f"{item.get('caption_excerpt', '')}"
                )
            )
            evidence = item.get("seasonal_timing_evidence", [])
            if evidence:
                lines.append("  Evidence: " + self.format_values(evidence[:3]))
            if item.get("safe_reuse_note"):
                lines.append("  Safety: " + item["safe_reuse_note"])
        for limitation in seasonal.get("limitations", [])[:2]:
            lines.append("Limitation: " + str(limitation))
        return "\n".join(lines) if lines else "No same-period MFR memory found."

    def generate_updated_from_memory(self, package):

        topic = package.get("interpreted_topic", {}) or {}
        prompt = (
            "Generate an updated public communication for "
            f"{topic.get('label') or package.get('prompt') or 'this topic'} "
            "using prior MFR same-season posts as reference only. "
            "Do not reuse old dates, warnings, event facts, or calls to action "
            "unless they are verified in current context."
        )
        self.prompt_entry.delete(0, "end")
        self.prompt_entry.insert(0, prompt)
        self.generate_suggestions()

    def show_around_this_time_memory(self, package):

        window = ctk.CTkToplevel(self)
        window.title("Around This Time in Communications Memory")
        window.geometry("760x520")
        try:
            window.transient(self.winfo_toplevel())
        except Exception:
            pass
        textbox = ctk.CTkTextbox(
            window,
            wrap="word"
        )
        textbox.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(12, 8)
        )
        textbox.insert(
            "1.0",
            self.around_this_time_text(package.get("around_this_time", {}))
        )
        textbox.configure(state="disabled")
        ctk.CTkButton(
            window,
            text="Close",
            width=110,
            command=window.destroy
        ).pack(
            pady=(0, 12)
        )

    def production_media_text(self, media):

        media = media or {}
        if media.get("no_suitable_media"):
            return "No suitable media passed the topic compatibility gate. Use a text or graphic-first package."

        rows = []
        primary = media.get("primary_image") or media.get("primary_video") or {}
        if primary:
            rows.append(
                f"Primary: {primary.get('filename', '')} ({primary.get('trust_state', '')})"
            )

        for item in media.get("alternates", [])[:4]:
            rows.append(
                f"Alternate: {item.get('filename', '')} ({item.get('trust_state', '')})"
            )

        for item in media.get("excluded_conflicts", [])[:4]:
            rows.append(
                "Excluded: " +
                item.get("filename", "") +
                " - " +
                self.format_values(item.get("exclusions", []))
            )

        return "\n".join(rows) if rows else "No media selected."

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
                rowspan=22,
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

        strategy_frame = ctk.CTkFrame(
            frame,
            fg_color="transparent"
        )
        strategy_frame.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=3
        )
        strategy_frame.grid_columnconfigure(0, weight=1)
        strategy_frame.grid_columnconfigure(1, weight=1)
        self.render_strategy_panel(
            strategy_frame,
            opportunity
        )
        next_row = 4

        footer = ctk.CTkFrame(
            frame,
            fg_color="transparent"
        )

        footer.grid(
            row=next_row,
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
            row=next_row + 1,
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

        for index, item in enumerate(media[1:], start=next_row + 2):
            self.add_caption_line(
                frame,
                index,
                "Additional Media",
                f"{item['filename']} - {item['reason']}"
            )

    ##########################################################

    def render_package_placeholder(self, parent, opportunity, start_row=0):

        self.add_caption_line(
            parent,
            start_row,
            "Complete Communication Package",
            "Select an editorial strategy, then generate the package."
        )
        self.add_caption_line(
            parent,
            start_row + 1,
            "Caption Theme",
            opportunity.get("caption_theme", "")
        )
        self.add_caption_line(
            parent,
            start_row + 2,
            "Best Time",
            opportunity.get("best_posting_time", "")
        )

    ##########################################################

    def request_package(self, opportunity, parent):

        key = self.package_cache_key(
            opportunity
        )

        if key in self.package_jobs:
            return

        future = self.executor.submit(
            self.generate_package,
            opportunity
        )
        self.package_jobs[key] = future
        future.add_done_callback(
            lambda item: self.enqueue_ui(
                self.finish_package,
                key,
                item,
                parent
            )
        )

    ##########################################################

    def finish_package(self, key, future, parent):

        if self._destroyed:
            return

        self.package_jobs.pop(
            key,
            None
        )

        try:
            package = future.result()

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
            return

        if not package:
            return

        self.package_cache[key] = package

        if not parent.winfo_exists():
            return

        for child in parent.winfo_children():
            child.destroy()

        self.render_package(
            parent,
            package,
            start_row=0
        )
        self.update_writing_provider_status(
            package
        )

    ##########################################################

    def generate_package(self, opportunity):

        communication_package = self.communication_package_service.generate_package(
            opportunity,
            "Facebook"
        )

        return self.content_generation_service.generate_from_package(
            communication_package
        )

    ##########################################################

    def package_cache_key(self, opportunity):

        media_ids = tuple(
            item.get("media_id")
            for item in opportunity.get("recommended_media", [])
        )

        return (
            opportunity.get("opportunity_type", ""),
            opportunity.get("title", ""),
            media_ids,
            (
                opportunity.get("selected_editorial_strategy") or {}
            ).get("strategy_id", "")
        )

    ##########################################################

    def render_strategy_panel(self, parent, opportunity):

        media = opportunity.get("recommended_media") or []

        if not media:
            self.add_caption_line(
                parent,
                0,
                "Editorial Strategies",
                "No media is available for strategy planning."
            )
            return

        media_id = media[0].get("media_id")
        comparison = self.strategy_cache.get(media_id)

        if comparison:
            self.render_strategy_summary(
                parent,
                opportunity,
                comparison
            )
            return

        self.add_caption_line(
            parent,
            0,
            "Editorial Strategies",
            "Comparing strategy options..."
        )
        self.request_strategy_comparison(
            media_id,
            parent,
            opportunity
        )

    ##########################################################

    def request_strategy_comparison(self, media_id, parent, opportunity):

        if media_id in self.strategy_jobs:
            return

        future = self.executor.submit(
            self.editorial_comparison_service.compare,
            media_id
        )
        self.strategy_jobs[media_id] = future
        future.add_done_callback(
            lambda item: self.enqueue_ui(
                self.finish_strategy_comparison,
                media_id,
                item,
                parent,
                opportunity
            )
        )

    ##########################################################

    def finish_strategy_comparison(
        self,
        media_id,
        future,
        parent,
        opportunity
    ):

        if self._destroyed:
            return

        self.strategy_jobs.pop(
            media_id,
            None
        )

        try:
            comparison = future.result()

        except Exception as ex:
            logger.error(
                "Editorial strategy comparison failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Strategy comparison error: {ex}"
            )
            return

        self.strategy_cache[media_id] = comparison

        if not parent.winfo_exists():
            return

        for child in parent.winfo_children():
            child.destroy()

        self.render_strategy_summary(
            parent,
            opportunity,
            comparison
        )

    ##########################################################

    def render_strategy_summary(self, parent, opportunity, comparison):

        best = comparison.get("recommended_strategy") or {}
        alternatives = comparison.get("alternative_strategies") or []

        if best:
            self.record_strategy_viewed(opportunity, best)
            self.add_caption_line(
                parent,
                0,
                "Best Strategy",
                (
                    f"{best.get('title', '')} - "
                    f"{best.get('confidence', 0)}% confidence"
                )
            )
            self.add_caption_line(
                parent,
                1,
                "Why This Strategy Won",
                comparison.get("debate_summary") or comparison.get(
                    "comparison_summary",
                    ""
                )
            )
            self.add_caption_line(
                parent,
                2,
                "Tradeoffs",
                " | ".join(comparison.get("tradeoffs", [])[:3])
            )

        for index, strategy in enumerate(alternatives[:2], start=3):
            self.add_caption_line(
                parent,
                index,
                "Alternative Strategy",
                (
                    f"{strategy.get('title', '')}: "
                    f"{strategy.get('objective', '')}"
                )
            )

        controls = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )
        controls.grid(
            row=6,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=3
        )

        selected = opportunity.get("selected_editorial_strategy") or best

        buttons = (
            (
                "Use This Strategy",
                lambda: self.use_strategy(opportunity, best)
            ),
            (
                "Show Alternative",
                lambda: self.show_alternative_strategy(opportunity, comparison)
            ),
            (
                "Dismiss Strategy",
                lambda: self.dismiss_strategy(opportunity, selected)
            ),
            (
                "Package Preview",
                lambda: self.generate_package_preview(opportunity)
            ),
            (
                "Generate Communication Package",
                lambda: self.generate_strategy_package(parent, opportunity)
            )
        )

        for label, command in buttons:
            button = ctk.CTkButton(
                controls,
                text=label,
            width=175,
            command=command
        )
            button.pack(
                side="left",
                padx=(0, 8),
                pady=(0, 6)
            )

        key = self.package_cache_key(
            opportunity
        )
        package = self.package_cache.get(key)

        if package:
            self.render_package(
                parent,
                package,
                start_row=7
            )
        else:
            self.render_package_placeholder(
                parent,
                opportunity,
                start_row=7
            )

    ##########################################################

    def generate_package_preview(self, opportunity):

        key = self.package_cache_key(opportunity)

        if key in self.package_preview_cache:
            self.show_package_preview(
                self.package_preview_cache[key]
            )
            return

        if key in self.package_preview_jobs:
            return

        self.status.configure(
            text="Preparing package preview..."
        )
        future = self.executor.submit(
            self.communication_package_service.generate_package,
            opportunity,
            "Facebook"
        )
        self.package_preview_jobs[key] = future
        future.add_done_callback(
            lambda item: self.enqueue_ui(
                self.finish_package_preview,
                key,
                item
            )
        )

    ##########################################################

    def finish_package_preview(self, key, future):

        if self._destroyed:
            return

        self.package_preview_jobs.pop(
            key,
            None
        )

        try:
            package = future.result()
        except Exception as ex:
            logger.error(
                "Communication package preview failed",
                exc_info=(type(ex), ex, ex.__traceback__)
            )
            self.status.configure(
                text=f"Package preview error: {ex}"
            )
            return

        self.package_preview_cache[key] = package
        self.status.configure(
            text="Package preview ready."
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
            open_callback=self.open_package_asset,
            reveal_callback=self.reveal_package_asset,
            copy_callback=self.copy_package_asset_path,
            replace_callback=lambda asset, role: self.show_package_alternatives(
                package,
                role=role
            ),
            exclude_callback=lambda asset: self.exclude_package_asset(
                package,
                asset
            ),
            preview_callback=self.show_asset_preview
        )
        visual_panel.pack(
            fill="x",
            padx=16,
            pady=(16, 8)
        )

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
            text="Why This Package?",
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
            text="Why This Media?",
            command=lambda item=package: self.show_media_decision(
                item,
                compare=False
            )
        ).pack(
            anchor="e",
            padx=16,
            pady=(0, 8)
        )

        primary = self.primary_package_asset(package)

        if primary:
            ctk.CTkButton(
                window,
                text="Open Primary Media",
                command=lambda item=primary: self.open_package_asset(item)
            ).pack(
                anchor="e",
                padx=16,
                pady=(0, 8)
            )

            ctk.CTkButton(
                window,
                text="Show Alternatives",
                command=lambda item=package: self.show_package_alternatives(item)
            ).pack(
                anchor="e",
                padx=16,
                pady=(0, 8)
            )

            ctk.CTkButton(
                window,
                text="Mark Primary Unsuitable",
                command=lambda item=package: self.mark_primary_unsuitable(item)
            ).pack(
                anchor="e",
                padx=16,
                pady=(0, 8)
            )

        ctk.CTkButton(
            window,
            text="Why Not Another Asset?",
            command=lambda item=package: self.show_media_decision(
                item,
                compare=True
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

    def primary_package_asset(self, package):

        media = (package or {}).get("media_package", {}) or {}
        return (
            media.get("primary_photo")
            or media.get("best_photo")
            or media.get("primary_video")
            or media.get("best_video")
            or {}
        )

    ##########################################################

    def show_package_alternatives(self, package, role=None):

        primary = self.primary_package_asset(package)
        role = role or (
            "primary_video"
            if primary.get("media_type") == "video"
            else "primary_photo"
        )
        alternatives = self.communication_package_service.alternatives_for_package(
            package,
            media_type=primary.get("media_type"),
            limit=10
        )
        window = ctk.CTkToplevel(self)
        window.title("Alternative Media")
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 960, 680, parent=self)
        window.lift()

        frame = ctk.CTkScrollableFrame(window)
        frame.pack(fill="both", expand=True, padx=16, pady=(16, 8))

        if not alternatives:
            ctk.CTkLabel(
                frame,
                text="No bounded alternatives are available for this package."
            ).pack(anchor="w", padx=8, pady=8)
        else:
            for item in alternatives[:10]:
                row = ctk.CTkFrame(frame, corner_radius=6)
                row.pack(fill="x", padx=8, pady=6)
                row.grid_columnconfigure(1, weight=1)

                panel = PackageMediaPanel(
                    row,
                    {
                        "primary_video" if item.get("media_type") == "video" else "primary_photo": item
                    },
                    self.thumbnail_service,
                    open_callback=self.open_package_asset,
                    reveal_callback=self.reveal_package_asset,
                    copy_callback=self.copy_package_asset_path,
                    preview_callback=self.show_asset_preview,
                    compact=True
                )
                panel.grid(row=0, column=0, sticky="w", padx=8, pady=8)

                detail = (
                    f"{item.get('filename', '')}\n"
                    f"trust {item.get('trust_state', '')} | "
                    f"media score {item.get('media_score', 0)} | "
                    f"platform fit {item.get('platform_fit_score', 0)}\n"
                    f"Why not primary: {item.get('why_not_primary') or item.get('why_selected', '')}"
                )
                ctk.CTkLabel(
                    row,
                    text=detail,
                    wraplength=420,
                    justify="left"
                ).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
                ctk.CTkButton(
                    row,
                    text="Select This Asset",
                    width=150,
                    command=lambda alt=item: self.use_top_package_alternative(
                        package,
                        alt,
                        window,
                        role=role
                    )
                ).grid(row=0, column=2, padx=8, pady=8)

        footer = ctk.CTkFrame(window, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            footer,
            text="Close",
            command=window.destroy
        ).pack(side="right")

    ##########################################################

    def use_top_package_alternative(self, package, alternative, window=None, role=None):

        primary = self.primary_package_asset(package)
        role = role or (
            "primary_video" if primary.get("media_type") == "video" else "primary_photo"
        )
        updated = self.communication_package_service.replace_package_asset(
            package,
            alternative,
            role,
            reason="Selected from Content Director alternatives"
        )
        self.status.configure(
            text=f"Primary media replaced with {alternative.get('filename', '')}."
        )

        if window and window.winfo_exists():
            window.destroy()

        self.show_package_preview(updated)

    ##########################################################

    def exclude_package_asset(self, package, asset):

        if not asset:
            return

        updated = self.communication_package_service.exclude_package_asset(
            package,
            asset.get("media_id"),
            reason="Marked unsuitable from visual package preview"
        )
        self.status.configure(
            text=f"Marked {asset.get('filename', '')} unsuitable for this package only."
        )
        self.show_package_preview(updated)

    ##########################################################

    def mark_primary_unsuitable(self, package):

        primary = self.primary_package_asset(package)

        if not primary:
            self.status.configure(text="No primary media is selected.")
            return

        updated = self.communication_package_service.exclude_package_asset(
            package,
            primary.get("media_id"),
            reason="Marked unsuitable from Content Director package preview"
        )
        self.status.configure(
            text=f"Marked {primary.get('filename', '')} unsuitable for this package only."
        )
        self.show_package_preview(updated)

    ##########################################################

    def open_package_asset(self, asset):

        asset = asset or {}

        if asset.get("media_type") == "video":
            path = asset.get("path", "")

            if path:
                os.startfile(path)
            return

        self.open_viewer(asset)

    ##########################################################

    def reveal_package_asset(self, asset):

        path = (asset or {}).get("path", "")

        if not path:
            return

        subprocess.Popen(
            ["explorer", "/select,", path]
        )

    ##########################################################

    def copy_package_asset_path(self, asset):

        self.copy_text(
            "Copy File Path",
            (asset or {}).get("path", "")
        )

    ##########################################################

    def show_asset_preview(self, asset):

        window = ctk.CTkToplevel(self)
        window.title(asset.get("filename", "Media Preview"))
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 660, 540, parent=self)
        window.lift()
        panel = PackageMediaPanel(
            window,
            {
                "primary_video" if asset.get("media_type") == "video" else "primary_photo": asset
            },
            self.thumbnail_service,
            open_callback=self.open_package_asset,
            reveal_callback=self.reveal_package_asset,
            copy_callback=self.copy_package_asset_path,
            preview_callback=None
        )
        panel.pack(fill="both", expand=True, padx=16, pady=16)

    ##########################################################

    def package_preview_text(self, package):

        strategy = package.get("writing_strategy", {}) or {}
        publishing = package.get("publishing_strategy", {}) or {}
        media = package.get("media_package", {}) or {}
        scoring = package.get("package_scoring", {}) or {}

        return "\n\n".join(
            [
                "Top Story\n" + package.get("headline", ""),
                "Audience\n" + self.format_values(package.get("audience", [])),
                "Trust Level\n" + package.get("trust_label", ""),
                "Platforms\n" + self.format_values(package.get("recommended_platforms", [])),
                "Publishing Strategy\n" + publishing.get("decision_note", ""),
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
                        "Gallery photos: " + self.media_names(media.get("gallery_photos", [])),
                        "Gallery videos: " + self.media_names(media.get("gallery_videos", []))
                    ]
                ),
                "Asset Selection\n" + "\n".join(
                    [
                        "Reasons: " + self.format_values(media.get("reasons", [])),
                        "Diversity: " + self.format_values(media.get("diversity_reasoning", [])),
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

    def show_media_decision(self, package, compare=False):

        media = package.get("media_package", {}) or {}
        selected = media.get("primary_photo") or media.get("primary_video")
        alternatives = []
        alternatives.extend(media.get("gallery_photos") or [])
        alternatives.extend(media.get("gallery_videos") or [])
        compared = None

        for item in alternatives:
            if item and item.get("media_id") != (selected or {}).get("media_id"):
                compared = item
                break

        if not selected:
            self.show_decision_audit({
                "headline": "No media selected",
                "summary": "This package has no primary media asset.",
                "limiting_factors": [
                    "Generate or choose a recommendation with media support first."
                ]
            })
            return

        explanation = self.explainability_service.explain_media_selection(
            selected,
            recommendation=package,
            compared_media=compared if compare else None,
            persist=False
        )
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
                "Why selected: " + self.format_values(
                    explanation.get("why_selected", [])[:3]
                ),
                "Evidence count: " + str(explanation.get("evidence_count", 0)),
                "Trust: " + explanation.get("trust_label", "")
            ]
        )

    ##########################################################

    def use_strategy(self, opportunity, strategy):

        if not strategy:
            return

        opportunity["selected_editorial_strategy"] = strategy
        media = opportunity.get("recommended_media") or []

        if media:
            self.editorial_comparison_service.select_strategy(
                media[0].get("media_id"),
                strategy
            )

        self.status.configure(
            text=f"Strategy selected: {strategy.get('title', '')}"
        )
        self.render_results()

    ##########################################################

    def record_strategy_viewed(self, opportunity, strategy):

        media = opportunity.get("recommended_media") or []

        if not media or not strategy:
            return

        key = (
            media[0].get("media_id"),
            strategy.get("strategy_id")
        )

        if key in self.strategy_views:
            return

        self.strategy_views.add(key)

        try:
            self.editorial_comparison_service.record_viewed(
                media[0].get("media_id"),
                strategy
            )

        except Exception as ex:
            logger.error(
                "Strategy viewed feedback failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )

    ##########################################################

    def show_alternative_strategy(self, opportunity, comparison):

        alternatives = comparison.get("alternative_strategies") or []

        if not alternatives:
            self.status.configure(
                text="No alternative strategy available."
            )
            return

        current = opportunity.get("selected_editorial_strategy") or {}
        current_id = current.get("strategy_id")
        next_strategy = alternatives[0]

        for strategy in alternatives:
            if strategy.get("strategy_id") != current_id:
                next_strategy = strategy
                break

        opportunity["selected_editorial_strategy"] = next_strategy
        media = opportunity.get("recommended_media") or []

        if media:
            self.editorial_comparison_service.alternative_requested(
                media[0].get("media_id"),
                next_strategy
            )

        self.status.configure(
            text=f"Alternative strategy shown: {next_strategy.get('title', '')}"
        )
        self.render_results()

    ##########################################################

    def dismiss_strategy(self, opportunity, strategy):

        if not strategy:
            return

        media = opportunity.get("recommended_media") or []

        if media:
            self.editorial_comparison_service.dismiss_strategy(
                media[0].get("media_id"),
                strategy
            )

        self.status.configure(
            text=f"Strategy dismissed: {strategy.get('title', '')}"
        )

    ##########################################################

    def generate_strategy_package(self, parent, opportunity):

        media = opportunity.get("recommended_media") or []

        if media and not opportunity.get("selected_editorial_strategy"):
            comparison = self.strategy_cache.get(
                media[0].get("media_id")
            ) or {}
            best = comparison.get("recommended_strategy")

            if best:
                opportunity["selected_editorial_strategy"] = best

        key = self.package_cache_key(
            opportunity
        )

        if key in self.package_cache:
            for child in parent.winfo_children():
                child.destroy()

            self.render_strategy_panel(
                parent,
                opportunity
            )
            return

        for child in parent.winfo_children():
            child.destroy()

        self.render_package_placeholder(
            parent,
            opportunity
        )
        self.request_package(
            opportunity,
            parent
        )

    ##########################################################

    def render_package(self, parent, package, start_row=3):

        self.update_writing_provider_status(package)

        if "facebook" in package:
            return self.render_generated_content_package(
                parent,
                package,
                start_row=start_row
            )

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
        review = package.get("editorial_review", {}) or {}
        self.add_caption_line(
            parent,
            start_row + 8,
            "Editorial Review Score",
            str(review.get("overall_score", package.get("editorial_score", "")))
        )
        self.add_caption_line(
            parent,
            start_row + 9,
            "Strengths",
            " | ".join(review.get("strengths", [])[:5])
        )
        self.add_caption_line(
            parent,
            start_row + 10,
            "Suggested Improvements",
            " | ".join(review.get("suggestions", [])[:5])
        )
        self.render_copy_controls(
            parent,
            package,
            start_row + 11
        )

        return start_row + 12

    ##########################################################

    def render_generated_content_package(self, parent, package, start_row=3):

        source = package.get("source_package", {}) or {}
        warning = package.get("internal_warning", "")

        self.add_caption_line(
            parent,
            start_row,
            "Multi-Platform Content Package",
            source.get("headline", "")
        )
        self.add_caption_line(
            parent,
            start_row + 1,
            "Internal Warning",
            warning or "No internal warning."
        )

        rows = (
            ("Facebook Post", "facebook"),
            ("Instagram Caption", "instagram"),
            ("LinkedIn Post", "linkedin"),
            ("Website Article", "website"),
            ("News Release", "news_release"),
            ("Newsletter Article", "newsletter")
        )

        for offset, (label, key) in enumerate(rows, start=2):
            self.add_caption_line(
                parent,
                start_row + offset,
                label,
                (package.get(key, {}) or {}).get("copy_text", "")
            )

        self.add_caption_line(
            parent,
            start_row + 8,
            "Word Counts",
            str(package.get("word_counts", {}))
        )
        self.add_caption_line(
            parent,
            start_row + 9,
            "Department Voice Match",
            self.department_voice_match_text(package)
        )
        controls = self.render_copy_controls(
            parent,
            package,
            start_row + 10
        )
        preview_button = ctk.CTkButton(
            controls,
            text="Preview Platforms",
            width=145,
            command=lambda item=package: self.show_generated_content_preview(item)
        )
        preview_button.grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 6)
        )

        return start_row + 11

    ##########################################################

    def department_voice_match_text(self, package, platform=None):

        matches = package.get("department_voice_match", {}) or {}

        if platform:
            matches = {
                platform: matches.get(platform, {})
            }

        lines = []

        for key, item in matches.items():
            if not item:
                continue

            reasons = " ".join(item.get("reasons", [])[:2])
            lines.append(
                (
                    f"{self.format_label(key)}: "
                    f"{item.get('score', 0)}% "
                    f"({reasons or 'No detailed voice signal yet.'})"
                )
            )

        if not lines:
            return "Department voice match has insufficient approved history."

        intelligence = package.get("communications_intelligence", {}) or {}

        if intelligence.get("sample_count", 0):
            lines.append(
                (
                    "Profile samples: "
                    f"{intelligence.get('sample_count', 0):,}; "
                    f"confidence {intelligence.get('learning_confidence', 0)}%."
                )
            )

        return "\n".join(lines)

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

        if "copy_buttons" in package:
            buttons = (
                ("Copy Facebook", package["copy_buttons"].get("facebook", "")),
                ("Copy Instagram", package["copy_buttons"].get("instagram", "")),
                ("Copy LinkedIn", package["copy_buttons"].get("linkedin", "")),
                ("Copy Website", package["copy_buttons"].get("website", "")),
                ("Copy News Release", package["copy_buttons"].get("news_release", "")),
                ("Copy Newsletter", package["copy_buttons"].get("newsletter", "")),
                ("Copy All", self.package_text(package))
            )
        else:
            hashtags = " ".join(
                dict.fromkeys(
                    (package.get("facebook_hashtags") or []) +
                    (package.get("instagram_hashtags") or []) +
                    (package.get("hashtags") or [])
                )
            )

            buttons = (
                ("Copy Facebook", package.get("facebook_caption", "")),
                ("Copy Instagram", package.get("instagram_caption", "")),
                ("Copy Hashtags", hashtags),
                ("Copy CTA", package.get("call_to_action", "")),
                ("Copy All", self.package_text(package))
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

        return controls

    ##########################################################

    def copy_text(self, label, value):

        self.clipboard_clear()
        self.clipboard_append(value)
        self.status.configure(
            text=f"{label} copied."
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
            f"Supporting: {self.format_values(support_names)}. "
            f"Why: {guidance.get('why', '')}"
        )

    ##########################################################

    def show_generated_content_preview(self, package):

        window = ctk.CTkToplevel(self)
        window.title("Generated Content Preview")
        window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(window, 950, 760, parent=self)
        window.lift()

        selected = {
            "platform": "facebook"
        }
        source_package = package.get("source_package", {}) or {}
        media_panel = PackageMediaPanel(
            window,
            source_package.get("media_package", {}),
            self.thumbnail_service,
            open_callback=self.open_package_asset,
            reveal_callback=self.reveal_package_asset,
            copy_callback=self.copy_package_asset_path,
            preview_callback=self.show_asset_preview,
            compact=True
        )
        media_panel.pack(fill="x", padx=16, pady=(16, 8))
        body = ctk.CTkTextbox(
            window,
            wrap="word"
        )
        body.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(0, 8)
        )

        controls = ctk.CTkFrame(
            window,
            fg_color="transparent"
        )
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
                        ),
                        "Notes: " + output.get("notes", ""),
                        (
                            "Department Voice Match: " +
                            self.department_voice_match_text(
                                package,
                                platform
                            )
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
            ).pack(
                side="left",
                padx=(0, 8),
                pady=(0, 8)
            )

        footer = ctk.CTkFrame(
            window,
            fg_color="transparent"
        )
        footer.pack(
            fill="x",
            padx=16,
            pady=(0, 16)
        )

        ctk.CTkButton(
            footer,
            text="Copy Current",
            command=lambda: self.copy_text(
                "Current platform",
                package.get("copy_buttons", {}).get(selected["platform"], "")
            )
        ).pack(
            side="left",
            padx=(0, 8)
        )
        ctk.CTkButton(
            footer,
            text="Regenerate Current",
            command=lambda: self.regenerate_generated_platform(
                package,
                selected["platform"],
                render
            )
        ).pack(
            side="left",
            padx=(0, 8)
        )
        ctk.CTkButton(
            footer,
            text="Decision Audit",
            command=lambda item=package: self.show_decision_audit(
                item.get("generated_content_audit", {})
            )
        ).pack(
            side="left",
            padx=(0, 8)
        )
        ctk.CTkButton(
            footer,
            text="Close",
            command=window.destroy
        ).pack(
            side="right"
        )
        render("facebook")

    ##########################################################

    def regenerate_generated_platform(self, package, platform, render_callback):

        self.status.configure(
            text=f"Regenerating {self.format_label(platform)}..."
        )
        future = self.executor.submit(
            self.content_generation_service.regenerate_platform,
            package,
            platform
        )
        future.add_done_callback(
            lambda item: self.enqueue_ui(
                self.finish_regenerate_generated_platform,
                item,
                package,
                platform,
                render_callback
            )
        )

    ##########################################################

    def finish_regenerate_generated_platform(
        self,
        future,
        package,
        platform,
        render_callback
    ):

        if self._destroyed:
            return

        try:
            updated = future.result()
        except Exception as ex:
            logger.error(
                "Generated platform regeneration failed",
                exc_info=(type(ex), ex, ex.__traceback__)
            )
            self.status.configure(
                text=f"Regeneration error: {ex}"
            )
            return

        package.clear()
        package.update(updated)
        self.status.configure(
            text=f"{self.format_label(platform)} regenerated."
        )
        render_callback(platform)

    ##########################################################

    def package_text(self, package):

        if "copy_buttons" in package:
            return "\n\n".join(
                [
                    self.format_label(platform) + ":\n" + text
                    for platform, text in package.get("copy_buttons", {}).items()
                    if text
                ]
            )

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
                "Reasoning:\n" + "\n".join(package.get("reasoning", [])),
                "Editorial Review:\n" + self.editorial_review_text(package)
            ]
        )

    ##########################################################

    def editorial_review_text(self, package):

        review = package.get("editorial_review", {}) or {}

        return "\n".join(
            [
                f"Score: {review.get('overall_score', package.get('editorial_score', ''))}",
                "Strengths: " + " | ".join(review.get("strengths", [])),
                (
                    "Suggested Improvements: " +
                    " | ".join(review.get("suggestions", []))
                )
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

            if feedback_type in ("accepted", "saved"):
                self.remember_accepted_strategy_package(opportunity)

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

    def remember_accepted_strategy_package(self, opportunity):

        strategy = opportunity.get("selected_editorial_strategy")

        if not strategy:
            return

        package = self.package_cache.get(
            self.package_cache_key(opportunity)
        )

        if not package:
            return

        self.memory_service.remember_strategy_package(
            package,
            strategy,
            opportunity
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

    def format_values(self, values):

        if not values:
            return "None"

        return ", ".join(
            self.format_label(value)
            for value in values[:6]
        )

    ##########################################################

    def media_names(self, media):

        if not media:
            return "None"

        return ", ".join(
            item.get("filename", "")
            for item in media[:5]
            if item.get("filename")
        ) or "None"

    ##########################################################

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

        if fallback:
            label = "Captions: deterministic fallback"
        elif provider == "ollama":
            label = "Captions: Ollama writing provider"
        elif provider:
            label = f"Captions: {provider}"
        else:
            label = "Captions: provider unknown"

        if model:
            label += f" ({model})"

        if error:
            label += " - Ollama failed, fallback used"

        return label

    ##########################################################

    def destroy(self):

        self._destroyed = True

        if hasattr(self, "thumbnail_service"):
            self.thumbnail_service.shutdown()

        if hasattr(self, "executor"):
            self.executor.shutdown(
                wait=False,
                cancel_futures=True
            )

        super().destroy()
