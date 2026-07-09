import json
import re
from abc import ABC, abstractmethod

import requests

from config.writing_config import WRITING_CONFIG
from services.ai_settings_service import AISettingsService
from services.logging_service import LoggingService
from services.prompt_engine import PromptEngine


logger = LoggingService.get_logger("content")


class WritingProvider(ABC):

    def __init__(self, settings=None):

        self.settings = settings or {}

    @abstractmethod
    def generate(self, request):
        pass

    def available(self):

        return True

    def provider_name(self):

        return self.__class__.__name__

    def model_name(self):

        return self.settings.get("model", "unknown")


class DeterministicWritingProvider(WritingProvider):

    def generate(self, request):

        package = dict(request.get("base_package", {}))
        package["prompt_engine"] = "professional"
        package["editorial_dna"] = request.get("editorial_dna", {})
        package["reasoning"] = list(
            package.get("reasoning", [])
        ) + [
            (
                "Prompt Engine applied Editorial DNA and platform rules "
                "before deterministic template fallback."
            )
        ]

        return package


class OllamaWritingProvider(WritingProvider):

    def available(self):

        tags_url = self.settings.get("tags_url")

        if not tags_url:
            return True

        response = requests.get(
            tags_url,
            timeout=self.settings.get("availability_timeout", 1)
        )
        response.raise_for_status()

        model = self.model_name()
        models = response.json().get("models", [])

        return any(
            item.get("name") == model
            for item in models
        )

    def generate(self, request):

        model = self.model_name()
        prompt = self._combined_prompt(
            request
        )

        response = requests.post(
            self.settings.get("url"),
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=self.settings.get("timeout", 60)
        )
        response.raise_for_status()

        raw = response.json().get("response", "")
        parsed = self._parse_json(raw)

        logger.info(
            "Ollama writing completed model=%s opportunity=%s",
            model,
            request.get("opportunity_type")
        )

        return parsed

    def _combined_prompt(self, request):

        prompts = request.get("prompts", {})

        return """
Use the platform-specific writing briefs below.

Return ONLY valid JSON. Do not wrap JSON in markdown. Required structure:

{
  "facebook_caption": "",
  "instagram_caption": "",
  "linkedin_caption": "",
  "short_version": "",
  "long_version": "",
  "call_to_action": "",
  "facebook_hashtags": [],
  "instagram_hashtags": [],
  "hashtags": [],
  "emoji_suggestions": [],
  "reasoning": []
}

Briefs:
%s
""" % (
            "\n\n".join(
                [
                    f"{platform.upper()} BRIEF\n{prompt}"
                    for platform, prompt in prompts.items()
                ]
            )
        )

    def _parse_json(self, value):

        text = str(value or "").strip()
        text = re.sub(
            r"^```(?:json)?|```$",
            "",
            text,
            flags=re.IGNORECASE | re.MULTILINE
        ).strip()

        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if match:
            text = match.group(0)

        return json.loads(text)


class WritingProviderRegistry:

    def __init__(self):

        self._providers = {}

    def register(self, name, provider_class):

        self._providers[name] = provider_class

    def create(self, name, settings=None):

        provider_class = self._providers.get(name)

        if provider_class is None:
            raise ValueError(f"Unknown writing provider: {name}")

        return provider_class(settings or {})

    def names(self):

        return sorted(self._providers.keys())


