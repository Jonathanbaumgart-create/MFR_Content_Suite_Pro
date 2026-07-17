import customtkinter as ctk
import threading

from gui.photo_viewer import PhotoViewer
from gui.tooltip import ToolTip
from media.image_dimensions import ImageDimensions


class PhotoCard(ctk.CTkFrame):

    IMAGE_AREA_SIZE = (170, 170)

    _thumbnail_update_lock = threading.Lock()
    _thumbnail_update_counter = 0

    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".gif",
        ".webp",
        ".tif",
        ".tiff",
        ".heic"
    }

    def __init__(
        self,
        parent,
        media_id,
        filename,
        filepath,
        thumbnail_service=None,
        selection_callback=None,
        analysis_status=None,
        media_type=None,
        duration_seconds=0,
        date_label="",
        filesystem_badge="",
        selected=False,
        open_callback=None,
        quick_approve_callback=None,
        quick_reject_callback=None
    ):

        super().__init__(
            parent,
            width=190,
            height=306,
            corner_radius=8
        )

        self.pack_propagate(False)

        self.filename = filename
        self.filepath = filepath
        self.media_id = media_id
        self.media_type = media_type or self._media_type_from_path()
        self.duration_seconds = float(duration_seconds or 0)
        self.date_label = date_label or ""
        self.filesystem_badge = filesystem_badge or ""
        self.analysis_status = analysis_status or "Not analyzed"
        self.selection_callback = selection_callback
        self.open_callback = open_callback
        self.quick_approve_callback = quick_approve_callback
        self.quick_reject_callback = quick_reject_callback
        self.thumbnail_service = thumbnail_service
        self.image = None
        self.selected = ctk.BooleanVar(value=bool(selected))

        self.image_area = ctk.CTkFrame(
            self,
            width=self.IMAGE_AREA_SIZE[0],
            height=self.IMAGE_AREA_SIZE[1],
            fg_color="transparent"
        )
        self.image_area.pack(
            padx=8,
            pady=(8, 4)
        )
        self.image_area.pack_propagate(False)

        if self.is_image():
            self.preview = ctk.CTkLabel(
                self.image_area,
                text="Loading...",
                width=self.IMAGE_AREA_SIZE[0],
                height=self.IMAGE_AREA_SIZE[1]
            )

        else:

            self.preview = ctk.CTkLabel(
                self.image_area,
                text="Loading video...",
                width=self.IMAGE_AREA_SIZE[0],
                height=self.IMAGE_AREA_SIZE[1]
            )

        self.preview.pack(
            fill="both",
            expand=True
        )

        self.select_box = ctk.CTkCheckBox(
            self.image_area,
            text="",
            variable=self.selected,
            command=self.selection_changed,
            width=28,
            height=28,
            checkbox_width=24,
            checkbox_height=24,
            border_width=2,
            corner_radius=5,
            fg_color="#2d7dff",
            hover_color="#1c5fcc"
        )
        self.select_box.place(
            x=6,
            y=6
        )
        self.select_box.lift()
        self.select_box.bind(
            "<Double-Button-1>",
            lambda _event: "break"
        )
        self.select_box.bind(
            "<Return>",
            self.toggle_selection_from_keyboard
        )
        self.select_box.bind(
            "<space>",
            self.toggle_selection_from_keyboard
        )

        self.filename_label = ctk.CTkLabel(
            self,
            text=filename,
            wraplength=170,
            justify="center"
        )

        self.filename_label.pack(
            padx=5,
            pady=(0, 4)
        )

        self.video_label = None

        if self.is_video():
            self.video_label = ctk.CTkLabel(
                self,
                text=self.video_badge_text(),
                font=("Segoe UI", 10, "bold"),
                text_color="#9fb7ff"
            )
            self.video_label.pack(
                padx=5,
                pady=(0, 3)
            )

        self.filesystem_label = None

        if self.filesystem_badge:
            self.filesystem_label = ctk.CTkLabel(
                self,
                text=self.filesystem_badge[:32],
                font=("Segoe UI", 10, "bold"),
                text_color=(
                    "#ffcf7a"
                    if self.filesystem_badge == "Folder Conflict"
                    else "#9bd8ff"
                )
            )
            self.filesystem_label.pack(
                padx=5,
                pady=(0, 3)
            )

        self.status_label = ctk.CTkLabel(
            self,
            text=self.analysis_status,
            font=("Segoe UI", 10),
            text_color=self.status_color()
        )

        self.status_label.pack(
            padx=5,
            pady=(0, 6)
        )

        self.quick_review_row = None

        if self.quick_review_allowed():
            self.quick_review_row = ctk.CTkFrame(
                self,
                fg_color="transparent"
            )
            self.quick_review_row.pack(
                fill="x",
                padx=8,
                pady=(0, 6)
            )

            review = ctk.CTkButton(
                self.quick_review_row,
                text="Review",
                width=78,
                height=24,
                fg_color="#38527a",
                hover_color="#4a6590",
                command=self.quick_review
            )
            review.grid(
                row=0,
                column=0,
                padx=(0, 4),
                pady=(0, 4)
            )
            ToolTip(
                review,
                "Open this media in the review viewer."
            )

            correct = ctk.CTkButton(
                self.quick_review_row,
                text="Correct",
                width=78,
                height=24,
                fg_color="#5a4b83",
                hover_color="#6d5a9c",
                command=self.quick_review
            )
            correct.grid(
                row=0,
                column=1,
                pady=(0, 4)
            )
            ToolTip(
                correct,
                "Open the viewer to improve or correct analysis."
            )

            approve = ctk.CTkButton(
                self.quick_review_row,
                text="Approve",
                width=78,
                height=24,
                fg_color="#287a4d",
                hover_color="#33945f",
                command=self.quick_approve
            )
            approve.grid(
                row=1,
                column=0,
                padx=(0, 4)
            )
            ToolTip(
                approve,
                "Approve this review-required real analysis."
            )

            reject = ctk.CTkButton(
                self.quick_review_row,
                text="Reject",
                width=78,
                height=24,
                fg_color="#8a3333",
                hover_color="#a24444",
                command=self.quick_reject
            )
            reject.grid(
                row=1,
                column=1
            )
            ToolTip(
                reject,
                "Reject this weak or misleading analysis."
            )

        ##########################################

        for widget in (
            self,
            self.image_area,
            self.preview,
            self.filename_label,
            self.status_label
        ):

            widget.bind(
                "<Double-Button-1>",
                self.open_viewer
            )

        if self.video_label is not None:
            self.video_label.bind(
                "<Double-Button-1>",
                self.open_viewer
            )

        if self.filesystem_label is not None:
            self.filesystem_label.bind(
                "<Double-Button-1>",
                self.open_viewer
            )

        if self.thumbnail_service:
            self.thumbnail_service.load_thumbnail(
                self.filepath,
                self.thumbnail_ready
            )

    ##########################################################

    def is_image(self):

        return self.media_type == "image" or self.filepath.lower().endswith(
            tuple(self.IMAGE_EXTENSIONS)
        )

    ##########################################################

    def is_video(self):

        return self.media_type == "video" and not self.is_image()

    ##########################################################

    def _media_type_from_path(self):

        if self.filepath.lower().endswith(
            tuple(self.IMAGE_EXTENSIONS)
        ):
            return "image"

        return "video"

    ##########################################################

    def video_badge_text(self):

        duration = self.duration_text()

        if duration:
            return f"VIDEO  {duration}"

        return "VIDEO"

    ##########################################################

    def duration_text(self):

        seconds = int(self.duration_seconds or 0)

        if seconds <= 0:
            return ""

        minutes = seconds // 60
        remainder = seconds % 60

        return f"{minutes}:{remainder:02d}"

    ##########################################################

    def thumbnail_ready(self, media_path, thumbnail_image):

        with self._thumbnail_update_lock:
            delay = (self._thumbnail_update_counter % 40) * 25
            self.__class__._thumbnail_update_counter += 1

        try:
            self.after(
                delay,
                lambda: self.show_thumbnail(thumbnail_image)
            )
        except Exception:
            pass

    ##########################################################

    def status_color(self):

        colors = {
            "Analyzing": "#f6c453",
            "Queued": "#9fb7ff",
            "Interrupted": "#ffcf7a",
            "Analyzed": "#7bd88f",
            "Real": "#7bd88f",
            "Real - Review Required": "#f6c453",
            "Real - Approved": "#7bd88f",
            "Real - Corrected": "#c9a8ff",
            "Real - Rejected": "#ff8a8a",
            "Effective Intelligence": "#7bd88f",
            "Human Corrected": "#c9a8ff",
            "Failed": "#ff8a8a",
            "Mock": "#ffcf7a",
            "Mock/Test Data": "#ffcf7a",
            "Not analyzed": "#a8a8a8"
        }

        return colors.get(
            self.analysis_status,
            "#a8a8a8"
        )

    ##########################################################

    def show_thumbnail(self, thumbnail_image):

        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        if thumbnail_image is None:
            self.preview.configure(
                text="No Preview",
                image=None
            )
            return

        try:
            self.image = ctk.CTkImage(
                light_image=thumbnail_image,
                dark_image=thumbnail_image,
                size=ImageDimensions.fit_size(
                    thumbnail_image.size,
                    self.IMAGE_AREA_SIZE
                )
            )

            self.preview.configure(
                image=self.image,
                text=""
            )
        except Exception:
            self.preview.configure(
                text="No Preview",
                image=None
            )

    ##########################################################

    def quick_review_allowed(self):

        return self.analysis_status == "Real - Review Required"

    ##########################################################

    def quick_approve(self):

        if self.quick_approve_callback:
            self.quick_approve_callback(self.media_id)

    ##########################################################

    def quick_reject(self):

        if self.quick_reject_callback:
            self.quick_reject_callback(self.media_id)

    ##########################################################

    def quick_review(self):

        self.open_viewer()

    ##########################################################

    def open_viewer(self, event=None):

        if self.open_callback:
            self.open_callback(self)
            return "break"

        PhotoViewer(
            self,
            self.media_id,
            self.filename,
            self.filepath
        )

    ##########################################################

    def selection_changed(self):

        if self.selection_callback:
            self.selection_callback(
                self.media_id,
                self.selected.get()
            )

    ##########################################################

    def set_selected(self, selected, notify=False):

        self.selected.set(bool(selected))

        if notify:
            self.selection_changed()

    ##########################################################

    def set_analysis_status(self, status):

        self.analysis_status = status or self.analysis_status
        self.status_label.configure(
            text=self.analysis_status,
            text_color=self.status_color()
        )

        if self.quick_review_row is not None and not self.quick_review_allowed():
            self.quick_review_row.pack_forget()

    ##########################################################

    def toggle_selection_from_keyboard(self, _event=None):

        self.selected.set(
            not self.selected.get()
        )
        self.selection_changed()

        return "break"
