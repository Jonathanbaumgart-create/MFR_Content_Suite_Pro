from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.opportunity_orchestration_service import OpportunityOrchestrationService


def add_media(db, index, filename, media_type="image"):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".mp4" if media_type == "video" else ".jpg",
            "type": media_type,
            "size": 1000 + index,
            "sha256": f"sprint48-hash-{index}",
            "first_seen_at": "2026-07-20T14:00:00+00:00"
        }
    )


def save_intelligence(db, media_id, values):

    db.save_ai_analysis(
        media_id,
        {
            "provider": "ollama",
            "model": "moondream:latest",
            "description": values.get("description", ""),
            "confidence": 86,
            "overall_score": 86,
            "community_score": values.get("community_score", 70),
            "recruitment_score": values.get("recruitment_score", 70),
            "education_score": values.get("education_score", 70),
            "technical_score": values.get("technical_score", 70),
            "review_status": values.get("review_status", "approved"),
            "trust_state": values.get("trust_state", "approved_real"),
            "last_analyzed": "2026-07-20T14:02:00+00:00"
        }
    )
    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": values.get("normalized_scene", "community"),
            "incident_type": values.get("incident_type", "community_event"),
            "primary_activity": values.get("primary_activity", "community_outreach"),
            "apparatus_tags": values.get("apparatus_tags", []),
            "equipment_tags": values.get("equipment_tags", []),
            "ppe_tags": values.get("ppe_tags", []),
            "people_tags": values.get("people_tags", ["firefighters"]),
            "content_tags": values.get("content_tags", []),
            "content_themes": values.get("content_themes", []),
            "recommended_uses": values.get("recommended_uses", []),
            "search_text": values.get("search_text", ""),
            "intelligence_score": values.get("intelligence_score", 88),
            "source_model": "moondream:latest"
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            add_media(db, 1, "daycare_spray_down_01.jpg")
            save_intelligence(
                db,
                1,
                {
                    "description": "Firefighters spraying water for children at a daycare community event.",
                    "primary_activity": "community outreach daycare spray down",
                    "content_tags": ["daycare", "community", "summer", "children"],
                    "content_themes": ["community", "summer safety"],
                    "recommended_uses": ["community engagement", "public education"],
                    "search_text": "daycare spray down firefighters children summer community"
                }
            )

            add_media(db, 2, "training_rope_rescue_01.jpg")
            save_intelligence(
                db,
                2,
                {
                    "description": "Firefighters practicing rope rescue training.",
                    "primary_activity": "rope rescue training",
                    "equipment_tags": ["rope", "rescue equipment"],
                    "ppe_tags": ["helmet", "gloves"],
                    "content_tags": ["training", "rope rescue", "recruitment"],
                    "content_themes": ["training", "recruitment"],
                    "recommended_uses": ["training", "recruitment"],
                    "search_text": "rope rescue training firefighters recruitment"
                }
            )

            add_media(db, 3, "helmet_cam_training.mp4", media_type="video")
            save_intelligence(
                db,
                3,
                {
                    "description": "Helmet camera training video.",
                    "primary_activity": "helmet camera training",
                    "content_tags": ["helmet camera", "training", "video"],
                    "recommended_uses": ["reel", "training"],
                    "search_text": "helmet cam helmet camera training reel video"
                }
            )
            db.save_helmet_camera_segments(
                3,
                [
                    {
                        "segment_id": "sprint48-helmet-1",
                        "media_id": 3,
                        "source_path": str(Path("library") / "helmet_cam_training.mp4"),
                        "start_seconds": 4,
                        "end_seconds": 16,
                        "duration_seconds": 12,
                        "reel_score": 92,
                        "technical_score": 90,
                        "stability_score": 80,
                        "orientation_score": 100,
                        "clarity_score": 80,
                        "exposure_score": 80,
                        "audio_score": 70,
                        "risk_level": "low",
                        "risk_flags": [],
                        "reason_selected": "Upright training sequence.",
                        "visual_summary": "Firefighter moving through a training evolution.",
                        "cover_frame_seconds": 8,
                        "status": "candidate",
                        "analysis_version": "smoke"
                    }
                ]
            )

            service = OpportunityOrchestrationService(database=db)
            command = service.command_center(force=True)

            assert command["title"] == "Communications Command Center", command
            assert command["top_packages"], command
            assert len(command["top_packages"]) <= 3, command["top_packages"]
            assert command["recommendations"], command
            assert command["recent_mfr_activity"] is not None, command
            assert command["ready_to_publish_media"], command
            assert command["communications_gaps"] is not None, command
            assert command["upcoming_programs"], command
            assert command["publishing_workflow"]["actions"], command
            assert command["daily_workflow"]["steps"], command
            assert command["planning_horizons"]["Today"] is not None, command
            assert command["metrics"]["provider_calls"] == 0, command["metrics"]

            top = command["top_packages"][0]
            assert top["facebook_caption"], top
            assert top["instagram_caption"], top
            assert "selected media" not in top["facebook_caption"].lower(), top
            assert "#MordenFireRescue" not in top["instagram_caption"], top

            draft = service.create_publication_draft(top)
            assert draft["persisted"], draft

            search = service.search("daycare", limit=5)
            assert search["groups"]["Post Opportunities"] or search["groups"]["Photos"], search
            assert "Historical MFR Posts" in search["groups"], search
            assert search["bounded"], search

            helmet_search = service.search("Helmet Cam", limit=5)
            assert "Helmet Camera Clips" in helmet_search["groups"], helmet_search

            from gui.home_page import HomePage
            from gui.content_director_page import ContentDirectorPage

            assert hasattr(HomePage, "render_search_results")
            assert hasattr(HomePage, "render_daily_workflow")
            assert hasattr(ContentDirectorPage, "load_proactive_brief")

        finally:
            os.chdir(original)

    print("sprint48 command center smoke passed")


if __name__ == "__main__":
    main()
