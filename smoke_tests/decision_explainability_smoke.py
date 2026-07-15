import json
import os
import sys
import tempfile
import types
from pathlib import Path


def insert_media(db, media_id, filename, trust_state, review_status, provider, scores):

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
            first_seen_at
        )
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            filename,
            str(Path("library") / filename),
            Path(filename).suffix,
            "video" if filename.lower().endswith(".mp4") else "image",
            1024,
            f"sha-{media_id}",
            "2026-07-13T12:00:00+00:00"
        )
    )
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
            model,
            provider,
            trust_state,
            review_status,
            failure_reason
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            "Firefighters training with ground ladders.",
            "training",
            "ladder operations",
            3,
            80,
            "2026-07-13T12:00:00+00:00",
            "qwen2.5vl:7b",
            provider,
            trust_state,
            review_status,
            ""
        )
    )
    cur.execute(
        """
        INSERT INTO media_intelligence(
            media_id,
            normalized_scene,
            incident_type,
            primary_activity,
            content_tags,
            recommended_uses,
            intelligence_score,
            communications_score,
            storytelling_score,
            community_engagement_score,
            educational_value_score,
            recruitment_value_score,
            trust_building_score,
            suggested_campaigns,
            suggested_audience,
            suggested_platform,
            generated_at,
            source_model
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            "training ground",
            "Training",
            "Ladder operations",
            json.dumps(["ladder operations", "training", "teamwork"]),
            json.dumps(["Training Tuesday", "Recruitment"]),
            scores.get("intelligence", 80),
            scores.get("communications", 82),
            scores.get("storytelling", 75),
            scores.get("community", 70),
            scores.get("education", 76),
            scores.get("recruitment", 78),
            scores.get("trust", 72),
            json.dumps(["Training Tuesday"]),
            json.dumps(["community", "future volunteers"]),
            json.dumps(["Facebook", "Instagram"]),
            "2026-07-13T12:00:00+00:00",
            "qwen2.5vl:7b"
        )
    )
    conn.commit()
    conn.close()


def recommendation_fixture():

    return {
        "recommendation_id": "training-tuesday-1",
        "title": "Training Tuesday: Ladder Operations",
        "headline": "Training Tuesday: Ladder Operations",
        "topic": "training",
        "category": "Training Highlight",
        "summary": "Reviewed training media supports a ladder operations story.",
        "primary_reason": "Strong reviewed media and a clear training story.",
        "priority_score": 88,
        "confidence_score": 82,
        "reasoning_factors": [
            {
                "label": "Reviewed media",
                "score": 22,
                "direction": "positive",
                "reason": "Approved and corrected real media support this story."
            },
            {
                "label": "Training gap",
                "score": 15,
                "direction": "positive",
                "reason": "Communications Memory shows limited recent training content."
            },
            {
                "label": "Unreviewed support",
                "score": -4,
                "direction": "negative",
                "reason": "One possible supporting item still needs review."
            }
        ],
        "supporting_topics": ["training", "ladder operations"],
        "supporting_programs": ["Training Tuesday"],
        "supporting_campaigns": ["Recruitment"],
        "story_strength": {"score": 86, "reason": "Clear operational activity."},
        "confidence_limitations": ["One supporting asset is unreviewed."],
        "editorial_angle": "Training Highlight",
        "supporting_photo_count": 2,
        "supporting_video_count": 1,
        "supporting_asset_ids": [1, 2, 3],
        "best_asset_ids": [1, 2],
        "editorial_angles": ["Training Highlight", "Recruitment"],
        "recommended_platforms": ["Facebook", "Instagram"],
        "recommended_audiences": ["community", "future volunteers"],
        "recommended_content_formats": ["photo gallery"],
        "recommended_posting_window": "This morning",
        "communications_gap": "Training has not been featured recently.",
        "repetition_risk": "Low",
        "source_signals": [
            "Scoring version editorial-recommendation-v1",
            "Uses Effective Intelligence with active human corrections applied."
        ],
        "generated_at": "2026-07-13T12:00:00+00:00",
        "scoring_version": "editorial-recommendation-v1"
    }


def assert_true(condition, message):

    if not condition:
        raise AssertionError(message)


def main():

    repo_root = Path(__file__).resolve().parents[1]

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.chdir(tmp)

        from database.db_manager import DatabaseManager
        from services.communication_package_service import CommunicationPackageService
        from services.decision_explainability_service import DecisionExplainabilityService

        db = DatabaseManager()
        insert_media(
            db,
            1,
            "ladder-training-1.jpg",
            "approved_real",
            "approved",
            "ollama",
            {"communications": 88, "intelligence": 86, "trust": 82}
        )
        insert_media(
            db,
            2,
            "ladder-training-2.jpg",
            "corrected_real",
            "corrected",
            "ollama",
            {"communications": 83, "intelligence": 80, "trust": 80}
        )
        insert_media(
            db,
            3,
            "ladder-training-video.mp4",
            "unreviewed_real",
            "pending",
            "ollama",
            {"communications": 66, "intelligence": 70, "trust": 55}
        )

        conn = db.connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO social_posts(
                platform,
                post_date,
                headline,
                caption,
                campaign,
                opportunity_type,
                source,
                imported
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                "Facebook",
                "2026-01-10",
                "Winter Training",
                "Our members trained on ladder operations.",
                "Training Tuesday",
                "training",
                "smoke",
                1
            )
        )
        cur.execute(
            """
            INSERT INTO media_usage(
                media_id,
                post_id,
                platform,
                used_at,
                campaign
            )
            VALUES(?,?,?,?,?)
            """,
            (1, 1, "Facebook", "2026-01-10", "Training Tuesday")
        )
        conn.commit()
        conn.close()

        service = DecisionExplainabilityService(database=db)
        recommendation = recommendation_fixture()
        alternative = dict(recommendation)
        alternative.update({
            "recommendation_id": "community-trust-1",
            "title": "Community Trust",
            "priority_score": 61,
            "confidence_score": 54,
            "confidence_limitations": ["Less direct training evidence."]
        })

        explanation = service.explain_recommendation(
            recommendation,
            alternatives=[alternative]
        )
        assert_true(
            explanation["decision_type"] == "recommendation",
            "recommendation decision type"
        )
        assert_true(
            explanation["score_reconciliation"]["priority_score"] == 88,
            "score reconciliation"
        )
        assert_true(
            explanation["trust_state_breakdown"]["approved_real"] == 1,
            "approved trust breakdown"
        )
        assert_true(
            explanation["trust_state_breakdown"]["corrected_real"] == 1,
            "corrected trust breakdown"
        )
        assert_true(
            explanation["why_not_selected"],
            "why-not comparison"
        )
        assert_true(
            explanation["supporting_communications"],
            "communications memory evidence"
        )

        second = service.explain_recommendation(
            recommendation,
            alternatives=[alternative]
        )
        assert_true(
            second["changed_since_previous"]["available"],
            "decision history comparison"
        )
        assert_true(
            db.recent_decision_audit_snapshots(
                decision_id="training-tuesday-1"
            ),
            "audit snapshot persisted"
        )

        media_explanation = service.explain_media_selection(
            1,
            recommendation=recommendation,
            compared_media=3
        )
        assert_true(
            media_explanation["decision_type"] == "media_selection",
            "media explanation decision type"
        )
        assert_true(
            media_explanation["why_selected"],
            "media why selected"
        )
        assert_true(
            media_explanation["why_not_selected"],
            "media why not selected"
        )

        campaign = service.explain_campaign_or_program(
            "Training Tuesday",
            subject_type="campaign",
            recommendation=recommendation
        )
        assert_true(
            campaign["supporting_communications"],
            "campaign memory support"
        )

        package_service = CommunicationPackageService(database=db)
        package = package_service.generate_package(
            recommendation,
            package_type="Facebook"
        )
        assert_true(
            package.get("decision_audit", {}).get("decision_type")
            == "communication_package",
            "package audit attached"
        )
        assert_true(
            "copy_buttons" not in package,
            "package preview is not public copy"
        )

        generated = {
            "source_package": package,
            "copy_buttons": {
                "facebook": "Training Tuesday public copy. #TrainingTuesday",
                "instagram": "Training Tuesday visual copy. #MordenFireRescue"
            },
            "facebook": {"copy_text": "Training Tuesday public copy."},
            "instagram": {"copy_text": "Training Tuesday visual copy."},
            "writing_provider": "deterministic",
            "writing_fallback_used": False,
            "writing_provider_error": "",
            "editorial_review": {"overall_score": 84}
        }
        generated["generated_content_audit"] = (
            service.audit_generated_content(
                generated,
                persist=False
            )
        )
        assert_true(
            generated.get("generated_content_audit", {}).get("decision_type")
            == "generated_content",
            "generated content audit attached"
        )
        assert_true(
            generated["copy_buttons"].get("facebook"),
            "facebook copy exists"
        )
        assert_true(
            "generated_content_audit" not in generated["copy_buttons"].get("facebook", ""),
            "audit metadata not exposed in public copy"
        )

        formatted = service.format_explanation_text(explanation)
        assert_true(
            "Why selected" in formatted and "Source signals" in formatted,
            "formatted explanation text"
        )

        install_gui_stubs()
        import gui.home_page
        import gui.content_director_page
        import gui.photo_viewer

        assert_true(
            hasattr(gui.home_page.HomePage, "show_decision_audit"),
            "Home decision audit hook"
        )
        assert_true(
            hasattr(gui.content_director_page.ContentDirectorPage, "show_decision_audit"),
            "Content Director decision audit hook"
        )
        assert_true(
            hasattr(gui.content_director_page.ContentDirectorPage, "show_media_decision"),
            "Content Director media decision hook"
        )
        assert_true(
            hasattr(gui.photo_viewer.PhotoViewer, "why_selected_lines"),
            "Photo Viewer why selected hook"
        )

        db.prune_decision_audit_history(keep_latest=1)
        assert_true(
            len(db.recent_decision_audit_snapshots(limit=10)) == 1,
            "audit retention pruning"
        )

        os.chdir(repo_root)

    print("decision_explainability_smoke passed")


def install_gui_stubs():

    if "requests" not in sys.modules:
        requests = types.ModuleType("requests")

        def unavailable(*args, **kwargs):
            raise RuntimeError("requests is unavailable in smoke stub")

        requests.get = unavailable
        requests.post = unavailable
        sys.modules["requests"] = requests

    if "customtkinter" not in sys.modules:
        ctk = types.ModuleType("customtkinter")

        class Widget:
            def __init__(self, *args, **kwargs):
                pass

            def pack(self, *args, **kwargs):
                pass

            def grid(self, *args, **kwargs):
                pass

            def configure(self, *args, **kwargs):
                pass

            def insert(self, *args, **kwargs):
                pass

            def delete(self, *args, **kwargs):
                pass

            def after(self, *args, **kwargs):
                return None

            def after_cancel(self, *args, **kwargs):
                pass

            def winfo_toplevel(self):
                return self

            def lift(self):
                pass

            def transient(self, *args, **kwargs):
                pass

            def title(self, *args, **kwargs):
                pass

            def geometry(self, *args, **kwargs):
                pass

            def minsize(self, *args, **kwargs):
                pass

            def focus_force(self):
                pass

            def attributes(self, *args, **kwargs):
                pass

        ctk.CTkFrame = Widget
        ctk.CTkScrollableFrame = Widget
        ctk.CTkToplevel = Widget
        ctk.CTkTextbox = Widget
        ctk.CTkButton = Widget
        ctk.CTkLabel = Widget
        ctk.CTkEntry = Widget
        ctk.CTkOptionMenu = Widget
        ctk.CTkCheckBox = Widget
        ctk.CTkImage = Widget
        sys.modules["customtkinter"] = ctk


if __name__ == "__main__":
    main()
