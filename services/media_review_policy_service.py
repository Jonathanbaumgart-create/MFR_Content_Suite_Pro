from core.app_context import context


class MediaReviewPolicyService:

    SEARCHABLE = "searchable"
    RANKABLE = "rankable"
    CANDIDATE = "candidate"
    DRAFT_ATTACHABLE = "draft_attachable"
    PUBLISHABLE = "publishable"

    def __init__(self, database=None, trust_service=None):

        self.db = database or context.database
        self.trust = trust_service

    ############################################################

    def policy_for_media(self, media):

        media = dict(media or {})
        trust = (
            self.trust.score_media(media)
            if self.trust is not None
            else self._fallback_trust(media)
        )
        trust_class = trust.get("trust_class", "")
        review = trust.get("review_requirement", "")
        excluded = trust_class == "excluded"

        permissions = {
            self.SEARCHABLE: not excluded,
            self.RANKABLE: not excluded,
            self.CANDIDATE: not excluded and trust.get("score", 0) >= 35,
            self.DRAFT_ATTACHABLE: (
                not excluded
                and review != "manual_review_required"
                and trust.get("score", 0) >= 45
            ),
            self.PUBLISHABLE: False
        }

        if trust_class in ("human_approved", "human_corrected"):
            permissions[self.DRAFT_ATTACHABLE] = True

        return {
            "media_id": media.get("media_id") or media.get("id"),
            "trust": trust,
            "permissions": permissions,
            "may_search": permissions[self.SEARCHABLE],
            "may_rank": permissions[self.RANKABLE],
            "may_show_candidate": permissions[self.CANDIDATE],
            "may_attach_to_draft": permissions[self.DRAFT_ATTACHABLE],
            "may_publish_without_confirmation": False,
            "package_review_required": True,
            "reason": self._reason(trust, permissions)
        }

    def can_use_for_draft(self, media):

        return self.policy_for_media(media)["may_attach_to_draft"]

    ############################################################

    def _fallback_trust(self, media):

        trust = media.get("trust_state") or ""
        review = media.get("review_status") or ""

        if trust == "corrected_real" or review == "corrected":
            return {
                "score": 96,
                "trust_class": "human_corrected",
                "review_requirement": "package_review",
                "evidence": ["Human correction exists."],
                "conflicts": [],
                "explanation": "Corrected media can support draft packages."
            }

        if trust == "approved_real" or review == "approved":
            return {
                "score": 90,
                "trust_class": "human_approved",
                "review_requirement": "package_review",
                "evidence": ["Human approval exists."],
                "conflicts": [],
                "explanation": "Approved media can support draft packages."
            }

        if media.get("failure_reason") or media.get("provider") == "mock":
            return {
                "score": 0,
                "trust_class": "excluded",
                "review_requirement": "manual_review_required",
                "evidence": [],
                "conflicts": ["Failed or mock analysis cannot support real packages."],
                "explanation": "Excluded from candidate use."
            }

        return {
            "score": 50,
            "trust_class": "usable_with_package_review",
            "review_requirement": "package_review",
            "evidence": ["Stored local metadata exists."],
            "conflicts": [],
            "explanation": "Unreviewed media may be searched and ranked for drafts."
        }

    def _reason(self, trust, permissions):

        if trust.get("trust_class") == "excluded":
            return "Media is excluded from discovery because it is failed, rejected, or mock."

        if permissions[self.DRAFT_ATTACHABLE]:
            return "Media may be attached to a draft package, with package-level review before publishing."

        return "Media may be searched and ranked, but needs manual review before use."
