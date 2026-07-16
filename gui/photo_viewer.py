import customtkinter as ctk
import threading
import os

from media.image_loader import ImageLoader
from media.image_dimensions import ImageDimensions
from media.thumbnail_cache import ThumbnailCache
from services.brain_service import BrainService
from services.decision_explainability_service import DecisionExplainabilityService
from services.editorial_comparison_service import EditorialComparisonService
from services.human_feedback_service import HumanFeedbackService
from services.analysis_review_service import AnalysisReviewService
from services.time_service import TimeService


class PhotoViewer(ctk.CTkToplevel):

    def __init__(self, parent, media_id, filename, filepath):

        super().__init__(parent)

        self.title(filename)

        self.geometry("1700x950")
        self.minsize(1200, 800)

        self.transient(parent.winfo_toplevel())
        self.lift()
        self.focus_force()

        self.attributes("-topmost", True)
        self.after(250, lambda: self.attributes("-topmost", False))

        self.filename = filename
        self.filepath = filepath
        self.media_id = media_id
        self.parent_window = parent
        self.brain = BrainService()
        self.feedback = HumanFeedbackService()
        self.review = AnalysisReviewService()
        self.editorial = EditorialComparisonService()
        self.explainability = DecisionExplainabilityService()
        self.analysis = None
        self.media_details = None
        self.intelligence = None
        self.fire_service_intelligence = None
        self.effective_intelligence = None
        self.source_image = None
        self.display_image = None
        self.image_load_token = 0
        self.resize_after_id = None
        self.image_panel_size = (1, 1)
        self.thumbnail_cache = ThumbnailCache()
        self.is_video = self._is_video_path(filepath)

        self.build_ui()
        self.media_details = self.brain.db.get_media_details(media_id)
        self.load_source_image_async()
        self.load_analysis()

    ##########################################################

    def build_ui(self):

        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)

        self.grid_rowconfigure(0, weight=1)

        #######################################################
        # IMAGE PANEL
        #######################################################

        self.image_frame = ctk.CTkFrame(self)

        self.image_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(15, 5),
            pady=15
        )

        title = ctk.CTkLabel(
            self.image_frame,
            text=self.filename,
            font=("Segoe UI", 22, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        self.preview = ctk.CTkLabel(
            self.image_frame,
            text=(
                "Loading video preview..."
                if self.is_video
                else "Loading image..."
            )
        )

        self.preview.pack(
            expand=True,
            fill="both",
            padx=20,
            pady=20
        )

        if self.is_video:
            self.system_player_button = ctk.CTkButton(
                self.image_frame,
                text="Open Video in System Player",
                command=self.open_system_player
            )
            self.system_player_button.pack(
                anchor="e",
                padx=20,
                pady=(0, 12)
            )
        else:
            self.system_player_button = None

        self.image_frame.bind(
            "<Configure>",
            self.image_panel_configured
        )

        #######################################################
        # AI PANEL
        #######################################################

        ai = ctk.CTkFrame(
            self,
            width=350
        )

        ai.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=(5, 15),
            pady=15
        )

        ai.grid_propagate(False)

        heading = ctk.CTkLabel(
            ai,
            text="AI Assistant",
            font=("Segoe UI", 22, "bold")
        )

        heading.pack(
            pady=(20, 8)
        )

        self.mock_notice = ctk.CTkLabel(
            ai,
            text="",
            text_color="#f5c542",
            wraplength=300
        )

        self.mock_notice.pack(
            padx=20,
            pady=(0, 8)
        )

        self.status = ctk.CTkLabel(
            ai,
            text="Status: Not analyzed"
        )

        self.status.pack(
            pady=10
        )

        self.analyze_button = ctk.CTkButton(
            ai,
            text=(
                "Analyze Video Metadata"
                if self.is_video
                else "Analyze Photo"
            ),
            command=self.analyze_photo
        )

        self.analyze_button.pack(
            fill="x",
            padx=20,
            pady=10
        )

        self.improve_button = ctk.CTkButton(
            ai,
            text="Improve Analysis",
            command=self.open_correction_dialog
        )

        self.improve_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        review_row = ctk.CTkFrame(
            ai,
            fg_color="transparent"
        )

        review_row.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.approve_button = ctk.CTkButton(
            review_row,
            text="Approve",
            command=self.approve_analysis,
            width=90
        )
        self.approve_button.pack(
            side="left",
            padx=(0, 5)
        )

        self.reject_button = ctk.CTkButton(
            review_row,
            text="Reject",
            command=self.reject_analysis,
            width=90
        )
        self.reject_button.pack(
            side="left",
            padx=(0, 5)
        )

        self.reanalyze_button = ctk.CTkButton(
            review_row,
            text="Reanalyze",
            command=self.request_reanalysis,
            width=100
        )
        self.reanalyze_button.pack(
            side="left"
        )

        self.content_director_button = ctk.CTkButton(
            ai,
            text="Open in Content Director",
            command=self.open_content_director
        )

        self.content_director_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.facebook_button = ctk.CTkButton(
            ai,
            text="Generate Facebook",
            state="disabled"
        )

        self.facebook_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.instagram_button = ctk.CTkButton(
            ai,
            text="Generate Instagram",
            state="disabled"
        )

        self.instagram_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.both_button = ctk.CTkButton(
            ai,
            text="Generate Both",
            state="disabled"
        )

        self.both_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.analysis_text = ctk.CTkTextbox(
            ai,
            height=420,
            wrap="word"
        )

        self.analysis_text.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.analysis_text.configure(state="disabled")
        self.update_mock_notice()

    ##########################################################

    def load_source_image_async(self):

        self.image_load_token += 1
        token = self.image_load_token

        thread = threading.Thread(
            target=self.load_source_image_worker,
            args=(token,),
            daemon=True
        )
        thread.start()

    ##########################################################

    def load_source_image_worker(self, token):

        try:
            if self.is_video:
                thumbnail = self.thumbnail_cache.get_thumbnail(
                    self.filepath
                )

                if thumbnail is None:
                    image = None
                else:
                    image = ImageLoader.load_pil_image(
                        thumbnail
                    )
            else:
                image = ImageLoader.load_pil_image(
                    self.filepath
                )
            error = None

        except Exception as ex:
            image = None
            error = ex

        try:
            self.after(
                0,
                lambda: self.source_image_ready(
                    token,
                    image,
                    error
                )
            )
        except Exception:
            pass

    ##########################################################

    def source_image_ready(self, token, image, error):

        if token != self.image_load_token:
            return

        if error is not None:
            self.preview.configure(
                image=None,
                text=(
                    f"Unable to open video preview:\n{error}"
                    if self.is_video
                    else f"Unable to open image:\n{error}"
                )
            )
            self.source_image = None
            self.display_image = None
            return

        if image is None and self.is_video:
            self.preview.configure(
                image=None,
                text=self.video_metadata_text()
            )
            self.source_image = None
            self.display_image = None
            return

        self.source_image = image
        self.redraw_image()

    ##########################################################

    def image_panel_configured(self, event=None):

        if event is not None:
            self.image_panel_size = (
                max(1, event.width - 40),
                max(1, event.height - 95)
            )

        if self.resize_after_id is not None:
            try:
                self.after_cancel(
                    self.resize_after_id
                )
            except Exception:
                pass

        self.resize_after_id = self.after(
            120,
            self.redraw_image
        )

    ##########################################################

    def redraw_image(self):

        self.resize_after_id = None

        if self.source_image is None:
            return

        size = ImageDimensions.fit_size(
            self.source_image.size,
            self.image_panel_size
        )

        self.display_image = ImageLoader.ctk_image_from_pil(
            self.source_image,
            size
        )

        self.preview.configure(
            image=self.display_image,
            text=""
        )

    ##########################################################

    def analyze_photo(self):

        self.analyze_button.configure(
            state="disabled"
        )

        self.status.configure(
            text="Status: Analyzing..."
        )

        self.brain.analyze_photo(
            self.media_id,
            self.filepath,
            force=self.analysis is not None,
            callback=self.analysis_complete,
            error_callback=self.analysis_failed,
            progress_callback=self.analysis_progress
        )

    ##########################################################

    def load_analysis(self):

        analysis = self.brain.get_analysis(self.media_id)

        if analysis is None:
            if self.is_video:
                self.show_video_metadata_only()
            return

        self.show_analysis(analysis)

    ##########################################################

    def analysis_complete(self, analysis):

        self.after(
            0,
            lambda: self.show_analysis(analysis)
        )

    ##########################################################

    def analysis_failed(self, error):

        self.after(
            0,
            lambda: self.show_error(error)
        )

    ##########################################################

    def analysis_progress(self, progress):

        status = progress.get("status", "")
        queued = progress.get("queued", 0)
        running = progress.get("running", 0)

        self.after(
            0,
            lambda: self.status.configure(
                text=f"Status: {status} ({queued} queued, {running} running)"
            )
        )

    ##########################################################

    def show_analysis(self, analysis):

        self.analysis = analysis
        self.effective_intelligence = self.brain.get_effective_intelligence(
            self.media_id
        )
        self.intelligence = self.effective_intelligence.get(
            "media_intelligence"
        )
        self.fire_service_intelligence = (
            self.effective_intelligence.get("fire_service_intelligence")
        )
        self.filesystem_intelligence = (
            self.effective_intelligence.get("filesystem_intelligence") or {}
        )
        self.update_mock_notice(analysis)

        failure = analysis.get("failure_reason", "")

        if failure:
            self.show_provider_failure(analysis)
            return

        self.status.configure(
            text="Status: Analyzed"
        )

        self.analyze_button.configure(
            state="normal",
            text="Analyze Again"
        )

        self.facebook_button.configure(state="normal")
        self.instagram_button.configure(state="normal")
        self.both_button.configure(state="normal")

        effective_description = self.effective_description()
        lines = [
            "AI Assistant Understanding",
            "Source: " + self.effective_source_label(),
            effective_description,
            "",
            f"Scene: {self.effective_value('incident_classification', analysis.get('scene_type', ''))}",
            f"Activity: {self.effective_value('primary_activity', analysis.get('activity', ''))}",
            f"People: {self.effective_value('people_count', analysis.get('people_count', 0))}",
            "",
            "Apparatus: " + self.format_list(self.effective_value("apparatus", analysis.get("apparatus"))),
            "Equipment: " + self.format_list(self.effective_value("equipment", analysis.get("equipment"))),
            "Keywords: " + self.format_list(analysis.get("keywords")),
            "",
            f"Community Score: {analysis.get('community_score', 0)}",
            f"Recruitment Score: {analysis.get('recruitment_score', 0)}",
            f"Education Score: {analysis.get('education_score', 0)}",
            f"Technical Score: {analysis.get('technical_score', 0)}",
            f"Overall Score: {analysis.get('overall_score', 0)}",
            "",
            "Raw AI Analysis",
            self.analysis_provider_label(analysis),
            f"Model: {analysis.get('model', '')}",
            "Description: " + analysis.get("description", ""),
            f"Duration: {analysis.get('analysis_duration', 0):.2f}s",
            f"Retries: {analysis.get('retry_count', 0)}",
            f"Failure: {analysis.get('failure_reason', '')}",
            f"Trust State: {self.effective_trust_state(analysis)}",
            f"Review Status: {analysis.get('review_status', '') or 'review_required'}",
            "Correction Timestamp: " + self.latest_correction_time(),
            "Quality Warnings: " + self.format_list(
                analysis.get("quality_warnings")
            ),
            f"Media Context: {analysis.get('media_context', '')}",
            (
                "Analyzed: " +
                self.local_time(
                    analysis.get("last_analyzed") or
                    analysis.get("analyzed_at", "")
                )
            )
        ]

        intelligence_lines = self.intelligence_lines()

        if intelligence_lines:
            lines.extend(
                [
                    "",
                    "Media Intelligence"
                ] + intelligence_lines
            )

        video_lines = self.video_intelligence_lines()

        if video_lines:
            lines.extend(
                [
                    "",
                    "Video Intelligence"
                ] + video_lines
            )

        filesystem_lines = self.filesystem_intelligence_lines()

        if filesystem_lines:
            lines.extend(
                [
                    "",
                    "Filesystem Intelligence",
                    "Folder context is supporting evidence, not visual proof."
                ] + filesystem_lines
            )

        communications_lines = self.communications_intelligence_lines()

        if communications_lines:
            lines.extend(
                [
                    "",
                    "Communications Intelligence"
                ] + communications_lines
            )

        fire_service_lines = self.fire_service_intelligence_lines()

        if fire_service_lines:
            lines.extend(
                [
                    "",
                    "Fire Service Intelligence"
                ] + fire_service_lines
            )

        correction_lines = self.correction_history_lines()

        if correction_lines:
            lines.extend(
                [
                    "",
                    "Human Corrections"
                ] + correction_lines
            )

        review_lines = self.analysis_review_lines()

        if review_lines:
            lines.extend(
                [
                    "",
                    "Analysis Review"
                ] + review_lines
            )

        why_selected_lines = self.why_selected_lines()

        if why_selected_lines:
            lines.extend(
                [
                    "",
                    "Why Selected"
                ] + why_selected_lines
            )

        editorial_lines = self.editorial_strategy_lines()

        if editorial_lines:
            lines.extend(
                [
                    "",
                    "Editorial Strategies"
                ] + editorial_lines
            )

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", "\n".join(lines))
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def show_video_metadata_only(self):

        details = self.media_details or {}
        self.status.configure(
            text="Status: Video metadata available"
        )
        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert(
            "end",
            self.video_metadata_text(details)
        )
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def video_metadata_text(self, details=None):

        details = details or self.media_details or {}
        duration = self.duration_text(
            details.get("duration_seconds", 0)
        )
        dimensions = self.dimensions_text(details)
        lines = [
            "Video Preview",
            "",
            f"Duration: {duration or 'Unknown'}",
            f"Dimensions: {dimensions}",
            f"Frame rate: {details.get('frame_rate', 0) or 'Unknown'}",
            f"Orientation: {details.get('orientation', '') or 'Unknown'}",
            f"Codec: {details.get('codec', '') or 'Unknown'}",
            f"Imported: {TimeService.format_local(details.get('date_added', ''))}",
            "",
            "Video analysis is staged and requires human review before publication."
        ]

        return "\n".join(lines)

    ##########################################################

    def video_intelligence_lines(self):

        if not self.is_video:
            return []

        details = self.media_details or {}

        try:
            video = self.brain.db.get_video_intelligence(
                self.media_id
            )
        except Exception:
            video = None

        lines = [
            f"Duration: {self.duration_text(details.get('duration_seconds', 0)) or 'Unknown'}",
            f"Orientation: {details.get('orientation', '') or 'Unknown'}",
            f"Dimensions: {self.dimensions_text(details)}",
            f"Codec: {details.get('codec', '') or 'Unknown'}"
        ]

        if video:
            lines.extend(
                [
                    "Summary: " + video.get("video_summary", ""),
                    f"Story Category: {video.get('story_category', '') or video.get('likely_content_category', '')}",
                    f"Primary Activity: {video.get('primary_activity', '')}",
                    f"Reel Potential: {video.get('reel_potential', 0)}",
                    f"Story Potential: {video.get('story_potential', 0)}",
                    f"Analyzed Frames: {video.get('analyzed_frame_count', 0)}",
                    "Frame Timestamps: " + self.format_list(
                        video.get("frame_timestamps")
                    ),
                    "Clip Windows: " + self.format_clip_windows(
                        video.get("clip_recommendations")
                    ),
                    "Cover Frame: " + self.format_cover_frame(
                        video.get("cover_recommendation")
                    ),
                    "Themes: " + self.format_list(
                        video.get("communications_themes")
                    ),
                    "Apparatus: " + self.format_list(
                        video.get("apparatus_observed")
                    ),
                    "PPE: " + self.format_list(
                        video.get("identified_ppe")
                    ),
                    "Tools: " + self.format_list(
                        video.get("equipment_observed")
                    ),
                    f"Likely Category: {video.get('likely_content_category', '')}",
                    f"Review State: {video.get('review_state', '')}",
                    "Explanation: " + video.get("explanation", ""),
                    "Uncertain Observations: " + self.format_list(
                        video.get("uncertain_observations")
                    )
                ]
            )
        else:
            lines.append(
                "Review State: metadata available, not analyzed"
            )

        lines.append(
            "Publishing Note: review footage manually before using as a Reel or short-form video."
        )

        return lines

    ##########################################################

    def format_clip_windows(self, clips):

        values = []

        for clip in clips or []:
            values.append(
                f"{clip.get('start', '')}-{clip.get('end', '')}"
            )

        return self.format_list(values)

    ##########################################################

    def format_cover_frame(self, cover):

        cover = cover or {}

        if not cover:
            return ""

        return (
            f"{cover.get('timecode', '')} - "
            f"{cover.get('reason', '')}"
        )

    ##########################################################

    def duration_text(self, seconds):

        seconds = int(float(seconds or 0))

        if seconds <= 0:
            return ""

        minutes = seconds // 60
        remainder = seconds % 60

        return f"{minutes}:{remainder:02d}"

    ##########################################################

    def dimensions_text(self, details):

        width = int(details.get("width") or 0)
        height = int(details.get("height") or 0)

        if width and height:
            return f"{width} x {height}"

        return "Unknown"

    ##########################################################

    def open_system_player(self):

        try:
            os.startfile(self.filepath)
        except Exception as ex:
            self.preview.configure(
                text=f"Unable to open system player:\n{ex}"
            )

    ##########################################################

    def _is_video_path(self, path):

        return str(path).lower().endswith(
            tuple(ThumbnailCache.VIDEO_EXTENSIONS)
        )

    ##########################################################

    def open_correction_dialog(self):

        CorrectionDialog(
            self,
            self.media_id,
            self.filename,
            self.feedback,
            on_saved=self.load_analysis,
            open_media_callback=self.open_suggested_media
        )

    ##########################################################

    def approve_analysis(self):

        self.review.approve(
            self.media_id,
            notes="Approved in Photo Viewer"
        )
        self.load_analysis()

    ##########################################################

    def reject_analysis(self):

        self.review.reject(
            self.media_id,
            notes="Rejected in Photo Viewer"
        )
        self.load_analysis()

    ##########################################################

    def request_reanalysis(self):

        self.review.request_reanalysis(
            self.media_id,
            notes="Reanalysis requested in Photo Viewer"
        )
        self.analyze_photo()

    ##########################################################

    def open_suggested_media(self, item):

        PhotoViewer(
            self,
            item["id"],
            item["filename"],
            item["path"]
        )

    ##########################################################

    def open_content_director(self):

        root = self.parent_window.winfo_toplevel()

        if hasattr(root, "show_content_director"):
            root.show_content_director()
            self.destroy()
            return

        if hasattr(root, "show_page"):
            root.show_page("content_director")
            self.destroy()

    ##########################################################

    def show_error(self, error):

        self.update_mock_notice()

        self.status.configure(
            text="Status: Provider failure"
        )

        self.analyze_button.configure(
            state="normal"
        )

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert(
            "1.0",
            f"Provider failure:\n{error}"
        )
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def show_provider_failure(self, analysis):

        self.update_mock_notice(analysis)

        self.status.configure(
            text="Status: Provider failure"
        )

        self.analyze_button.configure(
            state="normal",
            text="Analyze Again"
        )

        lines = [
            "Provider failure",
            "",
            analysis.get("failure_reason", ""),
            "",
            self.analysis_provider_label(analysis),
            f"Model: {analysis.get('model', '')}",
            f"Duration: {analysis.get('analysis_duration', 0):.2f}s",
            f"Retries: {analysis.get('retry_count', 0)}",
            (
                "Last Attempt: " +
                self.local_time(
                    analysis.get("last_analyzed") or
                    analysis.get("analyzed_at", "")
                )
            )
        ]

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", "\n".join(lines))
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def format_list(self, value):

        if not value:
            return "None"

        return ", ".join(str(item) for item in value)

    ##########################################################

    def format_label(self, value):

        return str(value or "").replace(
            "_",
            " "
        ).title()

    ##########################################################

    def update_mock_notice(self, analysis=None):

        provider = ""
        model = ""
        description = ""

        if not analysis:
            self.mock_notice.configure(
                text=""
            )
            return

        provider = analysis.get("provider", "")
        model = analysis.get("model", "")
        description = analysis.get("description", "")

        if (
            provider == "mock" or
            model.startswith("mock") or
            description.startswith("MOCK TEST ANALYSIS")
        ):
            self.mock_notice.configure(
                text="Mock provider active - test data only"
            )
        else:
            self.mock_notice.configure(
                text=""
            )

    ##########################################################

    def analysis_provider_label(self, analysis):

        provider = analysis.get("provider", "")
        model = analysis.get("model", "")
        description = analysis.get("description", "")

        if (
            provider == "mock" or
            model.startswith("mock") or
            description.startswith("MOCK TEST ANALYSIS")
        ):
            return "Analysis provider: mock - test data"

        if provider:
            return f"Analysis provider: {provider}"

        return "Analysis provider: unknown"

    ##########################################################

    def local_time(self, value):

        return TimeService.format_local(value) or str(value or "")

    ##########################################################

    def intelligence_lines(self):

        if not self.intelligence:
            return []

        top_tags = (
            self.intelligence.get("content_tags") or []
        )[:8]

        return [
            f"Scene: {self.intelligence.get('normalized_scene', '')}",
            f"Incident: {self.intelligence.get('incident_type', '')}",
            f"Activity: {self.intelligence.get('primary_activity', '')}",
            "Top Tags: " + self.format_list(top_tags),
            (
                "Recommended Uses: " +
                self.format_list(
                    self.intelligence.get("recommended_uses")
                )
            )
        ]

    ##########################################################

    def communications_intelligence_lines(self):

        if not self.intelligence:
            return []

        if not self.intelligence.get("communications_score"):
            return []

        categories = self.intelligence.get("communications_category_scores") or {}
        platforms = self.intelligence.get("platform_suitability") or {}
        category_lines = [
            f"{self.format_label(key)}: {value}"
            for key, value in sorted(
                categories.items(),
                key=lambda item: item[1],
                reverse=True
            )[:6]
        ]
        platform_lines = [
            f"{self.format_label(key)}: {value}"
            for key, value in sorted(
                platforms.items(),
                key=lambda item: item[1],
                reverse=True
            )
        ]

        return [
            f"Overall Score: {self.intelligence.get('communications_score', 0)}",
            "Category Breakdown: " + self.format_list(category_lines),
            (
                "Suggested Campaigns: " +
                self.format_list(self.intelligence.get("suggested_campaigns"))
            ),
            (
                "Suggested Platforms: " +
                self.format_list(platform_lines)
            ),
            (
                "Suggested Audience: " +
                self.format_list(self.intelligence.get("suggested_audience"))
            ),
            (
                "Suggested Time of Year: " +
                str(self.intelligence.get("suggested_time_of_year", ""))
            ),
            (
                "Reasoning: " +
                self.format_list(self.intelligence.get("communications_reasoning"))
            )
        ]

    ##########################################################

    def filesystem_intelligence_lines(self):

        filesystem = getattr(
            self,
            "filesystem_intelligence",
            None
        )

        if not filesystem:
            return []

        apparatus = filesystem.get("apparatus_name") or filesystem.get(
            "apparatus_identifier",
            ""
        )
        agreement = (
            "Conflict flagged"
            if filesystem.get("conflict_state") == "conflict"
            else "No folder conflict flagged"
        )

        return [
            f"Category: {filesystem.get('root_category', '') or 'unknown'}",
            f"Subcategory: {filesystem.get('subcategory', '') or 'unknown'}",
            f"Apparatus: {apparatus or 'unknown'}",
            f"Incident Type: {filesystem.get('incident_type', '') or 'unknown'}",
            f"Training Type: {filesystem.get('training_type', '') or 'unknown'}",
            f"Program: {filesystem.get('public_education_program', '') or 'unknown'}",
            f"Campaign: {filesystem.get('campaign', '') or 'unknown'}",
            f"Event: {filesystem.get('community_event', '') or 'unknown'}",
            (
                "Folder Hierarchy: " +
                self.format_list(filesystem.get("folder_hierarchy"))
            ),
            (
                "Normalized Tags: " +
                self.format_list(filesystem.get("normalized_tags"))
            ),
            f"Confidence: {filesystem.get('filesystem_confidence', 0)}",
            (
                "Department Knowledge Match: " +
                (
                    "resolved"
                    if filesystem.get("apparatus_resolved")
                    else "unresolved or not applicable"
                )
            ),
            f"Agreement: {agreement}",
            (
                "Conflict Details: " +
                self.format_list(filesystem.get("conflict_details"))
            ),
            f"Version: {filesystem.get('enrichment_version', '')}",
            "Derived: " + self.local_time(
                filesystem.get("last_derived_at", "")
            )
        ]

    ##########################################################

    def fire_service_intelligence_lines(self):

        fire_service = getattr(
            self,
            "fire_service_intelligence",
            None
        )

        if not fire_service:
            return []

        personnel = fire_service.get("personnel") or {}

        return [
            f"Incident: {fire_service.get('incident_classification', '')}",
            f"Activity: {fire_service.get('operational_activity', '')}",
            f"Operational Context: {fire_service.get('operational_context', '')}",
            (
                "Operational Skills: " +
                self.format_list(fire_service.get("operational_skills"))
            ),
            (
                "Communications Intent: " +
                self.format_list(fire_service.get("communications_intent"))
            ),
            f"Confidence: {fire_service.get('operational_confidence', 0)}",
            (
                "Personnel: " +
                f"firefighters {fire_service.get('firefighter_count', 0)}, " +
                f"civilians {fire_service.get('civilian_count', 0)}, " +
                f"group {fire_service.get('group_size', '')}, " +
                f"officer {'yes' if fire_service.get('officer_presence') else 'unknown'}, " +
                f"children {'yes' if fire_service.get('children_present') else 'unknown'}"
            ),
            "PPE: " + self.format_list(fire_service.get("ppe")),
            "Equipment: " + self.format_list(fire_service.get("equipment")),
            "Apparatus: " + self.format_list(fire_service.get("apparatus")),
            (
                "Communications Uses: " +
                self.format_list(fire_service.get("communications_uses"))
            ),
            (
                "Reasoning: " +
                self.format_list(
                    (
                        fire_service.get("operational_reasoning") or
                        fire_service.get("reasoning")
                    )
                )
            ),
            (
                "Evidence: " +
                self.format_list(
                    self.fire_reasoning_evidence_lines(
                        fire_service.get("reasoning_evidence")
                    )
                )
            )
        ]

    ##########################################################

    def fire_reasoning_evidence_lines(self, evidence):

        lines = []

        for item in evidence or []:

            if isinstance(item, dict):
                reason = item.get(
                    "reason",
                    item.get("relationship", "")
                )
                evidence = item.get(
                    "evidence",
                    item.get("entity", "")
                )
                lines.append(
                    (
                        f"{item.get('confidence', 0)} - "
                        f"{reason}: "
                        f"{evidence}"
                    )
                )
            else:
                lines.append(str(item))

        return lines

    ##########################################################

    def correction_history_lines(self):

        if not self.effective_intelligence:
            return []

        lines = []
        corrections = self.effective_intelligence.get("corrections") or []
        history = self.effective_intelligence.get("correction_history") or []

        if corrections:
            lines.append(
                f"Active corrections: {len(corrections)}"
            )

        for row in history[:8]:
            lines.append(
                (
                    f"{self.local_time(row.get('created_at', ''))} | "
                    f"{row.get('correction_source', '')} | "
                    f"{row.get('field_name', '')} | "
                    f"{self.format_value(row.get('previous_value'))} -> "
                    f"{self.format_value(row.get('new_value'))}"
                )
            )

        return lines

    ##########################################################

    def analysis_review_lines(self):

        if not self.effective_intelligence:
            return []

        history = self.effective_intelligence.get(
            "analysis_review_history"
        ) or []
        lines = []

        for row in history[:6]:
            lines.append(
                (
                    f"{self.local_time(row.get('created_at'))}: "
                    f"{row.get('reviewer', '')} {row.get('decision', '')} "
                    f"({row.get('trust_state', '')})"
                )
            )

            if row.get("notes"):
                lines.append("  Notes: " + row.get("notes", ""))

        return lines

    ##########################################################

    def editorial_strategy_lines(self):

        try:
            comparison = self.editorial.latest(
                self.media_id
            )

        except Exception:
            return []

        if not comparison:
            return []

        best = comparison.get("recommended_strategy") or {}
        alternatives = comparison.get("alternative_strategies") or []

        if not best:
            return []

        lines = [
            (
                "Top Strategy: " +
                f"{best.get('title', '')} "
                f"({best.get('confidence', 0)}%)"
            ),
            (
                "Alternatives: " +
                self.format_list(
                    [
                        item.get("title", "")
                        for item in alternatives[:2]
                    ]
                )
            ),
            f"Confidence: {comparison.get('confidence', 0)}",
            "Why: " + (
                comparison.get("debate_summary") or
                comparison.get("comparison_summary", "")
            )
        ]

        return lines

    ##########################################################

    def why_selected_lines(self):

        try:
            explanation = self.explainability.explain_media_selection(
                self.media_id,
                persist=False
            )
        except Exception:
            return []

        if not explanation:
            return []

        lines = [
            f"Trust: {explanation.get('trust_label', '')}",
            f"Communications score: {explanation.get('decision_score', 0)}"
        ]
        lines.extend(
            explanation.get("why_selected", [])[:3]
        )

        limitations = explanation.get("limiting_factors", [])[:2]

        if limitations:
            lines.append(
                "Limits: " + self.format_list(limitations)
            )

        return [
            line for line in lines
            if str(line or "").strip()
        ]

    ##########################################################

    def effective_description(self):

        effective = self.effective_intelligence or {}

        return (
            effective.get("description") or
            (effective.get("analysis") or {}).get("effective_description") or
            (effective.get("analysis") or {}).get("description") or
            (self.analysis or {}).get("description", "")
        )

    ##########################################################

    def effective_value(self, field, fallback=""):

        effective = self.effective_intelligence or {}
        value = effective.get(field)

        if value not in (None, "", []):
            return value

        return fallback

    ##########################################################

    def effective_source_label(self):

        effective = self.effective_intelligence or {}
        trust = effective.get("trust_state", "")

        if effective.get("is_human_corrected"):
            return "Human Corrected"

        if trust == "approved_real":
            return "Approved Real Analysis"

        if trust == "corrected_real":
            return "Human Corrected"

        if trust == "mock":
            return "Mock/Test Data"

        if trust == "failed":
            return "Provider Failure"

        return "Unreviewed Real Analysis"

    ##########################################################

    def effective_trust_state(self, analysis):

        effective = self.effective_intelligence or {}

        return (
            effective.get("trust_state") or
            analysis.get("trust_state", "") or
            "unreviewed_real"
        )

    ##########################################################

    def latest_correction_time(self):

        effective = self.effective_intelligence or {}
        corrections = effective.get("corrections") or []
        dates = [
            row.get("updated_at") or row.get("created_at") or ""
            for row in corrections
            if row.get("updated_at") or row.get("created_at")
        ]

        if not dates:
            return ""

        return self.local_time(
            sorted(dates)[-1]
        )

    ##########################################################

    def format_value(self, value):

        if isinstance(value, list):
            return self.format_list(value)

        return str(value or "")

    ##########################################################

    def destroy(self):

        if self.resize_after_id is not None:
            try:
                self.after_cancel(
                    self.resize_after_id
                )
            except Exception:
                pass
            self.resize_after_id = None

        self.image_load_token += 1
        self.source_image = None
        self.display_image = None

        super().destroy()


class CorrectionDialog(ctk.CTkToplevel):

    FIELD_LABELS = {
        "description": "AI Assistant Description",
        "people_count": "People Count",
        "incident_classification": "Incident",
        "primary_activity": "Activity",
        "operational_context": "Operational Context",
        "ppe": "PPE",
        "equipment": "Equipment",
        "apparatus": "Apparatus",
        "operational_skills": "Operational Skills",
        "communications_uses": "Communications Uses",
        "campaigns": "Campaigns",
        "notes": "Notes"
    }

    def __init__(
        self,
        parent,
        media_id,
        filename,
        feedback_service,
        on_saved=None,
        open_media_callback=None
    ):

        super().__init__(parent)

        self.title(f"Improve Analysis - {filename}")
        self.geometry("900x760")
        self.transient(parent.winfo_toplevel())
        self.lift()

        self.media_id = media_id
        self.feedback = feedback_service
        self.on_saved = on_saved
        self.open_media_callback = open_media_callback
        self.effective = self.feedback.effective_media_intelligence(media_id)
        self.entries = {}
        self.original_values = {}

        self.build_ui()

    ##########################################################

    def build_ui(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="Improve Analysis",
            font=("Segoe UI", 24, "bold")
        )
        header.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 8)
        )

        body = ctk.CTkScrollableFrame(self)
        body.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 12)
        )
        body.grid_columnconfigure(1, weight=1)

        row = 0

        for field, label in self.FIELD_LABELS.items():
            current = self.effective.get(field)
            inferred = self.feedback.inferred_value(
                self.media_id,
                field
            )
            self.original_values[field] = current

            ctk.CTkLabel(
                body,
                text=label
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=10,
                pady=(8, 2)
            )

            entry = ctk.CTkEntry(body)
            entry.insert(
                0,
                self.value_to_text(current)
            )
            entry.grid(
                row=row,
                column=1,
                sticky="ew",
                padx=10,
                pady=(8, 2)
            )
            self.entries[field] = entry

            ctk.CTkLabel(
                body,
                text="Inferred: " + self.value_to_text(inferred),
                text_color="#a8b3c7",
                wraplength=760,
                justify="left"
            ).grid(
                row=row + 1,
                column=1,
                sticky="w",
                padx=10,
                pady=(0, 6)
            )

            row += 2

        selector = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        selector.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 8)
        )
        selector.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            selector,
            text="Selected Field"
        ).grid(
            row=0,
            column=0,
            padx=(0, 8)
        )

        self.selected_field = ctk.StringVar(value="people_count")
        field_menu = ctk.CTkOptionMenu(
            selector,
            values=list(self.FIELD_LABELS.keys()),
            variable=self.selected_field
        )
        field_menu.grid(
            row=0,
            column=1,
            sticky="w"
        )

        controls = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        controls.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 10)
        )

        ctk.CTkButton(
            controls,
            text="Save Corrections",
            command=self.save
        ).pack(
            side="left",
            padx=(0, 8)
        )

        ctk.CTkButton(
            controls,
            text="Reset Field",
            command=self.reset_selected
        ).pack(
            side="left",
            padx=(0, 8)
        )

        ctk.CTkButton(
            controls,
            text="Restore Previous",
            command=self.restore_previous
        ).pack(
            side="left",
            padx=(0, 8)
        )

        ctk.CTkButton(
            controls,
            text="Close",
            command=self.destroy
        ).pack(
            side="right"
        )

        self.status = ctk.CTkLabel(
            self,
            text=""
        )
        self.status.grid(
            row=4,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 8)
        )

        self.suggestions = ctk.CTkScrollableFrame(
            self,
            height=120
        )
        self.suggestions.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )

    ##########################################################

    def save(self):

        saved = 0

        for field, entry in self.entries.items():
            value = entry.get().strip()
            original = self.value_to_text(
                self.original_values.get(field)
            )

            if value == original:
                continue

            self.feedback.save_correction(
                self.media_id,
                field,
                value,
                correction_source="Jonathan",
                notes=self.entries.get("notes").get().strip()
                if self.entries.get("notes")
                else ""
            )
            saved += 1

        self.effective = self.feedback.effective_media_intelligence(
            self.media_id
        )
        self.status.configure(
            text=f"Saved {saved} correction(s). Similar media may need the same correction."
        )
        self.render_suggestions(
            self.effective.get("similar_review_suggestions") or []
        )

        if self.on_saved:
            self.on_saved()

    ##########################################################

    def reset_selected(self):

        field = self.selected_field.get()
        self.feedback.reset_field(
            self.media_id,
            field,
            correction_source="Jonathan"
        )
        inferred = self.feedback.inferred_value(
            self.media_id,
            field
        )
        self.entries[field].delete(0, "end")
        self.entries[field].insert(
            0,
            self.value_to_text(inferred)
        )
        self.status.configure(
            text=f"{field} reset to inferred value."
        )

        if self.on_saved:
            self.on_saved()

    ##########################################################

    def restore_previous(self):

        field = self.selected_field.get()
        history = [
            row
            for row in self.feedback.history_for_media(self.media_id)
            if row.get("field_name") == field
        ]

        if not history:
            self.status.configure(
                text="No previous value found for selected field."
            )
            return

        previous = history[0].get("previous_value")
        self.entries[field].delete(0, "end")
        self.entries[field].insert(
            0,
            self.value_to_text(previous)
        )
        self.status.configure(
            text=f"Restored previous value for {field}. Save to apply."
        )

    ##########################################################

    def render_suggestions(self, rows):

        for child in self.suggestions.winfo_children():
            child.destroy()

        ctk.CTkLabel(
            self.suggestions,
            text="Similar Media Suggestions",
            font=("Segoe UI", 14, "bold")
        ).pack(
            anchor="w",
            padx=8,
            pady=(8, 4)
        )

        if not rows:
            ctk.CTkLabel(
                self.suggestions,
                text="No similar media found."
            ).pack(
                anchor="w",
                padx=8,
                pady=4
            )
            return

        for item in rows[:8]:
            button = ctk.CTkButton(
                self.suggestions,
                text=item["filename"],
                command=lambda value=item: self.open_suggestion(value)
            )
            button.pack(
                fill="x",
                padx=8,
                pady=3
            )

    ##########################################################

    def open_suggestion(self, item):

        if self.open_media_callback:
            self.open_media_callback(item)

    ##########################################################

    def value_to_text(self, value):

        if isinstance(value, list):
            return ", ".join(str(item) for item in value)

        return str(value or "")
