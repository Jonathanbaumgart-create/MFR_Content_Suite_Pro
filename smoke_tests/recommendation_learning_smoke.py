from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.context_engine import ContextEngine


class FixedContextEngine:

    def __init__(self, fixed_date):

        self.fixed_date = fixed_date
        self.engine = ContextEngine()

    def snapshot(self):

        return self.engine.snapshot(self.fixed_date)


def add_media(db, index, filename):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"learning-hash-{index}"
        }
    )


def save_analysis(db, media_id, values):

    db.save_ai_analysis(
        media_id,
        {
            "description": "Stored analysis for learning smoke test.",
            "scene_type": values.get("scene_type", "community"),
            "activity": values.get("activity", "community outreach"),
            "people_count": 4,
            "apparatus": values.get("apparatus", ["Engine"]),
            "equipment": values.get("equipment", ["Hose"]),
            "keywords": values.get("keywords", ["community", "recruitment"]),
            "community_score": values.get("community_score", 85),
            "recruitment_score": values.get("recruitment_score", 75),
            "education_score": values.get("education_score", 70),
            "technical_score": values.get("technical_score", 55),
            "overall_score": values.get("overall_score", 82),
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
            "normalized_scene": values.get("normalized_scene", "community"),
            "incident_type": values.get("incident_type", "public_education"),
            "primary_activity": values.get("primary_activity", "community_outreach"),
            "apparatus_tags": values.get("apparatus_tags", ["engine"]),
            "equipment_tags": values.get("equipment_tags", ["hose"]),
            "ppe_tags": values.get("ppe_tags", ["turnout_gear"]),
            "people_tags": values.get("people_tags", ["crew"]),
            "content_tags": values.get("content_tags", []),
            "content_themes": values.get("content_themes", []),
            "recommended_uses": values.get("recommended_uses", []),
            "search_text": values.get("search_text", ""),
            "intelligence_score": values.get("intelligence_score", 80),
            "source_model": "mock"
        }
    )


def seed(db):

    add_media(db, 1, "community_recruitment.jpg")
    save_analysis(
        db,
        1,
        {
            "community_score": 92,
            "recruitment_score": 88,
            "education_score": 76,
            "overall_score": 90
        }
    )
    save_intelligence(
        db,
        1,
        {
            "incident_type": "community_event",
            "primary_activity": "firefighter_interaction",
            "apparatus_tags": ["engine"],
            "content_tags": ["community", "recruitment", "firefighter_interaction"],
            "content_themes": ["community_engagement", "recruitment"],
            "recommended_uses": ["recruitment", "community_outreach", "social_media"],
            "search_text": "community recruitment firefighter interaction",
            "intelligence_score": 91
        }
    )

    add_media(db, 2, "technical_training.jpg")
    save_analysis(
        db,
        2,
        {
            "community_score": 55,
            "recruitment_score": 40,
            "education_score": 75,
            "technical_score": 92,
            "overall_score": 84
        }
    )
    save_intelligence(
        db,
        2,
        {
            "normalized_scene": "training",
            "incident_type": "training",
            "primary_activity": "technical_training",
            "apparatus_tags": ["rescue"],
            "content_tags": ["training", "technical", "tools"],
            "content_themes": ["technical_training"],
            "recommended_uses": ["training", "behind_the_scenes"],
            "search_text": "technical training rescue tools",
            "intelligence_score": 88
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed(db)

            from services.communications_director import CommunicationsDirector
            from services.communications_reasoning_service import (
                CommunicationsReasoningService
            )
            from services.recommendation_learning_service import (
                RecommendationLearningService
            )

            director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 7, 15))
            )
            learning = RecommendationLearningService(db)
            service = CommunicationsReasoningService(
                db,
                director=director,
                learning_service=learning
            )

            recommendations = service.generate_recommendations(
                prompt="need a recruitment post",
                limit=1
            )
            assert recommendations, recommendations

            recommendation = recommendations[0]
            top_media = recommendation["recommended_media"][0]

            learning.record_feedback(
                recommendation,
                "accepted",
                media=top_media,
                notes="manual smoke acceptance"
            )
            learning.record_feedback(
                recommendation,
                "opened",
                media=top_media
            )
            learning.record_feedback(
                recommendation,
                "regenerated",
                media=top_media
            )

            rows = db.recommendation_feedback_rows(limit=20)
            assert len(rows) >= 4, rows
            assert any(row["accepted"] for row in rows), rows
            assert any(row["opened"] for row in rows), rows
            assert any(row["regenerated"] for row in rows), rows

            preferences = learning.preferences()
            summary = " ".join(preferences["summary"])
            assert "Recruitment" in summary or "Community" in summary, preferences
            assert preferences["platforms"], preferences
            assert preferences["posting_times"], preferences

            analytics = learning.analytics()
            assert analytics["total_feedback"] >= 4, analytics
            assert analytics["acceptance_rate"] > 0, analytics
            assert analytics["average_confidence"] >= 0, analytics
            assert analytics["most_requested_prompts"], analytics

            candidates = db.content_director_candidates(limit=10)
            preferred = next(
                item
                for item in candidates
                if item["media_id"] == top_media["media_id"]
            )
            adjustment, reasons = learning.score_adjustment(
                preferred,
                recommendation["opportunity_type"],
                {}
            )
            assert adjustment != 0, (adjustment, reasons)
            assert reasons, reasons

            adjusted = service.generate_recommendations(
                opportunity_keys=[recommendation["opportunity_type"]],
                limit=1
            )[0]
            assert adjusted["recommended_media"], adjusted
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")
            assert not hasattr(learning, "vision")
            assert not hasattr(learning, "ai")

        finally:
            os.chdir(original)

    print("recommendation_learning smoke passed")


if __name__ == "__main__":
    main()
