import customtkinter as ctk
from PIL import Image


class ImageLoader:

    @staticmethod
    def load_image(path, size=(180, 180)):

        image = Image.open(path)

        return ctk.CTkImage(

            light_image=image,

            dark_image=image,

            size=size

        )