from abc import ABC, abstractmethod

import requests

from config.ai_config import AI_CONFIG
from services.ai_settings_service import AISettingsService
from services.logging_service import LoggingService
from services.vision_preprocessing_service import (
    VisionPreprocessingError,
    VisionPreprocessingService
)


logger = LoggingService.get_logger("ai")


class VisionProviderError(RuntimeError):

    def __init__(
        self,
        message,
        category="provider_unavailable",
        status_code=None,
        response_excerpt="",
        request_metadata=None,
        attempts=None
    ):

        self.category = category
        self.status_code = status_code
        self.response_excerpt = response_excerpt
        self.request_metadata = request_metadata or {}
        self.attempts = attempts or []
        super().__init__(message)


class VisionProvider(ABC):

    def __init__(self, settings=None):

        self.settings = settings or {}

    @abstractmethod
    def analyze(self, image_path: str, prompt_context: str = "") -> str:
        pass

    def model_name(self):

        return self.settings.get("model", "unknown")

    def capabilities(self):

        return {
            "supports_images": True,
            "supports_video_frames": False,
            "supports_multi_image_prompt": False,
            "cpu_safe": bool(self.settings.get("cpu_safe", False)),
            "gpu_dependent": bool(self.settings.get("gpu_dependent", False)),
            "recommended_frame_count": int(
                self.settings.get("recommended_frame_count", 1) or 1
            ),
            "timeout": self.settings.get("timeout"),
            "maximum_resolution": self.settings.get("analysis_max_dimension"),
            "production_approved": bool(
                self.settings.get("production_approved", False)
            )
        }


