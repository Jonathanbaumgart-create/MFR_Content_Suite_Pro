import json
import logging
from datetime import datetime
from pathlib import Path


class JsonFormatter(logging.Formatter):

    def format(self, record):

        data = {
            "time": datetime.utcnow().isoformat(timespec="seconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(data)


class LoggingService:

    _configured = False

    @classmethod
    def configure(cls):

        if cls._configured:
            return

        Path("logs").mkdir(exist_ok=True)

        for name in (
            "ai",
            "database",
            "gallery",
            "application"
        ):

            logger = logging.getLogger(name)
            logger.setLevel(logging.INFO)
            logger.propagate = False

            handler = logging.FileHandler(
                Path("logs") / f"{name}.log",
                encoding="utf-8"
            )

            handler.setFormatter(JsonFormatter())
            logger.addHandler(handler)

        cls._configured = True

    @classmethod
    def get_logger(cls, name):

        cls.configure()

        return logging.getLogger(name)
