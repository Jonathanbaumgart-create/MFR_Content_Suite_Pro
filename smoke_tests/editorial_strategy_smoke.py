from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.editorial_strategy_service import EditorialStrategyService
from services.media_intelligence_service import MediaIntelligenceService


def add_media(db, index):

    db.add_media(
        {
            "filename": f"editorial_strategy_{index}.jpg",
            "path": str(Path("library") / f"editorial_strategy_{index}.jpg"),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"editorial-strategy-hash-{index}"
        }
    )


def ladder_training_analysis():

    return {
        "media_id": 1,
        "description": (
            "One firefighter in turnout gear and helmet works from a ground "
            "ladder inside the training tower with SCBA and attack hose."
        ),
        "scene_type": "training tower",
        "activity": "ladder training",
        "people_count": 1,
        "apparatus": ["Engine"],
        "equipment": ["Ground ladder", "SCBA", "Attack hose"],
        "keywords": ["firefighter", "training", "ladder operations"],
        "community_score": 58,
        "recruitment_score": 82,
        "education_score": 76,
        "technical_score": 86,
        "overall_score": 84,
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
            add_media(db, 1)
            db.save_ai_analysis(
                1,
                ladder_training_analysis()
            )
            MediaIntelligenceService(db).generate_and_save(
                1,
                db.get_ai_analysis(1)
            )

            service = EditorialStrategyService(database=db)
            strategies = service.generate_for_media(
                1,
                limit=5,
                persist=True
            )

            assert len(strategies) >= 3, strategies
            assert len({item["objective"] for item in strategies[:3]}) == 3, strategies
            assert len({item["target_audience"] for item in strategies[:3]}) >= 2, strategies
            assert len({item["call_to_action"] for item in strategies[:3]}) == 3, strategies
            assert any(
                item["strategy_type"] == "training_highlight"
                for item in strategies
            ), strategies
            assert any(
                item["strategy_type"] == "recruitment"
                for item in strategies
            ), strategies
            assert all(item["supporting_evidence"] for item in strategies[:3]), strategies
            assert all(
                "Vision AI" in " ".join(item["limitations"])
                for item in strategies
            ), strategies

            stored = db.editorial_strategies_for_media(1)
            assert len(stored) >= 3, stored
            assert stored[0]["recommended_media"][0]["media_id"] == 1, stored

            counts = db.intelligence_filter_counts()
            assert counts.get("editorial_strategy"), counts
            page = db.get_intelligence_media_page(
                filters={
                    "editorial_strategy": [stored[0]["strategy_type"]]
                },
                sort_by="editorial_confidence",
                limit=10
            )
            assert page, page

            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")

        finally:
            os.chdir(original)

    print("editorial_strategy smoke passed")


if __name__ == "__main__":
    main()
