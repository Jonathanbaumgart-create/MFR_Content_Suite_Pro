from media.scanner import MediaScanner
from core.app_context import context
import traceback


class ScanService:

    def __init__(self):
        self.scanner = MediaScanner()

    def scan(self, folder, progress_callback=None):

        total = self.scanner.count_media(folder)
        current = 0

        print(f"Found {total} media files.")

        for item in self.scanner.scan_folder(folder):

            try:

                context.database.add_media(item)

                current += 1

                if current % 25 == 0:
                    print(f"Indexed {current}/{total}")

                if progress_callback:
                    progress_callback(current, total)

            except Exception as ex:

                print("\n==============================")
                print("ERROR INSERTING FILE")
                print(item["path"])
                traceback.print_exc()
                print("==============================\n")

        print(f"Finished. Indexed {current} files.")

        return current