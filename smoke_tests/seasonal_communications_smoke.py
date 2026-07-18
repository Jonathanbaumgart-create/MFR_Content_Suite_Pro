import hashlib
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.communications_officer_service import CommunicationsOfficerService
from services.content_director_retrieval_service import ContentDirectorRetrievalService
from services.seasonal_communications_service import SeasonalCommunicationsService


def save_post(
    db,
    title,
    text,
    published,
    topics=None,
    programs=None,
    campaigns=None,
    platform="facebook",
    source_id=None,
    confidence=80
):

    source_id = source_id or hashlib.sha1(
        f"{title}|{published}|{text}".encode("utf-8")
    ).hexdigest()[:16]
    result = db.save_communication_record({
        "title": title,
        "original_text": text,
        "summary": text[:160],
        "original_date": published,
        "normalized_date_utc": published,
        "source_type": "facebook_export",
        "source_identifier": source_id,
        "imported_from": "seasonal_smoke",
        "import_status": "active",
        "imported_at": "2026-07-17T12:00:00+00:00",
        "content_hash": source_id,
        "raw_record": {"text": text}
    })
    communication_id = result["communication_id"]
    db.save_communication_intelligence({
        "communication_id": communication_id,
        "primary_story": title,
        "editorial_angle": title,
        "communication_purpose": "community_safety",
        "category": "public education",
        "intended_audiences": ["Morden residents"],
        "topics": topics or [],
        "programs": programs or [],
        "campaigns": campaigns or [],
        "seasonal_relevance": ["same calendar period"],
        "educational_value": 80,
        "community_trust_value": 70,
        "confidence_score": confidence,
        "source_signals": ["smoke fixture"],
        "analysis_version": "seasonal-smoke",
        "generated_at": "2026-07-17T12:00:00+00:00"
    })
    db.save_communication_delivery({
        "communication_id": communication_id,
        "platform": platform,
        "published_at": published,
        "delivery_text": text,
        "photo_count": 1,
        "media_count": 1,
        "source_file": "seasonal_smoke",
        "delivery_hash": source_id + "-delivery"
    })
    return communication_id


def seed(db):

    save_post(
        db,
        "Water Safety Wednesday",
        "Water Safety Wednesday reminder: wear a life jacket near the water.",
        "2025-07-16T15:00:00+00:00",
        topics=["water safety"],
        programs=["Water Safety Wednesday"],
        campaigns=["Water Safety Wednesday"]
    )
    save_post(
        db,
        "Water Safety Wednesday",
        "Water Safety Wednesday returns with a reminder to supervise children near water.",
        "2024-07-20T15:00:00+00:00",
        topics=["water safety"],
        programs=["Water Safety Wednesday"],
        campaigns=["Water Safety Wednesday"]
    )
    save_post(
        db,
        "Water Rescue Reminder",
        "A late June water safety note about boating and life jackets.",
        "2023-06-28T15:00:00+00:00",
        topics=["water safety"],
        campaigns=["Water Safety Wednesday"]
    )
    save_post(
        db,
        "Fire Chief of the Day",
        "Fire Chief of the Day welcomed a young community member to the hall.",
        "2025-07-17T15:00:00+00:00",
        topics=["community event"],
        programs=["Fire Chief of the Day"]
    )
    save_post(
        db,
        "Fire Prevention Week",
        "Fire Prevention Week starts soon. Test smoke alarms and plan two ways out.",
        "2025-10-06T15:00:00+00:00",
        topics=["fire prevention", "smoke alarm"],
        campaigns=["Fire Prevention Week"]
    )
    save_post(
        db,
        "Fire Prevention Week",
        "Fire Prevention Week is a good time to check smoke alarms.",
        "2024-10-09T15:00:00+00:00",
        topics=["fire prevention", "smoke alarm"],
        campaigns=["Fire Prevention Week"]
    )
    save_post(
        db,
        "Volunteer Recruitment",
        "Volunteer recruitment is open for neighbours ready to serve Morden.",
        "2024-07-15T15:00:00+00:00",
        topics=["volunteer recruitment"],
        campaigns=["Volunteer Recruitment"]
    )
    save_post(
        db,
        "Volunteer Recruitment",
        "Join MFR as a volunteer firefighter and train with the team.",
        "2023-07-18T15:00:00+00:00",
        topics=["volunteer recruitment"],
        campaigns=["Volunteer Recruitment"]
    )
    save_post(
        db,
        "Smoke Advisory",
        "Wildfire smoke may affect air quality. Check current conditions before outdoor activity.",
        "2025-07-12T15:00:00+00:00",
        topics=["wildfire smoke", "air quality", "smoke advisory"],
        campaigns=["Smoke Advisory"]
    )
    save_post(
        db,
        "Ice Safety",
        "Ice safety reminder: stay off thin ice and keep children away from retention ponds.",
        "2025-01-18T15:00:00+00:00",
        topics=["ice safety"],
        campaigns=["Ice Safety"]
    )
    save_post(
        db,
        "Hydrant Heroes",
        "Hydrant Heroes helps keep hydrants clear in winter.",
        "2025-01-20T15:00:00+00:00",
        topics=["hydrant heroes"],
        programs=["Hydrant Heroes"]
    )
    save_post(
        db,
        "Canada Day Fireworks",
        "Canada Day fireworks safety reminder for July 1.",
        "2025-06-29T15:00:00+00:00",
        topics=["fireworks", "canada day"],
        campaigns=["Canada Day Fireworks"]
    )
    save_post(
        db,
        "Water Safety This Year",
        "This year we already shared a water safety reminder.",
        "2026-07-02T15:00:00+00:00",
        topics=["water safety"],
        campaigns=["Water Safety Wednesday"]
    )


