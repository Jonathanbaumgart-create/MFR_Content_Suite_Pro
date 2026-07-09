from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.ai_settings_service import AISettingsService
from services.provider_diagnostics_service import ProviderDiagnosticsService
from services.vision_service import VisionService


class FakeResponse:

    def __init__(self, payload=None, error=None):

        self.payload = payload or {}
        self.error = error

    def raise_for_status(self):

        if self.error:
            raise RuntimeError(self.error)

    def json(self):

        return self.payload


class FakeHTTP:

    def __init__(self, models=None, post_error=None):

        self.models = models or []
        self.post_error = post_error
        self.posts = []

    def get(self, url, timeout=0):

        return FakeResponse(
            {
                "models": [
                    {
                        "name": model
                    }
                    for model in self.models
                ]
            }
        )

    def post(self, url, json=None, timeout=0):

        self.posts.append(json or {})

        if self.post_error:
            return FakeResponse(error=self.post_error)

        return FakeResponse(
            {
                "response": "ok"
            }
        )


class FailingVisionService:

    def analyze(self, image_path):

        raise RuntimeError("CUDA provider failure")

    def provider_key(self):

        return "ollama"

    def model_name(self):

        return "qwen2.5vl:7b"


def base_config(provider="mock", model="qwen2.5vl:7b"):

    return {
        "default_provider": provider,
        "retry_attempts": 0,
        "retry_delay_seconds": 0,
        "diagnostics": {
            "text_model": "llama3.1:8b"
        },
        "providers": {
            "mock": {
                "model": "mock"
            },
            "ollama": {
                "url": "http://localhost:11434/api/generate",
                "tags_url": "http://localhost:11434/api/tags",
                "model": model,
                "text_model": "llama3.1:8b",
                "timeout": 1,
                "diagnostics_timeout": 1,
                "vision_diagnostics_timeout": 1
            }
        }
    }


def add_media(db, media_id):

    db.add_media(
        {
            "filename": f"provider_{media_id}.jpg",
            "path": str(Path("library") / f"provider_{media_id}.jpg"),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + media_id,
            "sha256": f"provider-diagnostics-{media_id}"
        }
    )


def good_analysis():

    return {
        "description": "Real Ollama analysis that must be preserved.",
        "scene_type": "training",
        "activity": "hose line training",
        "people_count": 3,
        "apparatus": ["Engine"],
        "equipment": ["Hose"],
        "keywords": ["training", "safety"],
        "community_score": 80,
        "recruitment_score": 75,
        "education_score": 78,
        "technical_score": 70,
        "overall_score": 82,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": "qwen2.5vl:7b",
        "analysis_duration": 0.1,
        "provider": "ollama",
        "retry_count": 0,
        "failure_reason": ""
    }


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            mock_diag = ProviderDiagnosticsService(
                config=base_config("mock")
            ).run()
            assert mock_diag["active_provider"] == "mock", mock_diag
            assert mock_diag["vision_model_call"] is True, mock_diag
            assert mock_diag["mock_warning"], mock_diag

            missing = ProviderDiagnosticsService(
                config=base_config("ollama", "missing-vision:latest"),
                http_client=FakeHTTP(models=["llama3.1:8b"])
            ).run()
            assert missing["ollama_reachable"] is True, missing
            assert missing["configured_model_present"] is False, missing
            assert "missing" in missing["provider_status"].lower(), missing
            assert "Pull or select" in missing["recommended_action"], missing

            settings = AISettingsService(
                base_config=base_config("mock")
            )
            settings.settings_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )
            settings.settings_path.write_text(
                json.dumps(
                    {
                        "provider": "ollama",
                        "vision_model": "Ollama"
                    }
                ),
                encoding="utf-8"
            )
            migrated = settings.load()
            assert migrated["vision_provider"] == "ollama", migrated
            assert migrated["vision_model"] == "qwen2.5vl:7b", migrated

            vision = VisionService(
                config=base_config("mock"),
                settings_service=settings
            )
            assert vision.provider_key() == "ollama", vision.provider_key()
            assert vision.model_name() == "qwen2.5vl:7b", vision.model_name()

            switched = vision.switch_provider(
                "ollama",
                model="qwen2.5vl:7b"
            )
            assert switched["provider"] == "ollama", switched
            assert switched["model"] == "qwen2.5vl:7b", switched
            assert settings.load()["provider"] == "ollama", settings.load()
            assert settings.load()["vision_model"] == "qwen2.5vl:7b", settings.load()

            from services.writing_service import WritingService

            writing = WritingService(
                settings_service=settings
            )
            assert writing.provider_key() == "ollama", writing.status()
            assert writing.model_name() == "llama3.1:8b", writing.status()

            healthy = ProviderDiagnosticsService(
                settings_service=settings,
                http_client=FakeHTTP(models=["qwen2.5vl:7b", "llama3.1:8b"])
            ).run()
            assert healthy["provider_status"] == "Ready", healthy
            assert healthy["configured_model"] == "qwen2.5vl:7b", healthy
            assert healthy["simple_text_call"] is True, healthy
            assert healthy["vision_model_call"] is True, healthy

            failed = ProviderDiagnosticsService(
                settings_service=settings,
                http_client=FakeHTTP(
                    models=["qwen2.5vl:7b", "llama3.1:8b"],
                    post_error="CUDA out of memory"
                )
            ).run()
            assert failed["provider_status"] == "Provider failure", failed
            assert "CPU mode" in failed["recommended_action"], failed

            db = DatabaseManager()
            add_media(db, 1)
            add_media(db, 2)
            db.save_ai_analysis(
                1,
                good_analysis()
            )

            from services.brain_service import BrainService
            from services.job_manager import JobManager

            jobs = JobManager()
            brain = BrainService(
                database=db,
                job_manager=jobs,
                vision_service=FailingVisionService(),
                config=base_config("ollama")
            )

            future = brain.analyze_photo(
                1,
                "unused.jpg",
                force=True
            )

            try:
                future.result(timeout=10)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Failing provider did not raise")

            preserved = db.get_ai_analysis(1)
            assert preserved["description"] == good_analysis()["description"], preserved
            assert preserved["overall_score"] == 82, preserved
            assert preserved["failure_reason"] == "", preserved

            failed_new = brain.analyze_photo(
                2,
                "unused.jpg",
                force=True
            )

            try:
                failed_new.result(timeout=10)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Failing provider did not raise")

            failure = db.get_ai_analysis(2)
            assert failure["failure_reason"], failure
            assert failure["overall_score"] == 0, failure
            assert brain.provider_bulk_warning(), brain.provider_bulk_warning()

            from gui.ai_dashboard_page import AIDashboardPage

            assert AIDashboardPage is not None
            assert not hasattr(ProviderDiagnosticsService(), "analyze")

            jobs.shutdown()

        finally:
            os.chdir(original)

    print("provider_diagnostics smoke passed")


if __name__ == "__main__":
    main()
