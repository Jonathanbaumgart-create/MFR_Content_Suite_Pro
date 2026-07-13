import threading
import time

from concurrent.futures import Future

from config.ai_config import AI_CONFIG
from core.app_context import context
from models.analysis_queue import (
    AnalysisFailureCategory,
    AnalysisQueueState,
    AnalysisSessionStatus
)
from services.ai_service import AIService
from services.analysis_quality_service import AnalysisQualityService
from services.logging_service import LoggingService
from services.media_intelligence_service import MediaIntelligenceService
from services.time_service import TimeService
from services.vision_service import VisionProviderError, VisionService
from services.human_feedback_service import HumanFeedbackService
from services.video_metadata_service import VideoMetadataService
from services.media_priority_service import MediaPriorityService


logger = LoggingService.get_logger("ai")
intelligence_logger = LoggingService.get_logger("intelligence")


class VisionParseError(RuntimeError):

    def __init__(self, analysis):

        self.analysis = analysis
        status = analysis.get("parse_status", "invalid_response")
        super().__init__(f"Vision provider returned {status}")


class BulkAnalysisHandle:

    def __init__(self, future, count):

        self.future = future
        self.count = count

    def __len__(self):

        return self.count


class BrainService:

    _active_jobs = {}
    _active_jobs_lock = threading.Lock()
    _bulk_cancel = threading.Event()
    _active_session_id = None
    BULK_BATCH_SIZE = 200

    def __init__(
        self,
        database=None,
        job_manager=None,
        ai_service=None,
        vision_service=None,
        intelligence_service=None,
        config=None
    ):

        self.db = database or context.database
        self.jobs = job_manager or context.job_manager
        self.ai = ai_service or AIService()
        self.vision = vision_service or VisionService()
        self.intelligence = (
            intelligence_service or
            MediaIntelligenceService(self.db)
        )
        self.feedback = HumanFeedbackService(
            database=self.db
        )
        self.video = VideoMetadataService()
        self.priority = MediaPriorityService(database=self.db)
        self.quality = AnalysisQualityService()
        self.config = config or AI_CONFIG

    ############################################################

    def get_analysis(self, media_id):

        return self.db.get_ai_analysis(media_id)

    ############################################################

    def get_intelligence(self, media_id):

        return self.feedback.effective_media_intelligence_row(media_id)

    ############################################################

    def get_fire_service_intelligence(self, media_id):

        return self.feedback.effective_media_intelligence(
            media_id
        ).get("fire_service_intelligence")

    ############################################################

    def get_effective_intelligence(self, media_id):

        return self.feedback.effective_media_intelligence(media_id)

    ############################################################

    def is_mock_provider(self):

        return self.vision.provider_key() == "mock"

    ############################################################

    def available_providers(self):

        return self.vision.available_providers()

    ############################################################

    def switch_provider(self, provider_key, model=None):

        return self.vision.switch_provider(
            provider_key,
            model=model
        )

    ############################################################

    def provider_bulk_warning(self):

        if self.is_mock_provider():
            return (
                "Mock provider active - test data only.\n\n"
                "Bulk analysis will save the same test analysis for each "
                "photo that does not already have real analysis."
            )

        failure = self.db.last_provider_failure()

        if not failure:
            return ""

        if failure.get("provider") != self.vision.provider_key():
            return ""

        if failure.get("model") and failure.get("model") != self.vision.model_name():
            return ""

        return (
            "The active real provider has a recent recorded failure.\n\n"
            f"Provider: {failure.get('provider', '')}\n"
            f"Model: {failure.get('model', '')}\n"
            f"Last error: {failure.get('failure_reason', '')}\n\n"
            "Run Provider Diagnostics first, try CPU mode, try a smaller "
            "vision model, or switch to mock for testing."
        )

    ############################################################

    def clear_mock_analysis(self):

        return self.db.clear_mock_analysis()

    ############################################################

    def legacy_mock_analysis_summary(self):

        return self.db.legacy_mock_analysis_summary()

    ############################################################

    def dashboard_metrics(self):

        progress = self.queue_progress()
        metrics = self.db.ai_metrics()
        mock_summary = self.legacy_mock_analysis_summary()
        session = self.db.analysis_session_summary(
            self._active_session_id
        ) or self.db.analysis_session_summary()

        metrics.update(progress)
        metrics["provider"] = self.vision.provider_key()
        metrics["provider_model"] = self.vision.model_name()
        metrics["legacy_mock_analysis"] = mock_summary.get(
            "media_count",
            0
        )
        today = self.newest_media_preview("today")
        metrics.update(
            {
                "new_media_today": today.get("total", 0),
                "new_photos_today": today.get("photos", 0),
                "new_videos_today": today.get("videos", 0),
                "new_unanalyzed_today": today.get("unanalyzed", 0),
                "new_review_required_today": today.get("review_required", 0),
                "new_approved_today": today.get("approved", 0),
                "new_failed_today": today.get("failed", 0)
            }
        )
        metrics.update(
            self._session_metrics(session)
        )
        metrics.update(
            self.db.analysis_review_metrics()
        )

        return metrics

    ############################################################

    def queue_progress(self):

        progress = self.jobs.progress()

        with self._active_jobs_lock:
            progress["active_jobs"] = len(self._active_jobs)

        return progress

    ############################################################

    def pause_queue(self):

        self.jobs.pause()

    ############################################################

    def resume_queue(self):

        self.jobs.resume()

    ############################################################

    def cancel_queued_jobs(self):

        self._bulk_cancel.set()

        canceled = self.jobs.cancel_queued()

        if self._active_session_id:
            canceled += self.db.cancel_analysis_session(
                self._active_session_id,
                "Canceled by user"
            )

        with self._active_jobs_lock:
            for media_id, future in list(self._active_jobs.items()):

                if future.cancelled():
                    self._active_jobs.pop(media_id, None)

        return canceled

    ############################################################

    def clear_completed_jobs(self):

        self.jobs.clear_completed()

    ############################################################

    def build_intelligence_index(
        self,
        limit=None,
        callback=None,
        error_callback=None,
        progress_callback=None
    ):

        return self.jobs.submit(
            self._rebuild_intelligence_index,
            limit,
            progress_callback,
            callback=callback,
            error_callback=error_callback
        )

    ############################################################

    def analyze_photo(
        self,
        media_id,
        image_path,
        force=False,
        callback=None,
        error_callback=None,
        progress_callback=None
    ):

        cached = self.get_analysis(media_id)

        if self.is_mock_provider() and self._is_non_mock_success(cached):
            return self._completed_future(
                cached,
                callback,
                progress_callback
            )

        if not force:
            if cached is not None and not cached.get("failure_reason"):
                return self._completed_future(
                    cached,
                    callback,
                    progress_callback
                )

        with self._active_jobs_lock:
            active = self._active_jobs.get(media_id)

        if active is not None:
            self._attach_callbacks(
                active,
                callback,
                error_callback,
                progress_callback
            )

            self._report_progress(
                progress_callback,
                "queued"
            )

            return active

        worker = (
            self._analyze_video_and_save
            if self.video.is_video(image_path)
            else self._analyze_and_save
        )

        future = self.jobs.submit(
            worker,
            media_id,
            image_path,
            callback=self._job_complete(
                media_id,
                callback,
                progress_callback
            ),
            error_callback=self._job_failed(
                media_id,
                error_callback,
                progress_callback
            )
        )

        with self._active_jobs_lock:
            self._active_jobs[media_id] = future

            if future.done():
                self._active_jobs.pop(media_id, None)

        self._report_progress(
            progress_callback,
            "queued"
        )

        return future

    ############################################################

    def analyze_media_items(
        self,
        media_items,
        force=False,
        progress_callback=None
    ):

        self._bulk_cancel.clear()

        session_id = self._create_analysis_session(
            "selected media",
            len(media_items),
            force=force
        )

        self.db.enqueue_analysis_items(
            session_id,
            media_items,
            self.vision.provider_key(),
            self.vision.model_name(),
            force=force
        )

        future = self.jobs.submit(
            self._run_persistent_analysis_session,
            session_id,
            progress_callback
        )

        self._report_progress(
            progress_callback,
            "bulk queued"
        )

        return BulkAnalysisHandle(
            future,
            len(media_items)
        )

    ############################################################

    def analyze_selected(
        self,
        media_ids,
        force=False,
        progress_callback=None
    ):

        media_items = self.db.get_media_by_ids(media_ids)

        return self.analyze_media_items(
            media_items,
            force=force,
            progress_callback=progress_callback
        )

    ############################################################

    def analyze_folder(
        self,
        folder_path,
        force=False,
        progress_callback=None
    ):

        total = self.db.media_under_path_count(folder_path)
        self._bulk_cancel.clear()

        session_id = self._create_analysis_session(
            f"folder:{folder_path}",
            total,
            force=force
        )

        future = self.jobs.submit(
            self._enqueue_folder_and_run,
            session_id,
            folder_path,
            total,
            force,
            progress_callback
        )

        self._report_progress(
            progress_callback,
            "bulk queued"
        )

        return BulkAnalysisHandle(
            future,
            total
        )

    ############################################################

    def analyze_entire_library(
        self,
        force=False,
        progress_callback=None
    ):

        total = self.db.image_media_count()
        self._bulk_cancel.clear()

        session_id = self._create_analysis_session(
            "entire library",
            total,
            force=force
        )

        future = self.jobs.submit(
            self._enqueue_library_and_run,
            session_id,
            total,
            force,
            progress_callback
        )

        self._report_progress(
            progress_callback,
            "bulk queued"
        )

        return BulkAnalysisHandle(
            future,
            total
        )

    ############################################################

    def _create_analysis_session(self, scope, total, force=False):

        settings = {
            "batch_size": self._batch_size(),
            "worker_count": self.config.get("worker_count", 1),
            "pause_between_batches": self._pause_between_batches(),
            "retry_limit": self.config.get("retry_attempts", 2),
            "timeout": self.vision.provider_settings().get("timeout")
        }
        settings["force"] = bool(force)

        session_id = self.db.create_analysis_session(
            scope,
            self.vision.provider_key(),
            self.vision.model_name(),
            total_items=total,
            settings=settings
        )
        self.__class__._active_session_id = session_id

        logger.info(
            "Created persistent analysis session id=%s scope=%s total=%s provider=%s model=%s",
            session_id,
            scope,
            total,
            self.vision.provider_key(),
            self.vision.model_name()
        )

        return session_id

    ############################################################

    def _enqueue_folder_and_run(
        self,
        session_id,
        folder_path,
        total,
        force,
        progress_callback
    ):

        offset = 0

        while offset < total and not self._bulk_cancel.is_set():

            self.jobs.wait_if_paused()
            media_items = self.db.get_media_under_path_page(
                folder_path,
                self._batch_size(),
                offset
            )

            if not media_items:
                break

            self.db.enqueue_analysis_items(
                session_id,
                media_items,
                self.vision.provider_key(),
                self.vision.model_name(),
                force=force
            )
            offset += len(media_items)

        return self._run_persistent_analysis_session(
            session_id,
            progress_callback
        )

    ############################################################

    def _enqueue_library_and_run(
        self,
        session_id,
        total,
        force,
        progress_callback
    ):

        offset = 0

        while offset < total and not self._bulk_cancel.is_set():

            self.jobs.wait_if_paused()
            media_items = self.db.get_image_media_page(
                self._batch_size(),
                offset
            )

            if not media_items:
                break

            self.db.enqueue_analysis_items(
                session_id,
                media_items,
                self.vision.provider_key(),
                self.vision.model_name(),
                force=force
            )
            offset += len(media_items)

        return self._run_persistent_analysis_session(
            session_id,
            progress_callback
        )

    ############################################################

    def _run_persistent_analysis_session(self, session_id, progress_callback):

        started = time.perf_counter()
        self.__class__._active_session_id = session_id
        self.db.reset_stale_analysis_items(session_id)
        self.db.update_analysis_session(
            session_id,
            status=AnalysisSessionStatus.RUNNING,
            started_at=TimeService.utc_now_iso(),
            provider=self.vision.provider_key(),
            model=self.vision.model_name(),
            cancel_reason=""
        )

        processed = 0

        try:
            while not self._bulk_cancel.is_set():

                self.jobs.wait_if_paused()
                batch = self.db.next_analysis_queue_batch(
                    session_id,
                    self._batch_size()
                )

                if not batch:
                    break

                for item in batch:

                    if self._bulk_cancel.is_set():
                        break

                    self.jobs.wait_if_paused()
                    processed += 1
                    self._run_queue_item(session_id, item)

                    if processed % 5 == 0:
                        self._report_persistent_progress(
                            session_id,
                            progress_callback
                        )

                self._report_persistent_progress(
                    session_id,
                    progress_callback
                )

                pause = self._pause_between_batches()
                if pause:
                    time.sleep(pause)

            if self._bulk_cancel.is_set():
                self.db.cancel_analysis_session(
                    session_id,
                    "Canceled by user"
                )
            else:
                self._finish_session(session_id, started)

            self._report_persistent_progress(
                session_id,
                progress_callback
            )

            return self._bulk_result_from_session(
                self.db.analysis_session_summary(session_id)
            )

        finally:
            if self._active_session_id == session_id:
                self.__class__._active_session_id = None

    ############################################################

    def _run_queue_item(self, session_id, item):

        queue_id = item["queue_id"]
        media_id = item["media_id"]
        path = item["path"]
        filename = item["filename"]
        force = bool(item.get("force"))
        started = time.perf_counter()

        self.db.mark_analysis_queue_analyzing(queue_id)
        self.db.update_analysis_session(
            session_id,
            current_media_id=media_id,
            current_filename=filename
        )

        try:
            cached = self.get_analysis(media_id)

            if self.is_mock_provider() and self._is_non_mock_success(cached):
                self.db.mark_analysis_queue_skipped(
                    queue_id,
                    "Existing real analysis preserved while mock provider is active"
                )
                return

            if not force and cached and not cached.get("failure_reason"):
                self.db.mark_analysis_queue_skipped(
                    queue_id,
                    "Existing successful analysis"
                )
                return

            if item.get("media_type") == "video":
                self._analyze_video_and_save(media_id, path)
            else:
                self._analyze_and_save(media_id, path)
            self.db.mark_analysis_queue_completed(
                queue_id,
                duration=time.perf_counter() - started
            )

        except Exception as error:
            duration = time.perf_counter() - started
            category = self._failure_category(error)
            self.db.mark_analysis_queue_failed(
                queue_id,
                category,
                str(error),
                duration=duration
            )
            logger.error(
                "Persistent analysis item failed session_id=%s media_id=%s category=%s",
                session_id,
                media_id,
                category,
                exc_info=(
                    type(error),
                    error,
                    error.__traceback__
                )
            )

        finally:
            self.db.refresh_analysis_session_counts(session_id)

    ############################################################

    def _finish_session(self, session_id, started_perf):

        summary = self.db.analysis_session_summary(session_id)
        failed = summary.get("failed_count", 0)
        queued = summary.get("queued_count", 0)
        status = AnalysisSessionStatus.COMPLETED

        if failed and not (
            summary.get("completed_count", 0) or
            summary.get("skipped_count", 0)
        ):
            status = AnalysisSessionStatus.FAILED

        if queued:
            status = AnalysisSessionStatus.QUEUED

        elapsed = time.perf_counter() - started_perf
        done = (
            summary.get("completed_count", 0) +
            summary.get("failed_count", 0) +
            summary.get("skipped_count", 0)
        )
        average = elapsed / done if done else 0
        throughput = (done / elapsed) * 3600 if elapsed else 0

        self.db.update_analysis_session(
            session_id,
            status=status,
            finished_at=TimeService.utc_now_iso(),
            elapsed_seconds=elapsed,
            average_seconds_per_item=average,
            throughput_per_hour=throughput,
            estimated_remaining_seconds=0,
            current_media_id=None,
            current_filename=""
        )

    ############################################################

    def _report_persistent_progress(self, session_id, progress_callback):

        if not progress_callback:
            return

        summary = self.db.analysis_session_summary(session_id)
        self._update_session_timing(session_id, summary)
        summary = self.db.analysis_session_summary(session_id)
        progress = self.queue_progress()
        progress.update(self._session_metrics(summary))
        progress["status"] = "bulk running"
        progress["bulk_total"] = progress.get("analysis_total", 0)
        progress["bulk_processed"] = progress.get("analysis_processed", 0)
        progress["bulk_analyzed"] = progress.get("analysis_completed", 0)
        progress["bulk_skipped"] = progress.get("analysis_skipped", 0)
        progress["bulk_failed"] = progress.get("analysis_failed", 0)

        progress_callback(progress)

    ############################################################

    def _update_session_timing(self, session_id, summary):

        started_at = summary.get("started_at")
        total = summary.get("total_items", 0)
        processed = (
            summary.get("completed_count", 0) +
            summary.get("failed_count", 0) +
            summary.get("skipped_count", 0)
        )

        if not started_at or not processed:
            return

        elapsed = max(
            0,
            TimeService.elapsed_seconds_since_utc(started_at)
        )
        average = elapsed / processed if processed else 0
        remaining = max(0, total - processed)
        eta = remaining * average
        throughput = (processed / elapsed) * 3600 if elapsed else 0
        self.db.update_analysis_session(
            session_id,
            elapsed_seconds=elapsed,
            average_seconds_per_item=average,
            throughput_per_hour=throughput,
            estimated_remaining_seconds=eta
        )

    ############################################################

    def _session_metrics(self, session):

        if not session:
            return {
                "analysis_session": "None",
                "analysis_status": "Idle",
                "analysis_total": 0,
                "analysis_completed": 0,
                "analysis_failed": 0,
                "analysis_skipped": 0,
                "analysis_remaining": 0,
                "analysis_current": "",
                "analysis_speed": "0/hr",
                "analysis_eta": "0s"
            }

        total = session.get("total_items", 0)
        completed = session.get("completed_count", 0)
        failed = session.get("failed_count", 0)
        skipped = session.get("skipped_count", 0)
        processed = completed + failed + skipped
        remaining = max(0, total - processed)

        return {
            "analysis_session": session.get("session_id", ""),
            "analysis_status": session.get("status", ""),
            "analysis_total": total,
            "analysis_processed": processed,
            "analysis_completed": completed,
            "analysis_failed": failed,
            "analysis_skipped": skipped,
            "analysis_remaining": remaining,
            "analysis_current": session.get("current_filename", ""),
            "analysis_provider": session.get("provider", ""),
            "analysis_model": session.get("model", ""),
            "analysis_speed": f"{session.get('throughput_per_hour', 0):.1f}/hr",
            "analysis_eta": self._format_seconds(
                session.get("estimated_remaining_seconds", 0)
            )
        }

    ############################################################

    def _bulk_result_from_session(self, session):

        session = session or {}
        completed = session.get("completed_count", 0)
        failed = session.get("failed_count", 0)
        skipped = session.get("skipped_count", 0)
        processed = completed + failed + skipped

        result = dict(session)
        result.update({
            "total": session.get("total_items", 0),
            "processed": processed,
            "analyzed": completed,
            "skipped": skipped,
            "failed": failed,
            "canceled": (
                session.get("status") == AnalysisSessionStatus.CANCELED
            )
        })

        return result

    ############################################################

    def _failure_category(self, error):

        category = getattr(error, "category", "")

        if category:
            return category

        text = str(error).lower()
        name = type(error).__name__.lower()

        if "timeout" in text or "timeout" in name or "timed out" in text:
            return AnalysisFailureCategory.TIMEOUT

        if "cuda" in text or "out of memory" in text or "memory" in text:
            return AnalysisFailureCategory.OUT_OF_MEMORY

        if "connection" in text or "refused" in text or "unreachable" in text:
            return AnalysisFailureCategory.PROVIDER_UNAVAILABLE

        if "unsupported" in text or "format" in text:
            return AnalysisFailureCategory.UNSUPPORTED_FORMAT

        if "corrupt" in text or "truncated" in text:
            return AnalysisFailureCategory.CORRUPT_MEDIA

        if "image" in text and "invalid" in text:
            return AnalysisFailureCategory.INVALID_IMAGE

        return AnalysisFailureCategory.UNEXPECTED

    ############################################################

    def _batch_size(self):

        return max(
            1,
            int(self.config.get("batch_size", self.BULK_BATCH_SIZE))
        )

    ############################################################

    def _provider_request_metadata(self):

        if not hasattr(self.vision, "request_metadata"):
            metadata = {}
        else:
            metadata = self.vision.request_metadata()

        return {
            "request_metadata": metadata.get("request", {}),
            "preprocessing_metadata": metadata.get("preprocessing", {}),
            "provider_attempts": metadata.get("attempts", []),
            "prompt_version": metadata.get("prompt_version", ""),
            "analysis_version": "sprint28_qwen_review_v1"
        }

    ############################################################

    def _pause_between_batches(self):

        return float(self.config.get("pause_between_batches", 0) or 0)

    ############################################################

    def _format_seconds(self, seconds):

        seconds = int(seconds or 0)

        if seconds < 60:
            return f"{seconds}s"

        minutes = seconds // 60

        if minutes < 60:
            return f"{minutes}m"

        hours = minutes // 60
        minutes = minutes % 60

        return f"{hours}h {minutes}m"

    ############################################################

    def resume_previous_analysis(self, session_id=None, progress_callback=None):

        session = (
            self.db.analysis_session_summary(session_id)
            if session_id
            else self.db.latest_incomplete_analysis_session()
        )

        if not session:
            future = Future()
            future.set_result({
                "resumed": False,
                "reason": "No incomplete analysis session found"
            })
            return BulkAnalysisHandle(future, 0)

        self._bulk_cancel.clear()
        self.db.reset_stale_analysis_items(session["session_id"])
        future = self.jobs.submit(
            self._run_persistent_analysis_session,
            session["session_id"],
            progress_callback
        )

        return BulkAnalysisHandle(
            future,
            session.get("total_items", 0)
        )

    ############################################################

    def retry_failed_analysis(self, session_id=None, progress_callback=None):

        retry_count = self.db.retry_failed_analysis_items(session_id)

        if not session_id:
            session = self.db.analysis_session_summary()
            session_id = session.get("session_id") if session else None

        if not session_id:
            future = Future()
            future.set_result({
                "retry_count": retry_count,
                "reason": "No analysis session found"
            })
            return BulkAnalysisHandle(future, retry_count)

        self._bulk_cancel.clear()
        future = self.jobs.submit(
            self._run_persistent_analysis_session,
            session_id,
            progress_callback
        )

        return BulkAnalysisHandle(
            future,
            retry_count
        )

    ############################################################

    def _analyze_and_save(self, media_id, image_path):

        started = time.perf_counter()

        try:

            analysis, retry_count = self._analyze_with_retries(image_path)
            analysis["analysis_duration"] = time.perf_counter() - started
            analysis["provider"] = self.vision.provider_key()
            analysis["retry_count"] = retry_count
            analysis["failure_reason"] = ""
            analysis.update(
                self._provider_request_metadata()
            )

            if analysis.get("parse_status") in (
                "empty_response",
                "invalid_response"
            ):
                raise VisionParseError(analysis)

            analysis.update(
                self.quality.evaluate(analysis)
            )

            self.db.save_ai_analysis(
                media_id,
                analysis
            )

            saved = self.db.get_ai_analysis(media_id)

            self._generate_intelligence(
                media_id,
                saved
            )

            return saved

        except Exception as error:

            duration = time.perf_counter() - started
            parsed = getattr(error, "analysis", {}) or {}
            category = getattr(
                error,
                "category",
                "provider_response_invalid"
            )
            failure_reason = str(error)

            if isinstance(error, VisionProviderError):
                parsed["provider_response_excerpt"] = error.response_excerpt
                parsed["provider_status_code"] = error.status_code
                parsed["request_metadata"] = error.request_metadata
                parsed["provider_attempts"] = error.attempts
                failure_reason = f"{error.category}: {error}"

            self.db.save_ai_failure(
                media_id,
                {
                    "analysis_duration": duration,
                    "provider": self.vision.provider_key(),
                    "retry_count": self.config.get("retry_attempts", 2),
                    "failure_reason": failure_reason,
                    "failure_category": category,
                    "model": self.vision.model_name(),
                    "raw_response": parsed.get("raw_response"),
                    "parse_status": parsed.get("parse_status"),
                    "parse_warnings": parsed.get("parse_warnings"),
                    "confidence": parsed.get("confidence"),
                    "people": parsed.get("people"),
                    "activities": parsed.get("activities"),
                    "setting": parsed.get("setting"),
                    "indoor_outdoor": parsed.get("indoor_outdoor"),
                    "safety_concerns": parsed.get("safety_concerns"),
                    "public_use_risks": parsed.get("public_use_risks"),
                    "structured_field_completeness": parsed.get(
                        "structured_field_completeness"
                    ),
                    "request_metadata": parsed.get("request_metadata"),
                    "preprocessing_metadata": parsed.get(
                        "preprocessing_metadata"
                    ),
                    "provider_attempts": parsed.get("provider_attempts"),
                    "provider_response_excerpt": parsed.get(
                        "provider_response_excerpt"
                    ),
                    "provider_status_code": parsed.get("provider_status_code"),
                    "quality_state": "provider_failed",
                    "trust_state": "failed",
                    "review_status": "failed"
                }
            )

            raise

    ############################################################

    def _analyze_video_and_save(self, media_id, video_path):

        started = time.perf_counter()
        metadata = self.video.inspect(video_path)
        self.db.update_media_video_metadata(
            media_id,
            metadata
        )
        analysis = self.video.video_analysis_from_metadata(
            media_id,
            video_path,
            metadata=metadata
        )
        analysis["analysis_duration"] = time.perf_counter() - started
        self.db.save_ai_analysis(
            media_id,
            analysis
        )
        saved = self.db.get_ai_analysis(media_id)
        self._generate_intelligence(
            media_id,
            saved
        )
        self.db.save_video_intelligence(
            media_id,
            {
                "duration_seconds": metadata.get("duration", 0),
                "analyzed_frame_count": len(
                    (analysis.get("preprocessing_metadata") or {}).get(
                        "keyframe_timestamps",
                        []
                    )
                ),
                "frame_timestamps": (
                    (analysis.get("preprocessing_metadata") or {}).get(
                        "keyframe_timestamps",
                        []
                    )
                ),
                "people_observed": [],
                "apparatus_observed": [],
                "equipment_observed": [],
                "activities_observed": [],
                "settings_observed": [],
                "visible_text": [],
                "uncertain_observations": analysis.get(
                    "uncertain_observations",
                    []
                ),
                "likely_content_category": "requires_review",
                "confidence": analysis.get("confidence", 0),
                "review_state": analysis.get("review_status", ""),
                "provider": analysis.get("provider", ""),
                "model": analysis.get("model", ""),
                "analysis_version": analysis.get("analysis_version", ""),
                "raw_frame_outputs": []
            }
        )

        return saved

    ############################################################

    def analyze_newest_media(
        self,
        preset="today",
        limit=200,
        include_photos=True,
        include_videos=True,
        only_unanalyzed=True,
        include_failed=False,
        force=False,
        progress_callback=None
    ):

        candidates = self.priority.candidates(
            preset=preset,
            limit=limit,
            include_photos=include_photos,
            include_videos=include_videos,
            only_unanalyzed=only_unanalyzed,
            include_failed=include_failed,
            force=force
        )
        self._bulk_cancel.clear()
        session_id = self._create_analysis_session(
            f"newest:{preset}",
            len(candidates),
            force=force
        )
        self.db.enqueue_analysis_items(
            session_id,
            candidates,
            self.vision.provider_key(),
            self.vision.model_name(),
            force=force
        )
        future = self.jobs.submit(
            self._run_persistent_analysis_session,
            session_id,
            progress_callback
        )

        self._report_progress(
            progress_callback,
            "newest media queued"
        )

        return BulkAnalysisHandle(
            future,
            len(candidates)
        )

    ############################################################

    def newest_media_preview(self, preset="today"):

        return self.priority.preview(preset)

    ############################################################

    def _analyze_media_batch(self, media_items, force, progress_callback):

        return self._run_bulk_items(
            media_items,
            len(media_items),
            force,
            progress_callback
        )

    ############################################################

    def _analyze_folder_batch(
        self,
        folder_path,
        total,
        force,
        progress_callback
    ):

        processed = 0
        analyzed = 0
        skipped = 0
        failed = 0
        offset = 0

        while offset < total and not self._bulk_cancel.is_set():

            self.jobs.wait_if_paused()

            media_items = self.db.get_media_under_path_page(
                folder_path,
                self.BULK_BATCH_SIZE,
                offset
            )

            if not media_items:
                break

            result = self._run_bulk_items(
                media_items,
                total,
                force,
                progress_callback,
                processed
            )

            processed = result["processed"]
            analyzed += result["analyzed"]
            skipped += result["skipped"]
            failed += result["failed"]
            offset += len(media_items)

        return {
            "total": total,
            "processed": processed,
            "analyzed": analyzed,
            "skipped": skipped,
            "failed": failed,
            "canceled": self._bulk_cancel.is_set()
        }

    ############################################################

    def _analyze_library_batch(self, total, force, progress_callback):

        processed = 0
        analyzed = 0
        skipped = 0
        failed = 0
        offset = 0

        while offset < total and not self._bulk_cancel.is_set():

            self.jobs.wait_if_paused()

            media_items = self.db.get_image_media_page(
                self.BULK_BATCH_SIZE,
                offset
            )

            if not media_items:
                break

            result = self._run_bulk_items(
                media_items,
                total,
                force,
                progress_callback,
                processed
            )

            processed = result["processed"]
            analyzed += result["analyzed"]
            skipped += result["skipped"]
            failed += result["failed"]
            offset += len(media_items)

        return {
            "total": total,
            "processed": processed,
            "analyzed": analyzed,
            "skipped": skipped,
            "failed": failed,
            "canceled": self._bulk_cancel.is_set()
        }

    ############################################################

    def _run_bulk_items(
        self,
        media_items,
        total,
        force,
        progress_callback,
        processed_offset=0
    ):

        processed = processed_offset
        analyzed = 0
        skipped = 0
        failed = 0

        for media_id, filename, path, media_type in media_items:

            if self._bulk_cancel.is_set():
                break

            self.jobs.wait_if_paused()

            processed += 1

            try:
                cached = self.get_analysis(media_id)

                if (
                    self.is_mock_provider() and
                    self._is_non_mock_success(cached)
                ):
                    skipped += 1
                    continue

                if not force and cached and not cached.get("failure_reason"):
                    skipped += 1
                    continue

                self._analyze_and_save(
                    media_id,
                    path
                )
                analyzed += 1

            except Exception:
                failed += 1

            if processed % 10 == 0:
                self._report_bulk_progress(
                    progress_callback,
                    total,
                    processed,
                    analyzed,
                    skipped,
                    failed
                )

        self._report_bulk_progress(
            progress_callback,
            total,
            processed,
            analyzed,
            skipped,
            failed
        )

        return {
            "total": total,
            "processed": processed,
            "analyzed": analyzed,
            "skipped": skipped,
            "failed": failed,
            "canceled": self._bulk_cancel.is_set()
        }

    ############################################################

    def _report_bulk_progress(
        self,
        progress_callback,
        total,
        processed,
        analyzed,
        skipped,
        failed
    ):

        if not progress_callback:
            return

        progress = self.queue_progress()
        progress["status"] = "bulk running"
        progress["bulk_total"] = total
        progress["bulk_processed"] = processed
        progress["bulk_analyzed"] = analyzed
        progress["bulk_skipped"] = skipped
        progress["bulk_failed"] = failed

        progress_callback(progress)

    ############################################################

    def _generate_intelligence(self, media_id, analysis):

        try:

            self.intelligence.generate_and_save(
                media_id,
                analysis
            )

        except Exception as error:

            intelligence_logger.error(
                "Media intelligence generation failed media_id=%s",
                media_id,
                exc_info=(
                    type(error),
                    error,
                    error.__traceback__
                )
            )

    ############################################################

    def _rebuild_intelligence_index(self, limit=None, progress_callback=None):

        return self.intelligence.rebuild_missing(
            limit=limit,
            progress_callback=progress_callback
        )

    ############################################################

    def _analyze_with_retries(self, image_path):

        retry_limit = self.config.get("retry_attempts", 2)
        attempts = retry_limit + 1
        delay = self.config.get("retry_delay_seconds", 2)
        last_error = None

        for attempt in range(1, attempts + 1):

            try:

                analysis = self.ai.analyze_image(
                    image_path,
                    self.vision
                )

                return analysis, attempt - 1

            except Exception as error:

                last_error = error

                logger.error(
                    "Vision provider failed attempt=%s attempts=%s provider=%s",
                    attempt,
                    attempts,
                    self.vision.provider_key(),
                    exc_info=(
                        type(error),
                        error,
                        error.__traceback__
                    )
                )

                if attempt >= attempts:
                    raise

                time.sleep(delay)

        raise RuntimeError(last_error or "Vision analysis failed")

    ############################################################

    def _is_non_mock_success(self, analysis):

        if not analysis:
            return False

        if analysis.get("failure_reason"):
            return False

        provider = analysis.get("provider", "")
        model = analysis.get("model", "")
        description = analysis.get("description", "")

        if provider == "mock":
            return False

        if model.startswith("mock"):
            return False

        if description.startswith("MOCK TEST ANALYSIS"):
            return False

        return True

    ############################################################

    def _completed_future(
        self,
        result,
        callback=None,
        progress_callback=None
    ):

        future = Future()
        future.set_result(result)

        if callback:
            callback(result)

        self._report_progress(
            progress_callback,
            "cached"
        )

        return future

    ############################################################

    def _attach_callbacks(
        self,
        future,
        callback=None,
        error_callback=None,
        progress_callback=None
    ):

        def done(completed):

            try:
                result = completed.result()

                if callback:
                    callback(result)

                self._report_progress(
                    progress_callback,
                    "completed"
                )

            except Exception as error:

                if error_callback:
                    error_callback(error)

                self._report_progress(
                    progress_callback,
                    "failed"
                )

        future.add_done_callback(done)

    ############################################################

    def _job_complete(
        self,
        media_id,
        callback=None,
        progress_callback=None
    ):

        def complete(result):

            with self._active_jobs_lock:
                self._active_jobs.pop(media_id, None)

            if callback:
                callback(result)

            self._report_progress(
                progress_callback,
                "completed"
            )

        return complete

    ############################################################

    def _job_failed(
        self,
        media_id,
        error_callback=None,
        progress_callback=None
    ):

        def failed(error):

            with self._active_jobs_lock:
                self._active_jobs.pop(media_id, None)

            logger.error(
                "AI analysis job failed media_id=%s",
                media_id,
                exc_info=(
                    type(error),
                    error,
                    error.__traceback__
                )
            )

            if error_callback:
                error_callback(error)

            self._report_progress(
                progress_callback,
                "failed"
            )

        return failed

    ############################################################

    def _report_progress(self, progress_callback, status):

        if not progress_callback:
            return

        progress = self.queue_progress()
        progress["status"] = status

        progress_callback(progress)
