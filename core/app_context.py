from database.db_manager import DatabaseManager
from services.job_manager import JobManager


class AppContext:

    def __init__(self):

        self.database = DatabaseManager()
        self.job_manager = JobManager()


context = AppContext()
