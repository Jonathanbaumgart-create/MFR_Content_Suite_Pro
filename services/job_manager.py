import threading
import traceback
from collections import deque
from concurrent.futures import Future

from services.logging_service import LoggingService


logger = LoggingService.get_logger("application")


class JobManager:
    """
    Executes long-running jobs on a dedicated background worker.

    This class is intentionally generic so it can be reused by every
    future AI subsystem (Vision, LLM, Semantic Search, Recommendations,
    Learning Engine, etc.).

    UI code should never perform heavy work directly.
    """

    def __init__(self):
        self._queue = deque()
        self._condition = threading.Condition()
        self._shutdown = threading.Event()
        self._paused = False
        self._lock = threading.Lock()
        self._queued = 0
        self._running = 0
        self._completed = 0
        self._failed = 0
        self._canceled = 0

        self._worker = threading.Thread(
            target=self._worker_loop,
            name="AIJobManager",
            daemon=True,
        )
        self._worker.start()

    # ---------------------------------------------------------

    def submit(self, func, *args, callback=None, error_callback=None, **kwargs):
        """
        Queue a callable for background execution.

        Returns:
            concurrent.futures.Future
        """

        future = Future()

        with self._lock:
            self._queued += 1

        with self._condition:
            self._queue.append(
                (
                    func,
                    args,
                    kwargs,
                    future,
                    callback,
                    error_callback,
                )
            )
            self._condition.notify()

        return future

    # ---------------------------------------------------------

    def pause(self):

        with self._condition:
            self._paused = True

    # ---------------------------------------------------------

    def resume(self):

        with self._condition:
            self._paused = False
            self._condition.notify_all()

    # ---------------------------------------------------------

    def cancel_queued(self):

        with self._condition:
            items = list(self._queue)
            self._queue.clear()

        canceled = 0

        for item in items:

            future = item[3]

            if future.cancel():
                canceled += 1

        with self._lock:
            self._queued = max(0, self._queued - canceled)
            self._canceled += canceled

        return canceled

    # ---------------------------------------------------------

    def clear_completed(self):

        with self._lock:
            self._completed = 0
            self._failed = 0
            self._canceled = 0

    # ---------------------------------------------------------

    def shutdown(self):
        self._shutdown.set()

        with self._condition:
            self._condition.notify_all()

    # ---------------------------------------------------------

    def progress(self):

        with self._lock:
            return {
                "queued": self._queued,
                "running": self._running,
                "completed": self._completed,
                "failed": self._failed,
                "canceled": self._canceled,
                "paused": self._paused
            }

    # ---------------------------------------------------------

    def wait_if_paused(self):

        with self._condition:

            while self._paused and not self._shutdown.is_set():
                self._condition.wait()

    # ---------------------------------------------------------

    def _worker_loop(self):

        while not self._shutdown.is_set():

            with self._condition:

                while (
                    not self._shutdown.is_set() and
                    (self._paused or not self._queue)
                ):
                    self._condition.wait()

                if self._shutdown.is_set():
                    break

                item = self._queue.popleft()

            (
                func,
                args,
                kwargs,
                future,
                callback,
                error_callback,
            ) = item

            if future.cancelled():
                continue

            with self._lock:
                self._queued = max(0, self._queued - 1)
                self._running += 1

            try:

                result = func(*args, **kwargs)

                future.set_result(result)

                with self._lock:
                    self._completed += 1
                    self._running = max(0, self._running - 1)

                if callback:
                    callback(result)

            except Exception as exc:

                future.set_exception(exc)

                with self._lock:
                    self._failed += 1
                    self._running = max(0, self._running - 1)

                if error_callback:
                    error_callback(exc)
                else:
                    logger.error(
                        "Background job failed",
                        exc_info=(
                            type(exc),
                            exc,
                            exc.__traceback__
                        )
                    )
                    traceback.print_exc()
