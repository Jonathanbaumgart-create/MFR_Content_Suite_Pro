from media.scanner import MediaScanner
from core.app_context import context
from services.logging_service import LoggingService
from datetime import datetime
from pathlib import Path
import json
import time
import traceback


logger = LoggingService.get_logger("application")


class ScanService:

    def __init__(self, scanner=None, database=None):
        self.scanner = scanner or MediaScanner()
        self.db = database or context.database

    def scan(self, folder, progress_callback=None):

        started = time.perf_counter()
        started_at = datetime.now()
        total_files = self.scanner.count_files(folder)
        total = self.scanner.count_media(folder)
        processed = 0
        inserted = 0
        duplicate_path = 0
        duplicate_hash = 0
        failed = 0
        existing_paths, existing_hashes = self._media_identity_sets()

        print(f"Found {total} supported media files.")
        logger.info(
            "Starting media scan folder=%s files=%s supported=%s",
            folder,
            total_files,
            total
        )

        for item in self.scanner.scan_folder(
            folder,
            skip_paths=existing_paths
        ):

            try:

                processed += 1

                if item.get("known_duplicate_path"):

                    duplicate_path += 1
                    logger.info(
                        "Skipped media path=%s reason=duplicate path",
                        item.get("path")
                    )

                elif item.get("sha256") in existing_hashes:

                    duplicate_hash += 1
                    logger.info(
                        "Skipped media path=%s reason=duplicate hash",
                        item.get("path")
                    )

                else:

                    was_inserted = self.db.add_media(item)

                    if was_inserted:
                        inserted += 1
                        existing_paths.add(item.get("path"))
                        existing_hashes.add(item.get("sha256"))
                    else:
                        reason = self._duplicate_reason(
                            item,
                            existing_paths,
                            existing_hashes
                        )

                        if reason == "duplicate path":
                            duplicate_path += 1
                        else:
                            duplicate_hash += 1

                        logger.info(
                            "Skipped media path=%s reason=%s",
                            item.get("path"),
                            reason
                        )

                if processed % 25 == 0:
                    print(f"Indexed {processed}/{total}")

                if progress_callback:
                    progress_callback(processed, total)

            except Exception as ex:

                failed += 1

                print("\n==============================")
                print("ERROR INSERTING FILE")
                print(item["path"])
                traceback.print_exc()
                print("==============================\n")
                logger.error(
                    "Error inserting media path=%s",
                    item.get("path"),
                    exc_info=(
                        type(ex),
                        ex,
                        ex.__traceback__
                    )
                )

        skipped = getattr(self.scanner, "skipped_count", 0)
        skipped_reasons = getattr(self.scanner, "skipped_reasons", {})
        skipped_categories = getattr(
            self.scanner,
            "skipped_categories",
            {}
        )
        unsupported_extensions = getattr(
            self.scanner,
            "unsupported_extensions",
            {}
        )
        duplicates = duplicate_path + duplicate_hash
        elapsed = time.perf_counter() - started

        stats = {
            "total": total_files,
            "supported": total,
            "processed": processed,
            "inserted": inserted,
            "duplicates": duplicates,
            "duplicate_path": duplicate_path,
            "duplicate_hash": duplicate_hash,
            "failed": failed,
            "skipped": skipped,
            "unsupported": skipped_categories.get("unsupported", 0),
            "unsupported_extensions": unsupported_extensions,
            "skipped_categories": skipped_categories,
            "skipped_reasons": skipped_reasons,
            "elapsed_time": elapsed
        }

        report_path = self._save_report(
            folder,
            stats,
            started_at
        )

        stats["report_path"] = str(report_path)

        print(
            f"Finished. Processed {processed} files. "
            f"Inserted {inserted}, duplicates {duplicates}, "
            f"failed {failed}, skipped {skipped}."
        )
        logger.info(
            "Finished media scan stats=%s",
            stats
        )

        return stats

    ############################################################

    def _save_report(self, folder, stats, started_at):

        Path("logs").mkdir(exist_ok=True)

        report_path = Path("logs") / (
            "scan_report_"
            f"{started_at.strftime('%Y%m%d_%H%M%S')}.json"
        )

        report = {
            "folder": folder,
            "started_at": started_at.isoformat(timespec="seconds"),
            "completed_at": datetime.now().isoformat(timespec="seconds"),
            "total_discovered": stats["total"],
            "supported": stats["supported"],
            "inserted": stats["inserted"],
            "duplicate_path": stats["duplicate_path"],
            "duplicate_hash": stats["duplicate_hash"],
            "unsupported": stats["unsupported"],
            "unsupported_extensions": stats["unsupported_extensions"],
            "skipped_by_category": stats["skipped_categories"],
            "skipped_reasons": stats["skipped_reasons"],
            "failed": stats["failed"],
            "elapsed_time": stats["elapsed_time"]
        }

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=2
            )

        logger.info(
            "Saved scan report path=%s",
            report_path
        )

        return report_path

    ############################################################

    def _media_identity_sets(self):

        if hasattr(self.db, "media_identity_sets"):
            return self.db.media_identity_sets()

        return set(), set()

    ############################################################

    def _duplicate_reason(
        self,
        item,
        existing_paths,
        existing_hashes
    ):

        if item.get("path") in existing_paths:
            return "duplicate path"

        if item.get("sha256") in existing_hashes:
            return "duplicate hash"

        existing_path = self.db.get_media_by_path(
            item.get("path")
        )

        if existing_path is not None:
            return "duplicate path"

        existing_hash = self.db.get_media_by_sha256(
            item.get("sha256")
        )

        if existing_hash is not None:
            return "duplicate hash"

        return "duplicate unknown"
