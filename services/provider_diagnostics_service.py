from urllib.parse import urlparse
import json

import requests

from services.ai_settings_service import AISettingsService
from services.ai_service import AIService
from services.logging_service import LoggingService
from services.vision_service import OllamaVisionProvider


logger = LoggingService.get_logger("ai")


class ProviderDiagnosticsService:

    SAMPLE_IMAGE_BASE64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNg"
        "YAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )

    def __init__(self, settings_service=None, config=None, http_client=None):

        self.settings_service = settings_service
        self.config = config
        self.http = http_client or requests

    ############################################################

    def run(self):

        if self.settings_service is not None:
            config = self.settings_service.effective_config()
        elif self.config is not None:
            config = self.config
        else:
            config = AISettingsService().effective_config()
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
                    "diagnostics. Mock remains available for testing only "
                    "until Ollama is healthy."
                )
            )

        model = result["configured_model"]
        result["configured_model_present"] = model in available_models

        if not result["configured_model_present"]:
            result["provider_status"] = "Configured model missing"
            result["recommended_action"] = (
                f"Pull or select the configured vision model '{model}'. "
                "For production, try a smaller vision model or update the "
                "model name here. Mock remains testing-only."
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
            production_prompt = OllamaVisionProvider(
                settings
            )._prompt("Provider diagnostics production schema test.")
            vision_response = self.http.post(
                generate_url,
                json={
                    "model": model,
                    "prompt": production_prompt,
                    "images": [self.SAMPLE_IMAGE_BASE64],
                    "stream": False
                },
                timeout=settings.get("vision_diagnostics_timeout", timeout)
            )
            vision_response.raise_for_status()
            result["vision_model_call"] = True
            result["image_request_accepted"] = True
            payload = vision_response.json()
            result["raw_response_received"] = True
            text, wrapper = self._extract_response_text(payload)
            result["response_wrapper"] = wrapper
            result["response_wrapper_recognized"] = True
            parsed = AIService().parse_analysis(
                text,
                model
            )
            result["json_extracted"] = parsed.get("parse_status") not in (
                AIService.STATUS_EMPTY,
                AIService.STATUS_INVALID
            )
            result["schema_validated"] = parsed.get(
                "parser_classification"
            ) in ("valid", "normalized_valid", "partial_valid")
            result["production_parser_accepted"] = result["schema_validated"]
            result["persistence_compatible"] = bool(
                parsed.get("description")
            ) and parsed.get("parse_status") not in (
                AIService.STATUS_EMPTY,
                AIService.STATUS_INVALID
            )
            result["production_schema_test"] = result["persistence_compatible"]
            result["parser_classification"] = parsed.get(
                "parser_classification",
                ""
            )
            result["parse_status"] = parsed.get("parse_status", "")
            result["parse_warnings"] = parsed.get("parse_warnings", [])
            result["failure_category"] = parsed.get("failure_category", "")

            if result["production_schema_test"]:
                result["provider_status"] = "Ready"
                result["recommended_action"] = (
                    "Ollama production schema diagnostics passed. Real analysis can be retried."
                )
            else:
                result["provider_status"] = "Production schema failure"
                result["recommended_action"] = (
                    "The model responded, but did not return usable production "
                    "analysis JSON. Retry diagnostics, try a smaller/steadier "
                    "vision model, or inspect the technical summary."
                )

        except requests.exceptions.ReadTimeout as ex:
            result["last_error"] = str(ex)
            result["provider_status"] = "Model may still be loading"
            result["model_loading"] = True
            result["recommended_action"] = (
                "The configured vision model is installed, but the first "
                "diagnostic call timed out while waiting for a response. "
                "This can happen while Ollama loads a model on Windows. "
                "Wait for the model load to finish, then run diagnostics "
                "again. This is not marked as a permanent provider failure."
            )
            result["gpu_cpu_notes"] = (
                "First local model load can be slow. If repeated timeouts "
                "continue, try CPU mode, try a smaller vision model, or "
                "keep mock active for testing."
            )

            logger.warning(
                "Provider diagnostics timed out while model may still be loading provider=%s model=%s",
                result.get("active_provider"),
                result.get("configured_model")
            )

            return result

        except Exception as ex:
            return self._fail(
                result,
                ex,
                (
                "The vision model failed during a test call. On this "
                "Windows machine, try CPU mode, try a smaller vision "
                "model, and use mock only for testing. Do not change "
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

    def _extract_response_text(self, payload):

        if not isinstance(payload, dict):
            raise ValueError("Unsupported Ollama response shape")

        candidates = (
            ("response", payload.get("response")),
            (
                "message.content",
                (payload.get("message") or {}).get("content")
                if isinstance(payload.get("message"), dict)
                else None
            ),
            ("content", payload.get("content")),
            ("output", payload.get("output")),
            ("text", payload.get("text"))
        )

        for name, value in candidates:
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                return json.dumps(value), name
            return str(value), name

        raise ValueError("No recognized analysis text wrapper")

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
            "image_request_accepted": False,
            "raw_response_received": False,
            "response_wrapper": "",
            "response_wrapper_recognized": False,
            "json_extracted": False,
            "schema_validated": False,
            "production_parser_accepted": False,
            "persistence_compatible": False,
            "production_schema_test": False,
            "parser_classification": "",
            "parse_status": "",
            "parse_warnings": [],
            "failure_category": "",
            "model_loading": False,
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
