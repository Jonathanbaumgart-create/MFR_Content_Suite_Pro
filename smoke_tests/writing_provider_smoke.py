from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.writing_config import WRITING_CONFIG
from services.writing_service import (
    DeterministicWritingProvider,
    WritingProvider,
    WritingProviderRegistry,
    WritingService
)


class FailingWritingProvider(WritingProvider):

    def available(self):

        return True

    def generate(self, request):

        raise RuntimeError("simulated local writing failure")


def base_request():

    package = {
        "headline": "Morden Fire & Rescue: Recruitment",
        "facebook_caption": "Join the team. #MordenFireRescue",
        "instagram_caption": "Join the team. #Recruitment",
        "linkedin_caption": "A recruitment update from Morden Fire & Rescue.",
        "short_version": "A recruitment-focused message.",
        "long_version": "A recruitment-focused message using stored intelligence.",
        "call_to_action": "Learn more about serving your community.",
        "facebook_hashtags": ["#MordenFireRescue"],
        "instagram_hashtags": ["#Recruitment"],
        "hashtags": ["#MordenFireRescue", "#Recruitment"],
        "emoji_suggestions": ["\U0001fa96", "\U0001f91d"],
        "reasoning": ["Uses stored recommendation data only."]
    }

    return {
        "recommendation": {
            "title": "Recruitment",
            "opportunity_type": "recruitment"
        },
        "media_intelligence": [
            {
                "incident_type": "training",
                "primary_activity": "recruitment_training",
                "content_tags": ["recruitment", "training"]
            }
        ],
        "department_knowledge": {
            "profile": {
                "department_name": "Morden Fire & Rescue"
            }
        },
        "context": {
            "season": "summer",
            "active_themes": ["recruitment"]
        },
        "opportunity_type": "recruitment",
        "platforms": [
            "facebook",
            "instagram",
            "linkedin"
        ],
        "base_package": package
    }


def main():

    assert (
        WRITING_CONFIG["providers"]["ollama"]["model"] == "llama3.1:8b"
    ), WRITING_CONFIG

    deterministic = WritingService(
        config={
            "default_provider": "deterministic",
            "fallback_provider": "deterministic",
            "providers": {
                "deterministic": {
                    "model": "deterministic-template"
                }
            }
        }
    )
    deterministic_package = deterministic.generate(
        base_request()
    )

    assert deterministic_package["facebook_caption"], deterministic_package
    assert deterministic_package["prompt_engine"] == "professional"
    assert deterministic_package["editorial_dna"], deterministic_package
    assert deterministic.status()["active_provider"] == "deterministic"
    assert deterministic.status()["fallback_used"] is False
    assert not hasattr(deterministic, "vision")
    assert not hasattr(deterministic, "ai")

    registry = WritingProviderRegistry()
    registry.register(
        "failing",
        FailingWritingProvider
    )
    registry.register(
        "deterministic",
        DeterministicWritingProvider
    )

    service = WritingService(
        config={
            "default_provider": "failing",
            "fallback_provider": "deterministic",
            "providers": {
                "failing": {
                    "model": "failing-local"
                },
                "deterministic": {
                    "model": "deterministic-template"
                }
            }
        },
        registry=registry
    )
    package = service.generate(
        base_request()
    )
    status = service.status()

    assert package["facebook_caption"].startswith("Join the team"), package
    assert package["instagram_caption"].startswith("Join the team"), package
    assert package["prompt_engine"] == "professional", package
    assert package["editorial_dna"], package
    assert status["active_provider"] == "deterministic", status
    assert status["fallback_used"] is True, status
    assert "simulated local writing failure" in status["last_error"], status
    assert not hasattr(service, "vision")
    assert not hasattr(service, "ai")
    assert not hasattr(service._provider, "analyze")

    print("writing_provider smoke passed")


if __name__ == "__main__":
    main()
