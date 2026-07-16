import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.filesystem_intelligence_service import FilesystemIntelligenceService
from services.gallery_service import GalleryService
from services.recommendation_scoring_service import RecommendationScoringService
from services.media_package_service import MediaPackageService
from services.scan_service import ScanService
from core.app_context import context


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def add_media(db, path, media_type="image", sha="sha"):
    return db.add_media(
        {
            "filename": Path(path).name,
            "path": str(path),
            "extension": Path(path).suffix.lower(),
            "type": media_type,
            "size": 12,
            "sha256": sha
        }
    )


def main():
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        os.chdir(tmp_path)
        db = DatabaseManager()
        context.database = db
        service = FilesystemIntelligenceService(database=db)

        root = tmp_path / "Pictures"
        paths = {
            "apparatus": root / "Apparatus" / "142" / "2026" / "pumper.jpg",
            "training": root / "Training" / "High-Angle_Rope Rescue" / "2026" / "drill.jpg",
            "live_burn": root / "Drills" / "Live Burn" / "Recruit-Class" / "burn.jpg",
            "incident": root / "Incidents" / "MVC" / "2026-06" / "scene.jpg",
            "program": root / "Public Education" / "Hydrant Heroes" / "school.jpg",
            "campaign": root / "Campaigns" / "Fire Prevention Week" / "demo.jpg",
            "community": root / "Community Events" / "Parade" / "event.jpg",
            "unknown": root / "Misc" / "Unsorted" / "plain.jpg",
            "video": root / "Training" / "SCBA" / "clip.mp4"
        }

        for index, path in enumerate(paths.values(), start=1):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"placeholder")
            add_media(
                db,
                path,
                media_type="video" if path.suffix == ".mp4" else "image",
                sha=f"sha-{index}"
            )

        rows = db.get_media_needing_filesystem_intelligence(
            service.rules_version,
            limit=20
        )
        assert_true(len(rows) == len(paths), "all rows need first derivation")

        result = service.backfill(limit=20)
        assert_true(result["updated"] == len(paths), "backfill persisted rows")
        assert_true(result["failed"] == 0, "backfill had no failures")

        apparatus_row = db.get_media_by_path(str(paths["apparatus"]))
        apparatus = db.get_filesystem_intelligence(apparatus_row[0])
        assert_true(apparatus["root_category"] == "Apparatus", "apparatus category")
        assert_true(apparatus["apparatus_identifier"] == "142", "numeric apparatus folder")
        assert_true(apparatus["apparatus_name"], "apparatus alias/name retained")

        training_row = db.get_media_by_path(str(paths["training"]))
        training = db.get_filesystem_intelligence(training_row[0])
        assert_true(training["training_type"] == "high_angle", "high angle training detection")
        assert_true("rope_rescue" in training["normalized_tags"], "punctuation normalization")

        live_row = db.get_media_by_path(str(paths["live_burn"]))
        live = db.get_filesystem_intelligence(live_row[0])
        assert_true(live["live_burn_context"], "live burn detection")
        assert_true(live["recruit_class"], "recruit class detection")

        incident_row = db.get_media_by_path(str(paths["incident"]))
        incident = db.get_filesystem_intelligence(incident_row[0])
        assert_true(incident["root_category"] == "Incidents", "incident category detection")
        assert_true(incident["incident_type"] == "mvc", "incident type detection")

        program_row = db.get_media_by_path(str(paths["program"]))
        program = db.get_filesystem_intelligence(program_row[0])
        assert_true(program["public_education_program"] == "hydrant_heroes", "program detection")

        campaign_row = db.get_media_by_path(str(paths["campaign"]))
        campaign = db.get_filesystem_intelligence(campaign_row[0])
        assert_true(campaign["campaign"] == "fire_prevention_week", "campaign detection")

        community_row = db.get_media_by_path(str(paths["community"]))
        community = db.get_filesystem_intelligence(community_row[0])
        assert_true(community["community_event"] in ("fireworks", "community_event", "parade"), "community event detection")

        unknown_row = db.get_media_by_path(str(paths["unknown"]))
        unknown = db.get_filesystem_intelligence(unknown_row[0])
        assert_true(unknown["root_category"] == "unknown", "unknown folder stays unknown")

        video_row = db.get_media_by_path(str(paths["video"]))
        video = db.get_filesystem_intelligence(video_row[0])
        assert_true(video["training_type"] == "scba", "video inherits folder context")

        assert_true(
            db.media_count(filter_key="filesystem_training") >= 3,
            "gallery training filter works"
        )
        assert_true(
            db.media_count(filter_key="filesystem_apparatus") == 1,
            "gallery apparatus filter works"
        )
        assert_true(
            db.media_count(filter_key="filesystem_incidents") == 1,
            "gallery incident filter works"
        )
        assert_true(
            db.media_count(filter_key="has_filesystem_intelligence") == len(paths),
            "has filesystem filter works"
        )

        folder_map = service.folder_knowledge_map(limit=20)
        assert_true(folder_map, "folder knowledge map returns aggregates")

        prompt = service.prompt_context(video_row[0])
        assert_true("Folder context suggests" in prompt, "prompt enrichment exists")
        assert_true(str(root) not in prompt, "no full path leakage in prompt")

        candidate = {
            "profile": {"topic": "scba", "terms": ("scba", "training")},
            "assets": [
                {
                    "media_id": video_row[0],
                    "media_type": "video",
                    "intelligence_score": 80,
                    "communications_score": 80,
                    "filesystem_intelligence": video,
                    "topics": [{"topic": "scba"}],
                    "trust_state": "approved_real"
                }
            ],
            "snapshot": object(),
            "memory_profile": {"memory_available": False, "matching_posts": 0},
            "recent_social": set(),
            "recent_recommended": set(),
            "supporting_topics": ["SCBA Training"],
            "is_topic_candidate": True
        }
        scored = RecommendationScoringService().score_candidate(candidate)
        assert_true(
            any(f["factor"] == "filesystem_agreement" for f in scored["reasoning_factors"]),
            "recommendation scoring includes filesystem agreement"
        )

        package_service = MediaPackageService(database=db)
        terms = package_service._asset_terms(
            {
                "filesystem_intelligence": video,
                "content_tags": []
            }
        )
        assert_true("scba" in terms, "media package sees filesystem terms")

        cancel = threading.Event()
        cancel.set()
        canceled = service.backfill(limit=10, cancel_event=cancel)
        assert_true(canceled["canceled"], "backfill cancellation supported")

        scan_root = tmp_path / "ScanRoot"
        scan_file = scan_root / "Training" / "SCBA" / "scan.jpg"
        scan_file.parent.mkdir(parents=True, exist_ok=True)
        scan_file.write_bytes(b"scan placeholder")
        try:
            scan = ScanService(database=db).scan(str(scan_root))
            assert_true(scan["inserted"] == 1, "scanner inserted generated file")
            scanned_row = db.get_media_by_path(str(scan_file))
            assert_true(
                db.get_filesystem_intelligence(scanned_row[0])["training_type"] == "scba",
                "scanner integration derives filesystem intelligence"
            )
        finally:
            os.chdir(original_cwd)

    print("filesystem_intelligence smoke passed")


if __name__ == "__main__":
    main()
