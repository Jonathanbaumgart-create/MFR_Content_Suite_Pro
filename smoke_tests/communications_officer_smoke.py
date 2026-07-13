import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communications_memory_service import CommunicationsMemoryService
from services.communications_officer_service import CommunicationsOfficerService
from services.time_service import TimeService


def add_media(db, index, filename, media_type="image", first_seen_at=None):

    extension = ".mp4" if media_type == "video" else ".jpg"
    db.add_media({
        "filename": filename,
        "path": str(Path("library") / filename),
        "extension": extension,
        "type": media_type,
        "size": 100 + index,
        "sha256": f"communications-officer-{index}",
        "first_seen_at": first_seen_at or TimeService.utc_now_iso()
    })


def save_analysis(db, media_id, trust_state="approved_real", review_status="approved", failure_reason=""):

    db.save_ai_analysis(
        media_id,
        {
            "description": "Reviewed fire service communications analysis.",
            "scene_type": "training",
            "activity": "training",
            "people_count": 3,
            "apparatus": ["Engine"],
            "equipment": ["Hose"],
            "keywords": ["training", "recruitment", "community"],
            "community_score": 88,
            "recruitment_score": 92,
            "education_score": 82,
            "technical_score": 80,
            "overall_score": 90,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": "moondream:latest",
            "analysis_duration": 0.1,
            "provider": "ollama",
            "retry_count": 0,
            "failure_reason": failure_reason,
            "last_analyzed": TimeService.utc_now_iso(),
            "trust_state": trust_state,
            "review_status": review_status
        }
    )


def save_intelligence(db, media_id, values):

    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": values.get("normalized_scene", "training"),
            "incident_type": values.get("incident_type", "training"),
            "primary_activity": values.get("primary_activity", "training"),
            "apparatus_tags": values.get("apparatus_tags", ["engine"]),
            "equipment_tags": values.get("equipment_tags", ["hose"]),
            "ppe_tags": values.get("ppe_tags", ["turnout_gear"]),
            "people_tags": values.get("people_tags", ["crew"]),
            "content_tags": values.get("content_tags", ["training", "recruitment"]),
            "content_themes": values.get("content_themes", ["training", "recruitment"]),
            "recommended_uses": values.get("recommended_uses", ["recruitment", "training_tuesday"]),
            "search_text": values.get("search_text", "training recruitment firefighter crew"),
            "intelligence_score": values.get("intelligence_score", 88),
            "source_model": "moondream:latest"
        }
    )
    db.save_communications_scores(
        media_id,
        {
            "communications_score": values.get("communications_score", 88),
            "communications_category_scores": {},
            "platform_suitability": values.get(
                "platform_suitability",
                {
                    "facebook": 90,
                    "instagram": 84,
                    "linkedin": 72,
                    "website": 66,
                    "annual_report": 70
                }
            ),
            "storytelling_score": values.get("storytelling_score", 86),
            "community_engagement_score": values.get("community_engagement_score", 80),
            "educational_value_score": values.get("educational_value_score", 76),
            "recruitment_value_score": values.get("recruitment_value_score", 94),
            "recognition_value_score": values.get("recognition_value_score", 72),
            "emergency_response_value_score": values.get("emergency_response_value_score", 35),
            "public_education_value_score": values.get("public_education_value_score", 68),
            "seasonal_relevance_score": values.get("seasonal_relevance_score", 58),
            "visual_impact_score": values.get("visual_impact_score", 82),
            "trust_building_score": values.get("trust_building_score", 84),
            "emotional_impact_score": values.get("emotional_impact_score", 78),
            "evergreen_score": values.get("evergreen_score", 76),
            "time_sensitive_score": values.get("time_sensitive_score", 45),
            "historical_importance_score": values.get("historical_importance_score", 50),
            "uniqueness_score": values.get("uniqueness_score", 70),
            "posting_frequency_risk": values.get("posting_frequency_risk", 0),
            "suggested_campaigns": values.get("suggested_campaigns", ["Recruitment"]),
            "suggested_audience": values.get("suggested_audience", ["Prospective firefighters", "Morden residents"]),
            "suggested_platform": values.get("suggested_platform", "facebook"),
            "suggested_time_of_year": "Any time",
            "communications_reasoning": ["Reviewed media has strong recruitment and training value."]
        }
    )


