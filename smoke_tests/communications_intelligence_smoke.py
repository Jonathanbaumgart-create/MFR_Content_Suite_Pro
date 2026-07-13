from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from gui.content_director_page import ContentDirectorPage
from gui.home_page import HomePage
from services.communication_package_service import CommunicationPackageService
from services.communications_intelligence_service import CommunicationsIntelligenceService
from services.communications_memory_service import CommunicationsMemoryService
from services.communications_officer_service import CommunicationsOfficerService
from services.content_generation_service import ContentGenerationService
from services.human_feedback_service import HumanFeedbackService


def add_media(db, media_id, filename):

    db.add_media(
        {
            "id": media_id,
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + media_id,
            "sha256": f"communications-intelligence-hash-{media_id}"
        }
    )


def seed_memory(memory):

    memory.remember_post(
        {
            "platform": "facebook",
            "created_at": "2026-01-15T09:00:00+00:00",
            "headline": "Hydrant Heroes",
            "caption": (
                "Hydrant Heroes helps our community keep hydrants clear "
                "through the winter. Thank you, Morden, for helping crews "
                "respond safely. Check the hydrant near your home today. "
                "\U0001f692 \u2744 #HydrantHeroes #MordenFireRescue #CommunitySafety"
            ),
            "campaign": "Hydrant Heroes",
            "writing_style": "educational",
            "opportunity_type": "public_education",
            "season": "winter",
            "media_ids": [1],
            "source": "import",
            "imported": True
        }
    )
    memory.remember_post(
        {
            "platform": "instagram",
            "created_at": "2026-06-12T20:00:00+00:00",
            "caption": (
                "Training night builds skill, confidence, and teamwork. "
                "Our firefighters train for the calls our community may need. "
                "\U0001f525 \U0001fa96 #TrainingTuesday #MordenFireRescue #Volunteer"
            ),
            "campaign": "Training Tuesday",
            "writing_style": "training",
            "opportunity_type": "training_highlight",
            "season": "summer",
            "media_ids": [2],
            "source": "approved",
            "imported": False,
            "generated": True
        }
    )
    memory.remember_post(
        {
            "platform": "linkedin",
            "created_at": "2026-09-01T15:00:00+00:00",
            "caption": (
                "Volunteer firefighters bring training, commitment, and "
                "service to Morden and the surrounding area. Learn how you "
                "can support public safety through service."
            ),
            "campaign": "Volunteer Recruitment",
            "writing_style": "recruitment",
            "opportunity_type": "recruitment",
            "season": "fall",
            "media_ids": [3],
            "source": "corrected",
            "imported": False,
            "generated": True
        }
    )
    memory.remember_post(
        {
            "platform": "facebook",
            "created_at": "2026-03-01T15:00:00+00:00",
            "caption": (
                "Mock provider active - test data only. This should not be "
                "used as department voice."
            ),
            "campaign": "Mock Campaign",
            "writing_style": "test",
            "source": "mock",
            "imported": True
        }
    )
    memory.remember_post(
        {
            "platform": "facebook",
            "created_at": "2026-04-01T15:00:00+00:00",
            "caption": "Unreviewed generated caption should not train style.",
            "campaign": "Unreviewed",
            "writing_style": "draft",
            "source": "unreviewed",
            "imported": True
        }
    )


