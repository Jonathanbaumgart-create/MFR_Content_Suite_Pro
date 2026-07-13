from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import json
import os
import sys
import time


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager


def write_csv(path):

    rows = [
        {
            "title": "Smoke Alarm Reminder",
            "text": "Smoke alarms save lives. Test your smoke alarms tonight.",
            "published_date": "2026-06-01T09:30:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-1",
            "photo_count": "1",
            "campaign": "Smoke Alarm Campaign",
            "topics": "smoke_alarm, fire_prevention",
            "engagement_metrics": "{\"likes\": 10, \"shares\": 2}"
        },
        {
            "title": "Smoke Alarm Reminder Instagram",
            "text": "Smoke alarms save lives. Test your smoke alarms tonight.",
            "published_date": "2026-06-01T09:30:00+00:00",
            "platform": "instagram",
            "source_identifier": "ig-1",
            "photo_count": "1",
            "campaign": "Smoke Alarm Campaign",
            "topics": "smoke_alarm"
        },
        {
            "title": "Smoke Alarm Reminder Exact Duplicate",
            "text": "Smoke alarms save lives. Test your smoke alarms tonight.",
            "published_date": "2026-06-01T09:30:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-1",
            "photo_count": "1",
            "campaign": "Smoke Alarm Campaign",
            "topics": "smoke_alarm"
        },
        {
            "title": "Smoke Alarm Reminder Website",
            "text": "  Smoke alarms save lives.   Test your smoke alarms tonight. ",
            "published_date": "2026-06-01T09:30:00+00:00",
            "platform": "website",
            "source_identifier": "web-smoke-1",
            "permalink": "https://example.invalid/smoke",
            "photo_count": "1",
            "campaign": "Smoke Alarm Campaign",
            "topics": "smoke_alarm"
        },
        {
            "title": "Smoke Alarm Battery Reminder",
            "text": "Smoke alarms save lives. Replace batteries and test alarms monthly.",
            "published_date": "2026-06-01T09:30:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-1-updated",
            "photo_count": "1",
            "campaign": "Smoke Alarm Campaign",
            "topics": "smoke_alarm"
        },
        {
            "title": "Hydrant Heroes",
            "text": "Hydrant Heroes helps keep hydrants clear during winter.",
            "published_date": "2026-01-05T12:00:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-hydrant-heroes",
            "program": "Hydrant Heroes"
        },
        {
            "title": "Generic winter hydrant note",
            "text": "Please keep snow cleared around hydrants this winter.",
            "published_date": "2026-01-10T12:00:00+00:00",
            "platform": "website",
            "source_identifier": "web-1",
            "campaign": "",
            "program": ""
        },
        {
            "title": "Travelling Sparky Visit",
            "text": "Travelling Sparky visited students for public education.",
            "published_date": "2026-05-03T12:00:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-2",
            "program": "Travelling Sparky"
        },
        {
            "title": "Training Night",
            "text": "Firefighters completed a general training drill at the station.",
            "published_date": "2026-03-02T18:00:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-training"
        },
        {
            "title": "SCBA Training",
            "text": "Firefighters completed SCBA confidence training with breathing apparatus.",
            "published_date": "2026-03-09T18:00:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-scba"
        },
        {
            "title": "Recruitment",
            "text": "Join our crew and volunteer with Morden Fire & Rescue.",
            "published_date": "2026-04-01T18:00:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-recruitment",
            "campaign": "Volunteer Recruitment"
        },
        {
            "title": "Firefighter Feature",
            "text": "A firefighter checked equipment at the station.",
            "published_date": "2026-04-03T18:00:00+00:00",
            "platform": "facebook",
            "source_identifier": "fb-firefighter-feature"
        },
        {
            "title": "Partial Record",
            "text": "Community open house at the fire hall.",
            "published_date": "",
            "platform": "website",
            "source_identifier": "web-partial"
        },
        {
            "title": "Invalid",
            "text": "",
            "published_date": "06/01/2026",
            "platform": "facebook",
            "source_identifier": "bad-1"
        }
    ]

    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        fieldnames = sorted({key for row in rows for key in row.keys()})
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path):

    payload = {
        "communications": [
            {
                "headline": "Recruitment Night",
                "caption": "Join our crew for training night and serve Morden.",
                "created_at": "2026-04-02T18:00:00+00:00",
                "platform": "facebook",
                "post_id": "fb-3",
                "program": "Recruit Academy",
                "campaign": "Volunteer Recruitment",
                "tags": ["recruitment", "training"]
            },
            {
                "headline": "Recruitment Night Instagram",
                "caption": "Join our crew for training night and serve Morden.",
                "created_at": "2026-04-02T18:00:00+00:00",
                "platform": "instagram",
                "post_id": "ig-3",
                "program": "Recruit Academy",
                "campaign": "Volunteer Recruitment",
                "tags": ["recruitment", "training"]
            },
            {
                "headline": "Recruitment Night Exact Duplicate",
                "caption": "Join our crew for training night and serve Morden.",
                "created_at": "2026-04-02T18:00:00+00:00",
                "platform": "facebook",
                "post_id": "fb-3",
                "program": "Recruit Academy",
                "campaign": "Volunteer Recruitment",
                "tags": ["recruitment", "training"]
            },
            {
                "headline": "Partial JSON Record",
                "caption": "Community open house at the fire hall.",
                "platform": "website"
            },
            {
                "headline": "Malformed JSON Record",
                "caption": "",
                "created_at": "06/01/2026",
                "platform": "facebook"
            }
        ]
    }

    Path(path).write_text(json.dumps(payload), encoding="utf-8")


