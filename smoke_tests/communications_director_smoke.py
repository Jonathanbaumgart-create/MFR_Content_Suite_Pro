from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager


def add_media(db, index, filename):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"communications-director-hash-{index}"
        }
    )


def save_analysis(db, media_id, scores):

    db.save_ai_analysis(
        media_id,
        {
            "description": "Stored analysis for communications smoke test.",
            "scene_type": "training",
            "activity": "hose line training",
            "people_count": 4,
            "apparatus": ["Engine"],
            "equipment": ["Hose", "SCBA"],
            "keywords": ["training", "recruitment", "community"],
            "community_score": scores.get("community", 75),
            "recruitment_score": scores.get("recruitment", 75),
            "education_score": scores.get("education", 75),
            "technical_score": scores.get("technical", 75),
            "overall_score": scores.get("overall", 80),
            "facebook_caption": "",
            "instagram_caption": "",
            "model": "mock",
            "analysis_duration": 0.1,
            "provider": "mock",
            "retry_count": 0,
            "failure_reason": ""
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
            "equipment_tags": values.get("equipment_tags", ["hose", "scba"]),
            "ppe_tags": values.get("ppe_tags", ["turnout_gear"]),
            "people_tags": values.get("people_tags", ["crew"]),
            "content_tags": values.get("content_tags", []),
            "content_themes": values.get("content_themes", []),
            "recommended_uses": values.get("recommended_uses", []),
            "search_text": values.get("search_text", ""),
            "intelligence_score": values.get("intelligence_score", 85),
            "source_model": "mock"
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:

            db = DatabaseManager()

            add_media(db, 1, "recruitment_training.jpg")
            save_analysis(
                db,
                1,
                {
                    "community": 82,
                    "recruitment": 94,
                    "education": 76,
                    "technical": 88,
                    "overall": 91
                }
            )
            save_intelligence(
                db,
                1,
                {
                    "content_tags": ["training", "recruitment", "crew", "scba"],
                    "content_themes": ["recruitment", "technical_training"],
                    "recommended_uses": ["recruitment", "training", "social_media"],
                    "search_text": "training recruitment crew scba engine",
                    "intelligence_score": 94
                }
            )

            add_media(db, 2, "community_open_house.jpg")
            save_analysis(
                db,
                2,
                {
                    "community": 96,
                    "recruitment": 55,
                    "education": 80,
                    "technical": 40,
                    "overall": 86
                }
            )
            save_intelligence(
                db,
                2,
                {
                    "normalized_scene": "community",
                    "incident_type": "community_event",
                    "primary_activity": "community_outreach",
                    "content_tags": ["community", "public_education"],
                    "content_themes": ["community", "public_education"],
                    "recommended_uses": ["community_outreach", "social_media"],
                    "search_text": "community open house education",
                    "intelligence_score": 90
                }
            )

            add_media(db, 3, "apparatus_engine.jpg")
            save_analysis(
                db,
                3,
                {
                    "community": 65,
                    "recruitment": 60,
                    "education": 50,
                    "technical": 88,
                    "overall": 82
                }
            )
            save_intelligence(
                db,
                3,
                {
                    "normalized_scene": "station",
                    "incident_type": "unknown",
                    "primary_activity": "apparatus_display",
                    "apparatus_tags": ["engine"],
                    "content_tags": ["apparatus", "engine", "station"],
                    "content_themes": ["community"],
                    "recommended_uses": ["social_media"],
                    "search_text": "apparatus engine station",
                    "intelligence_score": 87
                }
            )

            from services.communications_director import CommunicationsDirector

            director = CommunicationsDirector(db)

            assert "recruitment" in director.interpret_prompt(
                "need a recruitment post"
            )
            assert "storm_safety" in director.interpret_prompt(
                "storm coming tonight"
            )

            opportunities = director.generate_opportunities(
                "need a recruitment post"
            )
            assert opportunities, opportunities

            opportunity = opportunities[0]
            assert opportunity["title"] == "Recruitment", opportunity
            assert opportunity["recommended_media"], opportunity
            assert opportunity["reasoning"], opportunity
            assert opportunity["recommended_platforms"], opportunity
            assert opportunity["best_posting_time"], opportunity
            assert opportunity["priority"] in ("High", "Medium", "Low")
            assert opportunity["confidence"] > 0
            assert opportunity["caption_theme"], opportunity
            assert opportunity["hashtags"], opportunity
            assert opportunity["call_to_action"], opportunity
            assert opportunity["estimated_engagement"], opportunity

            brief = director.todays_brief()
            assert brief["top_opportunities"], brief
            assert brief["recommendations"], brief
            assert brief["library_health"]["total_media"] == 3, brief
            assert "processing_status" in brief, brief
            assert "upcoming_seasonal_opportunities" in brief, brief
            assert "content_gaps" in brief, brief

            insights = director.library_insights()
            assert insights["media_with_intelligence"] == 3, insights
            assert insights["most_common_incident"]["count"] >= 1, insights
            assert "community_content_percentage" in insights, insights
            assert "unused_high_value_media" in insights, insights

            gaps = director.content_gaps()
            assert isinstance(gaps, list), gaps
            assert not hasattr(director, "vision")
            assert not hasattr(director, "ai")

        finally:
            os.chdir(original)

    print("communications_director smoke passed")


if __name__ == "__main__":
    main()