def package_recommendation():

    return {
        "title": "Hydrant Heroes Winter Safety",
        "summary": "A community education story about winter hydrant access.",
        "why_today_matters": "Winter access to hydrants helps emergency crews respond quickly.",
        "opportunity_type": "public_education",
        "recommended_platforms": ["Facebook", "Instagram"],
        "confidence": 82,
        "positive_factors": ["Approved communications memory", "Seasonal campaign fit"],
        "negative_factors": [],
        "confidence_limitations": [],
        "recommended_media": [
            {
                "media_id": 1,
                "filename": "hydrant_heroes.jpg",
                "type": "image",
                "path": str(Path("library") / "hydrant_heroes.jpg"),
                "trust_state": "approved_real",
                "review_status": "approved",
                "provider": "ollama",
                "communications_score": 88,
                "story_strength": 85
            }
        ],
        "media_package": {
            "primary_photo": {
                "media_id": 1,
                "filename": "hydrant_heroes.jpg",
                "type": "image",
                "trust_state": "approved_real",
                "review_status": "approved",
                "provider": "ollama",
                "communications_score": 88,
                "story_strength": 85
            },
            "gallery_photos": [],
            "primary_video": {},
            "gallery_videos": []
        }
    }


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()

            for media_id, filename in (
                (1, "hydrant_heroes.jpg"),
                (2, "training_tuesday.jpg"),
                (3, "recruitment.jpg")
            ):
                add_media(db, media_id, filename)

            memory = CommunicationsMemoryService(db)
            seed_memory(memory)

            service = CommunicationsIntelligenceService(
                database=db,
                memory_service=memory
            )
            profile = service.rebuild_profile()

            assert profile["approved_communication_count"] == 3, profile
            assert profile["sample_count"] == 3, profile
            assert profile["learning_confidence"] >= 35, profile
            assert "department_voice" in profile, profile
            assert profile["platform_profiles"]["facebook"]["sample_count"] == 1, profile
            assert profile["platform_profiles"]["instagram"]["sample_count"] == 1, profile
            assert profile["campaign_profiles"]["Hydrant Heroes"]["sample_count"] == 1, profile
            assert profile["campaign_profiles"]["Training Tuesday"]["sample_count"] >= 1, profile
            assert profile["seasonal_profiles"]["winter"]["sample_count"] == 1, profile
            assert "Mock Campaign" not in profile["engagement_intelligence"]["common_campaigns"], profile
            openings = str(profile["writing_characteristics"]["opening_hook_style"]).lower()
            assert "mock provider" not in openings, profile
            assert "unreviewed generated" not in openings, profile
            assert profile["preferred_vocabulary"], profile
            assert profile["communication_fingerprint"]["confidence"] >= 35, profile

            cached = service.profile()
            assert cached["sample_count"] == profile["sample_count"], cached
            assert service.last_metrics["cache_hit"] is True, service.last_metrics

            source = service.source_report()
            assert source["eligible_count"] == 3, source
            assert source["excluded_mock_count"] == 1, source
            assert source["excluded_unreviewed_count"] == 1, source

            edit = service.record_approved_edit(
                "A practical reminder from MFR. Selected media supports this.",
                (
                    "Keep the hydrant near your home clear this winter. "
                    "Small steps help crews respond when minutes matter."
                ),
                platform="facebook"
            )
            assert edit["edit_id"], edit
            assert edit["summary"]["opening_changed"] is True, edit

            invalidated = service.profile()
            assert service.last_metrics["cache_hit"] is False, service.last_metrics
            assert invalidated["approved_edit_count"] == 1, invalidated

            refreshed = service.profile(force=True)
            assert refreshed["approved_edit_count"] == 1, refreshed
            assert refreshed["sample_count"] == 4, refreshed

            recommendation = package_recommendation()
            package_service = CommunicationPackageService(database=db)
            communication_package = package_service.generate_package(
                recommendation,
                package_type="Facebook"
            )
            assert communication_package["writing_strategy"]["purpose"], communication_package

            generator = ContentGenerationService(
                database=db,
                memory_service=memory
            )
            generated = generator.generate_from_package(
                communication_package
            )
            assert generated["communications_intelligence"]["sample_count"] == 4, generated
            assert generated["department_voice_match"]["facebook"]["score"] > 0, generated
            assert "Department voice" in generated["facebook"]["notes"], generated
            assert generated["copy_buttons"]["facebook"], generated

            match = service.voice_match(
                generated["copy_buttons"]["facebook"],
                "facebook",
                profile=refreshed
            )
            assert match["profile_sample_count"] == 4, match
            for key in (
                "opening_style_score",
                "sentence_length_score",
                "cta_score",
                "emoji_score",
                "hashtag_score",
                "vocabulary_score",
                "platform_fit_score",
                "confidence"
            ):
                assert key in match, match

            generic = service.voice_match(
                (
                    "This emergency service agency provides information to "
                    "the public. Please review safety information as needed."
                ),
                "facebook",
                profile=refreshed
            )
            assert match["score"] > generic["score"], (match, generic)

            officer = CommunicationsOfficerService(database=db)
            brief = officer.generate(force=True)
            assert "communications_memory_status" in brief, brief

            feedback = HumanFeedbackService(db)
            assert hasattr(feedback, "save_correction")
            assert hasattr(ContentDirectorPage, "department_voice_match_text")
            assert hasattr(HomePage, "render_communications_intelligence_status")

        finally:
            os.chdir(original)

    print("communications intelligence smoke passed")


if __name__ == "__main__":
    main()
