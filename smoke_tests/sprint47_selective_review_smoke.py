from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager
from services.automated_editorial_trust_service import AutomatedEditorialTrustService
from services.daily_communications_officer_service import DailyCommunicationsOfficerService
from services.editorial_story_classifier import EditorialStoryClassifier
from services.event_collection_service import EventCollectionService
from services.media_package_service import MediaPackageService
from services.media_review_policy_service import MediaReviewPolicyService
from services.package_review_service import PackageReviewService
from smoke_tests.sprint46_fast_officer_smoke import add_media, create_image


def save_media_intelligence(db, media_id, title, review_status="review_required", trust_state="unreviewed_real"):

    db.save_ai_analysis(media_id, {
        "description": f"{title} rope rescue training teamwork.",
        "scene_type": "training",
        "activity": "low angle rope rescue training",
        "people_count": 3,
        "apparatus": ["rescue"],
        "equipment": ["rope", "helmet"],
        "keywords": ["training", "rope rescue", "teamwork"],
        "community_score": 70,
        "recruitment_score": 74,
        "education_score": 76,
        "technical_score": 82,
        "overall_score": 80,
        "facebook_caption": "",
        "instagram_caption": "",
        "model": "stored-real",
        "provider": "ollama",
        "review_status": review_status,
        "trust_state": trust_state,
        "failure_reason": ""
    })
    db.save_media_intelligence(media_id, {
        "normalized_scene": "training",
        "incident_type": "training",
        "primary_activity": "low angle rope rescue training",
        "apparatus_tags": ["rescue"],
        "equipment_tags": ["rope", "helmet"],
        "ppe_tags": ["helmet"],
        "people_tags": ["firefighters"],
        "content_tags": ["training", "teamwork", "technical rescue"],
        "content_themes": ["training readiness", "this is what we do"],
        "recommended_uses": ["training", "recruitment"],
        "search_text": title,
        "intelligence_score": 82,
        "communications_score": 86,
        "source_model": "stored-real"
    })


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:
        os.chdir(folder)

        try:
            db = DatabaseManager()
            media_dir = Path(folder) / "2026" / "Training" / "Low Angle Rope Rescue"
            media_dir.mkdir(parents=True)
            ids = []

            for index in range(1, 7):
                path = media_dir / f"rope_training_{index:03d}.jpg"
                create_image(path, ("red", "green", "blue", "yellow", "purple", "orange")[index - 1])
                media_id = add_media(db, path, index, "image")
                ids.append(media_id)

            save_media_intelligence(db, ids[0], "confirmed low angle rope rescue", "approved", "approved_real")
            save_media_intelligence(db, ids[1], "confirmed low angle rope rescue", "corrected", "corrected_real")
            for media_id in ids[2:5]:
                save_media_intelligence(db, media_id, "related low angle rope rescue")
            save_media_intelligence(db, ids[5], "rejected unrelated scenic background", "rejected", "rejected_real")

            trust = AutomatedEditorialTrustService(database=db)
            policy = MediaReviewPolicyService(database=db, trust_service=trust)
            event_service = EventCollectionService(database=db, trust_service=trust)
            classifier = EditorialStoryClassifier()

            rows = db.media_package_asset_rows(ids, limit=10)
            unreviewed = next(row for row in rows if row["media_id"] == ids[2])
            trust_result = trust.score_media(unreviewed, event={"confidence": 80, "photo_count": 5}, anchors=rows[:2])
            assert trust_result["score"] >= 55, trust_result
            policy_result = policy.policy_for_media(unreviewed)
            assert policy_result["may_search"], policy_result
            assert policy_result["may_rank"], policy_result
            assert policy_result["may_show_candidate"], policy_result
            assert policy_result["may_publish_without_confirmation"] is False, policy_result

            rejected = next(row for row in rows if row["media_id"] == ids[5])
            assert policy.policy_for_media(rejected)["may_search"] is False

            collections = event_service.build_collections(limit=500)
            assert collections, collections
            event = collections[0]
            assert event["photo_count"] >= 5, event
            assert event["confidence"] >= 65, event
            assert event["representative_media"], event
            summary = event_service.event_summary(event)
            assert summary["best_photo"], summary

            ranked = event_service.rank_event_photos(event, limit=5)
            assert ranked, event
            assert ids[5] not in [item.get("media_id") for item in ranked]
            contact = event_service.contact_sheet_classification(event)
            assert contact["temporary_contact_sheet_stored"] is False, contact
            assert contact["full_library_deep_analysis_required"] is False, contact
            assert contact["strongest_frame_ids"], contact

            anchor = event_service.apply_event_anchor(
                event,
                ids[0],
                {"primary_activity": "low angle rope rescue training"}
            )
            assert anchor["raw_analysis_overwritten"] is False, anchor
            assert ids[2] in anchor["propagated_to_media_ids"], anchor

            story = classifier.classify({
                "title": "Behind the scenes rope rescue team training",
                "content_tags": ["training", "teamwork", "behind the scenes"]
            })
            assert story["primary_family"] in ("training_readiness", "technical_rescue")
            light = classifier.light_hearted_suitability({
                "title": "station team preparation candid harmless moment"
            })
            assert light["suitable"] is True, light
            unsafe = classifier.light_hearted_suitability({
                "title": "medical patient treatment serious incident"
            })
            assert unsafe["suitable"] is False, unsafe

            media_package_service = MediaPackageService(database=db)
            package = media_package_service.build_package({
                "title": "Low Angle Rope Rescue Training",
                "topic": "rope rescue training teamwork",
                "best_asset_ids": ids[2:5],
                "supporting_asset_ids": ids[:2],
                "recommended_platforms": ["Facebook", "Instagram"]
            }, persist=False)
            selected_ids = [
                (package.get("primary_photo") or {}).get("media_id"),
                *[item.get("media_id") for item in package.get("gallery_photos", [])]
            ]
            assert any(media_id in selected_ids for media_id in ids[2:5]), package
            assert ids[5] not in selected_ids, package
            assert package.get("limitations") or package.get("review_requirements"), package

            daily = DailyCommunicationsOfficerService(database=db)
            brief = daily.generate(force=True)
            packages = brief.get("daily_post_packages", [])
            assert len(packages) == 3, packages
            assert any(pkg.get("event_collection") for pkg in packages), packages
            families = {pkg.get("content_family") for pkg in packages}
            assert len(families) >= 3, families
            for pkg in packages:
                assert pkg.get("quality_gate", {}).get("passed"), pkg
                assert pkg.get("package_review", {}).get("required"), pkg
                assert "#MordenFireRescue" not in pkg.get("instagram_caption", ""), pkg
                assert "Review media before publishing" not in pkg.get("facebook_caption", ""), pkg

            review = PackageReviewService(database=db)
            decision = review.record_decision(
                packages[0],
                "approve_package",
                notes="Smoke acceptance"
            )
            assert decision["package_review_recorded"] is True, decision
            profile = review.profile()
            assert profile["evidence_count"] >= 1, profile
            assert "#MordenFireRescue" in profile["hashtag_exclusions"], profile

        finally:
            os.chdir(original)

    print("sprint47_selective_review_smoke passed")


if __name__ == "__main__":
    main()
