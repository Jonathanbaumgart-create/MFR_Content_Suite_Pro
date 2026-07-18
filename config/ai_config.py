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
            "vision_diagnostics_timeout": 120,
            "analysis_max_dimension": 1536,
            "analysis_retry_max_dimension": 1024,
            "analysis_max_payload_bytes": 12000000,
            "supports_images": True,
            "supports_video_frames": True,
            "supports_multi_image_prompt": False,
            "recommended_frame_count": 3,
            "production_approved": True,
            "cpu_safe": False,
            "gpu_dependent": True
        },
        "mock": {
            "model": "mock",
            "supports_images": True,
            "supports_video_frames": False,
            "supports_multi_image_prompt": False,
            "recommended_frame_count": 0,
            "production_approved": False,
            "cpu_safe": True,
            "gpu_dependent": False
        }
    }
}
