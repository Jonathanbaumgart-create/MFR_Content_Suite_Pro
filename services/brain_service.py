from core.app_context import context
from services.ai_service import AIService


class BrainService:

    def __init__(
        self,
        database=None,
        job_manager=None,
        ai_service=None
    ):

        self.db = database or context.database
        self.jobs = job_manager or context.job_manager
        self.ai = ai_service or AIService()

    ############################################################

    def get_analysis(self, media_id):

        return self.db.get_ai_analysis(media_id)

    ############################################################

    def analyze_photo(
        self,
        media_id,
        image_path,
        callback=None,
        error_callback=None
    ):

        return self.jobs.submit(
            self._analyze_and_save,
            media_id,
            image_path,
            callback=callback,
            error_callback=error_callback
        )

    ############################################################

    def _analyze_and_save(self, media_id, image_path):

        analysis = self.ai.analyze_image(image_path)

        self.db.save_ai_analysis(
            media_id,
            analysis
        )

        return self.db.get_ai_analysis(media_id)
