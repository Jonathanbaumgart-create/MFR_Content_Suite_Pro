from pathlib import Path
from PIL import Image
import hashlib


class ThumbnailCache:

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

    def __init__(self):

        self.cache = Path.cwd() / "thumbnails"
        self.cache.mkdir(parents=True, exist_ok=True)

    ########################################################

    def get_thumbnail(self, media_path, size=250):

        media_path = Path(media_path)

        # Skip videos for now
        if media_path.suffix.lower() not in self.IMAGE_EXTENSIONS:
            return None

        # Create a unique thumbnail filename from the FULL PATH
        thumb_name = hashlib.sha1(
            str(media_path).encode("utf-8")
        ).hexdigest() + ".jpg"

        thumbnail = self.cache / thumb_name

        if thumbnail.exists():
            return thumbnail

        try:

            image = Image.open(media_path)

            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            image.thumbnail((250, 250))

            image.save(
                thumbnail,
                format="JPEG",
                quality=90
            )

            return thumbnail

        except Exception as ex:

            print(f"Thumbnail failed: {media_path}")
            print(ex)

            return None