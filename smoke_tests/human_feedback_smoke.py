from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communications_scoring_service import CommunicationsScoringService
from services.human_feedback_service import HumanFeedbackService
from services.media_intelligence_service import MediaIntelligenceService
from services.operations_service import OperationsService


def add_media(db, index, filename):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"human-feedback-hash-{index}"
        }
    )


def analysis(media_id, description):

    return {
        "media_id": media_id,
        "description": description,
        "scene_type": "unknown",
        "activity": "unknown",
        "people_count": 0,
        "apparatus": [],
        "equipment": ["Ground ladder"],
        "keywords": ["ground ladder", "training tower"],
        "community_score": 40,
        "recruitment_score": 55,
        "education_score": 50,
        "technical_score": 70,
        "overall_score": 62,
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
            media_service = MediaIntelligenceService(db)

            add_media(db, 1, "ladder_training_1.jpg")
            add_media(db, 2, "ladder_training_2.jpg")
            add_media(db, 3, "community_event.jpg")

            db.save_ai_analysis(
                1,
                analysis(
                    1,
                    "Ground ladder at the training tower with firefighter gear visible."
                )
            )
            db.save_ai_analysis(
                2,
                analysis(
                    2,
                    "Ground ladder training tower drill with helmet and hose nearby."
                )
            )
            db.save_ai_analysis(
                3,
                {
                    **analysis(3, "Community open house with families."),
                    "equipment": [],
                    "keywords": ["community", "open house"],
                    "community_score": 82
                }
            )

            for media_id in (1, 2, 3):
                media_service.generate_and_save(
                    media_id,
                    db.get_ai_analysis(media_id)
                )

            feedback = HumanFeedbackService(db)

            raw_analysis = db.get_ai_analysis(1)
            assert raw_analysis["people_count"] == 0, raw_analysis

            feedback.save_correction(
                1,
                "people_count",
                1,
                notes="Firefighter visible."
            )
            feedback.save_correction(
                1,
                "operational_skills",
                ["ladder_operations"],
                notes="Ground ladder in training tower."
            )
            feedback.save_correction(
                1,
                "communications_uses",
                ["training_tuesday", "recruitment"],
                notes="Strong training content."
            )

            effective = feedback.effective_media_intelligence(1)
            assert effective["people_count"] == 1, effective
            assert "ladder_operations" in effective["operational_skills"], effective
            assert "training_tuesday" in effective["communications_uses"], effective
            assert effective["analysis"]["people_count"] == 1, effective
            assert db.get_ai_analysis(1)["people_count"] == 0, db.get_ai_analysis(1)

            history = feedback.history_for_media(1)
            assert len(history) >= 3, history
            assert any(row["field_name"] == "people_count" for row in history), history

            scored = CommunicationsScoringService(database=db).score_media(
                feedback.effective_media_intelligence_row(1)
            )
            assert scored["communications_score"] > 0, scored

            feedback.reset_field(
                1,
                "people_count"
            )
            reset_effective = feedback.effective_media_intelligence(1)
            assert reset_effective["people_count"] == feedback.inferred_value(
                1,
                "people_count"
            ), reset_effective
            assert any(
                row["action"] == "reset"
                for row in feedback.history_for_media(1)
            )

            feedback.save_correction(
                1,
                "people_count",
                1
            )
            feedback.save_correction(
                2,
                "people_count",
                1
            )
            patterns = db.correction_patterns()
            assert any(
                pattern["field_name"] == "people_count"
                for pattern in patterns
            ), patterns

            suggestions = feedback.similar_media_suggestions(
                1,
                limit=5
            )
            assert suggestions, suggestions
            assert suggestions[0]["id"] != 1, suggestions

            operations = OperationsService(
                database=db,
                job_manager=None
            ).communications_readiness()
            metrics = operations["human_feedback"]
            assert metrics["corrected_media_count"] >= 2, metrics
            assert metrics["active_corrections"] >= 3, metrics
            assert metrics["correction_patterns_found"] >= 1, metrics

            counts = db.intelligence_filter_counts().get("review_status")
            assert counts, counts
            page = db.get_intelligence_media_page(
                filters={"review_status": ["human_corrected"]},
                sort_by="correction_count",
                limit=10
            )
            assert page, page

            from gui.photo_viewer import PhotoViewer, CorrectionDialog

            viewer = object.__new__(PhotoViewer)
            viewer.effective_intelligence = feedback.effective_media_intelligence(1)
            viewer.format_list = PhotoViewer.format_list.__get__(viewer, PhotoViewer)
            viewer.format_value = PhotoViewer.format_value.__get__(viewer, PhotoViewer)
            lines = PhotoViewer.correction_history_lines(viewer)
            assert any("people_count" in line for line in lines), lines
            assert CorrectionDialog.FIELD_LABELS["people_count"] == "People Count"

            assert not hasattr(feedback, "vision")
            assert not hasattr(feedback, "ai")

        finally:
            os.chdir(original)

    print("human_feedback smoke passed")


if __name__ == "__main__":
    main()
