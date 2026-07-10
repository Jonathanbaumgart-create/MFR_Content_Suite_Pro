from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communications_memory_service import CommunicationsMemoryService
from services.daily_brief_service import DailyBriefService
from services.editorial_recommendation_service import EditorialRecommendationService
from services.recommendation_candidate_service import RecommendationCandidateService
from services.recommendation_scoring_service import RecommendationScoringService


def add_media(db, index, filename, media_type="image"):

    extension = ".mp4" if media_type == "video" else ".jpg"

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": extension,
            "type": media_type,
            "size": 100 + index,
            "sha256": f"editorial-recommendation-hash-{index}"
        }
    )


def save_analysis(db, media_id, values=None):

    values = values or {}
    db.save_ai_analysis(
        media_id,
        {
            "description": values.get("description", "Stored local analysis."),
            "scene_type": values.get("scene_type", "training"),
            "activity": values.get("activity", "training"),
            "people_count": values.get("people_count", 3),
            "apparatus": values.get("apparatus", ["Engine"]),
            "equipment": values.get("equipment", ["Hose"]),
            "keywords": values.get("keywords", ["training", "community"]),
            "community_score": values.get("community_score", 80),
            "recruitment_score": values.get("recruitment_score", 80),
            "education_score": values.get("education_score", 80),
            "technical_score": values.get("technical_score", 80),
            "overall_score": values.get("overall_score", 80),
            "facebook_caption": "",
            "instagram_caption": "",
            "model": values.get("model", "moondream:latest"),
            "analysis_duration": 0.1,
            "provider": values.get("provider", "ollama"),
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
            "equipment_tags": values.get("equipment_tags", ["hose"]),
            "ppe_tags": values.get("ppe_tags", ["turnout_gear"]),
            "people_tags": values.get("people_tags", ["crew"]),
            "content_tags": values.get("content_tags", ["training"]),
            "content_themes": values.get("content_themes", ["training"]),
            "recommended_uses": values.get("recommended_uses", ["training"]),
            "search_text": values.get("search_text", "training crew"),
            "intelligence_score": values.get("intelligence_score", 85),
            "source_model": values.get("source_model", "moondream:latest")
        }
    )

    if values.get("communications_score"):
        db.save_communications_scores(
            media_id,
            {
                "communications_score": values.get("communications_score", 80),
                "communications_category_scores": {},
                "platform_suitability": values.get(
                    "platform_suitability",
                    {
                        "facebook": 86,
                        "instagram": 80,
                        "linkedin": 72,
                        "website": 70,
                        "annual_report": 68
                    }
                ),
                "storytelling_score": values.get("storytelling_score", 80),
                "community_engagement_score": values.get("community_engagement_score", 75),
                "educational_value_score": values.get("educational_value_score", 70),
                "recruitment_value_score": values.get("recruitment_value_score", 80),
                "recognition_value_score": values.get("recognition_value_score", 60),
                "emergency_response_value_score": values.get("emergency_response_value_score", 40),
                "public_education_value_score": values.get("public_education_value_score", 60),
                "seasonal_relevance_score": values.get("seasonal_relevance_score", 50),
                "visual_impact_score": values.get("visual_impact_score", 82),
                "trust_building_score": values.get("trust_building_score", 75),
                "emotional_impact_score": values.get("emotional_impact_score", 78),
                "evergreen_score": values.get("evergreen_score", 72),
                "time_sensitive_score": values.get("time_sensitive_score", 35),
                "historical_importance_score": values.get("historical_importance_score", 55),
                "uniqueness_score": values.get("uniqueness_score", 70),
                "posting_frequency_risk": values.get("posting_frequency_risk", 0),
                "suggested_campaigns": values.get("suggested_campaigns", ["Recruitment"]),
                "suggested_audience": values.get("suggested_audience", ["Prospective firefighters"]),
                "suggested_platform": values.get("suggested_platform", "facebook"),
                "suggested_time_of_year": values.get("suggested_time_of_year", "Any time"),
                "communications_reasoning": values.get("communications_reasoning", ["Strong stored local intelligence."])
            }
        )


