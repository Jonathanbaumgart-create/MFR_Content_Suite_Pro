WRITING_PROVIDER = "ollama"


WRITING_CONFIG = {
    # Writing providers are separate from Vision providers.
    # "ollama" uses local llama3.1:8b text generation when Ollama is running
    # and the model is available.
    # "deterministic" uses local templates only and never calls Ollama.
    # If Ollama writing fails or is unavailable, the app falls back to the
    # deterministic provider automatically.
    "default_provider": WRITING_PROVIDER,
    "fallback_provider": "deterministic",
    "providers": {
        "ollama": {
            "url": "http://localhost:11434/api/generate",
            "tags_url": "http://localhost:11434/api/tags",
            "model": "llama3.1:8b",
            "timeout": 60,
            "availability_timeout": 1
        },
        "deterministic": {
            "model": "deterministic-template"
        }
    }
}
