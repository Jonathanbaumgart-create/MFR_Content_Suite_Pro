from core.app_context import context
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("gallery")


class GalleryService:

    def get_media(self):

        logger.info("Loading all gallery media")

        return context.database.get_media()

    ###########################################################

    def get_media_page(self, limit, offset=0, filter_key="all", sort_key="filename_az"):

        logger.info(
            "Loading media page limit=%s offset=%s",
            limit,
            offset
        )

        return context.database.get_media_page(
            limit,
            offset,
            filter_key=filter_key,
            sort_key=sort_key
        )

    ###########################################################

    def media_count(self, filter_key="all"):

        return context.database.media_count(filter_key=filter_key)

    ###########################################################

    def media_count_for_selection(self, filter_key="all", media_type=None):

        return context.database.media_count_for_selection(
            filter_key=filter_key,
            media_type=media_type
        )

    ###########################################################

    def get_media_ids_for_selection(
        self,
        filter_key="all",
        media_type=None,
        limit=10000
    ):

        return context.database.get_media_ids_for_selection(
            filter_key=filter_key,
            media_type=media_type,
            limit=limit
        )

    ###########################################################

    def analysis_selection_preview(
        self,
        media_ids,
        force=False,
        retry_failed=False
    ):

        return context.database.analysis_selection_preview(
            media_ids,
            force=force,
            retry_failed=retry_failed
        )

    ###########################################################

    def analysis_queue_summary(self):

        db = context.database
        session = db.latest_incomplete_analysis_session()
        if not session:
            session = db.analysis_session_summary()

        if not session:
            return {
                "has_session": False,
                "status": "Idle",
                "session_id": "",
                "provider": "",
                "model": "",
                "total": 0,
                "queued": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "remaining": 0,
                "progress_percent": 0,
                "current_filename": "",
                "elapsed": "",
                "eta": "Estimated time unavailable",
                "worker_status": "",
                "worker_stop_reason": "",
                "recoverable": False
            }

        session_id = session.get("session_id")
        counts = db.analysis_queue_counts(session_id)
        queued = (
            self._count(counts, "Waiting") +
            self._count(counts, "Queued") +
            self._count(counts, "Retry Pending")
        )
        running = self._count(counts, "Analyzing")
        completed = self._count(counts, "Completed")
        failed = self._count(counts, "Failed")
        cancelled = self._count(counts, "Canceled", "Cancelled")
        skipped = self._count(counts, "Skipped")
        total = int(session.get("total_items") or sum(counts.values()) or 0)
        remaining = max(0, total - completed - failed - skipped - cancelled)
        progress = int((completed / total) * 100) if total else 0
        elapsed = float(session.get("elapsed_seconds") or 0)
        eta = "Estimated time unavailable"
        estimate = float(session.get("estimated_remaining_seconds") or 0)
        average = float(session.get("average_seconds_per_item") or 0)
        if estimate > 0 and average > 0:
            eta = self._format_duration(estimate)

        return {
            "has_session": True,
            "status": self._readable(session.get("status") or "Idle"),
            "session_id": session_id,
            "provider": session.get("provider", ""),
            "model": session.get("model", ""),
            "total": total,
            "queued": queued,
            "running": running,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "skipped": skipped,
            "remaining": remaining,
            "progress_percent": progress,
            "current_media_id": session.get("current_media_id"),
            "current_filename": session.get("current_filename") or "",
            "created_at": TimeService.format_local(session.get("created_at") or ""),
            "elapsed": self._format_duration(elapsed),
            "eta": eta,
            "worker_status": session.get("worker_status") or "",
            "worker_stop_reason": session.get("worker_stop_reason") or "",
            "resume_count": session.get("resume_count") or 0,
            "recoverable": (
                session.get("status") in ("Recoverable", "Interrupted")
            )
        }

    ###########################################################

    def analysis_media_statuses(self, media_ids):

        return context.database.analysis_media_statuses(media_ids)

    ###########################################################

    def analysis_review_eligible_ids(self, media_ids):

        return context.database.analysis_review_eligible_ids(media_ids)

    ###########################################################

    def _readable(self, value):

        text = str(value or "").replace("_", " ").strip()
        return text[:1].upper() + text[1:] if text else ""

    def _count(self, counts, *names):

        return sum(int(counts.get(name, 0) or 0) for name in names)

    def _format_duration(self, seconds):

        seconds = int(float(seconds or 0))
        if seconds <= 0:
            return "0s"
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m {seconds % 60}s"
        hours = minutes // 60
        return f"{hours}h {minutes % 60}m"

    ###########################################################

    def get_media_by_ids(self, media_ids):

        return context.database.get_media_by_ids(media_ids)

    ###########################################################

    def get_media_under_path(self, folder_path):

        return context.database.get_media_under_path(folder_path)

    ###########################################################

    def get_image_media(self):

        return context.database.get_image_media()