def save_fire(db, media_id, values=None):

    values = values or {}
    db.save_fire_service_intelligence(
        media_id,
        {
            "firefighter_count": values.get("firefighter_count", 2),
            "civilian_count": values.get("civilian_count", 0),
            "officer_presence": values.get("officer_presence", False),
            "children_present": values.get("children_present", False),
            "group_size": values.get("group_size", "small_group"),
            "personnel": values.get("personnel", ["firefighters"]),
            "ppe": values.get("ppe", ["turnout_gear"]),
            "equipment": values.get("equipment", ["hose"]),
            "apparatus": values.get("apparatus", ["engine"]),
            "incident_classification": values.get("incident_classification", "training"),
            "operational_activity": values.get("operational_activity", "training"),
            "communications_uses": values.get("communications_uses", ["training_tuesday", "recruitment"]),
            "reasoning": values.get("reasoning", ["Stored fire service reasoning."]),
            "operational_context": values.get("operational_context", "training"),
            "operational_skills": values.get("operational_skills", ["hose_operations"]),
            "communications_intent": values.get("communications_intent", ["recruitment", "training_tuesday"]),
            "operational_confidence": values.get("operational_confidence", 86),
            "reasoning_evidence": values.get("reasoning_evidence", []),
            "operational_reasoning": values.get("operational_reasoning", ["Training context is clear."]),
            "source_model": values.get("source_model", "fire-service-v2")
        }
    )


