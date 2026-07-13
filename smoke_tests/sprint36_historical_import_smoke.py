import csv
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from gui.communications_memory_page import CommunicationsMemoryPage
from gui.home_page import HomePage
from services.communication_import_service import CommunicationImportService
from services.communications_intelligence_service import CommunicationsIntelligenceService
from services.communications_memory_service import CommunicationsMemoryService
from services.communications_officer_service import CommunicationsOfficerService
from services.editorial_recommendation_service import EditorialRecommendationService


def write_csv(path):

    rows = [
        {
            "title": "Hydrant Heroes",
            "body": "Hydrant Heroes helps keep hydrants clear through winter. Check the hydrant near your home today. #HydrantHeroes",
            "published_date": "2026-01-15T09:30:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-1",
            "reactions": "14",
            "comments": "2",
            "shares": "3",
            "attachment_filenames": "hydrant.jpg",
            "campaign": "Hydrant Heroes"
        },
        {
            "title": "Hydrant Heroes IG",
            "body": "Hydrant Heroes helps keep hydrants clear through winter. Check the hydrant near your home today. #HydrantHeroes",
            "published_date": "2026-01-15T09:35:00+00:00",
            "platform": "instagram",
            "source_identifier": "ig-1",
            "views": "80",
            "attachment_filenames": "hydrant.jpg",
            "campaign": "Hydrant Heroes"
        },
        {
            "title": "Training Night",
            "body": "Training night builds skill and teamwork for our volunteer firefighters. Learn how you can serve.",
            "published_date": "15/06/2026",
            "platform": "facebook",
            "source_identifier": "fb-2",
            "campaign": "Volunteer Recruitment",
            "program": "Recruit Academy"
        }
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = sorted(
            {
                key
                for row in rows
                for key in row.keys()
            }
        )
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json_list(path):

    payload = [
        {
            "caption": "Smoke alarms save lives. Check yours tonight.",
            "created_at": "2026-10-08T18:00:00Z",
            "platform": "facebook",
            "post_id": "fb-json-1"
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_facebook_export(path):

    payload = {
        "page": "Morden Fire Rescue",
        "posts": [
            {
                "timestamp": 1780000000,
                "data": [
                    {
                        "post": "Fire Prevention Week starts soon. Test your smoke alarms and plan two ways out."
                    }
                ],
                "attachments": [
                    {
                        "data": [
                            {
                                "media": {
                                    "uri": "photos/smoke_alarm.jpg"
                                }
                            }
                        ]
                    }
                ],
                "title": "Fire Prevention Week"
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_instagram_export(path):

    payload = {
        "profile": {
            "username": "mordenfire"
        },
        "media": [
            {
                "caption": "Community open house with families and firefighters. #MordenFireRescue",
                "taken_at": "2026-08-12T19:00:00+00:00",
                "media_type": "CAROUSEL_ALBUM",
                "permalink": "https://example.invalid/post",
                "id": "ig-export-1"
            }
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def assert_detect(importer, path, expected):

    result = importer.inspect_source(path)
    assert result["source_type"] == expected, result
    assert result["confidence"] > 0, result
    return result


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        folder = Path(folder)
        os.chdir(folder)

        try:
            db = DatabaseManager()
            importer = CommunicationImportService(db)

            csv_path = folder / "historical.csv"
            json_path = folder / "posts.json"
            facebook_path = folder / "facebook.json"
            instagram_path = folder / "instagram.json"
            unsupported_path = folder / "unsupported.json"
            ambiguous_path = folder / "ambiguous.csv"

            write_csv(csv_path)
            write_json_list(json_path)
            write_facebook_export(facebook_path)
            write_instagram_export(instagram_path)
            unsupported_path.write_text(json.dumps({"unexpected": {"shape": True}}), encoding="utf-8")
            ambiguous_path.write_text(
                "body,published_date,platform\nAmbiguous date,03/04/2026,facebook\n",
                encoding="utf-8"
            )

            assert_detect(importer, csv_path, "generic_csv")
            assert_detect(importer, json_path, "generic_json_list")
            assert_detect(importer, facebook_path, "facebook_export")
            assert_detect(importer, instagram_path, "instagram_export")
            unsupported = importer.inspect_source(unsupported_path)
            assert unsupported["source_type"] == "unsupported", unsupported

            preview = importer.preview_file(
                csv_path,
                mapping={
                    "title": "title",
                    "text": "body",
                    "published_date": "published_date",
                    "platform": "platform",
                    "source_identifier": "source_identifier"
                },
                date_format="canadian_date"
            )
            assert preview["manual_mapping_supported"], preview
            assert preview["sample_normalized_records"], preview
            assert preview["invalid_record_count"] == 0, preview

            ambiguous_preview = importer.preview_file(ambiguous_path)
            assert ambiguous_preview["invalid_record_count"] == 1, ambiguous_preview
            assert any("Ambiguous date" in warning for warning in ambiguous_preview["warnings"]), ambiguous_preview

            dst_preview = importer.preview_file(
                ambiguous_path,
                date_format="canadian_date"
            )
            assert dst_preview["invalid_record_count"] == 0, dst_preview

            progress = []
            summary = importer.import_file(
                csv_path,
                mapping={
                    "title": "title",
                    "text": "body",
                    "published_date": "published_date",
                    "platform": "platform",
                    "source_identifier": "source_identifier"
                },
                date_format="canadian_date",
                progress_callback=progress.append
            )
            assert summary["status"] == "completed", summary
            assert summary["records_inserted"] == 2, summary
            assert summary["linked_as_delivery"] == 1, summary
            assert summary["deliveries_inserted"] == 3, summary
            assert "Hydrant Heroes" in summary["campaigns_detected"], summary
            assert summary["profile_rebuild_seconds"] >= 0, summary

            conn = db.connection()
            conn.row_factory = __import__("sqlite3").Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM communication_records ORDER BY communication_id")
            records = cur.fetchall()
            assert records[0]["raw_record_json"], "raw record not preserved"
            assert records[0]["original_date_text"], "original date text not preserved"
            assert records[0]["normalized_date_utc"], "normalized date missing"
            assert records[0]["import_run_id"] == summary["import_run_id"], records[0]["import_run_id"]

            cur.execute("SELECT COUNT(*) FROM communication_media_references")
            assert cur.fetchone()[0] >= 1, "missing media references"
            cur.execute("SELECT COUNT(*) FROM communication_deliveries")
            assert cur.fetchone()[0] == 3, "expected cross-platform delivery link"
            conn.close()

            duplicate_summary = importer.import_file(
                csv_path,
                date_format="canadian_date"
            )
            assert duplicate_summary["duplicates_skipped"] >= 2, duplicate_summary

            changed_path = folder / "changed.csv"
            changed_path.write_text(
                "body,published_date,platform,source_identifier\n"
                "Hydrant Heroes helps keep hydrants clear through winter. Please check your closest hydrant today.,2026-01-15T10:00:00+00:00,facebook,fb-3\n",
                encoding="utf-8"
            )
            changed_summary = importer.import_file(changed_path)
            assert changed_summary["probable_duplicates_review"] >= 1, changed_summary

            effective = db.effective_communication_memory(limit=10)
            assert effective, "expected effective communication memory"
            corrected = importer.review_intelligence(
                effective[0]["communication_id"],
                {
                    "campaigns": ["Hydrant Heroes"],
                    "topics": ["winter_safety", "hydrant"]
                },
                notes="Smoke test correction."
            )
            assert corrected["source_layer"] == "human_corrected", corrected

            memory = CommunicationsMemoryService(db)
            stats = memory.statistics()
            assert stats["engine"]["memory_available"] is True, stats
            assert stats["communication_records"] >= 2, stats
            assert stats["communication_deliveries"] >= 3, stats
            assert stats["engine"]["top_topics"], stats

            profile = CommunicationsIntelligenceService(db).profile(force=True)
            assert profile["sample_count"] >= 2, profile
            assert profile["platform_profiles"]["facebook"]["sample_count"] >= 1, profile

            officer = CommunicationsOfficerService(db)
            brief = officer.generate(force=True)
            assert brief["communications_memory_status"]["historical_communications_imported"] >= 2, brief

            editorial = EditorialRecommendationService(db)
            recommendations = editorial.generate_recommendations(
                limit=1,
                candidate_limit=5,
                context="sprint36_smoke"
            )
            assert isinstance(recommendations, list), recommendations

            rollback = importer.rollback_import_run(summary["import_run_id"])
            assert rollback["status"] == "rolled_back", rollback
            assert rollback["communications_removed"] == 2, rollback

            cancelled = importer.import_file(
                csv_path,
                date_format="canadian_date",
                cancel_check=lambda: True
            )
            assert cancelled["status"] == "cancelled", cancelled

            assert hasattr(CommunicationsMemoryPage, "show_import_preview")
            assert hasattr(CommunicationsMemoryPage, "import_preview_text")
            assert hasattr(HomePage, "render_memory_status")
            assert not hasattr(importer, "network")

        finally:
            os.chdir(original)

    print("sprint36 historical import smoke passed")


if __name__ == "__main__":
    main()
