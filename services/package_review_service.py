from collections import Counter

from core.app_context import context
from services.time_service import TimeService


class PackageReviewService:

    def __init__(self, database=None):

        self.db = database or context.database

    ############################################################

    def record_decision(
        self,
        package,
        decision_type,
        media_id=None,
        notes="",
        metadata=None
    ):

        package = package or {}
        decision = {
            "package_id": package.get("package_id", ""),
            "decision_type": decision_type,
            "media_id": media_id or self._primary_media_id(package),
            "story_family": package.get("content_family", ""),
            "tone": (package.get("tone_options") or [""])[0],
            "notes": notes,
            "metadata": metadata or {},
            "source": "Jonathan",
            "created_at": TimeService.utc_now_iso()
        }
        decision_id = self.db.save_package_review_decision(decision)
        self._record_preference_signals(decision)
        result = {
            "decision_id": decision_id,
            "decision": decision,
            "raw_analysis_overwritten": False,
            "package_review_recorded": True
        }
        if decision_type in ("correct_event", "program_correction", "story_family_change"):
            result["event_anchor_recorded"] = True
            result["apply_confirmation_to_related_media"] = True
            result["affected_media_count"] = len(
                (package.get("event_collection") or {}).get("strongest_media", [])
            )
            result["preview_of_inferred_changes"] = [
                {
                    "media_id": item.get("media_id") or item.get("id"),
                    "inference": "package-level event correction"
                }
                for item in (
                    (package.get("event_collection") or {}).get("strongest_media", [])
                )[:10]
            ]
        return result

    def profile(self):

        decisions = self.db.package_review_decisions(limit=1000)
        signals = self.db.editorial_preference_signals(limit=1000)
        accepted = [
            item for item in decisions
            if item.get("decision_type") in ("approve_package", "accepted_media", "create_publication_draft")
        ]
        rejected = [
            item for item in decisions
            if item.get("decision_type") in ("reject_media", "use_another_option", "reject_package")
        ]
        preferred_families = Counter(item.get("story_family") for item in accepted if item.get("story_family"))
        rejected_families = Counter(item.get("story_family") for item in rejected if item.get("story_family"))
        preferred_tones = Counter(item.get("tone") for item in accepted if item.get("tone"))

        return {
            "evidence_count": len(decisions),
            "confidence": min(95, 20 + len(decisions) * 5),
            "last_updated": decisions[0].get("created_at", "") if decisions else "",
            "preferred_content_families": preferred_families.most_common(6),
            "rejected_content_families": rejected_families.most_common(6),
            "preferred_tones": preferred_tones.most_common(6),
            "hashtag_exclusions": ["#MordenFireRescue"],
            "media_match_strictness": "strict" if rejected else "normal",
            "light_hearted_acceptance": preferred_families.get("light_hearted_professional_personality", 0),
            "signals": signals[:12],
            "editable": True,
            "reset_supported": True
        }

    ############################################################

    def _record_preference_signals(self, decision):

        direction = (
            "positive"
            if decision.get("decision_type") in (
                "approve_package",
                "accepted_media",
                "create_publication_draft"
            )
            else "negative"
        )
        for signal_type, key in (
            ("content_family", decision.get("story_family", "")),
            ("tone", decision.get("tone", "")),
            ("hashtag_exclusion", "#MordenFireRescue")
        ):
            if not key:
                continue
            self.db.save_editorial_preference_signal({
                "signal_type": signal_type,
                "signal_key": key,
                "direction": direction,
                "weight": 1,
                "evidence_count": 1,
                "last_updated": TimeService.utc_now_iso(),
                "metadata": {
                    "package_id": decision.get("package_id", ""),
                    "decision_type": decision.get("decision_type", "")
                }
            })

    def _primary_media_id(self, package):

        media = (
            package.get("primary_media")
            or (package.get("media_package", {}) or {}).get("primary_photo")
            or (package.get("media_package", {}) or {}).get("primary_video")
            or {}
        )
        return media.get("media_id") or media.get("id") or 0
