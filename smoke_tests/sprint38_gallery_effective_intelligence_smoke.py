import os
import sys
import tempfile
from pathlib import Path


def assert_equal(actual, expected, label):

    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(condition, label):

    if not condition:
        raise AssertionError(label)


def insert_media(db, media_id, filename, media_type="image", first_seen="2026-07-01T12:00:00+00:00"):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO media(
            id,
            filename,
            path,
            extension,
            media_type,
            filesize,
            sha256,
            first_seen_at,
            capture_time
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            filename,
            f"C:/fixture/{filename}",
            Path(filename).suffix,
            media_type,
            1000 + media_id,
            f"sha38-{media_id}",
            first_seen,
            f"2026-06-{media_id:02d}T10:00:00+00:00"
        )
    )
    conn.commit()
    conn.close()


def insert_analysis(
    db,
    media_id,
    provider="ollama",
    model="qwen2.5vl:7b",
    description="Raw provider description",
    failure_reason="",
    trust_state="unreviewed_real",
    review_status="review_required",
    last_analyzed="2026-07-01T12:00:00+00:00"
):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ai_analysis(
            media_id,
            description,
            scene_type,
            activity,
            people_count,
            overall_score,
            analyzed_at,
            last_analyzed,
            model,
            provider,
            failure_reason,
            trust_state,
            review_status
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            description,
            "training",
            "ladder operations",
            2,
            80,
            last_analyzed,
            last_analyzed,
            model,
            provider,
            failure_reason,
            trust_state,
            review_status
        )
    )
    conn.commit()
    conn.close()


def insert_intelligence(db, media_id, score=80):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO media_intelligence(
            media_id,
            normalized_scene,
            incident_type,
            primary_activity,
            content_tags,
            content_themes,
            recommended_uses,
            intelligence_score,
            communications_score,
            storytelling_score,
            community_engagement_score,
            educational_value_score,
            recruitment_value_score,
            trust_building_score,
            search_text,
            generated_at,
            source_model
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            "training ground",
            "Training",
            "Ladder operations",
            '["training","ladder"]',
            '["training"]',
            '["Training Tuesday","Recruitment"]',
            score,
            score,
            score,
            score,
            score,
            score,
            score,
            "training ladder",
            "2026-07-01T12:00:00+00:00",
            "qwen2.5vl:7b"
        )
    )
    conn.commit()
    conn.close()


