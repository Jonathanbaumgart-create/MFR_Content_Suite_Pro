import base64
from abc import ABC, abstractmethod

import requests

from config.ai_config import AI_CONFIG
from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class VisionProvider(ABC):

    def __init__(self, settings=None):

        self.settings = settings or {}

    @abstractmethod
    def analyze(self, image_path: str) -> str:
        pass

    def model_name(self):

        return self.settings.get("model", "unknown")


class OllamaVisionProvider(VisionProvider):

    def analyze(self, image_path: str) -> str:

        with open(image_path, "rb") as image:
            encoded = base64.b64encode(image.read()).decode("utf-8")

        model = self.model_name()

        prompt = """
You are the AI assistant for Morden Fire & Rescue.

Analyze this image.

Return ONLY valid JSON.

Do not wrap the JSON in markdown.

Return this exact structure:

{
  "description":"",
  "scene_type":"",
  "activity":"",
  "people_count":0,
  "apparatus":[],
  "equipment":[],
  "keywords":[],
  "community_score":0,
  "recruitment_score":0,
  "education_score":0,
  "technical_score":0,
  "overall_score":0,
  "facebook_caption":"",
  "instagram_caption":"",
  "model":"%s"
}

Rules:

- Be factual.
- Do not invent information.
- Estimate scores from 0-100.
- Apparatus, equipment and keywords MUST be arrays.
- Return JSON only.
""" % model

        response = requests.post(
            self.settings.get("url"),
            json={
                "model": model,
                "prompt": prompt,
                "images": [encoded],
                "stream": False,
            },
            timeout=self.settings.get("timeout", 300),
        )
        response.raise_for_status()

        logger.info(
            "Ollama vision analysis completed model=%s",
            model
        )

        return response.json()["response"]


class MockVisionProvider(VisionProvider):

    def analyze(self, image_path: str) -> str:
        model = self.model_name()

        return """
{
  "description":"Mock analysis completed for the selected image.",
  "scene_type":"training",
  "activity":"fire service media review",
  "people_count":0,
  "apparatus":[],
  "equipment":[],
  "keywords":["mock","analysis"],
  "community_score":50,
  "recruitment_score":50,
  "education_score":50,
  "technical_score":50,
  "overall_score":50,
  "facebook_caption":"",
  "instagram_caption":"",
  "model":"%s"
}
""" % model


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
        registry=None
    ):

        self.config = config or AI_CONFIG
        self.registry = registry or self._default_registry()
        self._provider = provider or self._provider_from_config()

    def set_provider(self, provider: VisionProvider):

        self._provider = provider

    def analyze(self, image_path: str) -> str:

        return self._provider.analyze(image_path)

    def provider_name(self):

        return self._provider.__class__.__name__

    def provider_key(self):

        return self.config.get("default_provider", "ollama")

    def model_name(self):

        return self._provider.model_name()

    def _provider_from_config(self):

        provider_name = self.config.get("default_provider", "ollama")
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
