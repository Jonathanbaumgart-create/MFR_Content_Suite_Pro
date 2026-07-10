from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.fire_reasoning_service import FireReasoningService
from services.media_intelligence_service import MediaIntelligenceService
from services.operations_service import OperationsService


def add_media(db, index):

    db.add_media(
        {
            "filename": f"fire_reasoning_{index}.jpg",
            "path": str(Path("library") / f"fire_reasoning_{index}.jpg"),
            "extension": ".jpg",
            "type": "image",
            "size": 200 + index,
            "sha256": f"fire-reasoning-hash-{index}"
        }
    )


def ladder_training_analysis():

    return {
        "media_id": 1,
        "description": (
            "Firefighter wearing turnout gear and helmet ascends a ground "
            "ladder inside the training tower during a drill."
        ),
        "scene_type": "training tower",
        "activity": "",
        "people_count": 1,
        "apparatus": [],
        "equipment": ["Ground ladder", "SCBA"],
        "keywords": ["firefighter", "turnout gear", "training tower"],
        "community_score": 55,
        "recruitment_score": 78,
        "education_score": 75,
        "technical_score": 84,
        "overall_score": 82,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": "moondream:latest",
        "provider": "ollama",
        "retry_count": 0,
        "failure_reason": ""
    }


def public_education_analysis():

    return {
        "media_id": 2,
        "description": (
            "Crew members teach children and students about smoke alarms "
            "during a public education school visit."
        ),
        "scene_type": "public education",
        "activity": "public education",
        "people_count": 5,
        "apparatus": [],
        "equipment": ["Smoke alarm"],
        "keywords": ["children", "school", "prevention"],
        "community_score": 82,
        "recruitment_score": 50,
        "education_score": 90,
        "technical_score": 30,
        "overall_score": 79,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": "moondream:latest",
        "provider": "ollama",
        "retry_count": 0,
        "failure_reason": ""
    }


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            media_service = MediaIntelligenceService(db)

            add_media(db, 1)
            add_media(db, 2)

            db.save_ai_analysis(1, ladder_training_analysis())
            media_service.generate_and_save(
                1,
                db.get_ai_analysis(1)
            )
            fire_training = db.get_fire_service_intelligence(1)

            assert fire_training["operational_context"] == "training", fire_training
            assert "ladder_operations" in fire_training["operational_skills"], fire_training
            assert "training_tuesday" in fire_training["communications_intent"], fire_training
            assert "officer_development" in fire_training["communications_intent"], fire_training
            assert fire_training["operational_confidence"] >= 90, fire_training
            assert fire_training["reasoning_evidence"], fire_training
            assert any(
                "ladder evolution" in item.get("reason", "").lower()
                for item in fire_training["reasoning_evidence"]
            ), fire_training
            assert any(
                "Operational context inferred as training" in line
                for line in fire_training["operational_reasoning"]
            ), fire_training

            standalone = FireReasoningService(database=db).evaluate(
                media_intelligence=db.get_media_intelligence(1),
                fire_service_intelligence=fire_training
            )
            assert standalone["operational_context"] == "training", standalone
            assert standalone["operational_confidence"] >= 90, standalone
            assert not hasattr(FireReasoningService, "vision")

            db.save_ai_analysis(2, public_education_analysis())
            media_service.generate_and_save(
                2,
                db.get_ai_analysis(2)
            )
            fire_education = db.get_fire_service_intelligence(2)

            assert fire_education["operational_context"] == "public_education", fire_education
            assert "public_education" in fire_education["operational_skills"], fire_education
            assert "community_education" in fire_education["communications_intent"], fire_education
            assert fire_education["operational_confidence"] >= 80, fire_education

            from gui.photo_viewer import PhotoViewer
            viewer = object.__new__(PhotoViewer)
            viewer.fire_service_intelligence = fire_training
            lines = PhotoViewer.fire_service_intelligence_lines(viewer)
            assert any("Operational Context: training" in line for line in lines), lines
            assert any("Operational Skills:" in line for line in lines), lines
            assert any("Communications Intent:" in line for line in lines), lines
            assert any("Confidence:" in line for line in lines), lines
            assert any("Evidence:" in line for line in lines), lines

            operations = OperationsService(
                database=db,
                job_manager=None
            ).library_processing()
            assert operations["training_media_count"] == 1, operations
            assert operations["public_education_media_count"] == 1, operations
            assert operations["recruitment_media_count"] >= 1, operations
            assert operations["top_operational_categories"], operations
            assert operations["top_operational_skills"], operations

        finally:
            os.chdir(original)

    print("fire_reasoning smoke passed")


if __name__ == "__main__":
    main()
