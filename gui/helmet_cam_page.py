import customtkinter as ctk
import os

from core.app_context import context
from services.helmet_camera_service import HelmetCameraService


class HelmetCamPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.service = HelmetCameraService()
        self.future = None
        self.preview_future = None
        self.videos = []
        self.selected_video = None
        self.preview_image = None
        self.preview_clip_future = None
        self.temp_preview_paths = []
        self.build_page()
        self.refresh_status()

    ############################################################

    def build_page(self):

        title = ctk.CTkLabel(
            self,
            text="Helmet Camera",
            font=("Segoe UI", 30, "bold")
        )
        title.pack(
            anchor="w",
            padx=20,
            pady=(20, 8)
        )

        self.status = ctk.CTkLabel(
            self,
            text="Checking Helmet Camera source...",
            anchor="w"
        )
        self.status.pack(
            fill="x",
            padx=20,
            pady=(0, 10)
        )

        controls = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        controls.pack(
            fill="x",
            padx=20,
            pady=(0, 10)
        )

        ctk.CTkButton(
            controls,
            text="Refresh Source",
            command=self.refresh_status
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            controls,
            text="Scan Helmet Cam Folder",
            command=self.scan_source
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            controls,
            text="Analyze Selected Video",
            command=self.analyze_selected
        ).pack(side="left")

        body = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        body.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.video_list = ctk.CTkScrollableFrame(body)
        self.video_list.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 10)
        )

        self.segment_panel = ctk.CTkScrollableFrame(body)
        self.segment_panel.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

    ############################################################

    def refresh_status(self):

        source = self.service.source_status()
        self.videos = self.service.helmet_videos(limit=100)
        self.status.configure(
            text=(
                f"Source: {source.get('root_path')} | "
                f"Available: {'yes' if source.get('available') else 'no'} | "
                f"Indexed videos: {len(self.videos):,}"
            )
        )
        self.render_videos()

    def render_videos(self):

        for child in self.video_list.winfo_children():
            child.destroy()

        if not self.videos:
            ctk.CTkLabel(
                self.video_list,
                text="No Helmet Camera videos indexed yet."
            ).pack(anchor="w", padx=10, pady=10)
            return

        for video in self.videos[:100]:
            text = (
                f"{video.get('filename', '')}\n"
                f"{self.duration_text(video.get('duration_seconds', 0))} | "
                f"{video.get('width', 0)}x{video.get('height', 0)}"
            )
            button = ctk.CTkButton(
                self.video_list,
                text=text,
                anchor="w",
                command=lambda item=video: self.select_video(item)
            )
            button.pack(
                fill="x",
                padx=8,
                pady=5
            )

    def select_video(self, video):

        self.selected_video = video
        self.status.configure(
            text=f"Selected {video.get('filename', '')}"
        )
        self.render_segments(
            self.service.db.helmet_camera_segments(
                video.get("id") or video.get("media_id"),
                limit=10
            )
        )

    ############################################################

    def scan_source(self):

        self.status.configure(text="Scanning Helmet Camera source...")
        self.future = context.job_manager.submit(
            self.service.scan_source
        )
        self.after(200, self.check_scan_future)

    def check_scan_future(self):

        if not self.future.done():
            self.after(200, self.check_scan_future)
            return

        result = self.future.result()
        self.status.configure(
            text=(
                f"Scan complete. Processed {result.get('processed', 0):,}, "
                f"inserted {result.get('inserted', 0):,}."
            )
        )
        self.refresh_status()

    ############################################################

    def analyze_selected(self):

        if not self.selected_video:
            self.status.configure(text="Select a Helmet Camera video first.")
            return

        media_id = self.selected_video.get("id") or self.selected_video.get("media_id")
        path = self.selected_video.get("path", "")
        self.status.configure(text="Running fast technical pass...")
        self.future = context.job_manager.submit(
            self.service.analyze_video,
            media_id,
            path
        )
        self.after(200, self.check_analysis_future)

    def check_analysis_future(self):

        if not self.future.done():
            self.after(200, self.check_analysis_future)
            return

        result = self.future.result()
        self.status.configure(
            text=(
                f"Technical pass complete. "
                f"{result.get('candidate_count', 0):,} candidate segment(s), "
                f"{result.get('elapsed_seconds', 0)}s."
            )
        )
        self.render_segments(result.get("top_segments", []))

    ############################################################

    def render_segments(self, segments):

        for child in self.segment_panel.winfo_children():
            child.destroy()

        if not segments:
            ctk.CTkLabel(
                self.segment_panel,
                text="No candidate segments yet."
            ).pack(anchor="w", padx=10, pady=10)
            return

        for segment in segments:
            text = "\n".join([
                (
                    f"{self.duration_text(segment.get('start_seconds', 0))} - "
                    f"{self.duration_text(segment.get('end_seconds', 0))}"
                ),
                (
                    "Overall Reel Potential: " +
                    str(segment.get("overall_reel_potential") or segment.get("reel_score", 0))
                ),
                f"Classification: {segment.get('classification', 'Needs semantic screen')}",
                f"Visible activity: {segment.get('visible_activity_summary') or segment.get('visual_summary', '')}",
                f"Recommended tone: {segment.get('recommended_tone', '')}",
                f"Suggested hook: {segment.get('suggested_hook', '')}",
                f"Risk: {segment.get('risk_level', '')}",
                f"Strongest reason: {segment.get('strongest_reason') or segment.get('reason_selected', '')}",
                f"Flags: {', '.join(segment.get('risk_flags') or []) or 'none'}"
            ])
            frame = ctk.CTkFrame(self.segment_panel)
            frame.pack(
                fill="x",
                padx=8,
                pady=8
            )
            ctk.CTkLabel(
                frame,
                text=text,
                wraplength=520,
                justify="left"
            ).pack(
                anchor="w",
                padx=10,
                pady=10
            )
            ctk.CTkButton(
                frame,
                text="Preview Clip",
                command=lambda item=segment: self.preview_clip(item)
            ).pack(
                side="left",
                padx=(10, 6),
                pady=(0, 10)
            )
            ctk.CTkButton(
                frame,
                text="Contact Sheet",
                command=lambda item=segment: self.preview_segment(item)
            ).pack(
                side="left",
                padx=(0, 6),
                pady=(0, 10)
            )
            ctk.CTkButton(
                frame,
                text="Run Semantic Screen",
                command=self.semantic_screen_selected
            ).pack(
                side="left",
                padx=(0, 6),
                pady=(0, 10)
            )
            ctk.CTkButton(
                frame,
                text="Create Reel Package",
                command=lambda item=segment: self.show_reel_package(item)
            ).pack(
                side="left",
                padx=(0, 6),
                pady=(0, 10)
            )

    ############################################################

    def semantic_screen_selected(self):

        if not self.selected_video:
            self.status.configure(text="Select a Helmet Camera video first.")
            return

        media_id = self.selected_video.get("id") or self.selected_video.get("media_id")
        segments = self.service.semantic_screen_segments(media_id, limit=5)
        self.status.configure(text="Semantic screen complete for top candidates.")
        self.render_segments(segments)

    def preview_clip(self, segment):

        if not self.selected_video:
            self.status.configure(text="Select a Helmet Camera video first.")
            return

        path = self.selected_video.get("path", "")
        self.status.configure(text="Preparing playable preview clip...")
        self.preview_clip_future = context.job_manager.submit(
            self.service.create_preview_clip,
            path,
            segment
        )
        self.after(200, self.check_preview_clip_future)

    def check_preview_clip_future(self):

        if not self.preview_clip_future.done():
            self.after(200, self.check_preview_clip_future)
            return

        result = self.preview_clip_future.result()
        if not result.get("success"):
            self.status.configure(
                text="Playable preview unavailable: " + result.get("stderr", "")
            )
            return

        path = result.get("preview_path", "")
        if path:
            self.temp_preview_paths.append(path)
            try:
                os.startfile(path)
                self.status.configure(text="Playable preview opened.")
            except Exception as ex:
                self.status.configure(text=f"Could not open preview clip: {ex}")

    def preview_segment(self, segment):

        if not self.selected_video:
            self.status.configure(text="Select a Helmet Camera video first.")
            return

        path = self.selected_video.get("path", "")
        self.status.configure(text="Building segment preview...")
        self.preview_future = context.job_manager.submit(
            self.service.create_contact_sheet,
            path,
            segment
        )
        self.after(200, lambda: self.check_preview_future(segment))

    def check_preview_future(self, segment):

        if not self.preview_future.done():
            self.after(200, lambda: self.check_preview_future(segment))
            return

        image = self.preview_future.result()
        if image is None:
            self.status.configure(text="Preview unavailable for this segment.")
            return

        self.show_preview_window(image, segment)

    def show_preview_window(self, image, segment):

        window = ctk.CTkToplevel(self)
        window.title("Helmet Camera Segment Preview")
        window.geometry("780x460")
        window.transient(self.winfo_toplevel())

        fitted = image.copy()
        fitted.thumbnail((740, 360))
        self.preview_image = ctk.CTkImage(
            light_image=fitted,
            dark_image=fitted,
            size=(fitted.width, fitted.height)
        )

        ctk.CTkLabel(
            window,
            text=(
                f"{self.duration_text(segment.get('start_seconds', 0))} - "
                f"{self.duration_text(segment.get('end_seconds', 0))}"
            ),
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=18, pady=(18, 8))

        ctk.CTkLabel(
            window,
            image=self.preview_image,
            text=""
        ).pack(padx=18, pady=8)

        ctk.CTkButton(
            window,
            text="Close",
            command=window.destroy
        ).pack(anchor="e", padx=18, pady=(8, 18))

    def show_reel_package(self, segment):

        if not self.selected_video:
            self.status.configure(text="Select a Helmet Camera video first.")
            return

        media_id = self.selected_video.get("id") or self.selected_video.get("media_id")
        package = self.service.reel_package(media_id, segment)
        window = ctk.CTkToplevel(self)
        window.title("Helmet Camera Reel Package")
        window.geometry("760x560")
        window.transient(self.winfo_toplevel())

        text = ctk.CTkTextbox(window, wrap="word")
        text.pack(fill="both", expand=True, padx=16, pady=16)
        text.insert(
            "1.0",
            "\n".join([
                "Instagram Reel Caption:",
                package.get("instagram_reel_caption", ""),
                "",
                "Facebook Video Caption:",
                package.get("facebook_reel_caption", ""),
                "",
                "Hook: " + package.get("hook_text", ""),
                "Content family: " + package.get("content_family", ""),
                "Target audience: " + package.get("target_audience", ""),
                "Posting angle: " + package.get("posting_angle", ""),
                "Orientation correction: " + str(package.get("orientation_correction", 0)),
                "Warnings: " + ", ".join(package.get("risk_warnings") or [])
            ])
        )
        text.configure(state="disabled")

        ctk.CTkButton(
            window,
            text="Close",
            command=window.destroy
        ).pack(anchor="e", padx=16, pady=(0, 16))

    def duration_text(self, seconds):

        seconds = int(float(seconds or 0))
        minutes = seconds // 60
        remainder = seconds % 60
        return f"{minutes}:{remainder:02d}"

    def destroy(self):

        for path in self.temp_preview_paths:
            try:
                os.remove(path)
            except Exception:
                pass

        super().destroy()
