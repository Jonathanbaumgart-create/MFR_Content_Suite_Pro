from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.editorial_review_service import EditorialReviewService


def strong_package():

    return {
        "facebook_caption": (
            "Training nights help our team stay ready for the Morden community. "
            "\U0001f692 \U0001fa96 \U0001f91d If serving your neighbours has "
            "been on your mind, this is a great time to learn more. "
            "#MordenFireRescue #Recruitment #Training"
        ),
        "instagram_caption": (
            "Crew training, community service, and a team that keeps learning. "
            "\U0001f692 \U0001fa96 \U0001f91d \U0001f525 Learn how you can be "
            "part of it. #MordenFireRescue #JoinTheTeam #Training"
        ),
        "linkedin_caption": (
            "Morden Fire & Rescue continues to invest in training, service, "
            "and community readiness."
        ),
        "call_to_action": "Learn more about serving your community.",
        "facebook_hashtags": [
            "#MordenFireRescue",
            "#Recruitment",
            "#Training"
        ],
        "instagram_hashtags": [
            "#MordenFireRescue",
            "#JoinTheTeam",
            "#Training"
        ],
        "hashtags": [
            "#MordenFireRescue",
            "#Recruitment",
            "#Training"
        ],
        "suggested_media": [
            {
                "content_tags": ["training", "recruitment"],
                "content_themes": ["community"],
                "recommended_uses": ["recruitment"]
            }
        ]
    }


def weak_package():

    return {
        "facebook_caption": (
            "This image shows selected media from the database. "
            "A practical reminder from the provider."
        ),
        "instagram_caption": "Selected media. #One #Two #Three #Four #Five #Six",
        "linkedin_caption": "Metadata from provider.",
        "call_to_action": "",
        "facebook_hashtags": ["#One", "#Two", "#Three", "#Four", "#Five", "#Six"],
        "instagram_hashtags": ["#One", "#Two", "#Three", "#Four", "#Five", "#Six"],
        "hashtags": ["#One", "#Two", "#Three", "#Four", "#Five", "#Six"]
    }


def main():

    service = EditorialReviewService()
    strong = service.review_package(
        strong_package()
    )
    weak = service.review_package(
        weak_package()
    )

    assert strong["overall_score"] >= 70, strong
    assert weak["overall_score"] < strong["overall_score"], (strong, weak)

    for component in service.COMPONENTS:
        assert component in strong["scores"], strong

    assert strong["strengths"], strong
    assert strong["suggestions"], strong
    assert weak["suggestions"], weak
    assert any(
        "generic" in suggestion.lower() or
        "internal" in suggestion.lower()
        for suggestion in weak["suggestions"]
    ), weak

    print("editorial_review smoke passed")


if __name__ == "__main__":
    main()