def add_recommendation_media(db):

    db.add_media(
        {
            "filename": "smoke_alarm.jpg",
            "path": str(Path("library") / "smoke_alarm.jpg"),
            "extension": ".jpg",
            "type": "image",
            "size": 100,
            "sha256": "communication-memory-engine-media"
        }
    )
    db.save_media_intelligence(
        1,
        {
            "normalized_scene": "public_education",
            "incident_type": "public_education",
            "primary_activity": "smoke_alarm_education",
            "apparatus_tags": [],
            "equipment_tags": ["smoke_alarm"],
            "ppe_tags": [],
            "people_tags": ["community"],
            "content_tags": ["smoke_alarm", "fire_prevention", "safety"],
            "content_themes": ["public_education"],
            "recommended_uses": ["public_education", "smoke_alarm"],
            "search_text": "smoke alarm public education safety",
            "intelligence_score": 88,
            "source_model": "smoke-test"
        }
    )
    db.save_communications_scores(
        1,
        {
            "communications_score": 82,
            "communications_category_scores": {},
            "platform_suitability": {"facebook": 85, "instagram": 70},
            "storytelling_score": 65,
            "community_engagement_score": 70,
            "educational_value_score": 92,
            "recruitment_value_score": 10,
            "recognition_value_score": 10,
            "emergency_response_value_score": 5,
            "public_education_value_score": 95,
            "seasonal_relevance_score": 70,
            "visual_impact_score": 70,
            "trust_building_score": 70,
            "emotional_impact_score": 55,
            "evergreen_score": 90,
            "time_sensitive_score": 20,
            "historical_importance_score": 10,
            "uniqueness_score": 55,
            "posting_frequency_risk": 0,
            "suggested_campaigns": ["Smoke Alarm Campaign"],
            "suggested_audience": ["community"],
            "suggested_platform": "facebook",
            "suggested_time_of_year": "fall",
            "communications_reasoning": ["Smoke alarm education test media."]
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            db.initialize()
            add_recommendation_media(db)

            from services.communication_import_service import CommunicationImportService
            from services.communication_history_service import CommunicationHistoryService
            from services.communications_memory_service import CommunicationsMemoryService
            from services.recommendation_candidate_service import RecommendationCandidateService

            importer = CommunicationImportService(database=db)
            csv_path = Path(folder) / "communications.csv"
            json_path = Path(folder) / "communications.json"
            empty_path = Path(folder) / "empty.csv"
            write_csv(csv_path)
            write_json(json_path)
            empty_path.write_text("title,text,published_date\n", encoding="utf-8")

            memory = CommunicationsMemoryService(db)
            candidate = RecommendationCandidateService(database=db, memory_service=memory)
            profile = {
                "terms": ("smoke_alarm", "smoke alarms"),
                "topic": "smoke_alarm",
                "category": "Smoke Alarm"
            }
            before_profile = candidate._memory_profile(profile, memory.search("", limit=10))
            assert not before_profile["memory_available"], before_profile

            preview = importer.preview_file(csv_path)
            assert "text" in preview["mapped_fields"].values(), preview
            assert "platform" in preview["mapped_fields"].values(), preview
            assert preview["sample_normalized_records"], preview

            dry_run = importer.import_file(csv_path, dry_run=True)
            assert dry_run["records_processed"] == 14, dry_run
            assert db.communication_memory_engine_summary()["records"] == 0

            progress_updates = []
            csv_started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    importer.import_file,
                    csv_path,
                    progress_callback=progress_updates.append
                )
                summary = future.result(timeout=10)
            csv_elapsed = time.perf_counter() - csv_started

            assert progress_updates, progress_updates
            assert summary["records_processed"] == 14, summary
            assert summary["records_inserted"] == 9, summary
            assert summary["linked_as_delivery"] == 2, summary
            assert summary["deliveries_inserted"] == 11, summary
            assert summary["duplicates_skipped"] == 1, summary
            assert summary["records_failed"] == 2, summary
            assert summary["records_processed"] == (
                summary["records_inserted"] +
                summary["linked_as_delivery"] +
                summary["duplicates_skipped"] +
                summary["records_failed"]
            ), summary
            assert "Hydrant Heroes" in summary["campaigns_detected"], summary
            assert "Smoke Alarm Campaign" in summary["campaigns_detected"], summary
            assert "Travelling Sparky" in summary["programs_detected"], summary
            assert "SCBA Training" in summary["programs_detected"], summary
            assert "smoke_alarm" in summary["topics_extracted"], summary
            assert "scba_training" in summary["topics_extracted"], summary

            repeat = importer.import_file(csv_path)
            assert repeat["records_inserted"] == 0, repeat
            assert repeat["deliveries_inserted"] == 0, repeat
            assert repeat["duplicates_skipped"] == 12, repeat
            assert repeat["records_failed"] == 2, repeat

            json_started = time.perf_counter()
            json_summary = importer.import_file(json_path)
            json_elapsed = time.perf_counter() - json_started
            assert json_summary["records_processed"] == 5, json_summary
            assert json_summary["records_inserted"] == 1, json_summary
            assert json_summary["deliveries_inserted"] == 2, json_summary
            assert json_summary["linked_as_delivery"] == 1, json_summary
            assert json_summary["duplicates_skipped"] == 1, json_summary
            assert json_summary["records_failed"] == 2, json_summary
            assert "Volunteer Recruitment" in json_summary["campaigns_detected"], json_summary
            assert "Recruit Academy" in json_summary["programs_detected"], json_summary

            empty = importer.import_file(empty_path)
            assert empty["records_processed"] == 0, empty
            assert empty["records_inserted"] == 0, empty

            engine = db.communication_memory_engine_summary()
            assert engine["records"] == 10, engine
            assert engine["deliveries"] == 13, engine
            assert engine["campaigns"] >= 4, engine
            assert engine["programs"] >= 4, engine
            assert engine["topics"] >= 8, engine
            assert engine["import_runs"] >= 3, engine

            history = CommunicationHistoryService(database=db)
            smoke_history = history.topic_history("smoke_alarm")
            assert smoke_history["count"] >= 2, smoke_history
            assert smoke_history["last_posted"].startswith("2026-06-01"), smoke_history
            assert history.topic_history("unknown_topic")["count"] == 0
            assert history.campaign_history("Smoke Alarm Campaign")["count"] >= 2
            assert history.program_history("Travelling Sparky")["count"] == 1

            rows = history.effective_memory(limit=100)
            generic_winter = [row for row in rows if "hydrants this winter" in row["original_text"]][0]
            assert "Hydrant Heroes" not in generic_winter.get("campaigns", []), generic_winter
            assert "Hydrant Heroes" not in generic_winter.get("programs", []), generic_winter
            hydrant_heroes = [row for row in rows if "Hydrant Heroes helps" in row["original_text"]][0]
            assert "Hydrant Heroes" in hydrant_heroes.get("campaigns", []), hydrant_heroes
            assert "Hydrant Heroes" in hydrant_heroes.get("programs", []), hydrant_heroes
            general_training = [row for row in rows if "general training" in row["original_text"]][0]
            assert "scba_training" not in general_training.get("topics", []), general_training
            assert "SCBA Training" not in general_training.get("programs", []), general_training
            scba_training = [row for row in rows if "SCBA confidence" in row["original_text"]][0]
            assert "scba_training" in scba_training.get("topics", []), scba_training
            assert "SCBA Training" in scba_training.get("programs", []), scba_training
            firefighter_feature = [row for row in rows if "A firefighter checked" in row["original_text"]][0]
            assert "recruitment" not in firefighter_feature.get("topics", []), firefighter_feature
            recruitment = [row for row in rows if "Join our crew and volunteer" in row["original_text"]][0]
            assert "recruitment" in recruitment.get("topics", []), recruitment

            smoke_record = [
                row for row in rows
                if row["original_text"] == "Smoke alarms save lives. Test your smoke alarms tonight."
            ][0]
            smoke_deliveries = db.communication_deliveries(smoke_record["communication_id"], limit=10)
            assert {item["platform"] for item in smoke_deliveries} == {
                "facebook",
                "instagram",
                "website"
            }, smoke_deliveries

            first = history.effective_memory(limit=1)[0]
            original_category = first.get("category", "")
            original_text = first.get("original_text", "")
            original_date = first.get("original_date", "")
            original_source = first.get("source_identifier", "")
            db.save_communication_correction(
                {
                    "communication_id": first["communication_id"],
                    "field_name": "category",
                    "original_value": original_category,
                    "corrected_value": "human_corrected_category",
                    "correction_source": "Jonathan",
                    "notes": "Smoke test override."
                }
            )
            corrected = db.effective_communication_intelligence(first["communication_id"])
            assert corrected["category"] == "human_corrected_category", corrected
            db.save_communication_correction(
                {
                    "communication_id": first["communication_id"],
                    "field_name": "category",
                    "original_value": corrected["category"],
                    "corrected_value": "second_corrected_category",
                    "correction_source": "Jonathan",
                    "notes": "Smoke test supersede."
                }
            )
            superseded = db.effective_communication_intelligence(first["communication_id"])
            assert superseded["category"] == "second_corrected_category", superseded
            db.clear_communication_correction(first["communication_id"], "category")
            restored = db.effective_communication_intelligence(first["communication_id"])
            assert restored["category"] == original_category, restored
            raw_first = [
                row for row in db.communication_records(limit=20)
                if row["communication_id"] == first["communication_id"]
            ][0]
            assert raw_first["original_text"] == original_text, raw_first
            assert raw_first["original_date"] == original_date, raw_first
            assert raw_first["source_identifier"] == original_source, raw_first
            conn = db.connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM communication_editorial_intelligence WHERE communication_id=?",
                (first["communication_id"],)
            )
            assert cur.fetchone()[0] >= 1
            cur.execute(
                "SELECT COUNT(*) FROM communication_intelligence_corrections WHERE communication_id=?",
                (first["communication_id"],)
            )
            assert cur.fetchone()[0] >= 2
            conn.close()

            posts = memory.search("", limit=10)
            assert posts and posts[0].get("topics") is not None, posts
            stats = memory.statistics()
            assert stats["communication_records"] == 10, stats
            assert stats["communication_deliveries"] == 13, stats
            assert stats["engine"]["memory_available"], stats
            assert len(posts) <= 10, posts
            memory_profile = candidate._memory_profile(profile, posts)
            assert memory_profile["memory_available"], memory_profile
            assert memory_profile["matching_posts"] >= 1, memory_profile
            assert memory_profile["last_posted"].startswith("2026-06-01"), memory_profile
            unavailable = candidate._memory_profile(profile, [])
            assert not unavailable["memory_available"], unavailable
            assert before_profile["memory_available"] is False, before_profile

            db.initialize()

            from gui.communications_memory_page import CommunicationsMemoryPage
            assert CommunicationsMemoryPage is not None

            csv_rate = round(summary["records_processed"] / max(csv_elapsed, 0.001), 1)
            json_rate = round(json_summary["records_processed"] / max(json_elapsed, 0.001), 1)
            print(
                "communication memory engine metrics "
                f"csv_processed={summary['records_processed']} "
                f"csv_inserted={summary['records_inserted']} "
                f"csv_duplicates={summary['duplicates_skipped']} "
                f"csv_failed={summary['records_failed']} "
                f"csv_rate={csv_rate}/s "
                f"json_processed={json_summary['records_processed']} "
                f"json_inserted={json_summary['records_inserted']} "
                f"json_duplicates={json_summary['duplicates_skipped']} "
                f"json_failed={json_summary['records_failed']} "
                f"json_rate={json_rate}/s "
                f"progress_updates={len(progress_updates)} "
                f"json_payload_bytes={json_path.stat().st_size}"
            )

        finally:
            os.chdir(original)

    print("communication_memory_engine smoke passed")


if __name__ == "__main__":
    main()
