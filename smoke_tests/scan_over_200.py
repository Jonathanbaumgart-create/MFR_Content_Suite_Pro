from pathlib import Path
from tempfile import TemporaryDirectory
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.scan_service import ScanService


class FakeDatabase:

    def __init__(self):

        self.paths = set()

    def add_media(self, media):

        path = media["path"]

        if path in self.paths:
            return False

        self.paths.add(path)

        return True


def main():

    with TemporaryDirectory() as folder:

        root = Path(folder)

        for index in range(250):

            image = root / f"image_{index:03d}.jpg"
            image.write_bytes(f"image-{index}".encode("utf-8"))

        service = ScanService(
            database=FakeDatabase()
        )

        stats = service.scan(str(root))

        assert stats["total"] == 250, stats
        assert stats["processed"] == 250, stats
        assert stats["inserted"] == 250, stats
        assert stats["duplicates"] == 0, stats
        assert stats["failed"] == 0, stats
        assert stats["skipped"] == 0, stats

    print("scan_over_200 smoke passed")


if __name__ == "__main__":
    main()
