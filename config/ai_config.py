AI_CONFIG = {
    "default_provider": "ollama",
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
