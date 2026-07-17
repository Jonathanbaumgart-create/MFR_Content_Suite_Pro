from core.app_context import context
from services.analysis_review_service import AnalysisReviewService
from services.cache_invalidation_service import CacheInvalidationService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class PhotoReviewWorkflowService:

    MAX_CONTEXT_IDS = 10000

    def __init__(self, database=None):

        self.db = database or context.database
        self.review = AnalysisReviewService(database=self.db)

    ############################################################

    def context_from_ids(
        self,
        media_ids,
        current_media_id,
        label="Gallery",
        review_required_only=False
    ):

        ids = self._bounded_unique_ids(media_ids)

        if current_media_id not in ids:
            ids.insert(0, int(current_media_id))

        return {
            "ids": ids,
            "current_media_id": int(current_media_id),
            "position": self.position_for(ids, current_media_id),
            "label": label,
            "review_required_only": bool(review_required_only),
            "session_counts": {
                "approved": 0,
                "corrected": 0,
                "rejected": 0,
                "reanalyzed": 0
            }
        }

    ############################################################

    def context_from_filter(
        self,
        filter_key,
        sort_key,
        current_media_id,
        media_type=None,
        limit=MAX_CONTEXT_IDS
    ):

        ids = self.db.get_media_ids_for_selection(
            filter_key=filter_key,
            media_type=media_type,
            limit=min(int(limit or self.MAX_CONTEXT_IDS), self.MAX_CONTEXT_IDS)
        )

        return self.context_from_ids(
            ids,
            current_media_id,
            label=filter_key,
            review_required_only=filter_key == "review_required"
        )

    ############################################################

    def position_for(self, media_ids, media_id):

        try:
            return list(media_ids).index(int(media_id))
        except ValueError:
            return 0

    ############################################################

    def next_id(self, context, current_media_id, skip_removed=True):

        ids = list(context.get("ids") or [])
        if not ids:
            return None

        position = self.position_for(ids, current_media_id)

        if skip_removed and current_media_id not in ids:
            position = max(0, min(position, len(ids) - 1))
        else:
            position += 1

        if position >= len(ids):
            return None

        return ids[position]

    ############################################################

    def previous_id(self, context, current_media_id):

        ids = list(context.get("ids") or [])
        if not ids:
            return None

        position = self.position_for(ids, current_media_id) - 1

        if position < 0:
            return None

        return ids[position]

    ############################################################

    def first_id(self, context):

        ids = list(context.get("ids") or [])
        return ids[0] if ids else None

    ############################################################

    def last_id(self, context):

        ids = list(context.get("ids") or [])
        return ids[-1] if ids else None

    ############################################################

    def media_details(self, media_id):

        return self.db.get_media_details(media_id)

    ############################################################

    def remove_reviewed_from_queue(self, context, media_id):

        if not context or not context.get("review_required_only"):
            return context

        ids = [
            item
            for item in context.get("ids", [])
            if int(item) != int(media_id)
        ]
        context["ids"] = ids
        context["position"] = min(
            context.get("position", 0),
            max(0, len(ids) - 1)
        )

        return context

    ############################################################

    def record_session_action(self, context, action):

        if not context:
            return

        counts = context.setdefault(
            "session_counts",
            {
                "approved": 0,
                "corrected": 0,
                "rejected": 0,
                "reanalyzed": 0
            }
        )

        if action in counts:
            counts[action] += 1

    ############################################################

    def approve_selected_preview(self, media_ids):

        ids = self._bounded_unique_ids(media_ids)
        eligible = set(self.db.analysis_review_eligible_ids(ids))

        return {
            "selected_count": len(ids),
            "eligible_ids": [
                media_id
                for media_id in ids
                if media_id in eligible
            ],
            "eligible_count": len(eligible),
            "ineligible_count": len(ids) - len(eligible)
        }

    ############################################################

    def approve_selected(self, media_ids, reviewer="Jonathan", notes=""):

        preview = self.approve_selected_preview(media_ids)
        approved = []

        for media_id in preview["eligible_ids"]:
            self.review.approve(
                media_id,
                reviewer=reviewer,
                notes=notes
            )
            approved.append(media_id)

        logger.info(
            "Bulk approved selected review media approved=%s ineligible=%s",
            len(approved),
            preview["ineligible_count"]
        )

        if approved:
            CacheInvalidationService.invalidate(
                media_id=None,
                reason="bulk_review_approve",
                scopes=[
                    "gallery_status",
                    "gallery_filter",
                    "ai_dashboard",
                    "communications_officer",
                    "content_director",
                    "communication_package"
                ]
            )

        return {
            "approved_ids": approved,
            "approved_count": len(approved),
            "ineligible_count": preview["ineligible_count"],
            "selected_count": preview["selected_count"]
        }

    ############################################################

    def _bounded_unique_ids(self, media_ids):

        ids = []
        seen = set()

        for media_id in media_ids or []:
            try:
                value = int(media_id)
            except Exception:
                continue

            if not value or value in seen:
                continue

            seen.add(value)
            ids.append(value)

            if len(ids) >= self.MAX_CONTEXT_IDS:
                break

        return ids
