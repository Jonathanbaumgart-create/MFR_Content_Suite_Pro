import queue
import threading
import traceback
from concurrent.futures import Future


class JobManager:
    """
    Executes long-running jobs on a dedicated background worker.

    This class is intentionally generic so it can be reused by every
    future AI subsystem (Vision, LLM, Semantic Search, Recommendations,
    Learning Engine, etc.).

    UI code should never perform heavy work directly.
    """

    def __init__(self):
        self._queue = queue.Queue()
        self._shutdown = threading.Event()

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

        self._queue.put(
            (
                func,
                args,
                kwargs,
                future,
                callback,
                error_callback,
            )
        )

        return future

    # ---------------------------------------------------------

    def shutdown(self):
        self._shutdown.set()
        self._queue.put(None)

    # ---------------------------------------------------------

    def _worker_loop(self):

        while not self._shutdown.is_set():

            item = self._queue.get()

            if item is None:
                break

            (
                func,
                args,
                kwargs,
                future,
                callback,
                error_callback,
            ) = item

            try:

                result = func(*args, **kwargs)

                future.set_result(result)

                if callback:
                    callback(result)

            except Exception as exc:

                future.set_exception(exc)

                if error_callback:
                    error_callback(exc)
                else:
                    traceback.print_exc()

            finally:
                self._queue.task_done()