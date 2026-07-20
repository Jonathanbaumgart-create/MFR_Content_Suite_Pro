from core.app_context import context


class AutomatedEditorialTrustService:

    def __init__(self, database=None):

        self.db = database or context.database

    ############################################################

    def score_media(self, media, event=None, anchors=None):

        media = dict(media or {})
        event = event or {}
        anchors = anchors or []
        evidence = []
        conflicts = []
        score = 20

        trust = media.get("trust_state") or ""
        review = media.get("review_status") or ""
        provider = str(media.get("provider") or "").lower()

        if trust == "corrected_real" or review == "corrected":
            score += 76
            evidence.append("Human-corrected media.")

        elif trust == "approved_real" or review == "approved":
            score += 68
            evidence.append("Human-approved media.")

        if media.get("failure_reason"):
            conflicts.append("Provider failure recorded.")
            score -= 80

        if provider == "mock":
            conflicts.append("Mock/test analysis is not real evidence.")
            score -= 90
        elif provider:
            score += 10
            evidence.append("Real provider or local analysis record exists.")

        if trust in ("rejected_real", "failed") or review in ("rejected", "failed"):
            conflicts.append("Human or provider rejection exists.")
            score -= 100

        filesystem = media.get("filesystem_intelligence") or {}
        if filesystem.get("filesystem_confidence", 0):
            score += min(18, int(filesystem.get("filesystem_confidence") or 0) // 5)
            evidence.append("Filesystem intelligence supports the classification.")

        if media.get("path"):
            score += 8
            evidence.append("Folder/path context exists.")

        if media.get("filename"):
            score += 4
            evidence.append("Filename sequence context exists.")

        if media.get("media_type"):
            score += 3
            evidence.append("Media type is known.")

        for key in ("primary_activity", "incident_type", "normalized_scene"):
            if media.get(key):
                score += 6
                evidence.append(f"Stored intelligence includes {key.replace('_', ' ')}.")

        if media.get("communications_score"):
            score += min(15, int(media.get("communications_score") or 0) // 8)
            evidence.append("Communications score is available.")

        if event.get("confidence", 0) >= 65:
            score += 16
            evidence.append("Related event collection has supporting evidence.")

        if event.get("photo_count", 0) + event.get("video_count", 0) >= 3:
            score += 8
            evidence.append("Nearby media agree on a shared event/activity.")

        if anchors:
            score += min(20, len(anchors) * 10)
            evidence.append("High-authority event anchor media exists.")

        if filesystem.get("conflict_state") == "conflict":
            conflicts.append("Filesystem and inferred intelligence conflict.")
            score -= 30

        if media.get("sensitivity_risk") or media.get("privacy_risk"):
            conflicts.append("Possible privacy/sensitivity risk.")
            score -= 35

        if not evidence:
            evidence.append("Only weak local metadata is available.")

        score = max(0, min(100, int(score)))
        trust_class = self._trust_class(score, media, conflicts)
        review_requirement = self._review_requirement(score, trust_class, conflicts)

        return {
            "media_id": media.get("media_id") or media.get("id"),
            "score": score,
            "trust_class": trust_class,
            "evidence": evidence[:8],
            "conflicts": conflicts[:6],
            "review_requirement": review_requirement,
            "explanation": self._explanation(score, trust_class, evidence, conflicts)
        }

    ############################################################

    def _trust_class(self, score, media, conflicts):

        trust = media.get("trust_state") or ""
        review = media.get("review_status") or ""

        if trust in ("rejected_real", "failed") or review in ("rejected", "failed"):
            return "excluded"

        if media.get("failure_reason") or str(media.get("provider") or "").lower() == "mock":
            return "excluded"

        if trust == "corrected_real" or review == "corrected":
            return "human_corrected"

        if trust == "approved_real" or review == "approved":
            return "human_approved"

        if conflicts and score < 70:
            return "manual_review_recommended"

        if score >= 75:
            return "automatically_trusted_for_candidate_discovery"

        if score >= 55:
            return "usable_with_package_review"

        if score >= 35:
            return "manual_review_recommended"

        return "manual_review_required"

    def _review_requirement(self, score, trust_class, conflicts):

        if trust_class == "excluded":
            return "excluded"

        if trust_class == "manual_review_required" or len(conflicts) >= 2:
            return "manual_review_required"

        if trust_class == "manual_review_recommended":
            return "manual_review_recommended"

        return "package_review"

    def _explanation(self, score, trust_class, evidence, conflicts):

        if conflicts:
            return (
                f"Editorial trust {score}/100 ({trust_class}) with conflicts: "
                + "; ".join(conflicts[:3])
            )

        return (
            f"Editorial trust {score}/100 ({trust_class}) from "
            + "; ".join(evidence[:3])
        )
