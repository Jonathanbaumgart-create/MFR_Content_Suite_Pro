import customtkinter as ctk

from gui.photo_card import PhotoCard
from gui.photo_viewer import PhotoViewer
from services.content_director_service import ContentDirectorService
from services.logging_service import LoggingService
from services.thumbnail_service import ThumbnailService


logger = LoggingService.get_logger("content")


class ContentDirectorPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.service = ContentDirectorService()
        self.thumbnail_service = ThumbnailService()
        self.current_results = []

        self.build_page()
        self.render_daily_opportunities()

    ##########################################################

    def build_page(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

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

        content = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        content.grid(
            row=3,
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

    def render_daily_opportunities(self):

        for child in self.daily_frame.winfo_children():
            child.destroy()

        for opportunity in self.service.daily_opportunities():

            button = ctk.CTkButton(
                self.daily_frame,
                text=opportunity["label"],
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
            opportunity["prompt"]
        )
        self.generate_suggestions(
            opportunity_types=[opportunity["type"]]
        )

    ##########################################################

    def generate_suggestions(self, opportunity_types=None):

        prompt = self.prompt_entry.get().strip()

        try:
            result = self.service.recommend(
                prompt=prompt,
                opportunity_types=opportunity_types,
                limit=5
            )

        except Exception as ex:
            logger.error(
                "Content Director request failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Content Director error: {ex}"
            )
            return

        self.current_results = result["recommendations"]
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

        if not self.current_results:
            label = ctk.CTkLabel(
                self.results,
                text="No matching media intelligence found."
            )

            label.pack(
                pady=30
            )
            return

        for recommendation in self.current_results:
            self.render_recommendation(recommendation)

    ##########################################################

    def render_recommendation(self, recommendation):

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

        card = PhotoCard(
            frame,
            recommendation["media_id"],
            recommendation["filename"],
            recommendation["path"],
            thumbnail_service=self.thumbnail_service
        )

        card.grid(
            row=0,
            column=0,
            rowspan=6,
            padx=12,
            pady=12,
            sticky="nw"
        )

        title = ctk.CTkLabel(
            frame,
            text=(
                f"{recommendation['filename']} "
                f"- Score {recommendation['score']}"
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
            text=f"Reason: {recommendation['reason']}",
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

        captions = recommendation["captions"]
        self.add_caption_line(
            frame,
            2,
            "Facebook",
            captions["facebook_caption"]
        )
        self.add_caption_line(
            frame,
            3,
            "Instagram",
            captions["instagram_caption"]
        )
        self.add_caption_line(
            frame,
            4,
            "Hashtags",
            " ".join(captions["hashtags"])
        )

        footer = ctk.CTkFrame(
            frame,
            fg_color="transparent"
        )

        footer.grid(
            row=5,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=(3, 12)
        )

        cta = ctk.CTkLabel(
            footer,
            text=(
                f"CTA: {captions['call_to_action']} | "
                f"Tone: {captions['tone_label']} | "
                f"Platforms: {', '.join(recommendation['suggested_platforms'])}"
            ),
            wraplength=700,
            justify="left"
        )

        cta.pack(
            side="left",
            fill="x",
            expand=True
        )

        open_button = ctk.CTkButton(
            footer,
            text="Open in Viewer",
            command=lambda item=recommendation: self.open_viewer(item)
        )

        open_button.pack(
            side="right",
            padx=(12, 0)
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

    def destroy(self):

        if hasattr(self, "thumbnail_service"):
            self.thumbnail_service.shutdown()

        super().destroy()
