import customtkinter as ctk
import threading

from gui.photo_viewer import PhotoViewer
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
        analysis_status=None
    ):

        super().__init__(
            parent,
            width=190,
            height=245,
            corner_radius=8
        )

        self.pack_propagate(False)

        self.filename = filename
        self.filepath = filepath
        self.media_id = media_id
        self.analysis_status = analysis_status or "Not analyzed"
        self.selection_callback = selection_callback
        self.thumbnail_service = thumbnail_service
        self.image = None

        if self.is_image():

            self.preview = ctk.CTkLabel(
                self,
                text="Loading...",
                width=self.IMAGE_AREA_SIZE[0],
                height=self.IMAGE_AREA_SIZE[1]
            )

        else:

            self.preview = ctk.CTkLabel(
                self,
                text="VIDEO",
                width=self.IMAGE_AREA_SIZE[0],
                height=self.IMAGE_AREA_SIZE[1]
            )

        self.preview.pack(
            padx=8,
            pady=(8, 4)
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

        self.selected = ctk.BooleanVar(value=False)

        self.select_box = ctk.CTkCheckBox(
            self,
            text="Select",
            variable=self.selected,
            command=self.selection_changed
        )

        self.select_box.pack(
            pady=(0, 6)
        )

        ##########################################

        for widget in (
            self,
            self.preview,
            self.filename_label,
            self.status_label
        ):

            widget.bind(
                "<Double-Button-1>",
                self.open_viewer
            )

        if self.is_image() and self.thumbnail_service:
            self.thumbnail_service.load_thumbnail(
                self.filepath,
                self.thumbnail_ready
            )

    ##########################################################

    def is_image(self):

        return self.filepath.lower().endswith(
            tuple(self.IMAGE_EXTENSIONS)
        )

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
            "Analyzed": "#7bd88f",
            "Real": "#7bd88f",
            "Effective Intelligence": "#7bd88f",
            "Human Corrected": "#c9a8ff",
            "Failed": "#ff8a8a",
            "Mock": "#ffcf7a",
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

    def open_viewer(self, event=None):

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
