from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.daily_communications_officer_service import DailyCommunicationsOfficerService
from services.editorial_writing_service import EditorialWritingService
from services.content_director_retrieval_service import ContentDirectorRetrievalService


def hashtags(text):

    return [
        part for part in str(text or "").split()
        if part.startswith("#")
    ]


def assert_public(copy):

    lower = copy.lower()
    banned = (
        "attached media",
        "attached photo",
        "attached video",
        "use the attached",
        "communication opportunity",
        "content opportunity",
        "timely reminder",
        "practical readiness",
        "message worth bringing back",
        "when the timing is right",
        "provider",
        "confidence score",
        "semantic review",
        "publication package",
        "#mordenfirerescue"
    )
    for phrase in banned:
        assert phrase not in lower, copy

    tags = hashtags(copy)
    assert len(tags) <= 5, copy
    if tags:
        assert tags[-1] == "#MordenMB", copy
        assert len({tag.lower() for tag in tags}) == len(tags), copy


def add_media(db, index, filename, text):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 1000 + index,
            "sha256": f"sprint49-{index}",
            "first_seen_at": "2026-07-20T12:00:00+00:00"
        }
    )
    db.save_ai_analysis(
        index,
        {
            "provider": "ollama",
            "model": "moondream:latest",
            "description": text,
            "confidence": 88,
            "overall_score": 88,
            "review_status": "approved",
            "trust_state": "approved_real",
            "last_analyzed": "2026-07-20T12:01:00+00:00"
        }
    )
    db.save_media_intelligence(
        index,
        {
            "normalized_scene": "training",
            "incident_type": "training",
            "primary_activity": text,
            "apparatus_tags": [],
            "equipment_tags": ["rope", "rescue equipment"],
            "ppe_tags": ["helmet"],
            "people_tags": ["firefighters"],
            "content_tags": ["training", "rope rescue"],
            "content_themes": ["training", "public education"],
            "recommended_uses": ["training", "recruitment"],
            "search_text": text,
            "intelligence_score": 90,
            "source_model": "moondream:latest"
        }
    )


def main():

    writer = EditorialWritingService()
    rope_facts = {
        "event_title": "Low-Angle Rope Rescue Training",
        "actual_activity": (
            "patient already removed from water, traditional access too far away, "
            "steep embankment, low-angle rope system, move patient to EMS access"
        ),
        "what_occurred": "Firefighters worked through low-angle rope rescue training.",
        "why_it_matters": "Terrain and access can change the rescue plan.",
        "community_connection": "Realistic training helps Morden firefighters prepare for difficult rescues.",
        "content_type": "training",
        "has_enough_facts": True
    }
    rope = writer.generate_from_fact_sheet(rope_facts)
    assert rope["story_family"] == "training", rope
    assert "What happens when a patient cannot be safely carried" in rope["facebook"], rope
    assert "simply carrying the patient" in rope["facebook"], rope
    assert "low-angle rope system" in rope["facebook"], rope
    assert rope["selected_teaching_point"], rope
    assert rope["quality"]["passed"], rope["quality"]
    assert rope["scroll_stop_score"]["total_score"] >= 70, rope
    assert_public(rope["facebook"])
    assert_public(rope["instagram"])

    water = writer.generate_from_fact_sheet(
        writer.topic_fact_sheet(
            "water safety",
            current_relevance="Families are spending more time near water in summer.",
            known_facts=["life jackets and close supervision reduce risk near water"]
        )
    )
    assert water["story_family"] == "public_education", water
    assert "life jacket" in water["facebook"].lower(), water
    assert water["quality"]["passed"], water["quality"]
    assert_public(water["facebook"])
    assert_public(water["instagram"])

    daycare = writer.generate_from_fact_sheet(
        {
            "event_title": "Morden Daycare Spray Down July 2026",
            "actual_activity": "local daycare spray-down and summer community visit",
            "what_occurred": "MFR members visited a local daycare for a spray-down.",
            "why_it_matters": "It builds positive relationships with children and families.",
            "community_connection": "friendly interaction with local children during summer weather",
            "content_type": "daycare_spray_down",
            "has_enough_facts": True
        },
        tone="light"
    )
    assert daycare["story_family"] == "light_hearted", daycare
    assert "hose line was a hit" in daycare["facebook"].lower(), daycare
    assert daycare["variants"], daycare
    assert_public(daycare["facebook"])

    fail = writer.generate_from_fact_sheet(
        {
            "event_title": "Unknown",
            "content_type": "training",
            "has_enough_facts": False
        }
    )
    assert fail["quality"]["passed"] is False, fail
    assert fail["facebook"] == writer.FAIL_CLOSED_TEXT, fail

    bad = writer.quality_gate(
        "Here is a timely reminder from Morden Fire & Rescue. Use the attached photo.",
        "Selected media. #MordenFireRescue",
        {"has_enough_facts": True},
        "one practical action"
    )
    assert bad["passed"] is False, bad
    assert bad["banned_phrases"], bad

    original = Path.cwd()
    with TemporaryDirectory() as folder:
        os.chdir(folder)
        try:
            db = DatabaseManager()
            add_media(
                db,
                1,
                "rope_rescue_training.jpg",
                "low-angle rope rescue training steep embankment patient EMS access"
            )
            retrieval = ContentDirectorRetrievalService(database=db)
            package = retrieval.build_prompt_package(
                "rope rescue",
                option_count=3
            )
            option = package["options"][0]
            assert option["facebook_caption"], option
            assert option["selected_teaching_point"], option
            assert option["caption_quality"]["passed"], option["caption_quality"]
            assert_public(option["facebook_caption"])
            assert_public(option["instagram_caption"])

            daily = DailyCommunicationsOfficerService(database=db)
            brief = daily.generate(force=True)
            top = brief["daily_post_packages"][0]
            assert "selected_teaching_point" in top, top
            assert "scroll_stop_score" in top, top
            assert "caption_quality" in top, top
        finally:
            os.chdir(original)

    print("sprint49 editorial writing smoke passed")


if __name__ == "__main__":
    main()
