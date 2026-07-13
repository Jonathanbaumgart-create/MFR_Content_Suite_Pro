from pathlib import Path
from PIL import Image, ImageOps
import hashlib

from media.image_loader import ImageLoader
from services.video_metadata_service import VideoMetadataService


class ThumbnailCache:

    CACHE_VERSION = 2
    DEFAULT_SIZE = 420

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

    VIDEO_EXTENSIONS = VideoMetadataService.VIDEO_EXTENSIONS

    def __init__(self, cache_dir=None):

        self.cache = Path(cache_dir) if cache_dir else Path.cwd() / "thumbnails"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.video = VideoMetadataService()

    ########################################################

    def get_thumbnail(self, media_path, size=None):

        size = int(size or self.DEFAULT_SIZE)

        media_path = Path(media_path)

        suffix = media_path.suffix.lower()

        if (
            suffix not in self.IMAGE_EXTENSIONS and
            suffix not in self.VIDEO_EXTENSIONS
        ):
            return None

        thumb_name = self.cache_identity(
            media_path,
            size
        ) + ".jpg"

        thumbnail = self.cache / thumb_name

        if thumbnail.exists():
            return thumbnail

        try:

            if suffix in self.VIDEO_EXTENSIONS:
                if self.video.create_thumbnail(
                    media_path,
                    thumbnail,
                    size=size
                ):
                    return thumbnail

                return None

            with Image.open(media_path) as loaded:
                image = ImageOps.exif_transpose(loaded)
                image = ImageLoader._convert_mode(image).copy()

            if image.mode != "RGB":
                image = image.convert("RGB")

            image.thumbnail(
                (size, size),
                Image.Resampling.LANCZOS
            )

            image.save(
                thumbnail,
                format="JPEG",
                quality=92,
                optimize=True,
                subsampling=0
            )

            return thumbnail

        except Exception as ex:

            print(f"Thumbnail failed: {media_path}")
            print(ex)

            return None

    ########################################################

    def cache_identity(self, media_path, size=None):

        media_path = Path(media_path)
        size = int(size or self.DEFAULT_SIZE)

        try:
            resolved = str(media_path.resolve())
        except Exception:
            resolved = str(media_path.absolute())

        identity = "|".join(
            (
                f"v{self.CACHE_VERSION}",
                str(size),
                resolved
            )
        )

        return hashlib.sha1(
            identity.encode("utf-8")
        ).hexdigest()
