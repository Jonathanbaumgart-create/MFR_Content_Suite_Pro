import customtkinter as ctk
from PIL import Image, ImageOps

from media.image_dimensions import ImageDimensions


class ImageLoader:

    @staticmethod
    def load_image(path, size=(180, 180)):

        image = ImageLoader.load_pil_image(path)
        display_size = ImageDimensions.fit_size(
            image.size,
            size
        )

        return ctk.CTkImage(

            light_image=image,

            dark_image=image,

            size=display_size

        )

    ########################################################

    @staticmethod
    def load_pil_image(path):

        with Image.open(path) as loaded:
            image = ImageOps.exif_transpose(loaded)
            image = ImageLoader._convert_mode(image)
            return image.copy()

    ########################################################

    @staticmethod
    def ctk_image_from_pil(image, bounding_size, allow_upscale=False):

        display_size = ImageDimensions.fit_size(
            image.size,
            bounding_size,
            allow_upscale=allow_upscale
        )

        return ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=display_size
        )

    ########################################################

    @staticmethod
    def _convert_mode(image):

        if image.mode in ("RGB", "RGBA"):
            return image

        if "A" in image.getbands():
            return image.convert("RGBA")

        return image.convert("RGB")