class OllamaVisionProvider(VisionProvider):

    PROMPT_VERSION = "qwen_visual_json_v2"

    def __init__(self, settings=None):

        super().__init__(settings=settings)
        self.preprocessor = VisionPreprocessingService()

    def analyze(self, image_path: str, prompt_context: str = "") -> str:

        model = self.model_name()
        url = self.settings.get("url")
        prompt = self._prompt(prompt_context)
        attempts = []
        dimensions = [
            self.settings.get("analysis_max_dimension", 1536),
            self.settings.get("analysis_retry_max_dimension", 1024)
        ]
        last_error = None

        for index, max_dimension in enumerate(dimensions, start=1):

            try:
                response_text, metadata = self._attempt(
                    image_path,
                    url,
                    model,
                    prompt,
                    int(max_dimension or 1536),
                    index
                )
                attempts.append(metadata)
                self._last_metadata = {
                    "prompt_version": self.PROMPT_VERSION,
                    "attempts": attempts,
                    "preprocessing": metadata.get("preprocessing", {}),
                    "request": metadata.get("request", {})
                }

                logger.info(
                    "Ollama vision analysis completed model=%s attempt=%s submitted=%s bytes=%s",
                    model,
                    index,
                    metadata.get("preprocessing", {}).get("submitted_dimensions"),
                    metadata.get("preprocessing", {}).get("submitted_byte_size")
                )

                return response_text

            except VisionProviderError as ex:
                attempts.append(
                    {
                        "attempt": index,
                        "failure_category": ex.category,
                        "status_code": ex.status_code,
                        "response_excerpt": ex.response_excerpt,
                        "request": ex.request_metadata
                    }
                )
                last_error = ex

                if index == 1 and ex.category in {
                    "request_payload_invalid",
                    "image_encoding_failed",
                    "unsupported_image_mode",
                    "image_too_large",
                    "provider_http_400"
                }:
                    continue

                break

        self._last_metadata = {
            "prompt_version": self.PROMPT_VERSION,
            "attempts": attempts
        }
        if last_error:
            last_error.attempts = attempts
            raise last_error

        raise VisionProviderError(
            "Vision provider failed without returning a response",
            category="provider_unavailable",
            attempts=attempts
        )

    ############################################################

    def request_metadata(self):

        return getattr(self, "_last_metadata", {})

    ############################################################

    def _attempt(self, image_path, url, model, prompt, max_dimension, attempt):

        if not url:
            raise VisionProviderError(
                "Ollama provider URL is not configured",
                category="request_payload_invalid"
            )

        if not model:
            raise VisionProviderError(
                "Ollama vision model is not configured",
                category="request_payload_invalid"
            )

        if not prompt.strip():
            raise VisionProviderError(
                "Vision prompt is empty",
                category="request_payload_invalid"
            )

        try:
            prepared = self.preprocessor.preprocess(
                image_path,
                max_dimension=max_dimension
            )
        except VisionPreprocessingError as ex:
            raise VisionProviderError(
                str(ex),
                category=ex.category,
                request_metadata=ex.metadata
            ) from ex

        encoded = prepared["base64"]
        preprocessing = prepared["metadata"]
        max_payload = int(self.settings.get("analysis_max_payload_bytes", 0) or 0)

        if max_payload and preprocessing.get("submitted_byte_size", 0) > max_payload:
            raise VisionProviderError(
                "Encoded image payload is larger than configured limit",
                category="image_too_large",
                request_metadata=preprocessing
            )

        payload = {
            "model": model,
            "prompt": prompt,
            "images": [encoded],
            "stream": False,
        }
        self._validate_payload(payload)
        request_metadata = {
            "attempt": attempt,
            "model": model,
            "prompt_version": self.PROMPT_VERSION,
            "image_count": 1,
            "preprocessing": preprocessing,
            "payload_keys": sorted(payload.keys())
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.settings.get("timeout", 300),
            )
        except requests.exceptions.ReadTimeout as ex:
            raise VisionProviderError(
                "Vision provider timed out",
                category="provider_timeout",
                request_metadata=request_metadata
            ) from ex
        except requests.exceptions.RequestException as ex:
            raise VisionProviderError(
                f"Vision provider unavailable: {ex}",
                category="provider_unavailable",
                request_metadata=request_metadata
            ) from ex

        if response.status_code == 400:
            raise VisionProviderError(
                "Vision provider rejected the request with HTTP 400",
                category="provider_http_400",
                status_code=response.status_code,
                response_excerpt=self._safe_excerpt(response.text),
                request_metadata=request_metadata
            )

        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise VisionProviderError(
                f"Vision provider HTTP error: {ex}",
                category="provider_unavailable",
                status_code=response.status_code,
                response_excerpt=self._safe_excerpt(response.text),
                request_metadata=request_metadata
            ) from ex

        data = response.json()
        text = data.get("response", "")

        if not str(text).strip():
            raise VisionProviderError(
                "Vision provider returned an empty response",
                category="empty_provider_response",
                request_metadata=request_metadata
            )

        metadata = {
            "attempt": attempt,
            "failure_category": "",
            "status_code": response.status_code,
            "response_excerpt": self._safe_excerpt(text),
            "preprocessing": preprocessing,
            "request": request_metadata
        }

        return text, metadata

    ############################################################

    def _validate_payload(self, payload):

        if not isinstance(payload.get("images"), list) or not payload["images"]:
            raise VisionProviderError(
                "Vision request payload is missing images",
                category="request_payload_invalid"
            )

        required = ("model", "prompt", "images", "stream")

        for key in required:
            if key not in payload:
                raise VisionProviderError(
                    f"Vision request payload missing required field: {key}",
                    category="request_payload_invalid"
                )

    ############################################################

    def _safe_excerpt(self, value, limit=500):

        text = str(value or "").replace("\r", " ").replace("\n", " ")

        return text[:limit]

    ############################################################

    def _prompt(self, prompt_context=""):

        context_text = ""

        if str(prompt_context or "").strip():
            context_text = (
                "\nFolder context for orientation only: "
                + str(prompt_context).strip()
                + "\n"
            )

        return ("""
Describe only visible evidence in this image. Return JSON only.
Do not identify people, infer rank, infer department identity, infer location,
infer incident type, or invent apparatus types unless clearly visible.
Use unknown when uncertain. Use empty lists when evidence is absent.
Put uncertain claims in uncertain_observations.
visible_text must contain only clearly readable text.
people_count must be numeric. confidence must be between 0 and 1.
If folder context is provided, use it only to focus attention and confirm
only details that are visually supported.
No Markdown fences. No introductory text.
""" + context_text + """
{
  "description": "",
  "people_count": 0,
  "people": [],
  "apparatus": [],
  "equipment": [],
  "activities": [],
  "setting": "",
  "indoor_outdoor": "unknown",
  "visible_text": [],
  "training": false,
  "incident_scene": false,
  "public_education": false,
  "community_event": false,
  "safety_concerns": [],
  "public_use_risks": [],
  "uncertain_observations": [],
                "confidence": 0.0
}
""").strip()

    def capabilities(self):

        data = super().capabilities()
        data.update(
            {
                "supports_images": True,
                "supports_video_frames": bool(
                    self.settings.get("supports_video_frames", True)
                ),
                "supports_multi_image_prompt": bool(
                    self.settings.get("supports_multi_image_prompt", False)
                ),
                "recommended_frame_count": int(
                    self.settings.get("recommended_frame_count", 3) or 3
                ),
                "maximum_resolution": self.settings.get(
                    "analysis_max_dimension",
                    1536
                ),
                "production_approved": bool(
                    self.settings.get("production_approved", True)
                )
            }
        )
        return data


