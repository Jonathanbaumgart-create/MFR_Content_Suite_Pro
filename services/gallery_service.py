from core.app_context import context


class GalleryService:

    def get_media(self):

        return context.database.get_media()