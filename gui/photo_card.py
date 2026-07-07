import customtkinter as ctk

from media.thumbnail_cache import ThumbnailCache
from media.image_loader import ImageLoader
from gui.photo_viewer import PhotoViewer


class PhotoCard(ctk.CTkFrame):

    def __init__(
        self,
        parent,
        filename,
        filepath
    ):

        super().__init__(
            parent,
            width=190,
            height=220,
            corner_radius=8
        )

        self.pack_propagate(False)

        self.filename = filename
        self.filepath = filepath

        cache = ThumbnailCache()

        thumb = cache.get_thumbnail(filepath)

        if thumb:

            self.image = ImageLoader.load_image(
                thumb,
                (170, 170)
            )

            self.preview = ctk.CTkLabel(
                self,
                image=self.image,
                text=""
            )

        else:

            self.preview = ctk.CTkLabel(
                self,
                text="VIDEO",
                width=170,
                height=170
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
            pady=(0, 8)
        )

        ##########################################

        for widget in (
            self,
            self.preview,
            self.filename_label
        ):

            widget.bind(
                "<Double-Button-1>",
                self.open_viewer
            )

    ##########################################################

    def open_viewer(self, event=None):

        PhotoViewer(
            self,
            self.filename,
            self.filepath
        )