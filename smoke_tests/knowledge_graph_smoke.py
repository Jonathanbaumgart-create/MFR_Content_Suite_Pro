from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.content_director_service import ContentDirectorService
from services.fire_service_intelligence_service import FireServiceIntelligenceService
from services.knowledge_graph_service import KnowledgeGraphService
from services.media_intelligence_service import MediaIntelligenceService
from services.operations_service import OperationsService


def add_media(db, index):

    db.add_media(
        {
            "filename": f"knowledge_graph_{index}.jpg",
            "path": str(Path("library") / f"knowledge_graph_{index}.jpg"),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"knowledge-graph-hash-{index}"
        }
    )


def ladder_training_analysis():

    return {
        "media_id": 1,
        "description": (
            "Firefighter in turnout gear and helmet climbs a ground ladder "
            "inside the training tower during a drill."
        ),
        "scene_type": "training tower",
        "activity": "ladder training",
        "people_count": 1,
        "apparatus": ["Engine"],
        "equipment": ["Ground ladder"],
        "keywords": ["firefighter", "training", "turnout gear", "helmet"],
        "community_score": 60,
        "recruitment_score": 78,
        "education_score": 70,
        "technical_score": 88,
        "overall_score": 86,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": "stored-test",
        "provider": "mock",
        "retry_count": 0,
        "failure_reason": ""
    }


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            graph = KnowledgeGraphService(database=db)

            engine_id = graph.create_entity(
                "Engine 144",
                "Apparatus",
                description="Front-line engine.",
                aliases=["E144", "Engine One Forty Four"],
                confidence=90
            )
            hose_id = graph.create_entity(
                "Attack Line",
                "Equipment",
                description="Attack hose carried on engine apparatus.",
                aliases=["attack_line"],
                confidence=88
            )
            assert engine_id, engine_id
            assert hose_id, hose_id

            relationship_id = graph.create_relationship(
                "Engine 144",
                "carries",
                "Attack Line",
                confidence=91,
                description="Engine carries attack hose."
            )
            assert relationship_id, relationship_id

            assert graph.resolve_entity("E144")["name"] == "Engine 144"
            assert any(
                row["name"] == "Engine 144"
                for row in graph.search("one forty four")
            )
            related = graph.related_entities(
                "Engine 144",
                depth=1
            )
            assert any(row["name"] == "Attack Line" for row in related), related

            expanded = graph.reasoning_context(
                [
                    "ground_ladder"
                ]
            )
            assert "ladder_operations" in expanded["operational_skills"], expanded
            assert "training_tuesday" in expanded["communications_intent"], expanded
            assert "recruitment" in expanded["communications_intent"], expanded

            add_media(db, 1)
            db.save_ai_analysis(
                1,
                ladder_training_analysis()
            )
            media_service = MediaIntelligenceService(db)
            media_service.generate_and_save(
                1,
                db.get_ai_analysis(1)
            )
            fire_service = FireServiceIntelligenceService(database=db)
            fire = fire_service.generate_and_save(
                1,
                db.get_ai_analysis(1)
            )
            assert "ladder_operations" in fire["operational_skills"], fire
            assert "training_tuesday" in fire["communications_intent"], fire
            assert any(
                "Knowledge graph connects" in line
                for line in fire["operational_reasoning"]
            ), fire

            recommendation = ContentDirectorService(
                database=db
            ).recommend(
                prompt="need recruitment content",
                limit=1
            )
            assert recommendation["recommendations"], recommendation
            top = recommendation["recommendations"][0]
            assert top["media_id"] == 1, top

            health = graph.health()
            assert health["entities"] >= 10, health
            assert health["relationships"] >= 10, health

            operations = OperationsService(
                database=db,
                job_manager=None
            ).knowledge_health()
            assert operations["knowledge_graph_entities"] >= 10, operations
            assert operations["knowledge_graph_relationships"] >= 10, operations

            assert not hasattr(graph, "vision")
            assert not hasattr(graph, "ai")

        finally:
            os.chdir(original)

    print("knowledge_graph smoke passed")


if __name__ == "__main__":
    main()
