import customtkinter as ctk

from gui.photo_card import PhotoCard
from services.gallery_service import GalleryService


class GalleryPage(ctk.CTkFrame):

    PAGE_SIZE = 200

    def __init__(self, parent):

        super().__init__(parent)

        self.service = GalleryService()

        self.media = []

        self.loaded = 0

        self.build_page()

    ########################################################

    def build_page(self):

        title = ctk.CTkLabel(
            self,
            text="Gallery",
            font=("Segoe UI", 30, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        self.info = ctk.CTkLabel(
            self,
            text=""
        )

        self.info.pack(
            anchor="w",
            padx=20
        )

        self.scroll = ctk.CTkScrollableFrame(self)

        self.scroll.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.media = self.service.get_media()

        self.load_more()

        self.more = ctk.CTkButton(
            self,
            text="Load More",
            command=self.load_more
        )

        self.more.pack(pady=10)

    ########################################################

    def load_more(self):

        end = min(
            self.loaded + self.PAGE_SIZE,
            len(self.media)
        )

        for index in range(self.loaded, end):

            media_id, filename, path, media_type = self.media[index]

            try:

                card = PhotoCard(
                    self.scroll,
                    media_id,
                    filename,
                    path
                )

                row = index // 4
                column = index % 4

                card.grid(
                    row=row,
                    column=column,
                    padx=12,
                    pady=12
                )

            except Exception as ex:

                print(path)
                print(ex)

        self.loaded = end

        self.info.configure(
            text=f"Showing {self.loaded:,} of {len(self.media):,} media"
        )

        if self.loaded >= len(self.media):

            self.more.configure(
                state="disabled",
                text="All Media Loaded"
            )
