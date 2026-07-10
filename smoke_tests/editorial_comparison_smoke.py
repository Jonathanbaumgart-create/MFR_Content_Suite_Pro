from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communications_memory_service import CommunicationsMemoryService
from services.content_generation_service import ContentGenerationService
from services.editorial_comparison_service import EditorialComparisonService
from services.editorial_strategy_service import EditorialStrategyService
from services.media_intelligence_service import MediaIntelligenceService


def add_media(db, index):

    db.add_media(
        {
            "filename": f"editorial_comparison_{index}.jpg",
            "path": str(Path("library") / f"editorial_comparison_{index}.jpg"),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"editorial-comparison-hash-{index}"
        }
    )


def training_analysis():

    return {
        "media_id": 1,
        "description": (
            "Firefighter wearing turnout gear climbs a ground ladder during "
            "training tower ladder operations."
        ),
        "scene_type": "training tower",
        "activity": "ladder operations",
        "people_count": 1,
        "apparatus": ["Engine"],
        "equipment": ["Ground ladder", "SCBA", "Helmet"],
        "keywords": ["firefighter", "training", "recruitment"],
        "community_score": 62,
        "recruitment_score": 84,
        "education_score": 78,
        "technical_score": 88,
        "overall_score": 86,
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
                training_analysis()
            )
            MediaIntelligenceService(db).generate_and_save(
                1,
                db.get_ai_analysis(1)
            )

            strategy_service = EditorialStrategyService(database=db)
            strategies = strategy_service.generate_for_media(
                1,
                limit=5
            )
            comparison_service = EditorialComparisonService(
                database=db,
                strategy_service=strategy_service
            )
            comparison = comparison_service.compare(
                1,
                strategies=strategies
            )

            assert comparison["recommended_strategy"], comparison
            assert comparison["runner_up"], comparison
            assert comparison["tradeoffs"], comparison
            assert comparison["why_not_others"], comparison
            assert comparison["debate_summary"], comparison
            assert comparison["confidence"] > 0, comparison

            best = comparison["recommended_strategy"]
            runner_up = comparison["runner_up"]
            assert best["objective"] != runner_up["objective"], comparison
            assert best["target_audience"] != runner_up["target_audience"] or (
                best["call_to_action"] != runner_up["call_to_action"]
            ), comparison

            comparison_service.record_viewed(
                1,
                best
            )
            comparison_service.select_strategy(
                1,
                best
            )
            comparison_service.alternative_requested(
                1,
                runner_up
            )
            comparison_service.dismiss_strategy(
                1,
                runner_up
            )
            feedback = db.recommendation_feedback_rows(limit=20)
            assert any(
                row["notes"] == "strategy_selected"
                for row in feedback
            ), feedback
            assert any(
                row["notes"] == "strategy_dismissed"
                for row in feedback
            ), feedback

            stored = db.editorial_strategies_for_media(1)
            selected = [
                row
                for row in stored
                if row["strategy_id"] == best["strategy_id"]
            ][0]
            dismissed = [
                row
                for row in stored
                if row["strategy_id"] == runner_up["strategy_id"]
            ][0]
            assert selected["selected"], selected
            assert dismissed["dismissed"], dismissed

            metrics = db.editorial_metrics()
            assert metrics["media_with_editorial_strategies"] == 1, metrics
            assert metrics["strategy_acceptance_rate"] > 0, metrics

            recommendation = {
                "opportunity_type": "training_highlight",
                "title": "Training Highlight",
                "summary": "Stored recommendation for training media.",
                "caption_strategy": "Training highlight",
                "call_to_action": "Follow for more training updates.",
                "best_posting_time": "Evening",
                "recommended_platforms": ["Facebook", "Instagram"],
                "recommended_media": [
                    {
                        "media_id": 1,
                        "filename": "editorial_comparison_1.jpg",
                        "path": str(Path("library") / "editorial_comparison_1.jpg"),
                        "reason": "Strong training intelligence.",
                        "intelligence_score": 80
                    }
                ],
                "reasoning": ["No Vision AI required for package generation."]
            }
            assert "selected_editorial_strategy" not in recommendation
            recommendation["selected_editorial_strategy"] = best
            package = ContentGenerationService(database=db).generate_package(
                recommendation,
                editorial_strategy=best
            )
            assert package["editorial_strategy"]["strategy_id"] == best["strategy_id"], package
            assert package["facebook_caption"], package
            assert package["instagram_caption"], package

            memory = CommunicationsMemoryService(database=db)
            memory_result = memory.remember_strategy_package(
                package,
                best,
                recommendation
            )
            assert memory_result["post_id"], memory_result
            assert memory.media_memory(1)["posted_before"] is False, memory.media_memory(1)

            from gui.photo_viewer import PhotoViewer
            viewer = object.__new__(PhotoViewer)
            viewer.media_id = 1
            viewer.editorial = comparison_service
            viewer.format_list = PhotoViewer.format_list.__get__(viewer, PhotoViewer)
            lines = PhotoViewer.editorial_strategy_lines(viewer)
            assert any("Top Strategy:" in line for line in lines), lines

            assert not hasattr(comparison_service, "vision")
            assert not hasattr(comparison_service, "ai")

        finally:
            os.chdir(original)

    print("editorial_comparison smoke passed")


if __name__ == "__main__":
    main()
