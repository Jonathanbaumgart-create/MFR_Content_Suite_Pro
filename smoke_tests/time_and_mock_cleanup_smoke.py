from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.media_intelligence_service import MediaIntelligenceService
from services.time_service import TimeService


def add_media(db, index, filename):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"time-cleanup-hash-{index}"
        }
    )


def analysis(provider, model, description):

    return {
        "description": description,
        "scene_type": "training tower",
        "activity": "ladder training",
        "people_count": 1,
        "apparatus": ["Engine"],
        "equipment": ["Ground ladder"],
        "keywords": ["training", "firefighter"],
        "community_score": 55,
        "recruitment_score": 70,
        "education_score": 70,
        "technical_score": 80,
        "overall_score": 78,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": model,
        "provider": provider,
        "retry_count": 0,
        "failure_reason": ""
    }


def main():

    winter = TimeService.format_local("2026-01-15T18:00:00+00:00")
    summer = TimeService.format_local("2026-07-15T18:00:00+00:00")
    legacy = TimeService.format_local("2026-07-15 18:00:00")
    aware = TimeService.normalize_stored_timestamp(
        datetime(2026, 7, 15, 18, 0, tzinfo=timezone.utc)
    )

    assert "12:00 PM CST" in winter, winter
    assert "01:00 PM CDT" in summer, summer
    assert "01:00 PM CDT" in legacy, legacy
    assert aware.isoformat().startswith("2026-07-15T18:00:00"), aware

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            media_service = MediaIntelligenceService(db)

            add_media(db, 1, "legacy_mock.jpg")
            add_media(db, 2, "real_ollama.jpg")

            mock = analysis(
                "mock",
                "mock",
                "MOCK TEST ANALYSIS - test data only."
            )
            real = analysis(
                "ollama",
                "moondream:latest",
                "Real provider analysis of ladder training."
            )

            db.save_ai_analysis(1, mock)
            db.save_ai_analysis(2, real)
            media_service.generate_and_save(
                1,
                db.get_ai_analysis(1)
            )
            media_service.generate_and_save(
                2,
                db.get_ai_analysis(2)
            )

            db.save_media_correction(
                {
                    "media_id": 1,
                    "field_name": "people_count",
                    "original_value": 0,
                    "corrected_value": 1,
                    "correction_source": "Jonathan",
                    "confidence_before": 50,
                    "confidence_after": 100,
                    "notes": "Audit history should remain."
                }
            )

            db.save_editorial_strategy(
                1,
                {
                    "strategy_id": "1:test",
                    "strategy_type": "training_highlight",
                    "title": "Training Highlight",
                    "objective": "Test cleanup",
                    "target_audience": "Community",
                    "core_message": "Mock row cleanup.",
                    "reasoning": ["mock-derived"],
                    "confidence": 50,
                    "communications_score": 50,
                    "recommended_platforms": ["Facebook"],
                    "recommended_posting_window": "Any",
                    "recommended_media": [{"media_id": 1}],
                    "caption_direction": "Test",
                    "call_to_action": "Test",
                    "risks": [],
                    "limitations": [],
                    "supporting_evidence": []
                }
            )

            summary = db.legacy_mock_analysis_summary()
            assert summary["media_count"] == 1, summary
            assert summary["media_intelligence_rows"] == 1, summary
            assert summary["fire_service_rows"] == 1, summary
            assert summary["editorial_strategy_rows"] == 1, summary

            result = db.clear_mock_analysis()
            assert result["analysis_deleted"] == 1, result
            assert result["intelligence_deleted"] == 1, result
            assert result["fire_service_deleted"] == 1, result
            assert result["editorial_strategies_deleted"] == 1, result
            assert db.get_ai_analysis(1) is None
            assert db.get_media_intelligence(1) is None
            assert db.get_fire_service_intelligence(1) is None
            assert db.get_ai_analysis(2)["provider"] == "ollama"
            assert db.get_media_intelligence(2)
            assert db.media_needing_analysis_count() == 1
            assert db.correction_history_for_media(1)

            from gui.photo_viewer import PhotoViewer

            viewer = object.__new__(PhotoViewer)
            assert (
                PhotoViewer.analysis_provider_label(viewer, mock) ==
                "Analysis provider: mock - test data"
            )
            assert (
                PhotoViewer.analysis_provider_label(viewer, real) ==
                "Analysis provider: ollama"
            )
            assert "CDT" in PhotoViewer.local_time(
                viewer,
                "2026-07-15T18:00:00+00:00"
            )

        finally:
            os.chdir(original)

    print("time_and_mock_cleanup smoke passed")


if __name__ == "__main__":
    main()
