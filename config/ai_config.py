AI_PROVIDER = "mock"


AI_CONFIG = {
    # Switch AI_PROVIDER between "mock" and "ollama".
    # "mock" is for development/testing only. It does not inspect images and
    # returns the same labeled test data for every photo.
    # "ollama" is required for real image analysis. Switch back to "ollama"
    # after the local qwen2.5vl model is stable in Ollama.
    "default_provider": AI_PROVIDER,
    "retry_attempts": 2,
    "retry_delay_seconds": 2,
    "providers": {
        "ollama": {
            "url": "http://localhost:11434/api/generate",
            "model": "qwen2.5vl:7b",
            "timeout": 300
        },
        "mock": {
            "model": "mock"
        }
    }
}
