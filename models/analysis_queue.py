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
    RECOVERABLE = "Recoverable"
    INTERRUPTED = "Interrupted"
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
    REQUEST_PAYLOAD_INVALID = "request_payload_invalid"
    IMAGE_ENCODING_FAILED = "image_encoding_failed"
    UNSUPPORTED_IMAGE_MODE = "unsupported_image_mode"
    IMAGE_TOO_LARGE = "image_too_large"
    PROVIDER_HTTP_400 = "provider_http_400"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RESPONSE_INVALID = "provider_response_invalid"
    EMPTY_PROVIDER_RESPONSE = "empty_provider_response"


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