def insert_video_intelligence(db, media_id):

    conn = db.connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO video_intelligence(
            media_id,
            duration_seconds,
            provider,
            model,
            generated_at
        )
        VALUES(?,?,?,?,?)
        """,
        (
            media_id,
            22.0,
            "metadata",
            "local",
            "2026-07-01T12:00:00+00:00"
        )
    )
    conn.commit()
    conn.close()


def main():

    repo_root = Path(__file__).resolve().parents[1]

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.chdir(tmp)

        from database.db_manager import DatabaseManager
        from services.cache_invalidation_service import CacheInvalidationService
        from services.communication_package_service import CommunicationPackageService
        from services.decision_explainability_service import DecisionExplainabilityService
        from services.human_feedback_service import HumanFeedbackService
        from services.recommendation_candidate_service import RecommendationCandidateService

        db = DatabaseManager()

        for media_id, name, media_type in (
            (1, "not-analyzed-a.jpg", "image"),
            (2, "review-required.jpg", "image"),
            (3, "approved.jpg", "image"),
            (4, "corrected.jpg", "image"),
            (5, "rejected.jpg", "image"),
            (6, "failed.jpg", "image"),
            (7, "mock.jpg", "image"),
            (8, "video-new.mp4", "video"),
            (9, "video-metadata.mp4", "video"),
            (10, "analyzed-old.jpg", "image")
        ):
            insert_media(db, media_id, name, media_type=media_type)

        for media_id in (2, 3, 4, 5, 10):
            insert_intelligence(db, media_id, score=70 + media_id)

        insert_analysis(db, 2, trust_state="unreviewed_real", review_status="review_required", last_analyzed="2026-07-03T12:00:00+00:00")
        insert_analysis(db, 3, trust_state="approved_real", review_status="approved", last_analyzed="2026-07-04T12:00:00+00:00")
        insert_analysis(db, 4, description="Raw provider ladder training text.", trust_state="corrected_real", review_status="corrected", last_analyzed="2026-07-05T12:00:00+00:00")
        insert_analysis(db, 5, trust_state="rejected_real", review_status="rejected", last_analyzed="2026-07-06T12:00:00+00:00")
        insert_analysis(db, 6, failure_reason="provider timeout", trust_state="failed", review_status="failed", last_analyzed="2026-07-07T12:00:00+00:00")
        insert_analysis(db, 7, provider="mock", model="mock-v1", description="MOCK TEST ANALYSIS", trust_state="mock", review_status="mock", last_analyzed="2026-07-08T12:00:00+00:00")
        insert_analysis(db, 10, trust_state="approved_real", review_status="approved", last_analyzed="2026-07-02T12:00:00+00:00")
        insert_video_intelligence(db, 9)

        feedback = HumanFeedbackService(database=db)
        raw_before = db.get_ai_analysis(4)["description"]
        feedback.save_correction(
            4,
            "description",
            "Corrected description: firefighters training on ground ladders for public education and recruitment.",
            correction_source="Jonathan",
            notes="Sprint 38 fixture"
        )
        raw_after = db.get_ai_analysis(4)["description"]
        assert_equal(raw_after, raw_before, "raw AI description immutable")

        effective = feedback.effective_media_intelligence(4)
        assert_true(
            effective["description"].startswith("Corrected description"),
            "effective corrected description"
        )
        assert_equal(effective["trust_state"], "corrected_real", "corrected trust state")

        expected_counts = {
            "not_analyzed": 5,
            "analyzed": 5,
            "real_analysis": 5,
            "review_required": 1,
            "approved": 2,
            "corrected": 1,
            "rejected": 1,
            "failed": 1,
            "mock_test_data": 1,
            "photos_not_analyzed": 3,
            "videos_not_analyzed": 1
        }

        for key, expected in expected_counts.items():
            assert_equal(db.media_count(key), expected, f"{key} count")

        newest = db.get_media_ids_for_selection("analyzed", limit=10)
        assert_equal(newest, [10, 3, 4, 5, 2], "default analyzed deterministic ids")

        page = db.get_media_page(10, 0, filter_key="analyzed", sort_key="analysis_newest")
        assert_equal([row[0] for row in page], [5, 4, 3, 2, 10], "analysis newest sort")
        page = db.get_media_page(10, 0, filter_key="analyzed", sort_key="analysis_oldest")
        assert_equal([row[0] for row in page], [10, 2, 3, 4, 5], "analysis oldest sort")
        page = db.get_media_page(10, 0, filter_key="all", sort_key="not_analyzed_first")
        assert_true(page[0][0] in {1, 6, 7, 8, 9}, "not analyzed first")
        page = db.get_media_page(10, 0, filter_key="all", sort_key="review_required_first")
        assert_equal(page[0][0], 2, "review required first")
        page = db.get_media_page(10, 0, filter_key="all", sort_key="corrected_first")
        assert_equal(page[0][0], 4, "corrected first")
        page = db.get_media_page(10, 0, filter_key="all", sort_key="failed_first")
        assert_equal(page[0][0], 6, "failed first")
        page = db.get_media_page(10, 0, filter_key="all", sort_key="filename_az")
        assert_equal(page[0][1], "analyzed-old.jpg", "filename az")
        page = db.get_media_page(10, 0, filter_key="all", sort_key="filename_za")
        assert_equal(page[0][1], "video-new.mp4", "filename za")

        ids = db.get_media_ids_for_selection("not_analyzed", limit=3)
        assert_equal(len(ids), 3, "bounded select all current filter")

        preview = db.analysis_selection_preview([1, 2, 3, 4, 6, 7, 8], force=False, retry_failed=False)
        assert_equal(preview["selected_count"], 7, "preview selected count")
        assert_equal(preview["completed_real_analysis_count"], 3, "preview completed real count")
        assert_equal(preview["mock_only_count"], 1, "preview mock count")
        assert_equal(preview["failed_count"], 1, "preview failed count")
        assert_equal(set(preview["queueable_ids"]), {1, 7, 8}, "preview default queueable")

        retry_preview = db.analysis_selection_preview([6], retry_failed=True)
        assert_equal(retry_preview["queueable_ids"], [6], "retry failed queueable")

        force_preview = db.analysis_selection_preview([2], force=True)
        assert_equal(force_preview["queueable_ids"], [2], "force reanalysis queueable")

        candidates = RecommendationCandidateService(database=db).build_candidates(limit=20)
        flattened = [
            asset
            for candidate in candidates
            for asset in candidate.get("assets", [])
        ]
        corrected_asset = next(
            asset for asset in flattened
            if asset.get("media_id") == 4
        )
        assert_true(
            corrected_asset.get("description", "").startswith("Corrected description"),
            "candidate corrected description"
        )

        recommendation = {
            "recommendation_id": "sprint38-rec",
            "title": "Training Tuesday Ladder Operations",
            "summary": corrected_asset.get("description", ""),
            "priority_score": 88,
            "confidence_score": 82,
            "supporting_asset_ids": [4],
            "best_asset_ids": [4],
            "recommended_platforms": ["Facebook"],
            "reasoning_factors": [
                {
                    "label": "Corrected evidence",
                    "score": 20,
                    "direction": "positive",
                    "reason": corrected_asset.get("description", "")
                }
            ]
        }
        package = CommunicationPackageService(database=db).generate_package(
            recommendation
        )
        assert_true(
            "Corrected description" in "\n".join(package.get("supporting_evidence", [])),
            "package corrected description"
        )
        explanation = DecisionExplainabilityService(database=db).explain_recommendation(
            recommendation,
            persist=False
        )
        assert_true(
            "Corrected description" in str(explanation.get("supporting_assets", [])),
            "decision explainability corrected description"
        )

        event = CacheInvalidationService.latest(media_id=4)
        assert_equal(event.get("media_id"), 4, "cache invalidation media id")
        assert_true(
            "effective_intelligence" in event.get("scopes", []),
            "cache invalidation scope"
        )

        photo_viewer_source = (repo_root / "gui" / "photo_viewer.py").read_text()
        assert_true('wrap="word"' in photo_viewer_source, "word-boundary wrap")
        assert_true("Raw AI Analysis" in photo_viewer_source, "raw AI separate display")
        assert_true("AI Assistant Understanding" in photo_viewer_source, "assistant effective display")

        os.chdir(repo_root)

    print("sprint38_gallery_effective_intelligence_smoke passed")


if __name__ == "__main__":
    main()
