from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.ai_service import AIService
from services.job_manager import JobManager
from services.media_intelligence_service import MediaIntelligenceService
from services.vision_service import MockVisionProvider, VisionService


class FailingVisionService:

    def analyze(self, image_path):

        raise RuntimeError("CUDA error: mock Ollama failure")

    def provider_key(self):

        return "ollama"

    def model_name(self):

        return "qwen2.5vl:7b"


def sample_analysis(model="mock"):

    return {
        "description": (
            "Training photo with firefighters in turnout gear using hose "
            "lines near an engine at night."
        ),
        "scene_type": "training",
        "activity": "hose line training",
        "people_count": 4,
        "apparatus": ["Engine"],
        "equipment": ["Hose", "SCBA"],
        "keywords": ["training", "safety", "night"],
        "community_score": 65,
        "recruitment_score": 72,
        "education_score": 80,
        "technical_score": 70,
        "overall_score": 76,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": model,
        "analysis_duration": 0.1,
        "provider": "mock",
        "retry_count": 0,
        "failure_reason": ""
    }


def add_media(db, index):

    db.add_media(
        {
            "filename": f"media_{index}.jpg",
            "path": str(Path("library") / f"media_{index}.jpg"),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"hash-{index}"
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:

            db = DatabaseManager()
            service = MediaIntelligenceService(db)
            jobs = JobManager()
            from services.brain_service import BrainService

            add_media(db, 1)

            config = {
                "default_provider": "mock",
                "retry_attempts": 0,
                "retry_delay_seconds": 0,
                "providers": {
                    "mock": {
                        "model": "mock"
                    }
                }
            }
            vision = VisionService(
                provider=MockVisionProvider({"model": "mock"}),
                config=config
            )
            brain = BrainService(
                database=db,
                job_manager=jobs,
                vision_service=vision,
                config=config
            )

            future = brain.analyze_photo(
                1,
                "unused.jpg"
            )
            future.result(timeout=10)

            assert brain.is_mock_provider()

            generated = db.get_media_intelligence(1)

            assert generated["normalized_scene"] == "training", generated
            assert isinstance(generated["content_tags"], list), generated
            assert "mock_provider" in generated["content_tags"], generated
            assert "training" in generated["recommended_uses"], generated

            mock_analysis = db.get_ai_analysis(1)
            assert mock_analysis["description"].startswith(
                "MOCK TEST ANALYSIS"
            ), mock_analysis

            search = db.search_intelligence("mock")
            assert len(search) == 1, search
            assert isinstance(search[0]["recommended_uses"], list), search

            from gui.photo_viewer import PhotoViewer
            viewer = object.__new__(PhotoViewer)
            viewer.intelligence = generated
            lines = PhotoViewer.intelligence_lines(viewer)
            assert any("Scene: training" in line for line in lines), lines
            assert any("Recommended Uses:" in line for line in lines), lines

            good = db.get_ai_analysis(1)
            failing_brain = BrainService(
                database=db,
                job_manager=jobs,
                vision_service=FailingVisionService(),
                config={
                    "retry_attempts": 0,
                    "retry_delay_seconds": 0
                }
            )

            failed = failing_brain.analyze_photo(
                1,
                "unused.jpg",
                force=True
            )

            try:
                failed.result(timeout=10)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Failing provider did not raise")

            preserved = db.get_ai_analysis(1)
            assert preserved["description"] == good["description"], preserved
            assert preserved["overall_score"] == good["overall_score"], preserved
            assert preserved["failure_reason"] == "", preserved

            add_media(db, 5)
            failed_new = failing_brain.analyze_photo(
                5,
                "unused.jpg"
            )

            try:
                failed_new.result(timeout=10)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Failing provider did not raise")

            failure_row = db.get_ai_analysis(5)
            assert failure_row["failure_reason"], failure_row
            assert failure_row["provider"] == "ollama", failure_row
            assert failure_row["overall_score"] == 0, failure_row

            add_media(db, 6)
            real_analysis = sample_analysis(model="qwen2.5vl:7b")
            real_analysis["provider"] = "ollama"
            real_analysis["description"] = "Real Ollama analysis"
            real_analysis["overall_score"] = 91
            db.save_ai_analysis(
                6,
                real_analysis
            )

            preserved_real = brain.analyze_photo(
                6,
                "unused.jpg",
                force=True
            ).result(timeout=10)

            assert preserved_real["provider"] == "ollama", preserved_real
            assert preserved_real["description"] == "Real Ollama analysis", preserved_real
            assert preserved_real["overall_score"] == 91, preserved_real

            add_media(db, 7)
            add_media(db, 8)

            weak_analysis = sample_analysis(model="moondream:latest")
            weak_analysis.update(
                {
                    "description": "Unclear image with limited detail.",
                    "scene_type": "",
                    "activity": "",
                    "people_count": 0,
                    "apparatus": [],
                    "equipment": [],
                    "keywords": [],
                    "community_score": 20,
                    "recruitment_score": 20,
                    "education_score": 20,
                    "technical_score": 20,
                    "overall_score": 20,
                    "provider": "ollama"
                }
            )
            db.save_ai_analysis(7, weak_analysis)
            weak_intelligence = service.generate_and_save(
                7,
                db.get_ai_analysis(7)
            )

            provider_payload = json.dumps(
                {
                    "description": (
                        "A firefighter wearing a helmet and SCBA is at the "
                        "training tower with a hose, ladder, rope, apparatus, "
                        "and rescue equipment."
                    ),
                    "scene_type": "training tower",
                    "activity": "rope rescue training",
                    "people_count": "1 person",
                    "apparatus": "apparatus",
                    "equipment": "helmet, SCBA, hose, rope, rescue equipment",
                    "keywords": "firefighter, PPE, ladder, training tower",
                    "community_score": 64,
                    "recruitment_score": 74,
                    "education_score": 70,
                    "technical_score": 78,
                    "overall_score": 82,
                    "facebook_caption": "",
                    "instagram_caption": "",
                    "model": "moondream:latest"
                }
            )
            parsed = AIService().parse_analysis(
                provider_payload,
                model="moondream:latest"
            )
            parsed["provider"] = "ollama"
            db.save_ai_analysis(8, parsed)

            saved_provider_analysis = db.get_ai_analysis(8)
            assert saved_provider_analysis["people_count"] == 1, saved_provider_analysis
            assert saved_provider_analysis["scene_type"] == "training tower", saved_provider_analysis
            assert saved_provider_analysis["activity"] == "rope rescue training", saved_provider_analysis

            rich_intelligence = service.generate_and_save(
                8,
                saved_provider_analysis
            )

            assert rich_intelligence["normalized_scene"] == "training_tower", rich_intelligence
            assert rich_intelligence["primary_activity"] == "rope_rescue_training", rich_intelligence
            assert "no_people" not in rich_intelligence["people_tags"], rich_intelligence
            assert "people" in rich_intelligence["people_tags"], rich_intelligence
            assert "small_group" in rich_intelligence["people_tags"], rich_intelligence

            equipment_tags = set(rich_intelligence["equipment_tags"])
            assert {"scba", "hose", "rope", "rescue_equipment"}.issubset(
                equipment_tags
            ), rich_intelligence
            assert "helmet" in rich_intelligence["ppe_tags"], rich_intelligence
            assert "ppe" in rich_intelligence["ppe_tags"], rich_intelligence
            assert "firefighter" in rich_intelligence["content_tags"], rich_intelligence
            assert "training_tower" in rich_intelligence["content_tags"], rich_intelligence
            assert rich_intelligence["communications_score"] > weak_intelligence[
                "communications_score"
            ], (rich_intelligence, weak_intelligence)

            for index in range(2, 5):
                add_media(db, index)
                db.save_ai_analysis(
                    index,
                    sample_analysis(model=f"mock-{index}")
                )

            rebuilt = service.rebuild_missing(limit=2)
            assert rebuilt["total"] == 2, rebuilt
            assert rebuilt["completed"] == 2, rebuilt
            assert rebuilt["failed"] == 0, rebuilt

            bulk = brain.analyze_entire_library()
            assert len(bulk) == db.image_media_count(), bulk
            bulk_result = bulk.future.result(timeout=20)
            assert bulk_result["total"] == len(bulk), bulk_result

            cleared = brain.clear_mock_analysis()
            assert cleared["analysis_deleted"] >= 4, cleared
            assert cleared["intelligence_deleted"] >= 1, cleared
            assert db.get_ai_analysis(1) is None
            assert db.get_ai_analysis(6)["provider"] == "ollama"

            jobs.shutdown()

        finally:
            os.chdir(original)

    print("media_intelligence smoke passed")


if __name__ == "__main__":
    main()
