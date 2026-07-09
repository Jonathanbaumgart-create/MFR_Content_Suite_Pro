from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communications_scoring_service import CommunicationsScoringService
from services.fire_service_intelligence_service import FireServiceIntelligenceService
from services.media_intelligence_service import MediaIntelligenceService
from services.operations_service import OperationsService


def add_media(db, index):

    db.add_media(
        {
            "filename": f"fire_service_{index}.jpg",
            "path": str(Path("library") / f"fire_service_{index}.jpg"),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"fire-service-hash-{index}"
        }
    )


def training_analysis():

    return {
        "media_id": 1,
        "description": (
            "One firefighter in turnout gear and helmet wearing SCBA works "
            "inside the training tower with a ground ladder, attack hose, "
            "nozzle, life safety rope, and rescue equipment."
        ),
        "scene_type": "training tower",
        "activity": "ladder training",
        "people_count": 1,
        "apparatus": ["Engine"],
        "equipment": [
            "Ground ladder",
            "Attack hose",
            "Nozzle",
            "Life safety rope",
            "Rescue equipment",
            "SCBA"
        ],
        "keywords": ["firefighter", "turnout gear", "helmet", "training"],
        "community_score": 60,
        "recruitment_score": 76,
        "education_score": 72,
        "technical_score": 82,
        "overall_score": 84,
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
            "Firefighters speak with children and students at a school "
            "public education event near a hydrant."
        ),
        "scene_type": "public education",
        "activity": "public education",
        "people_count": 4,
        "apparatus": [],
        "equipment": ["Hydrant"],
        "keywords": ["children", "school", "prevention"],
        "community_score": 80,
        "recruitment_score": 55,
        "education_score": 88,
        "technical_score": 35,
        "overall_score": 78,
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
            fire_service = FireServiceIntelligenceService(database=db)

            add_media(db, 1)
            add_media(db, 2)

            db.save_ai_analysis(1, training_analysis())
            training_intelligence = media_service.generate_and_save(
                1,
                db.get_ai_analysis(1)
            )
            fire_training = db.get_fire_service_intelligence(1)

            assert fire_training["firefighter_count"] == 1, fire_training
            assert fire_training["group_size"] == "single", fire_training
            assert "turnout_gear" in fire_training["ppe"], fire_training
            assert "helmet" in fire_training["ppe"], fire_training
            assert "scba" in fire_training["ppe"], fire_training
            assert "ground_ladder" in fire_training["equipment"], fire_training
            assert "attack_hose" in fire_training["equipment"], fire_training
            assert "life_safety_rope" in fire_training["equipment"], fire_training
            assert fire_training["incident_classification"] == "training", fire_training
            assert fire_training["operational_activity"] in (
                "ladder_training",
                "ladder_operations"
            ), fire_training
            assert "training_tuesday" in fire_training["communications_uses"], fire_training
            assert "recruitment" in fire_training["communications_uses"], fire_training
            assert "officer_development" in fire_training["communications_uses"], fire_training
            assert "annual_report" in fire_training["communications_uses"], fire_training

            scored_training = db.get_media_intelligence(1)
            assert scored_training["fire_service_intelligence"], scored_training
            assert scored_training["communications_score"] > 0, scored_training

            plain_score = CommunicationsScoringService(database=db).score_media(
                {
                    **training_intelligence,
                    "fire_service_intelligence": None
                }
            )
            enriched_score = CommunicationsScoringService(database=db).score_media(
                db.get_media_intelligence(1)
            )
            assert enriched_score["communications_score"] >= plain_score[
                "communications_score"
            ], (enriched_score, plain_score)

            db.save_ai_analysis(2, public_education_analysis())
            media_service.generate_and_save(
                2,
                db.get_ai_analysis(2)
            )
            fire_education = fire_service.generate_and_save(
                2,
                db.get_ai_analysis(2)
            )

            assert fire_education["children_present"], fire_education
            assert fire_education["incident_classification"] == "public_education", fire_education
            assert "hydrant" in fire_education["equipment"], fire_education
            assert "community_education" in fire_education["communications_uses"], fire_education

            from gui.photo_viewer import PhotoViewer
            viewer = object.__new__(PhotoViewer)
            viewer.fire_service_intelligence = fire_training
            lines = PhotoViewer.fire_service_intelligence_lines(viewer)
            assert any("Incident: training" in line for line in lines), lines
            assert any("PPE:" in line for line in lines), lines
            assert any("Communications Uses:" in line for line in lines), lines

            operations = OperationsService(
                database=db,
                job_manager=None
            ).library_processing()
            assert operations["fire_service_intelligence_count"] == 2, operations
            assert operations["top_fire_service_incident_types"], operations
            assert operations["top_fire_service_opportunities"], operations

        finally:
            os.chdir(original)

    print("fire_service_intelligence smoke passed")


if __name__ == "__main__":
    main()
