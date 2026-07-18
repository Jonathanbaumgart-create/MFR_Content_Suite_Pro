from core.app_context import context
from services.analysis_review_service import AnalysisReviewService
from services.brain_service import BrainService
from services.human_feedback_service import HumanFeedbackService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("gallery")


class GalleryAnalysisInspectorService:

    CORRECTION_FIELDS = (
        "description",
        "content_tags",
        "primary_activity",
        "programs",
        "campaigns",
        "apparatus",
        "equipment",
        "people_count",
        "notes"
    )

    FIELD_MAP = {
        "content_tags": "communications_uses",
        "primary_activity": "primary_activity",
        "programs": "programs",
        "campaigns": "campaigns",
        "apparatus": "apparatus",
        "equipment": "equipment",
        "people_count": "people_count",
        "description": "description",
        "notes": "notes"
    }

    def __init__(
        self,
        database=None,
        review_service=None,
        feedback_service=None,
        brain_service=None
    ):

        self.db = database or context.database
        self.review = review_service or AnalysisReviewService(
            database=self.db
        )
        self.feedback = feedback_service or HumanFeedbackService(
            database=self.db
        )
        self.brain = brain_service or BrainService(database=self.db)

    ############################################################

    def inspector_payload(self, media_id):

        media = self.db.get_media_details(media_id) or {}
        analysis = self.db.get_ai_analysis(media_id) or {}
        intelligence = self.db.get_media_intelligence(media_id) or {}
        filesystem = self.db.get_filesystem_intelligence(media_id) or {}
        video = self.db.get_video_intelligence(media_id) or {}
        effective = self.feedback.effective_media_intelligence(media_id)
        review_history = self.db.analysis_review_history(media_id, limit=8)
        correction_history = self.feedback.history_for_media(media_id, limit=8)

        payload = {
            "media": media,
            "analysis": analysis,
            "intelligence": intelligence,
            "filesystem": filesystem,
            "video": video,
            "effective": effective,
            "review_history": review_history,
            "correction_history": correction_history,
            "display": self._display(media, analysis, intelligence, filesystem, video, effective)
        }
        logger.debug(
            "Gallery inspector payload media_id=%s has_analysis=%s video=%s",
            media_id,
            bool(analysis),
            bool(video)
        )
        return payload

    ############################################################

    def approve(self, media_id, notes="Approved in Gallery Inspector"):

        result = self.review.approve(
            media_id,
            notes=notes
        )
        return {
            "analysis": result,
            "status": "approved"
        }

    ############################################################

    def reject(self, media_id, notes="Rejected in Gallery Inspector"):

        result = self.review.reject(
            media_id,
            notes=notes
        )
        return {
            "analysis": result,
            "status": "rejected"
        }

    ############################################################

    def request_reanalysis(self, media_id, notes="Reanalysis requested in Gallery Inspector"):

        result = self.review.request_reanalysis(
            media_id,
            notes=notes
        )
        self.brain.analyze_selected(
            [media_id],
            force=True
        )
        return {
            "analysis": result,
            "status": "reanalyze_requested"
        }

    ############################################################

    def save_corrections(self, media_id, corrections, notes=""):

        saved = []

        for field, value in (corrections or {}).items():
            if field not in self.CORRECTION_FIELDS:
                continue

            if value is None:
                continue

            mapped = self.FIELD_MAP.get(field, field)
            saved.append(
                self.feedback.save_correction(
                    media_id,
                    mapped,
                    value,
                    correction_source="Jonathan",
                    notes=notes or "Corrected in Gallery Inspector"
                )
            )

        if not saved:
            raise ValueError("No supported correction fields were provided.")

        return {
            "saved_corrections": len(saved),
            "status": "corrected",
            "payload": self.inspector_payload(media_id)
        }

    ############################################################

    def video_status(self, media_id):

        media = self.db.get_media_details(media_id) or {}
        if media.get("media_type") != "video":
            return {}

        analysis = self.db.get_ai_analysis(media_id) or {}
        video = self.db.get_video_intelligence(media_id) or {}
        failure = analysis.get("failure_reason", "")

        if failure:
            if analysis.get("failure_category") == "unsupported_provider":
                return {
                    "state": "Unsupported Provider",
                    "reason": failure
                }
            return {
                "state": "Failed",
                "reason": failure
            }

        if not analysis and not video:
            return {
                "state": "Unanalyzed",
                "reason": ""
            }

        if video:
            review = video.get("review_state") or analysis.get("review_status")
            return {
                "state": self._review_state_label(review),
                "reason": video.get("explanation", "")
            }

        return {
            "state": self._review_state_label(analysis.get("review_status")),
            "reason": analysis.get("parse_status", "")
        }

    ############################################################

    def _display(self, media, analysis, intelligence, filesystem, video, effective):

        return {
            "filename": media.get("filename", ""),
            "capture_date": TimeService.format_local(
                media.get("capture_time") or media.get("date_added") or ""
            ),
            "review_state": self._review_state_label(
                effective.get("review_status") or analysis.get("review_status")
            ),
            "provider": analysis.get("provider", "") or video.get("provider", ""),
            "model": analysis.get("model", "") or video.get("model", ""),
            "confidence": analysis.get("confidence") or video.get("confidence") or 0,
            "raw_description": analysis.get("description", ""),
            "effective_description": effective.get("description", "") or analysis.get("description", ""),
            "topics": (
                intelligence.get("content_tags")
                or effective.get("communications_uses")
                or analysis.get("keywords")
                or []
            ),
            "activity": (
                effective.get("primary_activity")
                or intelligence.get("primary_activity")
                or analysis.get("activity")
                or video.get("primary_activity")
                or ""
            ),
            "program_campaign": self._program_campaign(effective, intelligence, filesystem, video),
            "apparatus": effective.get("apparatus") or intelligence.get("apparatus_tags") or analysis.get("apparatus") or [],
            "equipment": effective.get("equipment") or intelligence.get("equipment_tags") or analysis.get("equipment") or [],
            "people_count": effective.get("people_count") or analysis.get("people_count") or 0,
            "location": self._known_location(filesystem),
            "filesystem": self._filesystem_summary(filesystem),
            "human_correction_status": (
                f"{effective.get('correction_count', 0)} active correction(s)"
                if effective.get("is_human_corrected")
                else "No active corrections"
            ),
            "correction_history_summary": self._correction_summary(
                effective.get("correction_history") or []
            ),
            "video_status": self.video_status(media.get("id")) if media.get("media_type") == "video" else {},
            "analysis_status": self.analysis_status(
                media.get("id"),
                analysis,
                video
            )
        }

    def analysis_status(self, media_id, analysis, video):

        try:
            statuses = self.db.analysis_media_statuses([media_id])
            status = statuses.get(int(media_id))
            if status:
                return self._readable_status(status)
        except Exception:
            pass

        if analysis.get("failure_category") == "unsupported_provider":
            return "Unsupported Provider"

        if analysis.get("failure_reason"):
            return "Failed"

        if video:
            return self._review_state_label(video.get("review_state"))

        return self._review_state_label(
            analysis.get("review_status") or analysis.get("trust_state")
        )

    def _program_campaign(self, effective, intelligence, filesystem, video):

        values = []
        for source, keys in (
            (filesystem, ("public_education_program", "campaign", "community_event")),
            (video, ("program", "campaign", "community_event")),
            (intelligence, ("suggested_campaigns",)),
            (effective, ("programs", "campaigns")),
        ):
            for key in keys:
                value = source.get(key)
                if isinstance(value, list):
                    values.extend(value)
                elif value:
                    values.append(value)

        return ", ".join(self._unique(values))

    def _known_location(self, filesystem):

        location = filesystem.get("location_context") or ""
        if str(location).lower() in ("", "unknown", "none"):
            return ""
        return location

    def _filesystem_summary(self, filesystem):

        if not filesystem:
            return ""

        parts = []
        for key in (
            "root_category",
            "subcategory",
            "training_type",
            "incident_type",
            "public_education_program",
            "campaign",
            "community_event",
            "conflict_state"
        ):
            value = filesystem.get(key)
            if value and str(value).lower() != "unknown":
                parts.append(f"{key.replace('_', ' ').title()}: {value}")

        return "; ".join(parts)

    def _correction_summary(self, history):

        if not history:
            return "No correction history"

        return "; ".join(
            (
                f"{row.get('field_name', '')}: "
                f"{row.get('correction_source', '')} "
                f"{TimeService.format_local(row.get('created_at', ''))}"
            ).strip()
            for row in history[:3]
        )

    def _review_state_label(self, state):

        value = str(state or "").strip().lower()
        labels = {
            "approved": "Approved",
            "corrected": "Corrected",
            "rejected": "Rejected",
            "failed": "Failed",
            "review_required": "Review Required",
            "reanalyze_requested": "Reanalysis Requested",
            "cancelled": "Cancelled",
            "canceled": "Cancelled"
        }
        return labels.get(value, "Unanalyzed" if not value else value.replace("_", " ").title())

    def _readable_status(self, status):

        value = str(status or "").strip()
        if value.startswith("Real - "):
            return value.replace("Real - ", "")
        if value == "Not analyzed":
            return "Unanalyzed"
        return value

    def _unique(self, values):

        result = []
        seen = set()

        for value in values or []:
            text = str(value or "").strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            result.append(text)

        return result