class MockVisionProvider(VisionProvider):

    def capabilities(self):

        data = super().capabilities()
        data.update(
            {
                "supports_images": True,
                "supports_video_frames": False,
                "supports_multi_image_prompt": False,
                "cpu_safe": True,
                "gpu_dependent": False,
                "recommended_frame_count": 0,
                "maximum_resolution": 0,
                "production_approved": False
            }
        )
        return data

    def analyze(self, image_path: str, prompt_context: str = "") -> str:
        model = self.model_name()

        return """
{
  "description":"MOCK TEST ANALYSIS - test data only. This result was generated by the mock provider and does not inspect the selected image. Sample scene: firefighters in turnout gear using a hose line beside Engine 1 during an evening drill.",
  "scene_type":"training",
  "activity":"hose line training",
  "people_count":4,
  "apparatus":["Engine 1"],
  "equipment":["Hose line","SCBA","Nozzle"],
  "keywords":["mock provider","test data only","training","firefighter","ppe","safety","night drill"],
  "community_score":72,
  "recruitment_score":84,
  "education_score":78,
  "technical_score":81,
  "overall_score":82,
  "facebook_caption":"MOCK TEST CAPTION - Training night keeps our crews sharp and ready to serve.",
  "instagram_caption":"MOCK TEST CAPTION - Evening hose-line training with the crew.",
  "model":"%s"
}
""" % model

    def request_metadata(self):

        return {
            "prompt_version": "mock",
            "attempts": [],
            "preprocessing": {},
            "request": {}
        }


class VisionProviderRegistry:

    def __init__(self):

        self._providers = {}

    def register(self, name, provider_class):

        self._providers[name] = provider_class

    def create(self, name, settings=None):

        provider_class = self._providers.get(name)

        if provider_class is None:
            raise ValueError(f"Unknown vision provider: {name}")

        return provider_class(settings or {})

    def names(self):

        return sorted(self._providers.keys())


class VisionService:

    def __init__(
        self,
        provider: VisionProvider | None = None,
        config=None,
        registry=None,
        settings_service=None
    ):

        self.settings_service = settings_service or AISettingsService(
            base_config=config or AI_CONFIG
        )
        self.config = self.settings_service.effective_config()
        self.registry = registry or self._default_registry()
        self._provider_key = self.config.get(
            "default_provider",
            "ollama"
        )
        self._provider = provider or self._provider_from_config()

    def set_provider(self, provider: VisionProvider):

        self._provider = provider

    def switch_provider(self, provider_key, model=None):

        self.config = self.settings_service.save(
            provider=provider_key,
            vision_model=model
        )
        self._provider_key = self.config.get(
            "default_provider",
            provider_key
        )
        self._provider = self._provider_from_config()

        logger.info(
            "Vision provider switched provider=%s model=%s",
            self._provider_key,
            self.model_name()
        )

        return {
            "provider": self._provider_key,
            "model": self.model_name()
        }

    def analyze(self, image_path: str) -> str:

        return self._provider.analyze(image_path)

    def request_metadata(self):

        if hasattr(self._provider, "request_metadata"):
            return self._provider.request_metadata()

        return {}

    def provider_name(self):

        return self._provider.__class__.__name__

    def provider_key(self):

        return self._provider_key

    def model_name(self):

        return self._provider.model_name()

    def available_providers(self):

        return self.registry.names()

    def provider_settings(self):

        return self.config.get("providers", {}).get(
            self._provider_key,
            {}
        )

    def provider_capabilities(self):

        if hasattr(self._provider, "capabilities"):
            capabilities = self._provider.capabilities()
        else:
            capabilities = {}

        capabilities["provider"] = self.provider_key()
        capabilities["model"] = self.model_name()
        return capabilities

    def _provider_from_config(self):

        provider_name = self.config.get("default_provider", "ollama")
        self._provider_key = provider_name
        provider_settings = self.config.get("providers", {}).get(
            provider_name,
            {}
        )

        return self.registry.create(
            provider_name,
            provider_settings
        )

    def _default_registry(self):

        registry = VisionProviderRegistry()

        registry.register(
            "ollama",
            OllamaVisionProvider
        )

        registry.register(
            "mock",
            MockVisionProvider
        )

        return registry
