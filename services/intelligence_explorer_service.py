from core.app_context import context
from services.logging_service import LoggingService


logger = LoggingService.get_logger("intelligence")


class IntelligenceExplorerService:

    def __init__(self, database=None):

        self.db = database or context.database

    ############################################################

    def filter_counts(self, filters=None):

        logger.info(
            "Loading intelligence filter counts filters=%s",
            filters or {}
        )

        return self.db.intelligence_filter_counts(filters or {})

    ############################################################

    def media_count(self, filters=None):

        return self.db.intelligence_media_count(filters or {})

    ############################################################

    def media_page(
        self,
        filters=None,
        sort_by="filename",
        limit=200,
        offset=0
    ):

        logger.info(
            "Loading intelligence media page filters=%s sort=%s limit=%s offset=%s",
            filters or {},
            sort_by,
            limit,
            offset
        )

        return self.db.get_intelligence_media_page(
            filters=filters or {},
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )
