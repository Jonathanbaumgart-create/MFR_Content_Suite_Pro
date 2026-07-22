import os
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.content_director_retrieval_service import ContentDirectorRetrievalService
from smoke_tests.communications_officer_smoke import save_analysis, save_intelligence
from smoke_tests.sprint44_operational_activity_smoke import add_media, save_filesystem


BANNED = (
    "the main takeaway is simple",
    "one clear action is easier to remember",
    "that is why local safety messages work best",
    "one practical action residents can take today",
    "specific, practical, and easy to act on",
    "the goal is simple",
    "the message is simple",
    "here is a timely reminder",
    "worth bringing back",
    "prepares for all situations",
    "prepared for anything",
    "commitment to safety",
    "committed to serving",
    "helps ensure readiness",
    "training prepares us",
    "our members trained",
    "great night of training",
)


def _seed_media(db, media_id, filename, path, tags, activity, uses, score=88, **fs):

    add_media(db, media_id, filename, path=path)
    save_analysis(db, media_id, "approved_real", "approved")
    save_intelligence(
        db,
        media_id,
        {
            "normalized_scene": activity,
            "incident_type": fs.get("incident_type", "public education"),
            "primary_activity": activity,
            "content_tags": tags,
            "recommended_uses": uses,
            "search_text": " ".join(tags + uses + [activity]),
            "communications_score": score,
        },
    )
    save_filesystem(
        db,
        media_id,
        root_category=fs.get("root_category", "Public Education"),
        subcategory=fs.get("subcategory", activity.title()),
        campaign=fs.get("campaign", ""),
        public_education_program=fs.get("program", ""),
        training_type=fs.get("training_type", ""),
        normalized_tags=tags,
    )


def _seed(db):

    _seed_media(
        db,
        1,
        "daycare_spraydown.jpg",
        "library/2026/Public Education/Daycare Spraydown/daycare_spraydown.jpg",
        ["daycare", "spray down", "hose line", "children"],
        "daycare spray down",
        ["community visit", "public education"],
        subcategory="Daycare Spraydown",
        program="Daycare Visit",
    )
    _seed_media(
        db,
        2,
        "recruitment_training.jpg",
        "library/2026/Recruitment/recruitment_training.jpg",
        ["recruitment", "volunteer firefighting", "training", "equipment checks"],
        "volunteer recruitment training",
        ["recruitment", "community service"],
        root_category="Recruitment",
        subcategory="Recruitment",
        campaign="Volunteer Recruitment",
        incident_type="training",
    )
    _seed_media(
        db,
        3,
        "fireworks_safety.jpg",
        "library/2026/Public Education/Fireworks/fireworks_safety.jpg",
        ["fireworks", "local rules", "supervision", "Canada Day"],
        "fireworks safety",
        ["fireworks safety"],
        subcategory="Fireworks Safety",
        campaign="Fireworks Safety",
    )
    _seed_media(
        db,
        4,
        "smoke_alarm_check.jpg",
        "library/2026/Fire Prevention/Smoke Alarms/smoke_alarm_check.jpg",
        ["smoke alarm", "testing", "replacement", "home safety"],
        "smoke alarm reminder",
        ["smoke alarm", "fire prevention"],
        subcategory="Smoke Alarms",
        campaign="Fire Prevention",
        program="Smoke Alarms",
    )
    _seed_media(
        db,
        5,
        "rope_rescue_training.jpg",
        "library/2026/Training/Rope Rescue/rope_rescue_training.jpg",
        ["rope rescue", "embankment", "rope system", "training"],
        "rope rescue training",
        ["training", "technical education"],
        root_category="Training",
        subcategory="Rope Rescue",
        training_type="Rope Rescue",
        incident_type="training",
    )
    _seed_media(
        db,
        6,
        "hydrant_heroes.jpg",
        "library/2026/Public Education/Hydrant Heroes/hydrant_heroes.jpg",
        ["hydrant heroes", "hydrant", "winter safety", "snow"],
        "hydrant heroes winter safety",
        ["hydrant heroes", "public education"],
        subcategory="Hydrant Heroes",
        campaign="Hydrant Heroes",
        program="Hydrant Heroes",
    )
    _seed_media(
        db,
        7,
        "water_safety.jpg",
        "library/2026/Public Education/Water Safety/water_safety.jpg",
        ["water safety", "life jacket", "supervision"],
        "water safety reminder",
        ["water safety", "public education"],
        subcategory="Water Safety",
        campaign="Water Safety",
    )


