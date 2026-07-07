from pathlib import Path

from media.hash_manager import HashManager


class MediaScanner:

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

    def scan_folder(self, folder):

        folder = Path(folder)

        if not folder.exists():
            return

        for file in folder.rglob("*"):

            if not file.is_file():
                continue

            suffix = file.suffix.lower()

            if (
                suffix not in self.IMAGE_EXTENSIONS and
                suffix not in self.VIDEO_EXTENSIONS
            ):
                continue

            try:

                yield {

                    "path": str(file),

                    "filename": file.name,

                    "extension": suffix,

                    "type": (
                        "image"
                        if suffix in self.IMAGE_EXTENSIONS
                        else "video"
                    ),

                    "size": file.stat().st_size,

                    "sha256": HashManager.sha256(file)

                }

            except Exception as ex:

                print(f"Skipped {file}: {ex}")