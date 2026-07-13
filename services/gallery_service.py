from core.app_context import context
from services.logging_service import LoggingService


logger = LoggingService.get_logger("gallery")


class GalleryService:

    def get_media(self):

        logger.info("Loading all gallery media")

        return context.database.get_media()

    ###########################################################

    def get_media_page(self, limit, offset=0, filter_key="all"):

        logger.info(
            "Loading media page limit=%s offset=%s",
            limit,
            offset
        )

        return context.database.get_media_page(
            limit,
            offset,
            filter_key=filter_key
        )

    ###########################################################

    def media_count(self, filter_key="all"):

        return context.database.media_count(filter_key=filter_key)

    ###########################################################

    def media_count_for_selection(self, filter_key="all", media_type=None):

        return context.database.media_count_for_selection(
            filter_key=filter_key,
            media_type=media_type
        )

    ###########################################################

    def get_media_ids_for_selection(
        self,
        filter_key="all",
        media_type=None,
        limit=10000
    ):

        return context.database.get_media_ids_for_selection(
            filter_key=filter_key,
            media_type=media_type,
            limit=limit
        )

    ###########################################################

    def get_media_by_ids(self, media_ids):

        return context.database.get_media_by_ids(media_ids)

    ###########################################################

    def get_media_under_path(self, folder_path):

        return context.database.get_media_under_path(folder_path)

    ###########################################################

    def get_image_media(self):

        return context.database.get_image_media()
