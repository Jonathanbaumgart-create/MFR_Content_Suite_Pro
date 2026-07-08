from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.prompt_engine import PromptEngine


def request():

    return {
        "recommendation": {
            "title": "Recruitment Training Highlight",
            "summary": "Encourage residents to consider joining the department.",
            "caption_theme": "service and training",
            "reasoning": [
                "Recruitment value is high.",
                "Training activity is visible in stored intelligence."
            ]
        },
        "department_knowledge": {
            "profile": {
                "department_name": "Morden Fire & Rescue",
                "mission_statement": "Serving Morden with care and professionalism.",
                "common_hashtags": ["#MordenFireRescue"]
            },
            "programs": [
                {
                    "name": "Hydrant Heroes",
                    "audience": "local families"
                }
            ],
            "community_partners": [
                {
                    "name": "Boundary Trails Health Centre"
                }
            ],
            "response_area": [
                {
                    "name": "RM of Stanley"
                }
            ]
        },
        "communications_memory": {
            "average_caption_length": 142,
            "average_hashtags": 3,
            "average_emojis": 4,
            "common_openings": ["Big thanks to our community"],
            "common_ctas": ["Learn more about serving your community."],
            "top_hashtags": ["#MordenFireRescue", "#FireSafety"],
            "campaigns": ["Recruitment"]
        },
        "context": {
            "date": "2026-07-08",
            "season": "summer",
            "active_themes": ["recruitment", "water safety"],
            "priority_context": "Summer community safety"
        },
        "media_intelligence": [
            {
                "filename": "training.jpg",
                "incident_type": "training",
                "primary_activity": "recruitment_training",
                "content_tags": ["training", "recruitment"],
                "content_themes": ["recruitment"],
                "recommended_uses": ["recruitment", "social_media"],
                "intelligence_score": 94
            }
        ],
        "learning_preferences": {
            "preferred_content_themes": ["community", "recruitment"]
        },
        "opportunity_type": "recruitment",
        "platforms": [
            "facebook",
            "instagram",
            "linkedin"
        ]
    }


def main():

    engine = PromptEngine()
    payload = engine.build_all(
        request()
    )

    assert set(payload["prompts"]) == {
        "facebook",
        "instagram",
        "linkedin"
    }, payload

    facebook = payload["prompts"]["facebook"]
    instagram = payload["prompts"]["instagram"]
    linkedin = payload["prompts"]["linkedin"]

    for title in engine.SECTION_TITLES:
        assert title in facebook, title

    assert "Facebook: storytelling" in facebook, facebook
    assert "3 to 4 relevant emojis" in facebook, facebook
    assert "Instagram: visual" in instagram, instagram
    assert "4 to 6 relevant emojis" in instagram, instagram
    assert "LinkedIn: professional" in linkedin, linkedin
    assert "no more than 3 hashtags" in linkedin, linkedin

    dna = payload["editorial_dna"]
    assert dna["average_caption_length"] == 142.0, dna
    assert dna["emoji_frequency"] == 4.0, dna
    assert "Big thanks to our community" in dna["preferred_opening_styles"]
    assert "#MordenFireRescue" in dna["top_hashtags"]

    joined = "\n".join(payload["prompts"].values()).lower()
    assert "selected media" not in joined, joined
    assert "this image shows" not in joined, joined
    assert "a practical reminder" not in joined, joined
    assert "metadata leakage" not in joined, joined
    assert "vision ai" not in joined, joined

    print("prompt_engine smoke passed")


if __name__ == "__main__":
    main()
