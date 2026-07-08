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
from services.writing_service import WritingService


def has_emoji(value):

    return any(ord(character) > 10000 for character in value)


def hashtag_count(value):

    return len(
        [
            token
            for token in value.split()
            if token.startswith("#")
        ]
    )


def deterministic_writing_service():

    return WritingService(
        config={
            "default_provider": "deterministic",
            "fallback_provider": "deterministic",
            "providers": {
                "deterministic": {
                    "model": "deterministic-template"
                }
            }
        }
    )


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
            "sha256": f"content-generation-hash-{index}"
        }
    )


def save_analysis(db, media_id):

    db.save_ai_analysis(
        media_id,
        {
            "description": "Stored analysis for content generation smoke test.",
            "scene_type": "training",
            "activity": "recruitment training",
            "people_count": 4,
            "apparatus": ["Engine"],
            "equipment": ["SCBA", "Hose"],
            "keywords": ["training", "recruitment", "community"],
            "community_score": 84,
            "recruitment_score": 96,
            "education_score": 78,
            "technical_score": 86,
            "overall_score": 91,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": "mock",
            "analysis_duration": 0.1,
            "provider": "mock",
            "retry_count": 0,
            "failure_reason": ""
        }
    )


def save_intelligence(db, media_id):

    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": "training",
            "incident_type": "training",
            "primary_activity": "recruitment_training",
            "apparatus_tags": ["engine"],
            "equipment_tags": ["scba", "hose"],
            "ppe_tags": ["turnout_gear", "helmet"],
            "people_tags": ["crew"],
            "content_tags": ["training", "recruitment", "community"],
            "content_themes": ["recruitment", "technical_training"],
            "recommended_uses": ["recruitment", "training", "social_media"],
            "search_text": "training recruitment community engine scba hose",
            "intelligence_score": 94,
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
            save_analysis(db, 1)
            save_intelligence(db, 1)

            from services.knowledge_service import KnowledgeService

            knowledge = KnowledgeService(db)
            knowledge.save_item(
                "community_partners",
                {
                    "name": "Boundary Trails Health Centre",
                    "category": "health",
                    "description": "Stored community partner for local public-safety collaboration.",
                    "tags": ["community", "health", "partner"],
                    "active": True
                }
            )
            knowledge.save_item(
                "response_area",
                {
                    "name": "RM of Stanley",
                    "category": "mutual_aid",
                    "description": "Stored response-area reference.",
                    "tags": ["response_area", "community"],
                    "active": True
                }
            )

            from services.communications_director import CommunicationsDirector
            from services.communications_reasoning_service import (
                CommunicationsReasoningService
            )
            from services.content_generation_service import (
                ContentGenerationService
            )

            director = CommunicationsDirector(
                db,
                context_engine=FixedContextEngine(date(2026, 9, 15))
            )
            reasoning = CommunicationsReasoningService(
                db,
                director=director,
                knowledge_service=knowledge
            )
            recommendation = reasoning.generate_recommendations(
                prompt="need a recruitment post",
                limit=1
            )[0]

            service = ContentGenerationService(
                db,
                knowledge_service=knowledge,
                context_engine=FixedContextEngine(date(2026, 9, 15)),
                writing_service=deterministic_writing_service()
            )
            package = service.generate_package(
                recommendation
            )

            assert package["headline"], package
            assert package["facebook_caption"], package
            assert package["instagram_caption"], package
            assert package["linkedin_caption"], package
            assert package["short_version"], package
            assert package["long_version"], package
            assert package["call_to_action"], package
            assert package["hashtags"], package
            assert package["facebook_hashtags"], package
            assert package["instagram_hashtags"], package
            assert package["emoji_suggestions"], package
            assert package["suggested_posting_time"], package
            assert package["suggested_media"], package
            assert package["reasoning"], package
            assert package["prompt_engine"] == "professional", package
            assert package["editorial_dna"], package
            assert package["editorial_review"], package
            assert package["editorial_score"] > 0, package
            assert has_emoji(package["facebook_caption"]), package
            assert has_emoji(package["instagram_caption"]), package
            assert hashtag_count(package["facebook_caption"]) <= 5, package
            assert hashtag_count(package["instagram_caption"]) <= 5, package
            assert len(package["facebook_hashtags"]) <= 5, package
            assert len(package["instagram_hashtags"]) <= 5, package

            text = " ".join(
                [
                    package["headline"],
                    package["facebook_caption"],
                    package["instagram_caption"],
                    package["linkedin_caption"],
                    package["long_version"],
                    " ".join(package["reasoning"])
                ]
            )

            assert "Morden Fire & Rescue" in text, text
            assert "Boundary Trails Health Centre" in text, text
            assert "RM of Stanley" in text, text
            assert "Winkler" not in text, text
            assert "uses stored recommendation" in text.lower(), text

            recruitment = service.generate_package(
                recommendation,
                writing_style="recruitment"
            )
            training = service.generate_package(
                recommendation,
                writing_style="training"
            )

            assert recruitment["writing_style"] == "Recruitment", recruitment
            assert training["writing_style"] == "Training", training
            assert recruitment["facebook_caption"] != training["facebook_caption"]
            assert package["writing_provider"] == "deterministic", package
            assert package["writing_fallback_used"] is False, package
            assert service.templates(), "default content templates were not stored"
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")

            from gui.content_director_page import ContentDirectorPage

            assert ContentDirectorPage is not None

        finally:
            os.chdir(original)

    print("content_generation smoke passed")


if __name__ == "__main__":
    main()
