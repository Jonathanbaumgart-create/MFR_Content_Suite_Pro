import base64
import io
import os
import time
from pathlib import Path

from PIL import Image, ImageOps

from media.image_dimensions import ImageDimensions
from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class VisionPreprocessingError(RuntimeError):

    def __init__(self, category, message, metadata=None):

        self.category = category
        self.metadata = metadata or {}
        super().__init__(message)


class VisionPreprocessingService:

    VERSION = "qwen_preprocess_v1"
    SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}

    def preprocess(self, image_path, max_dimension=1536, quality=92):

        started = time.perf_counter()
        metadata = {
            "preprocessing_version": self.VERSION,
            "media_path_name": Path(image_path).name,
            "requested_max_dimension": int(max_dimension or 1536)
        }

        try:
            metadata["file_size"] = os.path.getsize(image_path)
        except Exception:
            metadata["file_size"] = 0

        try:
            with Image.open(image_path) as loaded:
                metadata["image_format"] = loaded.format or ""
                metadata["original_dimensions"] = list(loaded.size)
                metadata["original_mode"] = loaded.mode
                metadata["exif_orientation"] = self._exif_orientation(loaded)

                image = ImageOps.exif_transpose(loaded)
                image = self._convert_for_jpeg(image)
                image.thumbnail(
                    ImageDimensions.fit_size(
                        image.size,
                        (max_dimension, max_dimension),
                        allow_upscale=False
                    ),
                    Image.Resampling.LANCZOS
                )
                image = image.copy()

        except VisionPreprocessingError:
            raise
        except Exception as ex:
            metadata["elapsed_seconds"] = round(time.perf_counter() - started, 4)
            raise VisionPreprocessingError(
                "image_encoding_failed",
                f"Could not open or preprocess image: {ex}",
                metadata
            ) from ex

        metadata["submitted_dimensions"] = list(image.size)
        metadata["submitted_mode"] = image.mode

        try:
            buffer = io.BytesIO()
            image.save(
                buffer,
                format="JPEG",
                quality=int(quality or 92),
                optimize=True,
                subsampling=0
            )
            encoded_bytes = buffer.getvalue()
            encoded = base64.b64encode(encoded_bytes).decode("utf-8")

        except Exception as ex:
            metadata["elapsed_seconds"] = round(time.perf_counter() - started, 4)
            raise VisionPreprocessingError(
                "image_encoding_failed",
                f"Could not encode image for provider: {ex}",
                metadata
            ) from ex

        if not encoded:
            metadata["elapsed_seconds"] = round(time.perf_counter() - started, 4)
            raise VisionPreprocessingError(
                "image_encoding_failed",
                "Encoded image payload was empty",
                metadata
            )

        metadata["submitted_byte_size"] = len(encoded_bytes)
        metadata["encoded_character_size"] = len(encoded)
        metadata["elapsed_seconds"] = round(time.perf_counter() - started, 4)

        return {
            "base64": encoded,
            "metadata": metadata
        }

    ############################################################

    def _convert_for_jpeg(self, image):

        if image.mode == "RGB":
            return image

        if image.mode in ("RGBA", "LA") or "A" in image.getbands():
            background = Image.new("RGB", image.size, (255, 255, 255))
            alpha = image.convert("RGBA").getchannel("A")
            background.paste(image.convert("RGBA"), mask=alpha)
            return background

        try:
            return image.convert("RGB")
        except Exception as ex:
            raise VisionPreprocessingError(
                "unsupported_image_mode",
                f"Unsupported image mode for provider analysis: {image.mode}",
                {"original_mode": image.mode}
            ) from ex

    ############################################################

    def _exif_orientation(self, image):

        try:
            return int(image.getexif().get(274, 1))
        except Exception:
            return 1
