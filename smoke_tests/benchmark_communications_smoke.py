import csv
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.benchmark_communications_service import BenchmarkCommunicationsService
from services.communication_package_service import CommunicationPackageService
from services.communications_intelligence_service import CommunicationsIntelligenceService
from services.communications_memory_service import CommunicationsMemoryService
from services.content_generation_service import ContentGenerationService
from services.editorial_recommendation_service import EditorialRecommendationService


def write_csv(path):

    rows = [
        {
            "department": "Central Pierce Fire & Rescue",
            "platform": "Facebook",
            "date": "2026-01-15",
            "post_text": "Training today focused on ladder operations. Crews practiced a three-step approach: place, climb, and communicate. Learn more about how training keeps communities ready.",
            "source_url": "https://example.test/central-pierce/1",
            "post_id": "cp-1",
            "media_type": "carousel",
            "photo_count": "4",
            "reactions": "120",
            "comments": "8",
            "shares": "20",
            "hashtags": "#Training #FireService",
            "campaign": "Training Tuesday",
            "topic": "training",
            "audience": "Community residents",
            "editorial_angle": "Training Highlight"
        },
        {
            "department": "South Metro Fire Rescue",
            "platform": "Instagram",
            "date": "2026-02-10",
            "post_text": "Watch the first seconds of this hose evolution and notice the communication between firefighters. Training builds trust before the emergency.",
            "source_url": "https://example.test/south-metro/reel",
            "post_id": "smfr-1",
            "media_type": "reel",
            "video_count": "1",
            "reel": "true",
            "views": "9000",
            "reactions": "640",
            "comments": "28",
            "shares": "71",
            "topic": "training",
            "editorial_angle": "Reel Concept"
        },
        {
            "department": "Orange County Fire Authority",
            "platform": "Facebook",
            "date": "2026-03-01",
            "post_text": "Test your smoke alarms and talk through your home escape plan this weekend.",
            "source_url": "https://example.test/ocfa/smoke",
            "post_id": "ocfa-1",
            "media_type": "photo",
            "photo_count": "1",
            "topic": "smoke_alarm",
            "editorial_angle": "Public Education"
        }
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = sorted({
            key
            for row in rows
            for key in row.keys()
        })
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path):

    path.write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "department": "Calgary Fire Department",
                        "platform": "Facebook",
                        "published_at": "2026-04-05T12:00:00Z",
                        "caption": "Wildfire season is a good time to clear dry material and review your emergency plan.",
                        "source_url": "https://example.test/calgary/wildfire",
                        "post_id": "cfd-1",
                        "media_type": "photo",
                        "topic": "wildfire",
                        "campaign": "Wildfire Awareness"
                    }
                ]
            }
        ),
        encoding="utf-8"
    )


