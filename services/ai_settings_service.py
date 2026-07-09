import json
from copy import deepcopy
from pathlib import Path

from config.ai_config import AI_CONFIG
from config.writing_config import WRITING_CONFIG
from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class AISettingsService:

    SETTINGS_PATH = Path("config") / "local_ai_settings.json"

    def __init__(self, base_config=None, settings_path=None):

        self.base_config = base_config or AI_CONFIG
        self.settings_path = Path(settings_path or self.SETTINGS_PATH)

    ############################################################

    def effective_config(self):

        return self.effective_vision_config()

    ############################################################

    def effective_vision_config(self):

        config = deepcopy(self.base_config)
        local = self.load()

        provider = local.get("vision_provider") or local.get("provider")
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

    def effective_writing_config(self, base_config=None):

        config = deepcopy(base_config or WRITING_CONFIG)
        local = self.load()

        provider = local.get("writing_provider")
        model = local.get("writing_model")

        if provider in config.get("providers", {}):
            config["default_provider"] = provider

        provider_settings = config.get("providers", {}).get(
            config.get("default_provider", "deterministic"),
            {}
        )

        if model:
            provider_settings["model"] = model

        return config

    ############################################################

    def load(self):

        if not self.settings_path.exists():
            return {}

        try:
            settings = json.loads(
                self.settings_path.read_text(encoding="utf-8")
            )
            migrated = self._migrate(settings)

            if migrated != settings:
                self._write(migrated)

            return migrated

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

        return self.save_vision(
            provider=provider,
            vision_model=vision_model
        )

    ############################################################

    def save_vision(self, provider=None, vision_model=None):

        config = self.effective_config()
        provider = provider or config.get("default_provider", "mock")
        providers = config.get("providers", {})

        if provider not in providers:
            raise ValueError(f"Unknown AI provider: {provider}")

        settings = self.load()
        settings["provider"] = provider
        settings["vision_provider"] = provider

        if vision_model is not None:
            settings["vision_model"] = self._safe_model(
                "vision",
                provider,
                vision_model.strip()
            )

        self._write(settings)

        logger.info(
            "Saved AI provider settings provider=%s model=%s",
            provider,
            settings.get("vision_model", "")
        )

        return self.effective_config()

    ############################################################

    def save_writing(self, provider=None, writing_model=None, base_config=None):

        config = self.effective_writing_config(base_config)
        provider = provider or config.get("default_provider", "deterministic")
        providers = config.get("providers", {})

        if provider not in providers:
            raise ValueError(f"Unknown writing provider: {provider}")

        settings = self.load()
        settings["writing_provider"] = provider

        if writing_model is not None:
            settings["writing_model"] = self._safe_model(
                "writing",
                provider,
                writing_model.strip()
            )

        self._write(settings)

        logger.info(
            "Saved writing provider settings provider=%s model=%s",
            provider,
            settings.get("writing_model", "")
        )

        return self.effective_writing_config(base_config)

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

    ############################################################

    def writing_provider(self, base_config=None):

        return self.effective_writing_config(base_config).get(
            "default_provider",
            "deterministic"
        )

    ############################################################

    def writing_model(self, base_config=None):

        config = self.effective_writing_config(base_config)
        provider = config.get("default_provider", "deterministic")

        return config.get("providers", {}).get(
            provider,
            {}
        ).get("model", "")

    ############################################################

    def _migrate(self, settings):

        migrated = dict(settings or {})
        provider = migrated.get("vision_provider") or migrated.get("provider")

        if provider in self.base_config.get("providers", {}):
            migrated["vision_provider"] = provider
            migrated["provider"] = provider

        provider = migrated.get("vision_provider")

        if provider:
            migrated["vision_model"] = self._safe_model(
                "vision",
                provider,
                migrated.get("vision_model", "")
            )

        writing_provider = migrated.get("writing_provider")

        if writing_provider:
            migrated["writing_model"] = self._safe_model(
                "writing",
                writing_provider,
                migrated.get("writing_model", "")
            )

        return migrated

    ############################################################

    def _safe_model(self, model_type, provider, value):

        value = str(value or "").strip()

        if model_type == "writing":
            config = WRITING_CONFIG
            default_provider = config.get("default_provider", "deterministic")
        else:
            config = self.base_config
            default_provider = config.get("default_provider", "mock")

        provider = provider or default_provider
        providers = config.get("providers", {})
        provider_names = set(providers.keys())
        provider_labels = {
            name.title()
            for name in provider_names
        }
        default_model = providers.get(provider, {}).get("model", "")

        if not value:
            return default_model

        if value.lower() in provider_names or value in provider_labels:
            return default_model

        return value

    ############################################################

    def _write(self, settings):

        self.settings_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        self.settings_path.write_text(
            json.dumps(settings, indent=2),
            encoding="utf-8"
        )
