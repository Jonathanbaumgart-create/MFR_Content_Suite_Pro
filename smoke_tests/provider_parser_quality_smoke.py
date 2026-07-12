import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ai_service import AIService


def assert_between(value, low, high):

    assert low <= value <= high, value


def main():

    parser = AIService()

    valid = parser.parse_analysis(
        """
        {
          "description": "Two firefighters standing beside a fire truck.",
          "people_count": "2",
          "people": ["firefighters"],
          "apparatus": ["fire truck"],
          "equipment": null,
          "activities": ["standing"],
          "setting": "station bay",
          "indoor_outdoor": "indoor",
          "training": false,
          "incident_scene": false,
          "public_education": false,
          "community_event": false,
          "safety_concerns": [],
          "public_use_risks": [],
          "confidence": 0.82
        }
        """,
        "test-model"
    )
    assert valid["parse_status"] == parser.STATUS_VALID, valid
    assert valid["people_count"] == 2, valid
    assert valid["equipment"] == [], valid
    assert valid["confidence"] == 0.82, valid

    repaired = parser.parse_analysis(
        "Here is JSON:\n```json\n{\"description\":\"A fire engine.\",\"confidence\":75}\n```",
        "test-model"
    )
    assert repaired["parse_status"] == parser.STATUS_REPAIRED, repaired
    assert_between(repaired["confidence"], 0, 0.7)

    partial = parser.parse_analysis(
        "{\"description\":\"A firefighter holding a hose\",\"people_count\":1,\"confidence\":0.9",
        "test-model"
    )
    assert partial["parse_status"] == parser.STATUS_PARTIAL, partial
    assert partial["people_count"] == 1, partial
    assert_between(partial["confidence"], 0, 0.35)

    invalid = parser.parse_analysis(
        "not json at all",
        "test-model"
    )
    assert invalid["parse_status"] == parser.STATUS_INVALID, invalid
    assert invalid["description"] == "", invalid
    assert invalid["confidence"] <= 0.05, invalid

    empty = parser.parse_analysis("", "test-model")
    assert empty["parse_status"] == parser.STATUS_EMPTY, empty
    assert empty["raw_response"] == "", empty
    assert empty["confidence"] == 0, empty

    inferred_people = parser.parse_analysis(
        "{\"description\":\"A firefighter beside equipment\",\"confidence\":0.5}",
        "test-model"
    )
    assert inferred_people["people_count"] == 1, inferred_people

    print("provider_parser_quality_smoke passed")


if __name__ == "__main__":
    main()