def seed(db):

    add_media(db, 1, "recruitment_training_1.jpg")
    save_analysis(db, 1)
    save_intelligence(
        db,
        1,
        {
            "content_tags": ["training", "recruitment", "firefighter", "teamwork"],
            "content_themes": ["recruitment", "training"],
            "recommended_uses": ["recruitment", "training_tuesday"],
            "search_text": "training recruitment firefighter crew teamwork",
            "intelligence_score": 92,
            "communications_score": 91,
            "recruitment_value_score": 94,
            "storytelling_score": 88,
            "visual_impact_score": 86
        }
    )
    save_fire(db, 1)

    add_media(db, 2, "recruitment_training_video.mp4", media_type="video")
    save_analysis(db, 2)
    save_intelligence(
        db,
        2,
        {
            "content_tags": ["training", "recruitment", "crew"],
            "content_themes": ["recruitment", "training"],
            "recommended_uses": ["recruitment", "short_form_video"],
            "search_text": "training recruitment video crew",
            "intelligence_score": 84,
            "communications_score": 86,
            "recruitment_value_score": 88,
            "storytelling_score": 86,
            "visual_impact_score": 80,
            "platform_suitability": {
                "facebook": 84,
                "instagram": 82,
                "linkedin": 78,
                "website": 60,
                "annual_report": 58
            }
        }
    )
    save_fire(db, 2)

    add_media(db, 3, "training_recent.jpg")
    save_analysis(db, 3)
    save_intelligence(
        db,
        3,
        {
            "content_tags": ["training", "hose", "scba"],
            "content_themes": ["training"],
            "recommended_uses": ["training_tuesday"],
            "search_text": "training hose scba drill",
            "intelligence_score": 88,
            "communications_score": 84,
            "educational_value_score": 88,
            "recruitment_value_score": 76
        }
    )
    save_fire(db, 3)

    add_media(db, 4, "weak_public_education.jpg")
    save_analysis(
        db,
        4,
        {
            "community_score": 40,
            "education_score": 42,
            "overall_score": 38,
            "provider": "mock",
            "model": "mock"
        }
    )
    save_intelligence(
        db,
        4,
        {
            "normalized_scene": "public_education",
            "incident_type": "public_education",
            "primary_activity": "unknown",
            "content_tags": ["public_education", "safety"],
            "content_themes": ["public_education"],
            "recommended_uses": ["public_education"],
            "search_text": "public education safety",
            "intelligence_score": 42,
            "communications_score": 35,
            "source_model": "mock"
        }
    )

    from services.human_feedback_service import HumanFeedbackService

    HumanFeedbackService(db).save_correction(
        4,
        "incident_classification",
        "recruitment",
        notes="Test correction should affect recommendation terms."
    )

    memory = CommunicationsMemoryService(db)
    recent = (datetime.now() - timedelta(days=5)).date().isoformat()
    older = (datetime.now() - timedelta(days=90)).date().isoformat()

    memory.remember_post(
        {
            "platform": "facebook",
            "post_date": recent,
            "caption": "Training night with crews practicing hose operations.",
            "campaign": "Training",
            "opportunity_type": "training",
            "media_ids": [3],
            "imported": True
        }
    )
    memory.remember_post(
        {
            "platform": "facebook",
            "post_date": older,
            "caption": "Community event with firefighters and families.",
            "campaign": "Community",
            "opportunity_type": "community_events",
            "media_ids": [],
            "imported": True
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            empty = DatabaseManager()
            empty_service = EditorialRecommendationService(database=empty)
            assert empty_service.generate_recommendations() == []

            db = DatabaseManager()
            seed(db)

            candidate_service = RecommendationCandidateService(database=db)
            scoring_service = RecommendationScoringService()
            service = EditorialRecommendationService(
                database=db,
                candidate_service=candidate_service,
                scoring_service=scoring_service
            )

            first = service.generate_recommendations(limit=10)
            second = service.generate_recommendations(limit=10)

            assert first, first
            assert [item["recommendation_id"] for item in first] == [
                item["recommendation_id"] for item in second
            ], (first, second)
            assert len(first) <= 10

            top = first[0]
            assert top["scoring_version"] == scoring_service.SCORING_VERSION, top
            assert 0 <= top["priority_score"] <= 100, top
            assert 0 <= top["confidence_score"] <= 100, top
            assert top["reasoning_factors"], top
            assert any(
                factor["direction"] == "positive"
                for factor in top["reasoning_factors"]
            ), top
            assert any(
                factor["direction"] == "negative"
                for item in first
                for factor in item["reasoning_factors"]
            ), first
            assert any(
                factor["factor"] == "communication_gap"
                for item in first
                for factor in item["reasoning_factors"]
            ), first
            assert any(
                factor["factor"] == "recent_repetition"
                for item in first
                for factor in item["reasoning_factors"]
            ), first
            assert top["supporting_photo_count"] >= 1, top
            assert any(item["supporting_video_count"] >= 1 for item in first), first
            assert len(top["supporting_asset_ids"]) <= candidate_service.MAX_SUPPORTING_IDS
            assert len(top["best_asset_ids"]) <= candidate_service.MAX_BEST_IDS
            assert top["editorial_angles"], top
            assert top["recommended_platforms"], top
            assert top["recommended_audiences"], top
            assert top["recommended_content_formats"], top
            assert top["recommended_posting_window"], top
            assert top["source_signals"], top
            assert any(
                "Effective Intelligence" in signal
                for signal in top["source_signals"]
            ), top
            assert any(
                "Communications Memory" in signal
                for signal in top["source_signals"]
            ), top

            assert any(
                item["confidence_score"] < top["confidence_score"]
                for item in first[1:]
            ), first

            scores = [
                item["priority_score"]
                for item in first
            ]
            assert scores == sorted(scores, reverse=True), scores

            limited = service.generate_recommendations(limit=2)
            assert len(limited) == 2, limited

            candidates = candidate_service.build_candidates()
            corrected = [
                asset
                for candidate in candidates
                for asset in candidate["assets"]
                if asset.get("media_id") == 4
            ]
            assert corrected, candidates
            assert corrected[0]["incident_type"] == "recruitment", corrected[0]

            brief = DailyBriefService(
                database=db,
                editorial_recommendation_service=service
            ).generate()
            assert brief["editorial_recommendations"], brief

            from gui.home_page import HomePage

            viewer = object.__new__(HomePage)
            viewer.format_list = HomePage.format_list.__get__(viewer, HomePage)
            text = HomePage.recommendation_detail_text(viewer, top)
            assert "Positive Factors" in text, text
            assert "Negative Factors" in text, text
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")

        finally:
            os.chdir(original)

    print("editorial_recommendation smoke passed")


if __name__ == "__main__":
    main()
