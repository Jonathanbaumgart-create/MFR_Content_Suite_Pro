from core.app_context import context
from services.logging_service import LoggingService


logger = LoggingService.get_logger("intelligence")


class HumanFeedbackService:

    CORRECTABLE_FIELDS = (
        "people_count",
        "personnel_types",
        "incident_classification",
        "operational_context",
        "primary_activity",
        "operational_skills",
        "ppe",
        "equipment",
        "apparatus",
        "programs",
        "campaigns",
        "communications_uses",
        "suggested_audience",
        "suggested_platforms",
        "suggested_time_of_year",
        "notes"
    )

    LIST_FIELDS = {
        "personnel_types",
        "operational_skills",
        "ppe",
        "equipment",
        "apparatus",
        "programs",
        "campaigns",
        "communications_uses",
        "suggested_audience",
        "suggested_platforms"
    }

    def __init__(self, database=None):

        self.db = database or context.database

    ############################################################

    def corrections_for_media(self, media_id):

        return self.db.active_media_corrections(media_id)

    ############################################################

    def history_for_media(self, media_id, limit=50):

        return self.db.correction_history_for_media(
            media_id,
            limit=limit
        )

    ############################################################

    def save_correction(
        self,
        media_id,
        field_name,
        corrected_value,
        correction_source="Jonathan",
        notes="",
        confidence_after=100
    ):

        if field_name not in self.CORRECTABLE_FIELDS:
            raise ValueError("Unsupported correction field")

        original_value = self.inferred_value(
            media_id,
            field_name
        )
        normalized = self._normalize_value(
            field_name,
            corrected_value
        )

        correction_id = self.db.save_media_correction(
            {
                "media_id": media_id,
                "field_name": field_name,
                "original_value": original_value,
                "corrected_value": normalized,
                "correction_source": correction_source,
                "confidence_before": self._confidence_before(media_id),
                "confidence_after": confidence_after,
                "notes": notes
            }
        )
        self._update_patterns(
            field_name,
            original_value,
            normalized
        )

        try:
            self.db.record_analysis_review(
                media_id,
                decision="correct",
                trust_state="corrected_real",
                review_status="corrected",
                reviewer=correction_source,
                corrections={field_name: normalized},
                notes=notes
            )
        except Exception:
            logger.warning(
                "Could not update analysis review state for correction media_id=%s field=%s",
                media_id,
                field_name
            )

        logger.info(
            "Saved human correction media_id=%s field=%s source=%s",
            media_id,
            field_name,
            correction_source
        )

        return correction_id

    ############################################################

    def reset_field(
        self,
        media_id,
        field_name,
        correction_source="Jonathan",
        notes="Reset to inferred value"
    ):

        return self.db.deactivate_media_correction(
            media_id,
            field_name,
            source=correction_source,
            notes=notes
        )

    ############################################################

    def effective_media_intelligence(self, media_id):

        analysis = self.db.get_ai_analysis(media_id) or {}
        media = self.db.get_media_intelligence(media_id) or {}
        fire = self.db.get_fire_service_intelligence(media_id) or {}
        corrections = self.corrections_for_media(media_id)
        correction_map = {
            row["field_name"]: row["corrected_value"]
            for row in corrections
        }

        effective = {
            "media_id": media_id,
            "analysis": dict(analysis),
            "media_intelligence": dict(media),
            "fire_service_intelligence": dict(fire),
            "corrections": corrections,
            "correction_history": self.history_for_media(media_id),
            "analysis_review_history": self.db.analysis_review_history(
                media_id
            ),
            "trust_state": self._trust_state(analysis, corrections),
            "review_status": analysis.get("review_status", ""),
            "quality_state": analysis.get("quality_state", ""),
            "quality_warnings": analysis.get("quality_warnings", []),
            "is_human_corrected": bool(corrections),
            "correction_count": len(corrections)
        }

        for field in self.CORRECTABLE_FIELDS:
            effective[field] = self._resolve_field(
                field,
                analysis,
                media,
                fire
            )

        for field, value in correction_map.items():
            effective[field] = value
            self._apply_to_nested(
                effective,
                field,
                value
            )

        for field in self.CORRECTABLE_FIELDS:

            if field in correction_map:
                continue

            self._apply_to_nested(
                effective,
                field,
                effective.get(field)
            )

        effective["similar_review_suggestions"] = self.similar_media_suggestions(
            media_id,
            limit=8
        )

        return effective

    ############################################################

    def effective_media_intelligence_row(self, media_id):

        effective = self.effective_media_intelligence(media_id)
        media = dict(effective.get("media_intelligence") or {})
        fire = dict(effective.get("fire_service_intelligence") or {})

        media["fire_service_intelligence"] = fire
        media["human_corrections"] = effective.get("corrections", [])
        media["is_human_corrected"] = effective.get("is_human_corrected", False)
        media["correction_count"] = effective.get("correction_count", 0)
        media["trust_state"] = effective.get("trust_state", "")
        media["review_status"] = effective.get("review_status", "")
        media["quality_state"] = effective.get("quality_state", "")
        media["quality_warnings"] = effective.get("quality_warnings", [])

        return media

    ############################################################

    def similar_media_suggestions(self, media_id, limit=12):

        media = self.db.get_media_intelligence(media_id) or {}
        fire = self.db.get_fire_service_intelligence(media_id) or {}
        terms = []

        for key in (
            "incident_type",
            "primary_activity",
            "normalized_scene",
            "search_text"
        ):
            terms.extend(
                self._split_terms(media.get(key))
            )

        for key in (
            "content_tags",
            "content_themes",
            "recommended_uses",
            "equipment_tags",
            "ppe_tags",
            "apparatus_tags"
        ):
            terms.extend(media.get(key) or [])

        for key in (
            "incident_classification",
            "operational_context",
            "operational_activity"
        ):
            terms.extend(
                self._split_terms(fire.get(key))
            )

        for key in (
            "ppe",
            "equipment",
            "apparatus",
            "operational_skills",
            "communications_uses",
            "communications_intent"
        ):
            terms.extend(fire.get(key) or [])

        return self.db.similar_media_for_correction(
            media_id,
            self._unique(terms),
            limit=limit
        )

    ############################################################

    def metrics(self):

        metrics = self.db.human_feedback_metrics()
        metrics["media_suggested_for_review"] = self._suggested_review_count()

        return metrics

    ############################################################

    def inferred_value(self, media_id, field_name):

        analysis = self.db.get_ai_analysis(media_id) or {}
        media = self.db.get_media_intelligence(media_id) or {}
        fire = self.db.get_fire_service_intelligence(media_id) or {}

        return self._resolve_field(
            field_name,
            analysis,
            media,
            fire
        )

    ############################################################

    def _resolve_field(self, field, analysis, media, fire):

        if field == "people_count":
            return (
                fire.get("firefighter_count") or
                analysis.get("people_count") or
                0
            )

        if field == "personnel_types":
            values = []

            if fire.get("firefighter_count", 0) > 0:
                values.append("firefighters")

            if fire.get("civilian_count", 0) > 0:
                values.append("civilians")

            if fire.get("officer_presence"):
                values.append("officer")

            if fire.get("children_present"):
                values.append("children")

            return values or media.get("people_tags") or []

        if field == "incident_classification":
            return (
                fire.get("incident_classification") or
                media.get("incident_type") or
                analysis.get("scene_type") or
                ""
            )

        if field == "operational_context":
            return fire.get("operational_context") or media.get("normalized_scene") or ""

        if field == "primary_activity":
            return (
                fire.get("operational_activity") or
                media.get("primary_activity") or
                analysis.get("activity") or
                ""
            )

        if field == "operational_skills":
            return fire.get("operational_skills") or []

        if field == "ppe":
            return fire.get("ppe") or media.get("ppe_tags") or []

        if field == "equipment":
            return fire.get("equipment") or media.get("equipment_tags") or analysis.get("equipment") or []

        if field == "apparatus":
            return fire.get("apparatus") or media.get("apparatus_tags") or analysis.get("apparatus") or []

        if field == "programs":
            return [
                value
                for value in fire.get("communications_uses", [])
                if value in ("hydrant_heroes", "travelling_sparky")
            ]

        if field == "campaigns":
            return media.get("suggested_campaigns") or []

        if field == "communications_uses":
            return fire.get("communications_uses") or media.get("recommended_uses") or []

        if field == "suggested_audience":
            return media.get("suggested_audience") or []

        if field == "suggested_platforms":
            platforms = media.get("platform_suitability") or {}

            if isinstance(platforms, dict):
                return [
                    key
                    for key, value in sorted(
                        platforms.items(),
                        key=lambda item: item[1],
                        reverse=True
                    )[:3]
                ]

            return []

        if field == "suggested_time_of_year":
            return media.get("suggested_time_of_year") or ""

        if field == "notes":
            return ""

    ############################################################

    def _trust_state(self, analysis, corrections):

        if corrections:
            return "corrected_real"

        trust_state = analysis.get("trust_state", "")

        if trust_state:
            return trust_state

        if analysis.get("failure_reason"):
            return "failed"

        provider = analysis.get("provider", "")
        model = analysis.get("model", "")

        if provider == "mock" or str(model).startswith("mock"):
            return "mock"

        if provider:
            return "unreviewed_real"

        return ""

        return ""

    ############################################################

    def _apply_to_nested(self, effective, field, value):

        media = effective["media_intelligence"]
        fire = effective["fire_service_intelligence"]
        analysis = effective["analysis"]

        if field == "people_count":
            analysis["people_count"] = self._to_int(value)
            fire["firefighter_count"] = self._to_int(value)
            media["people_tags"] = self._people_tags(value)

        elif field == "personnel_types":
            media["people_tags"] = self._as_list(value)

        elif field == "incident_classification":
            fire["incident_classification"] = str(value or "")
            media["incident_type"] = str(value or "")

        elif field == "operational_context":
            fire["operational_context"] = str(value or "")
            media["normalized_scene"] = str(value or "")

        elif field == "primary_activity":
            fire["operational_activity"] = str(value or "")
            media["primary_activity"] = str(value or "")

        elif field == "operational_skills":
            fire["operational_skills"] = self._as_list(value)

        elif field == "ppe":
            fire["ppe"] = self._as_list(value)
            media["ppe_tags"] = self._as_list(value)

        elif field == "equipment":
            fire["equipment"] = self._as_list(value)
            media["equipment_tags"] = self._as_list(value)

        elif field == "apparatus":
            fire["apparatus"] = self._as_list(value)
            media["apparatus_tags"] = self._as_list(value)

        elif field == "programs":
            fire["communications_uses"] = self._unique(
                fire.get("communications_uses", []) +
                self._as_list(value)
            )

        elif field == "campaigns":
            media["suggested_campaigns"] = self._as_list(value)

        elif field == "communications_uses":
            fire["communications_uses"] = self._as_list(value)
            media["recommended_uses"] = self._as_list(value)

        elif field == "suggested_audience":
            media["suggested_audience"] = self._as_list(value)

        elif field == "suggested_platforms":
            media["suggested_platforms"] = self._as_list(value)

        elif field == "suggested_time_of_year":
            media["suggested_time_of_year"] = str(value or "")

        elif field == "notes":
            effective["correction_notes"] = str(value or "")

    ############################################################

    def _update_patterns(self, field_name, original_value, corrected_value):

        media_ids = self.db.correction_pattern_candidates(
            field_name,
            original_value,
            corrected_value
        )

        if len(media_ids) < 2:
            return

        confidence = min(
            95,
            50 + len(media_ids) * 10
        )
        self.db.update_correction_pattern(
            {
                "field_name": field_name,
                "original_value": original_value,
                "corrected_value": corrected_value,
                "occurrence_count": len(media_ids),
                "confidence": confidence,
                "example_media_ids": media_ids[:10],
                "notes": "Repeated human correction pattern detected; not automatically applied."
            }
        )

    ############################################################

    def _confidence_before(self, media_id):

        fire = self.db.get_fire_service_intelligence(media_id) or {}
        media = self.db.get_media_intelligence(media_id) or {}

        return (
            fire.get("operational_confidence") or
            media.get("intelligence_score") or
            0
        )

    ############################################################

    def _suggested_review_count(self):

        patterns = self.db.correction_patterns(limit=20)

        if not patterns:
            return 0

        return min(
            100,
            sum(pattern.get("occurrence_count", 0) for pattern in patterns)
        )

    ############################################################

    def _normalize_value(self, field_name, value):

        if field_name == "people_count":
            return self._to_int(value)

        if field_name in self.LIST_FIELDS:
            return self._as_list(value)

        return str(value or "").strip()

    ############################################################

    def _as_list(self, value):

        if value is None:
            return []

        if isinstance(value, list):
            return [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

        return [
            item.strip()
            for item in str(value).replace("\n", ",").split(",")
            if item.strip()
        ]

    ############################################################

    def _split_terms(self, value):

        return [
            part.strip()
            for part in str(value or "").replace("_", " ").split()
            if part.strip()
        ]

    ############################################################

    def _people_tags(self, value):

        count = self._to_int(value)

        if count <= 0:
            return ["unknown_people"]

        if count <= 2:
            return ["people", "small_group"]

        if count <= 6:
            return ["people", "crew"]

        return ["people", "large_group"]

    ############################################################

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values or []:
            text = str(value or "").strip()

            if not text or text in seen:
                continue

            seen.add(text)
            unique.append(text)

        return unique

    ############################################################

    def _to_int(self, value):

        try:
            return int(value)
        except Exception:
            return 0
