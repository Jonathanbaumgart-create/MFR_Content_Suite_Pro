from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from models.editorial_recommendation import EditorialRecommendation
from services.editorial_recommendation_service import EditorialRecommendationService
from services.recommendation_candidate_service import RecommendationCandidateService

from smoke_tests.editorial_recommendation_smoke import (
    add_media,
    save_analysis,
    save_fire,
    save_intelligence,
)
from services.communications_memory_service import CommunicationsMemoryService


def seed_quality_data(db):

    add_media(db, 1, "scba_training_1.jpg")
    save_analysis(
        db,
        1,
        {
            "description": "Firefighters training with SCBA in turnout gear.",
            "keywords": ["training", "scba", "firefighter"]
        }
    )
    save_intelligence(
        db,
        1,
        {
            "content_tags": ["training", "scba", "firefighter"],
            "content_themes": ["training", "technical_education"],
            "equipment_tags": ["scba"],
            "ppe_tags": ["turnout_gear", "scba"],
            "recommended_uses": ["training_tuesday", "recruitment"],
            "search_text": "firefighter training scba turnout gear",
            "intelligence_score": 94,
            "communications_score": 92,
            "storytelling_score": 90,
            "educational_value_score": 90,
            "recruitment_value_score": 82,
            "visual_impact_score": 88
        }
    )
    save_fire(
        db,
        1,
        {
            "ppe": ["turnout_gear", "scba"],
            "equipment": ["scba"],
            "operational_activity": "scba confidence training",
            "operational_skills": ["scba", "training"],
            "communications_uses": ["training_tuesday", "recruitment"],
            "communications_intent": ["training_tuesday", "technical_education"],
            "operational_confidence": 92
        }
    )

    add_media(db, 2, "scba_training_video.mp4", media_type="video")
    save_analysis(
        db,
        2,
        {
            "description": "SCBA training evolution video.",
            "keywords": ["training", "scba"]
        }
    )
    save_intelligence(
        db,
        2,
        {
            "content_tags": ["training", "scba"],
            "content_themes": ["training"],
            "equipment_tags": ["scba"],
            "recommended_uses": ["training_tuesday", "short_form_video"],
            "search_text": "scba training video",
            "intelligence_score": 86,
            "communications_score": 88,
            "storytelling_score": 88,
            "educational_value_score": 86,
            "recruitment_value_score": 78,
            "visual_impact_score": 84
        }
    )
    save_fire(
        db,
        2,
        {
            "ppe": ["scba"],
            "equipment": ["scba"],
            "operational_skills": ["scba", "training"],
            "communications_uses": ["training_tuesday"],
            "communications_intent": ["technical_education"],
            "operational_confidence": 86
        }
    )

    add_media(db, 3, "public_education_smoke_alarm.jpg")
    save_analysis(
        db,
        3,
        {
            "description": "Smoke alarm public education table.",
            "keywords": ["smoke alarm", "public education"]
        }
    )
    save_intelligence(
        db,
        3,
        {
            "normalized_scene": "public_education",
            "incident_type": "public_education",
            "primary_activity": "smoke_alarm_education",
            "content_tags": ["smoke_alarm", "public_education", "safety"],
            "content_themes": ["fire_prevention"],
            "recommended_uses": ["public_education", "fire_prevention"],
            "search_text": "smoke alarm public education fire prevention",
            "intelligence_score": 82,
            "communications_score": 80,
            "storytelling_score": 70,
            "educational_value_score": 90,
            "public_education_value_score": 92,
            "seasonal_relevance_score": 76
        }
    )

    memory = CommunicationsMemoryService(db)
    memory.remember_post(
        {
            "platform": "facebook",
            "post_date": "2026-01-01",
            "caption": "Training Tuesday: crews practiced SCBA confidence skills.",
            "campaign": "Training Tuesday",
            "opportunity_type": "training",
            "media_ids": [1],
            "imported": True
        }
    )
    memory.remember_post(
        {
            "platform": "instagram",
            "post_date": "2025-10-01",
            "caption": "Smoke alarms save lives. Test yours this week.",
            "campaign": "Fire Prevention",
            "opportunity_type": "public_education",
            "media_ids": [],
            "imported": True
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed_quality_data(db)

            candidate_service = RecommendationCandidateService(database=db)
            assert_specificity_guards(candidate_service)
            candidates = candidate_service.build_candidates()
            topic_candidates = [
                item
                for item in candidates
                if item.get("is_topic_candidate")
            ]
            assert topic_candidates, candidates
            assert any(
                "SCBA Training" in item.get("supporting_topics", [])
                for item in topic_candidates
            ), topic_candidates
            assert any(
                item["memory_profile"]["memory_available"]
                for item in topic_candidates
            ), topic_candidates

            service = EditorialRecommendationService(
                database=db,
                candidate_service=candidate_service
            )
            recommendations = service.generate_recommendations(limit=8)
            assert recommendations, recommendations

            titles = [item["title"] for item in recommendations]
            assert any(
                "SCBA" in title
                for title in titles
            ), titles
            assert not all(
                title.endswith("Opportunity")
                for title in titles
            ), titles

            first = recommendations[0]
            assert first["supporting_topics"], first
            assert first["story_strength"]["overall"] > 0, first
            assert first["editorial_angle"], first
            assert "Communications Memory" in " ".join(first["source_signals"]), first
            assert len(first["best_asset_ids"]) <= candidate_service.MAX_BEST_IDS
            assert len({item["topic"] for item in recommendations[:5]}) >= 2, recommendations

            confidences = [
                item["confidence_score"]
                for item in recommendations
            ]
            assert max(confidences) > min(confidences), confidences
            assert service.last_metrics["diversity_pruned_count"] >= 0
            assert_priority_remains_major_signal(service)

            try:
                from gui.home_page import HomePage
            except ModuleNotFoundError:
                HomePage = None

            if HomePage is not None:
                viewer = object.__new__(HomePage)
                viewer.format_list = HomePage.format_list.__get__(viewer, HomePage)
                viewer.story_strength_text = HomePage.story_strength_text.__get__(
                    viewer,
                    HomePage
                )
                text = HomePage.recommendation_detail_text(viewer, first)
                assert "Supporting topics" in text, text
                assert "Story strength" in text, text
                assert "Known Confidence Limitations" in text, text

        finally:
            os.chdir(original)

    print("editorial_recommendation_quality smoke passed")


def assert_priority_remains_major_signal(service):

    high_priority = EditorialRecommendation(
        recommendation_id="high-priority",
        title="Recruit Volunteer Firefighters",
        topic="recruitment",
        category="Recruitment",
        priority_score=70,
        confidence_score=60,
        summary="Higher priority recommendation.",
        primary_reason="Material priority advantage.",
        supporting_topics=["Recruit Volunteer Firefighters"],
        story_strength={"overall": 65},
        editorial_angle="Recruitment",
        supporting_photo_count=4,
        supporting_video_count=0
    )
    trivial_confidence_edge = EditorialRecommendation(
        recommendation_id="trivial-edge",
        title="SCBA Training",
        topic="scba",
        category="Training",
        priority_score=45,
        confidence_score=61,
        summary="Lower priority recommendation.",
        primary_reason="One point confidence edge.",
        supporting_topics=["SCBA Training"],
        story_strength={"overall": 65},
        editorial_angle="Training Highlight",
        supporting_photo_count=4,
        supporting_video_count=0
    )

    service._attach_ordering_inputs(high_priority)
    service._attach_ordering_inputs(trivial_confidence_edge)

    assert (
        high_priority.final_order_score >
        trivial_confidence_edge.final_order_score
    ), (
        high_priority.final_order_score,
        trivial_confidence_edge.final_order_score
    )


def assert_specificity_guards(candidate_service):

    cases = [
        (
            {"all_terms": ["training"]},
            "scba",
            "Generic training must not become SCBA."
        ),
        (
            {"all_terms": ["hydrant"]},
            "hydrant_heroes",
            "Generic hydrant evidence must not become Hydrant Heroes."
        ),
        (
            {"all_terms": ["rescue"]},
            "recruitment",
            "Rescue evidence must not become recruitment."
        ),
        (
            {"all_terms": ["winter"]},
            "ice_safety",
            "Seasonal winter evidence alone must not become ice safety."
        )
    ]

    for asset, forbidden_topic, message in cases:
        topics = {
            item["topic"]
            for item in candidate_service.extract_topics(asset)
        }
        assert forbidden_topic not in topics, (message, topics)

    corrected = {
        "all_terms": ["firefighter"],
        "topics": []
    }
    corrected["all_terms"].append("recruitment")
    topics = {
        item["topic"]
        for item in candidate_service.extract_topics(corrected)
    }
    assert "recruitment" in topics, topics


if __name__ == "__main__":
    main()
