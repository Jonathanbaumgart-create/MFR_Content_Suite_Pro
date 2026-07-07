import customtkinter as ctk

from media.image_loader import ImageLoader
from services.brain_service import BrainService


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
        self.brain = BrainService()
        self.analysis = None

        self.build_ui()
        self.load_analysis()

    ##########################################################

    def build_ui(self):

        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)

        self.grid_rowconfigure(0, weight=1)

        #######################################################
        # IMAGE PANEL
        #######################################################

        image_frame = ctk.CTkFrame(self)

        image_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(15, 5),
            pady=15
        )

        title = ctk.CTkLabel(
            image_frame,
            text=self.filename,
            font=("Segoe UI", 22, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        self.image = ImageLoader.load_image(
            self.filepath,
            size=(1200, 800)
        )

        preview = ctk.CTkLabel(
            image_frame,
            image=self.image,
            text=""
        )

        preview.pack(
            expand=True,
            padx=20,
            pady=20
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
            pady=(20, 15)
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
            text="Analyze Photo",
            command=self.analyze_photo
        )

        self.analyze_button.pack(
            fill="x",
            padx=20,
            pady=10
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
            height=420
        )

        self.analysis_text.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.analysis_text.configure(state="disabled")

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

        lines = [
            analysis.get("description", ""),
            "",
            f"Scene: {analysis.get('scene_type', '')}",
            f"Activity: {analysis.get('activity', '')}",
            f"People: {analysis.get('people_count', 0)}",
            "",
            "Apparatus: " + self.format_list(analysis.get("apparatus")),
            "Equipment: " + self.format_list(analysis.get("equipment")),
            "Keywords: " + self.format_list(analysis.get("keywords")),
            "",
            f"Community Score: {analysis.get('community_score', 0)}",
            f"Recruitment Score: {analysis.get('recruitment_score', 0)}",
            f"Education Score: {analysis.get('education_score', 0)}",
            f"Technical Score: {analysis.get('technical_score', 0)}",
            f"Overall Score: {analysis.get('overall_score', 0)}",
            "",
            f"Model: {analysis.get('model', '')}",
            f"Provider: {analysis.get('provider', '')}",
            f"Duration: {analysis.get('analysis_duration', 0):.2f}s",
            f"Retries: {analysis.get('retry_count', 0)}",
            f"Failure: {analysis.get('failure_reason', '')}",
            f"Analyzed: {analysis.get('last_analyzed') or analysis.get('analyzed_at', '')}"
        ]

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", "\n".join(lines))
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def show_error(self, error):

        self.status.configure(
            text=f"Status: Analysis failed"
        )

        self.analyze_button.configure(
            state="normal"
        )

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", str(error))
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def format_list(self, value):

        if not value:
            return "None"

        return ", ".join(str(item) for item in value)