def _public_text(package):

    return "\n".join(
        [
            package.get("facebook_caption", ""),
            package.get("instagram_caption", ""),
        ]
    )


def _body_signature(text):

    body = re.sub(r"#[A-Za-z0-9_]+", "", text)
    body = re.sub(r"[^\w\s]", " ", body.lower())
    body = re.sub(r"\b(daycare|recruitment|volunteer|morden|fire|rescue|mfr)\b", "", body)
    return {token for token in body.split() if len(token) > 4}


def _similarity(a, b):

    left = _body_signature(a)
    right = _body_signature(b)
    if not left or not right:
        return 0
    return len(left & right) / max(1, len(left | right))


def _assert_package(package, expected_filename):

    assert package["package_status"] == "ready", package
    assert package["quality_gate"]["passed"], package
    assert package["media_package"]["verified_media_ids"], package
    text = _public_text(package)
    lower = text.lower()
    for phrase in BANNED:
        assert phrase not in lower, (phrase, package)
    assert "#MordenFireRescue" not in text, package
    assert package["facebook_caption"] != package["instagram_caption"], package
    assert any(
        item["filename"] == expected_filename
        for item in package["search_diagnostics"]["matched_media"]
    ), package
    option = package["options"][0]
    quality = option["caption_quality"]
    assert quality["emoji_compliance"], quality
    assert quality["hashtag_compliance"], quality
    assert quality["grounded_fact_count"] >= 2, quality
    assert quality["specificity_score"] >= 70, quality
    assert option["communication_objective"], option
    assert option["narrative_angle"], option
    assert option["narrative_focus"], option
    return option


def main():

    original = Path.cwd()
    with TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            db = DatabaseManager()
            db.initialize()
            _seed(db)
            service = ContentDirectorRetrievalService(database=db)

            daycare = service.build_prompt_package("daycare visit")
            daycare_option = _assert_package(daycare, "daycare_spraydown.jpg")
            daycare_text = _public_text(daycare).lower()
            assert daycare_option["communication_objective"] in (
                "Build Community Connection",
                "Entertain",
            ), daycare_option
            assert "hose line" in daycare_text or "spray-down" in daycare_text or "spray down" in daycare_text, daycare
            assert "one action" not in daycare_text, daycare
            assert "residents can take" not in daycare_text, daycare

            recruitment = service.build_prompt_package("volunteer recruitment")
            recruitment_option = _assert_package(recruitment, "recruitment_training.jpg")
            recruitment_text = _public_text(recruitment).lower()
            assert recruitment_option["communication_objective"] == "Recruit", recruitment_option
            assert "training" in recruitment_text, recruitment
            assert "equipment" in recruitment_text or "pager" in recruitment_text, recruitment
            assert "community education" not in recruitment_text, recruitment
            assert _similarity(_public_text(daycare), _public_text(recruitment)) < 0.5

            fireworks = service.build_prompt_package("fireworks")
            _assert_package(fireworks, "fireworks_safety.jpg")
            assert "fireworks" in _public_text(fireworks).lower(), fireworks

            smoke = service.build_prompt_package("smoke alarm")
            _assert_package(smoke, "smoke_alarm_check.jpg")
            assert "smoke alarm" in _public_text(smoke).lower(), smoke

            rope = service.build_prompt_package("rope rescue")
            _assert_package(rope, "rope_rescue_training.jpg")
            assert "rope" in _public_text(rope).lower(), rope

            hydrant = service.build_prompt_package("hydrant heroes")
            _assert_package(hydrant, "hydrant_heroes.jpg")
            assert "hydrant" in _public_text(hydrant).lower(), hydrant

            water = service.build_prompt_package("water safety")
            _assert_package(water, "water_safety.jpg")

            packages = [daycare, recruitment, fireworks, smoke, rope, hydrant, water]
            for index, left in enumerate(packages):
                for right in packages[index + 1:]:
                    assert _similarity(_public_text(left), _public_text(right)) < 0.5, (
                        left["prompt"],
                        right["prompt"],
                    )
        finally:
            os.chdir(original)

    print("sprint49_2 narrative writing smoke passed")


if __name__ == "__main__":
    main()
