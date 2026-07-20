from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from gui.content_director_page import ContentDirectorPage
from services.daily_communications_officer_service import DailyCommunicationsOfficerService
from services.editorial_fact_sheet_service import EditorialFactSheetService
from services.time_service import TimeService
from smoke_tests.sprint46_fast_officer_smoke import add_media, create_image


BANNED = (
    "attached media",
    "visual anchor",
    "similar seasonal reminders",
    "keeps the message familiar",
    "selected media",
    "historical evidence",
    "practical readiness",
    "one task at a time",
    "#MordenFireRescue"
)


def save_event_media(db, media_id, title, capture_time, review="review_required", trust="unreviewed_real"):

    db.save_ai_analysis(media_id, {
        "description": f"{title} community event firefighters people local activity.",
        "scene_type": "community",
        "activity": title,
        "people_count": 3,
        "keywords": title.lower().split(),
        "provider": "ollama",
        "model": "real-test",
        "review_status": review,
        "trust_state": trust,
        "failure_reason": "",
        "overall_score": 86,
        "last_analyzed": TimeService.utc_now_iso()
    })
    db.save_media_intelligence(media_id, {
        "normalized_scene": "community",
        "incident_type": "community event",
        "primary_activity": title,
        "content_tags": title.lower().split(),
        "content_themes": ["community connection"],
        "recommended_uses": ["community", "recruitment"],
        "search_text": title,
        "intelligence_score": 84,
        "communications_score": 88,
        "source_model": "real-test"
    })
    conn = db.connection()
    conn.execute(
        "UPDATE media SET capture_time=?, width=640, height=420 WHERE id=?",
        (capture_time.isoformat(timespec="seconds"), media_id)
    )
    conn.commit()
    conn.close()


def seed_event(db, root, folder_name, title, start_index, base_time):

    folder = root / folder_name
    folder.mkdir(parents=True)
    ids = []
    for index in range(3):
        path = folder / f"IMG_{start_index + index}.jpg"
        create_image(path, ("red", "green", "blue", "yellow", "purple")[index])
        media_id = add_media(db, path, start_index + index)
        save_event_media(
            db,
            media_id,
            title,
            base_time + timedelta(minutes=index * 3),
            review="approved" if index == 0 else "review_required",
            trust="approved_real" if index == 0 else "unreviewed_real"
        )
        ids.append(media_id)
    return ids


def assert_public_copy(package):

    facebook = package.get("facebook_caption", "")
    instagram = package.get("instagram_caption", "")
    combined = (facebook + "\n" + instagram).lower()
    assert facebook, package
    assert instagram, package
    assert facebook.strip() != instagram.strip(), package
    for phrase in BANNED:
        assert phrase.lower() not in combined, (phrase, package)
    assert package.get("caption_quality", {}).get("passed"), package
    assert package.get("caption_quality", {}).get("specificity_score", 0) >= 70, package


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            media_root = Path(folder) / "media"
            base_time = TimeService.to_local(TimeService.utc_now())
            seed_event(
                db,
                media_root,
                "Morden Daycare Spray Down July 2026",
                "Morden Daycare Spray Down July 2026",
                100,
                base_time
            )
            seed_event(
                db,
                media_root,
                "Helmet Promotion",
                "Helmet Promotion",
                200,
                base_time + timedelta(hours=1)
            )

            daily = DailyCommunicationsOfficerService(database=db)
            brief = daily.generate(force=True)
            packages = brief.get("daily_post_packages") or []
            assert len(packages) == 3, packages

            by_title = {
                package.get("title"): package
                for package in packages
            }
            daycare = by_title["Morden Daycare Spray Down July 2026"]
            helmet = by_title["Helmet Promotion"]

            assert daycare["event_fact_sheet"]["content_type"] == "daycare_spray_down", daycare
            assert "daycare" in daycare["facebook_caption"].lower(), daycare
            assert "spray-down" in daycare["facebook_caption"].lower(), daycare
            assert "hose line" in daycare["facebook_caption"].lower(), daycare
            assert "firefighter-sized" in daycare["instagram_caption"].lower(), daycare
            assert_public_copy(daycare)

            assert helmet["event_fact_sheet"]["content_type"] == "helmet_promotion", helmet
            assert "new helmet" in helmet["facebook_caption"].lower(), helmet
            assert "milestone" in helmet["facebook_caption"].lower(), helmet
            assert "responsibility" in helmet["instagram_caption"].lower(), helmet
            assert_public_copy(helmet)

            fact_service = EditorialFactSheetService()
            missing = fact_service.build_fact_sheet({"title": "Unknown"})
            copy = fact_service.generate_captions(missing)
            assert "More event context is needed" in copy["facebook"], copy
            assert copy["quality"]["passed"] is False, copy

            page = object.__new__(ContentDirectorPage)
            page.daily_officer_service = daily
            proactive = page.load_proactive_brief(force=True)
            opportunities = proactive.get("recommendations") or []
            diagnostics = proactive.get("opportunity_rejection_diagnostics") or {}
            assert len(opportunities) >= 3, proactive
            assert opportunities[0]["title"] == packages[0]["title"], opportunities
            assert diagnostics["examined"] == 3, diagnostics
            assert diagnostics["accepted"] == len(opportunities), diagnostics

        finally:
            os.chdir(original)

    print("sprint47_editorial_quality_smoke passed")


if __name__ == "__main__":
    main()
