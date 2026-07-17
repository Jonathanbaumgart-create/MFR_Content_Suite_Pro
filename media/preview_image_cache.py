from collections import OrderedDict
from io import BytesIO
import os
import time

from PIL import Image, ImageOps

from media.image_dimensions import ImageDimensions
from media.image_loader import ImageLoader
from media.thumbnail_cache import ThumbnailCache
from services.logging_service import LoggingService


logger = LoggingService.get_logger("gallery")


class PreviewImageCache:

    def __init__(self, max_items=4, max_dimension=1800):

        self.max_items = max(2, int(max_items or 4))
        self.max_dimension = max(1, int(max_dimension or 1800))
        self.items = OrderedDict()
        self.thumbnail_cache = ThumbnailCache()

    ############################################################

    def clear(self):

        self.items.clear()

    ############################################################

    def get(self, media_id, path, is_video=False):

        key = self.cache_key(media_id, path, is_video=is_video)

        if key in self.items:
            entry = self.items.pop(key)
            self.items[key] = entry
            entry["cache_hit"] = True
            return entry

        entry = self.load_preview(
            media_id,
            path,
            is_video=is_video
        )
        self.items[key] = entry
        self.evict()
        return entry

    ############################################################

    def prefetch(self, media_id, path, is_video=False):

        key = self.cache_key(media_id, path, is_video=is_video)

        if key in self.items:
            return

        try:
            self.get(media_id, path, is_video=is_video)
        except Exception as ex:
            logger.debug(
                "Preview prefetch failed media_id=%s error=%s",
                media_id,
                ex
            )

    ############################################################

    def load_preview(self, media_id, path, is_video=False):

        timings = {}
        started = time.perf_counter()

        try:
            source_path = path

            if is_video:
                thumb_started = time.perf_counter()
                source_path = self.thumbnail_cache.get_thumbnail(path)
                timings["video_thumbnail_seconds"] = self.elapsed(thumb_started)

                if not source_path:
                    return {
                        "media_id": media_id,
                        "image": None,
                        "error": None,
                        "timings": timings,
                        "cache_hit": False
                    }

            read_started = time.perf_counter()
            with open(source_path, "rb") as handle:
                data = handle.read()
            timings["file_read_seconds"] = self.elapsed(read_started)

            decode_started = time.perf_counter()
            with Image.open(BytesIO(data)) as loaded:
                loaded.load()
                timings["image_decode_seconds"] = self.elapsed(decode_started)

                exif_started = time.perf_counter()
                image = ImageOps.exif_transpose(loaded)
                timings["exif_transpose_seconds"] = self.elapsed(exif_started)

                convert_started = time.perf_counter()
                image = ImageLoader._convert_mode(image)
                timings["mode_convert_seconds"] = self.elapsed(convert_started)

                resize_started = time.perf_counter()
                image = image.copy()
                image.thumbnail(
                    ImageDimensions.fit_size(
                        image.size,
                        (self.max_dimension, self.max_dimension)
                    ),
                    Image.Resampling.LANCZOS
                )
                timings["preview_resize_seconds"] = self.elapsed(resize_started)

            timings["total_preview_load_seconds"] = self.elapsed(started)
            return {
                "media_id": media_id,
                "image": image,
                "error": None,
                "timings": timings,
                "cache_hit": False
            }

        except Exception as ex:
            timings["total_preview_load_seconds"] = self.elapsed(started)
            return {
                "media_id": media_id,
                "image": None,
                "error": ex,
                "timings": timings,
                "cache_hit": False
            }

    ############################################################

    def cache_key(self, media_id, path, is_video=False):

        try:
            stat = os.stat(path)
            stamp = (
                int(stat.st_mtime_ns),
                int(stat.st_size)
            )
        except Exception:
            stamp = (0, 0)

        return (
            int(media_id or 0),
            str(path or ""),
            bool(is_video),
            stamp
        )

    ############################################################

    def evict(self):

        while len(self.items) > self.max_items:
            self.items.popitem(last=False)

    ############################################################

    def size(self):

        return len(self.items)

    ############################################################

    def elapsed(self, started):

        return round(time.perf_counter() - started, 4)