def assert_water_safety(service):

    result = service.around_this_time(
        topic="water safety",
        current_date="2026-07-17",
        window_days=21,
        limit=6
    )
    assert result["bounded"], result
    assert result["matching_year_count"] >= 2, result
    assert result["current_year_already_communicated"], result
    assert "already" in result["communications_gap_risk"].lower(), result
    assert result["matches"][0]["topic"].lower() == "water safety", result
    assert "Fire Chief" not in result["matches"][0]["caption_excerpt"], result
    assert any("Within" in " ".join(item["seasonal_timing_evidence"]) for item in result["matches"]), result
    assert result["recurring_annual_pattern_confidence"] >= 60, result


def assert_edge_cases(service):

    leap = service.around_this_time(
        topic="ice safety",
        current_date="2024-02-29",
        limit=4
    )
    assert leap["query"]["current_date"] == "2024-02-29", leap

    one_off = service.around_this_time(
        topic="fire chief of the day",
        current_date="2026-07-17",
        limit=4
    )
    assert one_off["matching_year_count"] == 1, one_off
    assert "one prior" in one_off["communications_gap_risk"].lower(), one_off

    smoke = service.around_this_time(
        topic="smoke advisory",
        current_date="2026-07-17",
        limit=4
    )
    assert smoke["matches"], smoke
    assert any("current warning" in item.lower() for item in smoke["limitations"]), smoke
    assert "verify current conditions" in smoke["matches"][0]["safe_reuse_note"].lower(), smoke

    missing = service.around_this_time(
        topic="safe grad fireworks",
        current_date="2026-07-17",
        limit=4
    )
    assert not missing["matches"], missing
    assert "no" in missing["communications_gap_risk"].lower(), missing


def assert_integrations(db):

    retrieval = ContentDirectorRetrievalService(database=db)
    package = retrieval.build_prompt_package(
        "water safety Wednesday",
        now="2026-07-17"
    )
    seasonal = package.get("around_this_time", {})
    assert seasonal.get("matches"), package
    assert "Water Safety" in package["opportunity_summary"]["year_over_year_evidence"]["summary"], package
    assert any("Year-over-year" in item for item in package.get("source_signals", [])), package

    officer = CommunicationsOfficerService(database=db)
    opportunity = {
        "title": "Water Safety Wednesday",
        "topic": "water safety",
        "supporting_topics": ["life jackets"],
        "supporting_programs": ["Water Safety Wednesday"],
        "supporting_recent_activity": {"activity_id": "water"},
        "source_signals": [],
        "media_package": {"media_count": 1},
        "uses_reviewed_media": True
    }
    officer._attach_historical_evidence(
        [opportunity],
        [{"activity_id": "water", "historical_matches": []}],
        "2026-07-17"
    )
    assert opportunity["year_over_year_signal"]["summary"], opportunity
    assert any("Year-over-year" in item for item in opportunity["source_signals"]), opportunity


def main():

    original = Path.cwd()
    with TemporaryDirectory() as folder:
        folder = Path(folder)
        os.chdir(folder)
        try:
            db = DatabaseManager()
            seed(db)
            service = SeasonalCommunicationsService(database=db)
            assert_water_safety(service)
            assert_edge_cases(service)
            assert_integrations(db)
        finally:
            os.chdir(original)

    print("seasonal_communications_smoke passed")


if __name__ == "__main__":
    main()
