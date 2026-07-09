import json
from copy import deepcopy
from pathlib import Path

from config.ai_config import AI_CONFIG
from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class AISettingsService:

    SETTINGS_PATH = Path("config") / "local_ai_settings.json"

    def __init__(self, base_config=None, settings_path=None):

        self.base_config = base_config or AI_CONFIG
        self.settings_path = Path(settings_path or self.SETTINGS_PATH)

    ############################################################

    def effective_config(self):

        config = deepcopy(self.base_config)
        local = self.load()

        provider = local.get("provider")
        model = local.get("vision_model")

        if provider in config.get("providers", {}):
            config["default_provider"] = provider

        provider_settings = config.get("providers", {}).get(
            config.get("default_provider", "mock"),
            {}
        )

        if model and config.get("default_provider") == "ollama":
            provider_settings["model"] = model

        return config

    ############################################################

    def load(self):

        if not self.settings_path.exists():
            return {}

        try:
            return json.loads(
                self.settings_path.read_text(encoding="utf-8")
            )

        except Exception as ex:
            logger.error(
                "Failed to read local AI settings path=%s",
                self.settings_path,
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            return {}

    ############################################################

    def save(self, provider=None, vision_model=None):

        config = self.effective_config()
        provider = provider or config.get("default_provider", "mock")
        providers = config.get("providers", {})

        if provider not in providers:
            raise ValueError(f"Unknown AI provider: {provider}")

        settings = self.load()
        settings["provider"] = provider

        if vision_model is not None:
            settings["vision_model"] = vision_model.strip()

        self.settings_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        self.settings_path.write_text(
            json.dumps(settings, indent=2),
            encoding="utf-8"
        )

        logger.info(
            "Saved AI provider settings provider=%s model=%s",
            provider,
            settings.get("vision_model", "")
        )

        return self.effective_config()

    ############################################################

    def provider(self):

        return self.effective_config().get(
            "default_provider",
            "mock"
        )

    ############################################################

    def vision_model(self):

        config = self.effective_config()
        provider = config.get("default_provider", "mock")

        return config.get("providers", {}).get(
            provider,
            {}
        ).get("model", "")