class WritingService:

    BANNED_PUBLIC_PHRASES = (
        "selected media",
        "stored tags",
        "incident type:",
        "activity:",
        "supported by",
        "a safety campaign message",
        "a practical reminder"
    )

    def __init__(
        self,
        provider=None,
        fallback_provider=None,
        config=None,
        registry=None,
        prompt_engine=None,
        settings_service=None
    ):

        self.settings_service = settings_service or AISettingsService()
        self.config = (
            config or
            self.settings_service.effective_writing_config(WRITING_CONFIG)
        )
        self.registry = registry or self._default_registry()
        self.prompt_engine = prompt_engine or PromptEngine()
        self._provider_key = self.config.get("default_provider", "ollama")
        self._provider = provider or self._provider_from_config(
            self._provider_key
        )
        fallback_key = self.config.get("fallback_provider", "deterministic")
        self._fallback_key = fallback_key
        self._fallback_provider = fallback_provider or self._provider_from_config(
            fallback_key
        )
        self._status = {
            "provider": self._provider_key,
            "model": self._provider.model_name(),
            "active_provider": self._provider_key,
            "active_model": self._provider.model_name(),
            "fallback_used": False,
            "available": None,
            "last_error": ""
        }

    def switch_provider(self, provider_key, model=None):

        self.config = self.settings_service.save_writing(
            provider=provider_key,
            writing_model=model,
            base_config=WRITING_CONFIG
        )
        self._provider_key = self.config.get(
            "default_provider",
            provider_key
        )
        self._provider = self._provider_from_config(
            self._provider_key
        )
        self._status.update(
            {
                "provider": self._provider_key,
                "model": self._provider.model_name(),
                "active_provider": self._provider_key,
                "active_model": self._provider.model_name(),
                "fallback_used": False,
                "last_error": ""
            }
        )

        logger.info(
            "Writing provider switched provider=%s model=%s",
            self._provider_key,
            self._provider.model_name()
        )

        return {
            "provider": self._provider_key,
            "model": self._provider.model_name()
        }

    def available_providers(self):

        return self.registry.names()

    def generate(self, request):

        request = dict(request)
        base_package = dict(request.get("base_package", {}))
        prompt_payload = self.prompt_engine.build_all(
            request
        )
        request.update(
            prompt_payload
        )

        try:
            available = self._provider.available()
            self._status["available"] = available

            if not available:
                raise RuntimeError(
                    f"Writing provider unavailable: {self._provider_key}"
                )

            generated = self._provider.generate(request)
            package = self._normalize_package(
                generated,
                base_package
            )
            package["prompt_engine"] = "professional"
            package["editorial_dna"] = request.get("editorial_dna", {})
            self._set_status(
                self._provider_key,
                self._provider.model_name(),
                False,
                ""
            )

            return package

        except Exception as error:

            logger.error(
                "Writing provider failed provider=%s model=%s",
                self._provider_key,
                self._provider.model_name(),
                exc_info=(
                    type(error),
                    error,
                    error.__traceback__
                )
            )

            fallback = self._fallback_provider.generate(
                request
            )
            package = self._normalize_package(
                fallback,
                base_package
            )
            package["prompt_engine"] = "professional"
            package["editorial_dna"] = request.get("editorial_dna", {})
            self._set_status(
                self._fallback_key,
                self._fallback_provider.model_name(),
                True,
                str(error)
            )

            return package

    def status(self):

        return dict(self._status)

    def provider_key(self):

        return self._status.get(
            "active_provider",
            self._provider_key
        )

    def model_name(self):

        return self._status.get(
            "active_model",
            self._provider.model_name()
        )

    def _normalize_package(self, generated, base_package):

        generated = generated or {}
        package = dict(base_package)

        for key in (
            "facebook_caption",
            "instagram_caption",
            "linkedin_caption",
            "short_version",
            "long_version",
            "call_to_action"
        ):
            package[key] = self._safe_public_text(
                key,
                generated.get(key),
                package.get(key, ""),
                package
            )

        package["facebook_hashtags"] = self._hashtags(
            generated.get("facebook_hashtags") or
            package.get("facebook_hashtags") or
            package.get("hashtags", [])
        )
        package["instagram_hashtags"] = self._hashtags(
            generated.get("instagram_hashtags") or
            package.get("instagram_hashtags") or
            package.get("hashtags", [])
        )
        package["hashtags"] = self._unique(
            self._hashtags(generated.get("hashtags") or []) +
            package["facebook_hashtags"] +
            package["instagram_hashtags"]
        )
        package["emoji_suggestions"] = self._unique(
            self._as_list(generated.get("emoji_suggestions")) +
            self._as_list(package.get("emoji_suggestions"))
        )[:5]
        package["reasoning"] = self._unique(
            self._as_list(generated.get("reasoning")) +
            self._as_list(package.get("reasoning"))
        )

        return package

    def _safe_public_text(self, key, generated_value, fallback_value, package):

        value = self._clean(
            generated_value or fallback_value
        )

        if key not in (
            "facebook_caption",
            "instagram_caption",
            "linkedin_caption",
            "short_version",
            "long_version"
        ):
            return value

        if self._contains_banned_public_phrase(value):
            logger.warning(
                "Writing output contained banned public phrase key=%s opportunity=%s",
                key,
                package.get("opportunity_type", "")
            )
            value = self._clean(
                fallback_value
            )

        value = self._remove_forbidden_public_lines(
            value,
            package.get("opportunity_type", "")
        )

        if self._contains_banned_public_phrase(value):
            value = self._public_fallback_text(
                key,
                package
            )

        return value

    def _contains_banned_public_phrase(self, value):

        lower = str(value or "").lower()

        return any(
            phrase in lower
            for phrase in self.BANNED_PUBLIC_PHRASES
        )

    def _remove_forbidden_public_lines(self, value, opportunity):

        lines = []

        for line in str(value or "").splitlines():
            lower = line.lower()

            if (
                "hydrant heroes" in lower and
                opportunity != "hydrant_heroes"
            ):
                continue

            if self._looks_like_alias_list(line):
                continue

            lines.append(line)

        return self._clean(
            "\n".join(lines)
        )

    def _looks_like_alias_list(self, line):

        lower = str(line or "").lower()

        return (
            "mfr" in lower and
            "city of morden" in lower and
            lower.count(",") >= 2
        )

    def _public_fallback_text(self, key, package):

        body = package.get("short_version") or (
            "Morden Fire & Rescue is sharing a timely community-safety "
            "message for residents."
        )
        cta = package.get("call_to_action", "")
        hashtags = " ".join(
            self._hashtags(
                package.get("facebook_hashtags") or
                package.get("hashtags", [])
            )
        )

        if key == "linkedin_caption":
            return self._clean(
                f"{body}\n\n{cta}"
            )

        return self._clean(
            f"{body}\n\n{cta}\n\n{hashtags}"
        )

    def _hashtags(self, values):

        tags = []

        for value in self._as_list(values):
            tag = str(value or "").strip()

            if not tag:
                continue

            if not tag.startswith("#"):
                tag = "#" + "".join(
                    part.capitalize()
                    for part in tag.replace("-", "_").replace(" ", "_").split("_")
                    if part
                )

            if tag != "#":
                tags.append(tag)

        return self._unique(tags)[:5]

    def _as_list(self, value):

        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        return [value]

    def _clean(self, value):

        return "\n\n".join(
            " ".join(line.strip().split())
            for line in str(value or "").splitlines()
            if line.strip()
        )

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique

    def _set_status(self, provider, model, fallback_used, error):

        self._status.update(
            {
                "provider": self._provider_key,
                "model": self._provider.model_name(),
                "active_provider": provider,
                "active_model": model,
                "fallback_used": fallback_used,
                "last_error": error
            }
        )

    def _provider_from_config(self, provider_name):

        settings = self.config.get("providers", {}).get(
            provider_name,
            {}
        )

        return self.registry.create(
            provider_name,
            settings
        )

    def _default_registry(self):

        registry = WritingProviderRegistry()

        registry.register(
            "ollama",
            OllamaWritingProvider
        )
        registry.register(
            "deterministic",
            DeterministicWritingProvider
        )

        return registry
