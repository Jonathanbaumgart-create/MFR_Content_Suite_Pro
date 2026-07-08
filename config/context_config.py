CONTEXT_CONFIG = {
    # Lower priority numbers run first. Providers can be disabled here
    # without changing GUI or Communications Director code.
    "providers": {
        "calendar": {
            "enabled": True,
            "priority": 30
        },
        "season": {
            "enabled": True,
            "priority": 10
        },
        "campaign": {
            "enabled": True,
            "priority": 20
        }
    }
}
