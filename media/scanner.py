from pathlib import Path
import os

from media.hash_manager import HashManager
from services.logging_service import LoggingService


logger = LoggingService.get_logger("application")
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4


class MediaScanner:

    def __init__(self):

        self.skipped_count = 0
        self.skipped_reasons = {}
        self.skipped_categories = self._empty_skip_categories()
        self.unsupported_extensions = {}

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

    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".wmv",
        ".m4v"
    }

    def count_media(self, folder):

        folder = Path(folder)

        count = 0

        for file in folder.rglob("*"):

            if not file.is_file():
                continue

            suffix = file.suffix.lower()

            if (
                suffix in self.IMAGE_EXTENSIONS or
                suffix in self.VIDEO_EXTENSIONS
            ):
                count += 1

        return count

    ###########################################################

    def count_files(self, folder):

        folder = Path(folder)

        count = 0

        for file in folder.rglob("*"):

            try:

                if file.is_file():
                    count += 1

            except Exception as ex:

                self._record_skip(
                    file,
                    str(ex)
                )

        return count

    ###########################################################

    def scan_folder(self, folder, skip_paths=None):

        folder = Path(folder)
        self.skipped_count = 0
        self.skipped_reasons = {}
        self.skipped_categories = self._empty_skip_categories()
        self.unsupported_extensions = {}
        skip_paths = skip_paths or set()

        if not folder.exists():
            self._record_skip(
                folder,
                "folder does not exist",
                "other"
            )
            return

        for file in folder.rglob("*"):

            try:

                if not file.is_file():
                    continue

            except PermissionError as ex:

                self._record_skip(
                    file,
                    str(ex),
                    "permission_denied"
                )
                continue

            except Exception as ex:

                self._record_skip(
                    file,
                    str(ex),
                    "unreadable"
                )
                continue

            suffix = file.suffix.lower()
            self._record_hidden_system(file)

            if (
                suffix not in self.IMAGE_EXTENSIONS and
                suffix not in self.VIDEO_EXTENSIONS
            ):
                self._record_skip(
                    file,
                    f"unsupported extension: {suffix or '<none>'}",
                    "unsupported",
                    extension=suffix or "<none>"
                )
                continue

            try:

                size = file.stat().st_size

                if size == 0:
                    self._record_skip(
                        file,
                        "zero-byte file",
                        "zero_byte"
                    )
                    continue

                if str(file) in skip_paths:

                    yield {

                        "path": str(file),

                        "filename": file.name,

                        "extension": suffix,

                        "type": (
                            "image"
                            if suffix in self.IMAGE_EXTENSIONS
                            else "video"
                        ),

                        "size": size,

                        "sha256": None,

                        "known_duplicate_path": True

                    }

                    continue

                yield {

                    "path": str(file),

                    "filename": file.name,

                    "extension": suffix,

                    "type": (
                        "image"
                        if suffix in self.IMAGE_EXTENSIONS
                        else "video"
                    ),

                    "size": size,

                    "sha256": HashManager.sha256(file)

                }

            except Exception as ex:

                category = self._category_from_exception(ex)

                self._record_skip(
                    file,
                    str(ex),
                    category
                )

    ###########################################################

    def _record_skip(
        self,
        path,
        reason,
        category="other",
        extension=None
    ):

        self.skipped_count += 1
        self.skipped_reasons[reason] = (
            self.skipped_reasons.get(reason, 0) + 1
        )
        self.skipped_categories[category] = (
            self.skipped_categories.get(category, 0) + 1
        )

        if extension is not None:
            self.unsupported_extensions[extension] = (
                self.unsupported_extensions.get(extension, 0) + 1
            )

        logger.info(
            "Skipped media path=%s category=%s reason=%s",
            path,
            category,
            reason
        )

    ###########################################################

    def _record_hidden_system(self, path):

        try:
            attributes = getattr(
                os.stat(path),
                "st_file_attributes",
                0
            )
        except Exception:
            return

        hidden = bool(attributes & FILE_ATTRIBUTE_HIDDEN)
        system = bool(attributes & FILE_ATTRIBUTE_SYSTEM)

        if hidden or system:
            self.skipped_categories["hidden_system"] += 1

    ###########################################################

    def _category_from_exception(self, error):

        if isinstance(error, PermissionError):
            return "permission_denied"

        text = str(error).lower()

        if "permission" in text or "access is denied" in text:
            return "permission_denied"

        if "cannot identify image" in text or "corrupt" in text:
            return "corrupt"

        if "read" in text:
            return "unreadable"

        return "other"

    ###########################################################

    def _empty_skip_categories(self):

        return {
            "unsupported": 0,
            "unreadable": 0,
            "permission_denied": 0,
            "corrupt": 0,
            "zero_byte": 0,
            "hidden_system": 0,
            "other": 0
        }