def save_fire(db, media_id):

    db.save_fire_service_intelligence(
        media_id,
        {
            "firefighter_count": 3,
            "civilian_count": 0,
            "officer_presence": False,
            "children_present": False,
            "group_size": "small_group",
            "personnel": ["firefighters"],
            "ppe": ["turnout_gear"],
            "equipment": ["hose"],
            "apparatus": ["engine"],
            "incident_classification": "training",
            "operational_activity": "training",
            "communications_uses": ["recruitment", "training_tuesday"],
            "reasoning": ["Reviewed training media supports recruitment."],
            "operational_context": "training",
            "operational_skills": ["hose_operations"],
            "communications_intent": ["recruitment", "training_tuesday"],
            "operational_confidence": 88,
            "reasoning_evidence": ["turnout gear", "hose", "crew"],
            "operational_reasoning": ["Training context is clear."],
            "source_model": "fire-service-v2"
        }
    )


def seed(db):

    now = TimeService.utc_now()
    yesterday = now - timedelta(days=1)

    add_media(db, 1, "approved_training.jpg", first_seen_at=yesterday.isoformat(timespec="seconds"))
    save_analysis(db, 1, "approved_real", "approved")
    save_intelligence(db, 1, {"communications_score": 92, "recruitment_value_score": 96})
    save_fire(db, 1)

    add_media(db, 2, "corrected_training.jpg", first_seen_at=yesterday.isoformat(timespec="seconds"))
    save_analysis(db, 2, "corrected_real", "corrected")
    save_intelligence(db, 2, {"communications_score": 88, "storytelling_score": 90})
    save_fire(db, 2)

    add_media(db, 3, "approved_training_video.mp4", media_type="video", first_seen_at=yesterday.isoformat(timespec="seconds"))
    save_analysis(db, 3, "approved_real", "approved")
    save_intelligence(db, 3, {"communications_score": 86, "storytelling_score": 84})
    save_fire(db, 3)

    add_media(db, 4, "rejected_high_score.jpg", first_seen_at=yesterday.isoformat(timespec="seconds"))
    save_analysis(db, 4, "rejected_real", "rejected")
    save_intelligence(db, 4, {"communications_score": 99, "storytelling_score": 99})
    save_fire(db, 4)

    add_media(db, 5, "failed_high_score.jpg", first_seen_at=yesterday.isoformat(timespec="seconds"))
    save_analysis(db, 5, "failed", "review_required", failure_reason="Provider failed")
    save_intelligence(db, 5, {"communications_score": 97})
    save_fire(db, 5)

    add_media(db, 6, "unreviewed_training.jpg", first_seen_at=yesterday.isoformat(timespec="seconds"))
    save_analysis(db, 6, "unreviewed_real", "review_required")
    save_intelligence(db, 6, {"communications_score": 89})
    save_fire(db, 6)

    memory = CommunicationsMemoryService(db)
    memory.remember_post({
        "platform": "facebook",
        "post_date": (datetime.now(timezone.utc) - timedelta(days=20)).date().isoformat(),
        "caption": "Training night with crews practicing hose operations.",
        "campaign": "Training",
        "opportunity_type": "training",
        "media_ids": [1],
        "imported": True
    })


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed(db)
            service = CommunicationsOfficerService(database=db)
            brief = service.generate()

            assert brief["title"] == "AI Communications Officer Morning Brief", brief
            assert brief["summary"]["new_media_added_yesterday"] >= 3, brief
            assert brief["summary"]["review_queue_size"] >= 1, brief
            assert brief["summary"]["approved_media_count"] >= 2, brief
            assert brief["summary"]["corrected_media_count"] >= 1, brief
            assert brief["summary"]["failed_analysis_count"] >= 1, brief
            assert brief["videos_awaiting_review"] >= 0, brief
            assert brief["communications_memory_status"]["total_posts"] >= 1, brief

            opportunities = brief["top_three_communication_opportunities"]
            assert opportunities, brief
            top = opportunities[0]
            assert top["uses_reviewed_media"], top
            assert top["why_today_matters"], top
            assert top["why_public_would_care"], top
            assert top["why_it_should_outperform"], top
            assert top["positive_factors"], top
            assert top["source_signals"], top

            package = top["media_package"]
            assert package["communications_score"] > 0, package
            assert package["best_photo"] or package["best_video"], package

            all_package_files = " ".join(
                str(value)
                for value in [
                    package.get("best_photo", {}).get("filename", ""),
                    package.get("best_video", {}).get("filename", ""),
                    package.get("supporting_photos", []),
                    package.get("supporting_videos", [])
                ]
            )
            assert "rejected_high_score" not in all_package_files, package
            assert "failed_high_score" not in all_package_files, package

            assert brief["highest_confidence_editorial_recommendation"], brief
            assert brief["recommended_media_package"], brief
            assert service.last_metrics["ran_on_main_thread"] is True

        finally:
            os.chdir(original)

    print("communications officer smoke passed")


if __name__ == "__main__":
    main()
