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
from services.communications_learning_service import CommunicationsLearningService
from services.communications_memory_service import CommunicationsMemoryService
from services.communications_officer_service import CommunicationsOfficerService
from services.content_generation_service import ContentGenerationService
from services.editorial_recommendation_service import EditorialRecommendationService


def write_learning_csv(path):

    rows = [
        {
            "platform": "facebook",
            "post_id": "mfr-1",
            "date": "2026-06-01",
            "time": "09:00",
            "campaign": "Training Tuesday",
            "topic": "training",
            "reach": "1200",
            "impressions": "1500",
            "reactions": "90",
            "comments": "12",
            "shares": "18",
            "caption": "Training keeps our crews ready. Learn how ladder practice supports safe fireground operations.",
            "media_type": "carousel",
            "hashtags": "#TrainingTuesday #MordenFireRescue",
            "cta": "learn more"
        },
        {
            "platform": "facebook",
            "post_id": "mfr-2",
            "date": "2026-06-08",
            "time": "09:15",
            "campaign": "Training Tuesday",
            "topic": "training",
            "reach": "1400",
            "impressions": "1700",
            "reactions": "110",
            "comments": "14",
            "shares": "22",
            "caption": "Training night focused on hose movement. Crews practiced communication, control, and teamwork.",
            "media_type": "reel",
            "views": "2100",
            "average_watch_duration": "12",
            "hashtags": "#TrainingTuesday #MordenFireRescue",
            "cta": "follow for more"
        },
        {
            "platform": "instagram",
            "post_id": "mfr-3",
            "date": "2026-06-15",
            "time": "18:30",
            "campaign": "Training Tuesday",
            "topic": "training",
            "reach": "900",
            "views": "2400",
            "reactions": "180",
            "comments": "16",
            "shares": "35",
            "saves": "25",
            "caption": "A quick look at training night. Teamwork before the call matters.",
            "media_type": "reel",
            "average_watch_duration": "14",
            "hashtags": "#TrainingTuesday #MordenFireRescue",
            "cta": "share"
        },
        {
            "platform": "facebook",
            "post_id": "mfr-4",
            "date": "2026-06-20",
            "time": "12:00",
            "campaign": "Smoke Alarm Safety",
            "topic": "public_education",
            "reach": "600",
            "impressions": "700",
            "reactions": "18",
            "comments": "2",
            "shares": "4",
            "caption": "Test your smoke alarms this weekend and practice your home escape plan.",
            "media_type": "photo",
            "hashtags": "#FireSafety #Morden",
            "cta": "check"
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


def main():

    original = os.getcwd()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            learning = CommunicationsLearningService(database=db)
            csv_path = Path(folder) / "learning.csv"
            write_learning_csv(csv_path)

            memory_before = len(CommunicationsMemoryService(database=db).search("", limit=1000))
            mfr_profile_before = CommunicationsIntelligenceService(database=db).profile(force=True)
            benchmark_before = BenchmarkCommunicationsService(database=db).insights()

            preview = learning.preview_file(csv_path)
            assert preview["detected_format"] == "csv", preview
            assert preview["metrics_available"]["reach"] == 4, preview
            assert "facebook" in preview["detected_platforms"], preview

            summary = learning.import_file(csv_path)
            assert summary["records_inserted"] == 4, summary

            duplicate = learning.import_file(csv_path)
            assert duplicate["duplicates_skipped"] == 4, duplicate

            manual = learning.manual_entry(
                {
                    "platform": "facebook",
                    "post_id": "manual-1",
                    "publication_date": "2026-07-01",
                    "publication_time": "10:00",
                    "topic": "recruitment",
                    "campaign": "Recruitment",
                    "reach": 800,
                    "reactions": 44,
                    "comments": 9,
                    "shares": 12,
                    "caption": "Interested in serving Morden? Learn more about paid-on-call firefighting.",
                    "media_type": "photo",
                    "cta": "apply"
                }
            )
            assert manual["inserted"], manual

            records = learning.records(limit=20)
            assert len(records) == 5, records
            assert records[0]["derived_metrics"].get("engagement_score") is not None

            first = records[0]
            db.review_communication_learning_record(
                first["learning_id"],
                {
                    "review_status": "approved",
                    "anomaly": False,
                    "exclude_from_learning": False,
                    "boosted_post": False,
                    "seasonal": True,
                    "reviewer_notes": "Looks representative.",
                    "updated_at": "2026-07-16T00:00:00+00:00"
                }
            )
            experiment_id = db.save_communication_experiment(
                {
                    "hypothesis": "Training Reels outperform static training photos.",
                    "expected_outcome": "Higher saves and shares.",
                    "actual_outcome": "",
                    "lesson_learned": "",
                    "target_platform": "Instagram",
                    "target_campaign": "Training Tuesday",
                    "topic": "training",
                    "experiment_type": "photo_vs_reel",
                    "test_date": "2026-07-20",
                    "status": "planned",
                    "created_at": "2026-07-16T00:00:00+00:00",
                    "updated_at": "2026-07-16T00:00:00+00:00"
                }
            )
            assert experiment_id > 0

            dashboard = learning.dashboard()
            assert dashboard["sample_count"] == 5, dashboard
            assert dashboard["learning_confidence"] > 0, dashboard
            assert "training" in dashboard["topics"], dashboard
            assert dashboard["topics"]["training"]["sample_size"] >= 3, dashboard
            assert dashboard["fatigue"]["topic_fatigue"], dashboard
            assert dashboard["reel_performance"]["sample_size"] >= 2, dashboard

            recommendation = {
                "recommendation_id": "learn-training",
                "title": "Firefighter Training",
                "topic": "training",
                "category": "Training",
                "summary": "Training post",
                "recommended_platforms": ["Facebook", "Instagram"],
                "best_asset_ids": [],
                "supporting_asset_ids": []
            }
            evidence = learning.recommendation_evidence(recommendation)
            assert evidence["sample_size"] >= 3, evidence
            assert evidence["source"] == "mfr_historical_performance", evidence
            assert evidence["separate_from_benchmark"], evidence

            package = CommunicationPackageService(database=db).generate_package(
                recommendation,
                package_type="Facebook"
            )
            assert package["performance_prediction"], package
            generated = ContentGenerationService(database=db).generate_from_package(
                package,
                platforms=["facebook", "instagram"]
            )
            public_copy = json.dumps(generated["copy_buttons"])
            assert "performance_prediction" not in public_copy
            assert "engagement_score" not in public_copy
            assert "benchmark" not in public_copy.lower()

            recs = EditorialRecommendationService(database=db).generate_recommendations(
                limit=1,
                candidate_limit=1
            )
            assert isinstance(recs, list)
            if recs:
                assert "historical_mfr_evidence" in recs[0], recs[0]

            brief = CommunicationsOfficerService(database=db).generate(force=True)
            assert brief["communications_learning"]["available"], brief["communications_learning"]
            assert brief["communications_learning"]["sample_count"] == 5

            benchmark_after = BenchmarkCommunicationsService(database=db).insights()
            memory_after = len(CommunicationsMemoryService(database=db).search("", limit=1000))
            mfr_profile_after = CommunicationsIntelligenceService(database=db).profile(force=True)
            assert benchmark_before["records"] == benchmark_after["records"] == 0
            assert memory_before == memory_after == 0
            assert mfr_profile_before["sample_count"] == mfr_profile_after["sample_count"] == 0

        finally:
            os.chdir(original)

    print("communications_learning_smoke passed")


if __name__ == "__main__":
    main()
