import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from gui.gallery_page import GalleryPage
from gui.photo_card import PhotoCard
from gui.photo_viewer import PhotoViewer
from services.analysis_review_service import AnalysisReviewService
from services.cache_invalidation_service import CacheInvalidationService
from services.human_feedback_service import HumanFeedbackService
from services.photo_review_workflow_service import PhotoReviewWorkflowService


def add_media(db, media_id, filename, media_type="image"):
    suffix = ".mp4" if media_type == "video" else ".jpg"
    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO media(id, filename, path, extension, media_type, filesize, sha256)
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            media_id,
            filename,
            str(Path(filename).resolve()),
            suffix,
            media_type,
            123,
            f"review-hash-{media_id}"
        )
    )
    conn.commit()
    conn.close()


def sample_analysis(trust_state="unreviewed_real", review_status="review_required", provider="ollama", failure=""):
    return {
        "description": "A firefighter in turnout gear is completing ladder training.",
        "scene_type": "training ground",
        "activity": "ladder training",
        "people_count": 1,
        "apparatus": [],
        "equipment": ["ladder", "helmet"],
        "keywords": ["training", "ladder"],
        "community_score": 35,
        "recruitment_score": 70,
        "education_score": 55,
        "technical_score": 80,
        "overall_score": 82,
        "model": "qwen2.5vl:7b" if provider == "ollama" else "mock",
        "provider": provider,
        "retry_count": 0,
        "failure_reason": failure,
        "raw_response": "{\"description\":\"ladder training\"}",
        "parse_status": "valid_structured_response",
        "parse_warnings": [],
        "confidence": 0.86,
        "quality_state": "review_required",
        "trust_state": trust_state,
        "review_status": review_status,
        "quality_warnings": [],
        "media_context": "physical_scene"
    }


def main():
    original_cwd = os.getcwd()

    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            db = DatabaseManager()
            db.initialize()

            for media_id in range(1, 7):
                add_media(
                    db,
                    media_id,
                    f"review-{media_id}.jpg",
                    "video" if media_id == 6 else "image"
                )

            db.save_ai_analysis(1, sample_analysis())
            db.save_ai_analysis(2, sample_analysis())
            db.save_ai_analysis(3, sample_analysis("approved_real", "approved"))
            db.save_ai_analysis(4, sample_analysis("rejected_real", "rejected"))
            db.save_ai_analysis(5, sample_analysis("mock", "mock", provider="mock"))
            db.save_ai_analysis(6, sample_analysis())

            workflow = PhotoReviewWorkflowService(database=db)
            context = workflow.context_from_ids(
                [1, 2, 6],
                1,
                label="Review Required",
                review_required_only=True
            )
            assert context["position"] == 0, context
            assert workflow.next_id(context, 1, skip_removed=False) == 2
            assert workflow.previous_id(context, 2) == 1
            assert workflow.first_id(context) == 1
            assert workflow.last_id(context) == 6
            assert len(context["ids"]) == 3, context

            preview = workflow.approve_selected_preview([1, 3, 4, 5, 6])
            assert preview["eligible_ids"] == [1, 6], preview
            assert preview["ineligible_count"] == 3, preview

            result = workflow.approve_selected([1, 3, 4, 5, 6])
            assert result["approved_count"] == 2, result
            assert db.get_ai_analysis(1)["review_status"] == "approved"
            assert db.get_ai_analysis(6)["review_status"] == "approved"
            assert db.get_ai_analysis(4)["review_status"] == "rejected"
            assert db.get_ai_analysis(5)["provider"] == "mock"
            assert len(db.analysis_review_history(1)) == 1
            assert CacheInvalidationService.latest()["reason"] == "bulk_review_approve"

            review = AnalysisReviewService(database=db)
            rejected = review.reject(2, notes="Weak analysis")
            assert rejected["review_status"] == "rejected", rejected
            workflow.record_session_action(context, "approved")
            workflow.record_session_action(context, "rejected")
            workflow.remove_reviewed_from_queue(context, 1)
            assert 1 not in context["ids"], context
            assert workflow.next_id(context, 1, skip_removed=True) == 2

            feedback = HumanFeedbackService(database=db)
            feedback.save_correction(
                3,
                "primary_activity",
                "ladder operations",
                correction_source="Jonathan",
                notes="Corrected during review smoke"
            )
            corrected = db.get_ai_analysis(3)
            assert corrected["trust_state"] == "corrected_real", corrected
            history = db.analysis_review_history(3)
            assert history[0]["decision"] == "correct", history

            reanalysis = review.request_reanalysis(3, notes="Try again")
            assert reanalysis["review_status"] == "reanalyze_requested", reanalysis

            assert hasattr(PhotoViewer, "navigate_next")
            assert hasattr(PhotoViewer, "shortcut_blocked")
            assert hasattr(PhotoViewer, "approve_and_advance_shortcut")
            assert hasattr(PhotoViewer, "after_review_action")
            assert hasattr(GalleryPage, "approve_selected_review_items")
            assert hasattr(GalleryPage, "quick_approve_media")
            assert hasattr(GalleryPage, "quick_reject_media")
            assert hasattr(GalleryPage, "review_state_changed")
            assert hasattr(PhotoCard, "quick_review_allowed")

            eligible_card = PhotoCard.__new__(PhotoCard)
            eligible_card.analysis_status = "Real - Review Required"
            assert PhotoCard.quick_review_allowed(eligible_card)
            ineligible_card = PhotoCard.__new__(PhotoCard)
            ineligible_card.analysis_status = "Real - Approved"
            assert not PhotoCard.quick_review_allowed(ineligible_card)

            metrics = review.metrics()
            assert metrics["review_approved"] >= 1, metrics
            assert metrics["review_rejected"] >= 1, metrics
            assert db.analysis_review_eligible_ids([1, 2, 3, 4, 5, 6]) == [], metrics
        finally:
            os.chdir(original_cwd)

    print("photo_review_workflow_smoke passed")


if __name__ == "__main__":
    main()
