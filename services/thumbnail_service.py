from queue import Queue
import threading

from PIL import Image

from media.thumbnail_cache import ThumbnailCache
from services.logging_service import LoggingService


logger = LoggingService.get_logger("gallery")


class ThumbnailService:

    def __init__(self, max_workers=2, thumbnail_cache=None):

        self.cache = thumbnail_cache or ThumbnailCache()
        self._queue = Queue()
        self._shutdown = threading.Event()
        self._lock = threading.Lock()
        self._active = {}
        self._workers = []

        for index in range(max_workers):

            worker = threading.Thread(
                target=self._worker_loop,
                name=f"ThumbnailWorker-{index + 1}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)

    ########################################################

    def load_thumbnail(self, media_path, callback):

        with self._lock:

            callbacks = self._active.get(media_path)

            if callbacks is not None:
                callbacks.append(callback)
                return

            self._active[media_path] = [callback]

        self._queue.put(
            media_path
        )

    ########################################################

    def _worker_loop(self):

        while not self._shutdown.is_set():

            media_path = self._queue.get()

            if media_path is None:
                self._queue.task_done()
                break

            try:
                self._load(media_path)
            finally:
                self._queue.task_done()

    ########################################################

    def _load(self, media_path):

        thumbnail = None
        image = None

        try:
            thumbnail = self.cache.get_thumbnail(media_path)

            if thumbnail is not None:
                with Image.open(thumbnail) as loaded:
                    image = loaded.copy()

        except Exception as ex:
            logger.error(
                "Thumbnail load failed path=%s",
                media_path,
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )

        with self._lock:
            callbacks = self._active.pop(
                media_path,
                []
            )

        for callback in callbacks:

            try:
                callback(
                    media_path,
                    image
                )
            except Exception as ex:
                logger.error(
                    "Thumbnail callback failed path=%s",
                    media_path,
                    exc_info=(
                        type(ex),
                        ex,
                        ex.__traceback__
                    )
                )

    ########################################################

    def shutdown(self):

        self._shutdown.set()

        for _ in self._workers:
            self._queue.put(None)
