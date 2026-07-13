import re

from services.ai_service import AIService


class AnalysisQualityService:

    APPROVED = "approved_automatically"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"
    PROVIDER_FAILED = "provider_failed"

    def evaluate(self, analysis):

        warnings = []
        parser_status = analysis.get("parse_status") or ""
        confidence = float(analysis.get("confidence") or 0)
        completeness = float(
            analysis.get("structured_field_completeness") or 0
        )

        if analysis.get("failure_reason"):
            return self._result(
                self.PROVIDER_FAILED,
                "failed",
                ["Provider failure: " + str(analysis.get("failure_reason"))],
                analysis,
                review_status="failed"
            )

        if parser_status in (AIService.STATUS_EMPTY, AIService.STATUS_INVALID):
            return self._result(
                self.REJECTED,
                "failed",
                ["Provider output was not usable structured JSON"],
                analysis,
                review_status="rejected"
            )

        if parser_status in (AIService.STATUS_REPAIRED, AIService.STATUS_PARTIAL):
            warnings.append(f"Parser status requires review: {parser_status}")

        if not analysis.get("description"):
            warnings.append("Missing factual description")

        if confidence < 0.7:
            warnings.append("Confidence below automatic approval threshold")

        if completeness < 0.65:
            warnings.append("Structured field completeness is low")

        if self._unsupported_department_claim(analysis):
            warnings.append("Possible unsupported department identity claim")

        if self._unsupported_location_claim(analysis):
            warnings.append("Possible unsupported location claim")

        if self._people_count_conflict(analysis):
            warnings.append("People count may conflict with visible people fields")

        if self._conflicting_booleans(analysis):
            warnings.append("Potentially conflicting scene classifications")

        if self._generic_language(analysis):
            warnings.append("Description contains generic language")

        media_context = "screenshot" if self.is_likely_screenshot(analysis) else "physical_scene"

        if media_context == "screenshot":
            warnings.append("Likely screenshot or document image; review required")

        quality_state = self.APPROVED if not warnings else self.REVIEW_REQUIRED
        trust_state = "unreviewed_real"
        review_status = "review_required"

        if str(analysis.get("provider", "")).lower() == "mock":
            trust_state = "mock"
            quality_state = self.REVIEW_REQUIRED
            review_status = "mock"
            warnings.append("Mock provider output is test data only")

        return self._result(
            quality_state,
            trust_state,
            warnings,
            analysis,
            media_context=media_context,
            review_status=review_status
        )

    ############################################################

    def is_likely_screenshot(self, analysis):

        text = " ".join(
            str(value)
            for value in (
                analysis.get("description", ""),
                " ".join(analysis.get("visible_text") or []),
                analysis.get("filename", ""),
                analysis.get("setting", "")
            )
        ).lower()
        indicators = (
            "screenshot",
            "screen",
            "browser",
            "website",
            "social media",
            "facebook",
            "instagram",
            "email",
            "document",
            "menu bar",
            "window",
            "interface",
            "text message"
        )
        hits = sum(1 for term in indicators if term in text)
        visible_text = analysis.get("visible_text") or []
        physical_terms = (
            "vehicle",
            "apparatus",
            "truck",
            "fire truck",
            "utility vehicle",
            "garage",
            "workshop",
            "building",
            "person",
            "people",
            "firefighter"
        )
        physical_scene = any(term in text for term in physical_terms)

        if hits >= 1:
            return True

        return len(visible_text) >= 8 and not physical_scene

    ############################################################

    def _unsupported_department_claim(self, analysis):

        text = str(analysis.get("description", "")).lower()
        visible = " ".join(analysis.get("visible_text") or []).lower()

        return "morden fire" in text and "morden fire" not in visible

    ############################################################

    def _unsupported_location_claim(self, analysis):

        text = str(analysis.get("description", "")).lower()
        visible = " ".join(analysis.get("visible_text") or []).lower()

        location_terms = ("morden", "manitoba", "fire hall", "station")

        return any(term in text and term not in visible for term in location_terms)

    ############################################################

    def _people_count_conflict(self, analysis):

        count = int(analysis.get("people_count") or 0)
        people = analysis.get("people") or []
        description = str(analysis.get("description", "")).lower()

        if count == 0 and (people or re.search(r"\b(person|people|firefighter|crew|child)\b", description)):
            return True

        return count > 0 and re.search(r"\b(no|without)\s+(people|person|firefighter|crew)\b", description)

    ############################################################

    def _conflicting_booleans(self, analysis):

        true_fields = [
            key
            for key in (
                "training",
                "incident_scene",
                "public_education",
                "community_event"
            )
            if analysis.get(key)
        ]

        return len(true_fields) >= 3

    ############################################################

    def _generic_language(self, analysis):

        text = str(analysis.get("description", "")).lower()

        return any(
            phrase in text
            for phrase in (
                "appears to show",
                "could be",
                "possibly",
                "generic image",
                "stock photo"
            )
        )

    ############################################################

    def _result(
        self,
        quality_state,
        trust_state,
        warnings,
        analysis,
        media_context="unknown",
        review_status="review_required"
    ):

        return {
            "quality_state": quality_state,
            "trust_state": trust_state,
            "review_status": review_status,
            "quality_warnings": warnings,
            "media_context": media_context,
            "confidence": float(analysis.get("confidence") or 0)
        }
