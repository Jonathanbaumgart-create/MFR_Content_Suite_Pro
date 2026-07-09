from urllib.parse import urlparse

import requests

from services.ai_settings_service import AISettingsService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class ProviderDiagnosticsService:

    SAMPLE_IMAGE_BASE64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNg"
        "YAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )

    def __init__(self, settings_service=None, config=None, http_client=None):

        self.settings_service = settings_service or AISettingsService(
            base_config=config
        )
        self.config = config
        self.http = http_client or requests

    ############################################################

    def run(self):

        config = (
            self.settings_service.effective_config()
            if self.config is None
            else AISettingsService(
                base_config=self.config
            ).effective_config()
        )
        provider = config.get("default_provider", "mock")
        provider_settings = config.get("providers", {}).get(provider, {})

        if provider == "mock":
            return self._mock_result(provider_settings)

        if provider != "ollama":
            return self._result(
                active_provider=provider,
                configured_model=provider_settings.get("model", ""),
                provider_status="Unknown provider",
                recommended_action="Switch to mock or ollama."
            )

        return self._ollama_result(config, provider_settings)

    ############################################################

    def _ollama_result(self, config, settings):

        result = self._result(
            active_provider="ollama",
            configured_model=settings.get("model", ""),
            provider_status="Checking",
            recommended_action=""
        )
        generate_url = settings.get("url", "http://localhost:11434/api/generate")
        tags_url = settings.get("tags_url") or self._tags_url(generate_url)
        timeout = settings.get("diagnostics_timeout", 5)
        available_models = []

        try:
            response = self.http.get(
                tags_url,
                timeout=timeout
            )
            response.raise_for_status()
            result["ollama_reachable"] = True
            available_models = [
                item.get("name", "")
                for item in response.json().get("models", [])
                if item.get("name")
            ]
            result["available_models"] = available_models

        except Exception as ex:
            return self._fail(
                result,
                ex,
                (
                    "Ollama is not reachable. Start Ollama, then retry "
                    "diagnostics. Keep mock active for testing until Ollama "
                    "is healthy."
                )
            )

        model = result["configured_model"]
        result["configured_model_present"] = model in available_models

        if not result["configured_model_present"]:
            result["provider_status"] = "Configured model missing"
            result["recommended_action"] = (
                f"Pull or select the configured vision model '{model}'. "
                "You can keep mock active for testing, try a smaller vision "
                "model, or update the model name here."
            )
            return result

        text_model = settings.get(
            "text_model",
            config.get("diagnostics", {}).get("text_model", model)
        )
        result["text_model"] = text_model

        try:
            text_response = self.http.post(
                generate_url,
                json={
                    "model": text_model,
                    "prompt": "Reply with the word ok.",
                    "stream": False
                },
                timeout=timeout
            )
            text_response.raise_for_status()
            result["simple_text_call"] = True

        except Exception as ex:
            result["simple_text_call"] = False
            result["last_error"] = str(ex)

        try:
            vision_response = self.http.post(
                generate_url,
                json={
                    "model": model,
                    "prompt": "Reply with one short sentence about this image.",
                    "images": [self.SAMPLE_IMAGE_BASE64],
                    "stream": False
                },
                timeout=settings.get("vision_diagnostics_timeout", timeout)
            )
            vision_response.raise_for_status()
            result["vision_model_call"] = True
            result["provider_status"] = "Ready"
            result["recommended_action"] = (
                "Ollama vision diagnostics passed. Real analysis can be retried."
            )

        except Exception as ex:
            return self._fail(
                result,
                ex,
                (
                    "The vision model failed during a test call. On this "
                    "Windows machine, try CPU mode, try a smaller vision "
                    "model, or keep mock active for testing. Do not change "
                    "system environment variables permanently without approval."
                )
            )

        result["gpu_cpu_notes"] = (
            "Ollama does not expose reliable GPU/CPU mode through this app. "
            "If CUDA crashes continue, launch Ollama in CPU mode or use a "
            "smaller local vision model."
        )

        logger.info(
            "Provider diagnostics completed provider=%s model=%s status=%s",
            result["active_provider"],
            result["configured_model"],
            result["provider_status"]
        )

        return result

    ############################################################

    def _mock_result(self, settings):

        return self._result(
            active_provider="mock",
            configured_model=settings.get("model", "mock"),
            provider_status="Mock testing only",
            available_models=["mock"],
            ollama_reachable=False,
            configured_model_present=True,
            simple_text_call=True,
            vision_model_call=True,
            gpu_cpu_notes="Mock provider does not use GPU, CPU, Ollama, or image inspection.",
            mock_warning="Mock provider active - test data only",
            recommended_action=(
                "Use mock for development/testing only. Switch to ollama "
                "when you are ready to run real local image analysis."
            )
        )

    ############################################################

    def _result(self, **values):

        result = {
            "active_provider": "",
            "configured_model": "",
            "available_models": [],
            "ollama_reachable": False,
            "configured_model_present": False,
            "simple_text_call": False,
            "vision_model_call": False,
            "gpu_cpu_notes": "",
            "last_error": "",
            "provider_status": "",
            "mock_warning": "",
            "recommended_action": ""
        }
        result.update(values)

        return result

    ############################################################

    def _fail(self, result, error, recommended_action):

        result["last_error"] = str(error)
        result["provider_status"] = "Provider failure"
        result["recommended_action"] = recommended_action

        logger.error(
            "Provider diagnostics failed provider=%s model=%s error=%s",
            result.get("active_provider"),
            result.get("configured_model"),
            error
        )

        return result

    ############################################################

    def _tags_url(self, generate_url):

        parsed = urlparse(generate_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        return f"{base}/api/tags"
