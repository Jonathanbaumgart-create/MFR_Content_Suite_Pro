import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from gui.content_director_page import ContentDirectorPage
from gui.home_page import HomePage
from services.communication_package_service import CommunicationPackageService
from services.communications_officer_service import CommunicationsOfficerService
from services.editorial_recommendation_service import EditorialRecommendationService
from smoke_tests.communications_officer_smoke import (
    add_media,
    save_analysis,
    save_fire,
    save_intelligence
)


def seed(db):

    add_media(db, 1, "package_approved_training.jpg")
    save_analysis(db, 1, "approved_real", "approved")
    save_intelligence(
        db,
        1,
        {
            "communications_score": 94,
            "storytelling_score": 90,
            "recruitment_value_score": 96,
            "content_tags": ["training", "recruitment", "community"],
            "recommended_uses": ["recruitment", "training_tuesday"]
        }
    )
    save_fire(db, 1)

    add_media(db, 2, "package_corrected_training.jpg")
    save_analysis(db, 2, "corrected_real", "corrected")
    save_intelligence(
        db,
        2,
        {
            "communications_score": 89,
            "storytelling_score": 88,
            "recruitment_value_score": 91
        }
    )
    save_fire(db, 2)

    add_media(db, 3, "package_video.mp4", media_type="video")
    save_analysis(db, 3, "approved_real", "approved")
    save_intelligence(
        db,
        3,
        {
            "communications_score": 84,
            "storytelling_score": 82
        }
    )
    save_fire(db, 3)

    add_media(db, 4, "package_rejected.jpg")
    save_analysis(db, 4, "rejected_real", "rejected")
    save_intelligence(
        db,
        4,
        {
            "communications_score": 99,
            "storytelling_score": 99
        }
    )
    save_fire(db, 4)

    add_media(db, 5, "package_mock.jpg")
    save_analysis(db, 5, "approved_real", "approved")
    db.save_ai_analysis(
        5,
        {
            "description": "Mock test analysis.",
            "scene_type": "training",
            "activity": "training",
            "people_count": 1,
            "apparatus": ["Engine"],
            "equipment": ["Hose"],
            "keywords": ["training"],
            "overall_score": 80,
            "model": "mock",
            "provider": "mock",
            "last_analyzed": "",
            "trust_state": "approved_real",
            "review_status": "approved"
        }
    )
    save_intelligence(
        db,
        5,
        {
            "communications_score": 98,
            "storytelling_score": 98
        }
    )
    save_fire(db, 5)


def assert_package(package, package_type):

    required = (
        "headline",
        "primary_story",
        "editorial_angle",
        "audience",
        "why_today_matters",
        "supporting_evidence",
        "recommended_platforms",
        "publishing_priority",
        "confidence",
        "trust_label",
        "suggested_hashtags",
        "suggested_cta",
        "suggested_posting_time",
        "writing_strategy",
        "publishing_strategy",
        "media_package",
        "package_scoring"
    )

    for key in required:
        assert key in package, (key, package)

    assert package["package_type"] == package_type, package
    assert package["headline"], package
    assert package["writing_strategy"]["purpose"], package
    assert package["writing_strategy"]["platform_notes"], package
    assert len(package["suggested_hashtags"]) <= 5, package
    assert package["package_scoring"]["overall_score"] > 0, package
    assert package["media_package"]["primary_photo"] or package["media_package"]["primary_video"], package

    all_media = str(package["media_package"])
    assert "package_rejected" not in all_media, package
    assert "package_mock" not in all_media, package


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            seed(db)

            editorial = EditorialRecommendationService(database=db)
            recommendations = editorial.generate_recommendations(
                limit=3,
                candidate_limit=20,
                context="communication_package_smoke"
            )
            assert recommendations, "Expected editorial recommendations"

            package_service = CommunicationPackageService(database=db)
            package = package_service.generate_package(
                recommendations[0],
                package_type="Instagram"
            )
            assert_package(package, "Instagram")
            assert package_service.last_metrics["asset_count"] >= 1

            packages = package_service.generate_packages(
                recommendations[0]
            )
            assert len(packages) == len(package_service.PACKAGE_TYPES), packages

            for item in packages:
                assert_package(item, item["package_type"])

            officer = CommunicationsOfficerService(database=db)
            brief = officer.generate(force=True)
            top_package = package_service.generate_package(
                brief["top_story"],
                package_type="Facebook"
            )
            assert_package(top_package, "Facebook")
            assert top_package["trust_label"], top_package

            assert hasattr(HomePage, "request_communication_package")
            assert hasattr(ContentDirectorPage, "generate_package_preview")
            assert hasattr(ContentDirectorPage, "show_package_preview")

        finally:
            os.chdir(original)

    print("communication package smoke passed")


if __name__ == "__main__":
    main()
