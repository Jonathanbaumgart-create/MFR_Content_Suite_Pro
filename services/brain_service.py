import threading
import time

from concurrent.futures import Future

from config.ai_config import AI_CONFIG
from core.app_context import context
from services.ai_service import AIService
from services.logging_service import LoggingService
from services.media_intelligence_service import MediaIntelligenceService
from services.vision_service import VisionService


logger = LoggingService.get_logger("ai")
intelligence_logger = LoggingService.get_logger("intelligence")


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
        self.config = config or AI_CONFIG

    ############################################################

    def get_analysis(self, media_id):

        return self.db.get_ai_analysis(media_id)

    ############################################################

    def get_intelligence(self, media_id):

        return self.db.get_media_intelligence(media_id)

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

    def dashboard_metrics(self):

        progress = self.queue_progress()
        metrics = self.db.ai_metrics()

        metrics.update(progress)
        metrics["provider"] = self.vision.provider_key()
        metrics["provider_model"] = self.vision.model_name()

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

        future = self.jobs.submit(
            self._analyze_and_save,
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

        media_items = [
            item
            for item in media_items
            if item[3] == "image"
        ]

        self._bulk_cancel.clear()

        future = self.jobs.submit(
            self._analyze_media_batch,
            media_items,
            force,
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

        future = self.jobs.submit(
            self._analyze_folder_batch,
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

        future = self.jobs.submit(
            self._analyze_library_batch,
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

    def _analyze_and_save(self, media_id, image_path):

        started = time.perf_counter()

        try:

            analysis, retry_count = self._analyze_with_retries(image_path)
            analysis["analysis_duration"] = time.perf_counter() - started
            analysis["provider"] = self.vision.provider_key()
            analysis["retry_count"] = retry_count
            analysis["failure_reason"] = ""

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

            self.db.save_ai_failure(
                media_id,
                {
                    "analysis_duration": duration,
                    "provider": self.vision.provider_key(),
                    "retry_count": self.config.get("retry_attempts", 2),
                    "failure_reason": str(error),
                    "model": self.vision.model_name()
                }
            )

            raise

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
