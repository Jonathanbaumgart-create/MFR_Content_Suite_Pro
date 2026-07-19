AI_TASK_ROUTING = {
    "metadata_indexing": {
        "provider": "local",
        "model": "deterministic-filesystem-v1",
        "uses_vision": False
    },
    "fast_candidate_screening": {
        "provider": "configurable_vision",
        "model": "configured_lightweight_vision",
        "uses_vision": True,
        "max_candidates": 5
    },
    "deep_finalist_analysis": {
        "provider": "ollama",
        "model": "qwen2.5vl:7b",
        "uses_vision": True,
        "explicit_opt_in": True
    },
    "helmet_camera_technical": {
        "provider": "local",
        "model": "opencv-technical-pass-v1",
        "uses_vision": False
    },
    "caption_enhancement": {
        "provider": "writing_provider",
        "model": "llama3.1:8b",
        "uses_vision": False
    }
}
