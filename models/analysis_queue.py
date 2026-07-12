from dataclasses import dataclass


class AnalysisQueueState:

    WAITING = "Waiting"
    QUEUED = "Queued"
    ANALYZING = "Analyzing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    RETRY_PENDING = "Retry Pending"
    CANCELED = "Canceled"

    ACTIVE = (
        WAITING,
        QUEUED,
        ANALYZING,
        RETRY_PENDING
    )

    FINAL = (
        COMPLETED,
        FAILED,
        SKIPPED,
        CANCELED
    )


class AnalysisSessionStatus:

    QUEUED = "Queued"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    CANCELED = "Canceled"
    FAILED = "Failed"


class AnalysisFailureCategory:

    PROVIDER_UNAVAILABLE = "Provider unavailable"
    TIMEOUT = "Timeout"
    INVALID_IMAGE = "Invalid image"
    CORRUPT_MEDIA = "Corrupt media"
    UNSUPPORTED_FORMAT = "Unsupported format"
    OUT_OF_MEMORY = "Out of memory"
    UNEXPECTED = "Unexpected"


@dataclass
class AnalysisSession:

    session_id: int
    status: str
    scope: str
    provider: str
    model: str
    total_items: int = 0


@dataclass
class AnalysisQueueItem:

    queue_id: int
    session_id: int
    media_id: int
    filename: str
    path: str
    state: str
    attempts: int = 0