def main():

    original = os.getcwd()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            service = BenchmarkCommunicationsService(database=db)
            csv_path = Path(folder) / "benchmarks.csv"
            json_path = Path(folder) / "benchmarks.json"
            write_csv(csv_path)
            write_json(json_path)

            memory_before = len(CommunicationsMemoryService(database=db).search("", limit=1000))
            profile_before = CommunicationsIntelligenceService(database=db).profile(force=True)

            preview = service.preview_file(csv_path)
            assert preview["detected_format"] == "csv", preview
            assert "Central Pierce Fire & Rescue" in preview["detected_departments"], preview
            assert preview["mapped_fields"]["department"] == "department", preview
            assert preview["engagement_availability"]["with_engagement"] >= 2, preview

            summary = service.import_file(csv_path)
            assert summary["records_inserted"] == 3, summary
            assert summary["patterns_generated"] >= 1, summary

            duplicate = service.import_file(csv_path)
            assert duplicate["duplicates_skipped"] == 3, duplicate

            json_summary = service.import_file(json_path)
            assert json_summary["records_inserted"] == 1, json_summary

            records = service.search({"platform": "instagram"}, limit=10)
            assert any(record["reel_indicator"] for record in records), records
            assert service.search({"media_type": "photo"}, limit=10), "photo filter failed"
            assert service.search({"topic": "training"}, limit=10), "topic filter failed"

            insights = service.insights()
            assert insights["records"] == 4, insights
            assert insights["departments"] >= 3, insights
            assert insights["reel_records"] == 1, insights

            patterns = db.benchmark_patterns(limit=10)
            assert patterns, "patterns missing"
            assert patterns[0]["applicability"], patterns[0]
            db.review_benchmark_pattern(
                patterns[0]["pattern_id"],
                {
                    "human_status": "approved",
                    "applicability": "Highly applicable",
                    "reviewer_notes": "Useful structure for MFR training content.",
                    "adaptation_notes": "Adapt with MFR footage and language.",
                    "saved_for_testing": True,
                    "linked_mfr_campaign": "Training Tuesday",
                    "updated_at": "2026-07-16T00:00:00+00:00"
                }
            )
            experiment_id = db.save_benchmark_experiment(
                {
                    "pattern_id": patterns[0]["pattern_id"],
                    "mfr_adaptation": "Use a three-part training explanation.",
                    "target_platform": "Facebook",
                    "target_campaign": "Training Tuesday",
                    "test_date": "2026-07-20",
                    "expected_outcome": "Better training education clarity.",
                    "created_at": "2026-07-16T00:00:00+00:00",
                    "updated_at": "2026-07-16T00:00:00+00:00"
                }
            )
            assert experiment_id > 0

            recommendation = {
                "recommendation_id": "bench-training",
                "title": "Firefighter Training",
                "summary": "Use MFR training media for a public education post.",
                "topic": "training",
                "category": "Training",
                "editorial_angle": "Training Highlight",
                "recommended_platforms": ["Facebook", "Instagram"],
                "best_asset_ids": [],
                "supporting_asset_ids": []
            }
            evidence = service.advisory_patterns(recommendation, limit=3)
            assert evidence, evidence
            package = CommunicationPackageService(database=db).generate_package(
                recommendation,
                package_type="Facebook"
            )
            assert package["benchmark_inspiration"], package
            generated = ContentGenerationService(database=db).generate_from_package(
                package,
                platforms=["facebook", "instagram"]
            )
            public_copy = json.dumps(generated["copy_buttons"])
            forbidden = (
                "Central Pierce",
                "South Metro",
                "Orange County",
                "https://example.test",
                "benchmark",
                "engagement"
            )
            assert not any(term in public_copy for term in forbidden), public_copy
            assert generated["benchmark_inspiration"], generated

            mfr_profile_after = CommunicationsIntelligenceService(database=db).profile(force=True)
            memory_after = len(CommunicationsMemoryService(database=db).search("", limit=1000))
            assert memory_before == memory_after == 0
            assert profile_before["sample_count"] == mfr_profile_after["sample_count"]

            rolled_back = db.rollback_benchmark_import_run(summary["import_run_id"])
            assert rolled_back == 3, rolled_back
            assert service.insights()["records"] == 1

            # Optional XLSX smoke if openpyxl is available in the current env.
            try:
                from openpyxl import Workbook
                xlsx_path = Path(folder) / "benchmarks.xlsx"
                workbook = Workbook()
                sheet = workbook.active
                sheet.append(["department", "platform", "date", "post_text", "source_url"])
                sheet.append([
                    "Mesa Fire & Medical Department",
                    "LinkedIn",
                    "2026-05-01",
                    "A professional public education update about prevention.",
                    "https://example.test/mesa/1"
                ])
                workbook.save(xlsx_path)
                xlsx_preview = service.preview_file(xlsx_path)
                assert xlsx_preview["detected_format"] == "xlsx", xlsx_preview
            except Exception:
                pass

            editorial = EditorialRecommendationService(database=db)
            recs = editorial.generate_recommendations(limit=1, candidate_limit=1)
            assert isinstance(recs, list)

        finally:
            os.chdir(original)

    print("benchmark_communications_smoke passed")


if __name__ == "__main__":
    main()
