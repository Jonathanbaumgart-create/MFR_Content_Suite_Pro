AI_PROVIDER = "mock"


AI_CONFIG = {
    # Switch AI_PROVIDER between "mock" and "ollama".
    # "mock" is for development/testing only. It does not inspect images and
    # returns the same labeled test data for every photo.
    # "ollama" is required for real image analysis. Switch back to "ollama"
    # after the local vision model is stable in Ollama.
    #
    # The app can persist a local provider/model choice in
    # config/local_ai_settings.json from the AI Dashboard. This file is
    # intentionally local and should not be used to modify Windows or Ollama
    # environment settings permanently.
    "default_provider": AI_PROVIDER,
    "retry_attempts": 2,
    "retry_delay_seconds": 2,
    "batch_size": 200,
    "worker_count": 1,
    "pause_between_batches": 0,
    "diagnostics": {
        "text_model": "llama3.1:8b"
    },
    "providers": {
        "ollama": {
            "url": "http://localhost:11434/api/generate",
            "tags_url": "http://localhost:11434/api/tags",
            "model": "qwen2.5vl:7b",
            "text_model": "llama3.1:8b",
            "timeout": 300,
            "diagnostics_timeout": 5,
            "vision_diagnostics_timeout": 120
        },
        "mock": {
            "model": "mock"
        }
    }
}
