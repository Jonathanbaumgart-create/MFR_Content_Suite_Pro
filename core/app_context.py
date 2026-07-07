from database.db_manager import DatabaseManager
from services.job_manager import JobManager
from services.logging_service import LoggingService


class AppContext:

    def __init__(self):

        LoggingService.configure()

        self.database = DatabaseManager()
        self.job_manager = JobManager()


context = AppContext()
