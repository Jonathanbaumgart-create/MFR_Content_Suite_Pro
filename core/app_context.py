from database.db_manager import DatabaseManager


class AppContext:

    def __init__(self):

        self.database = DatabaseManager()


context = AppContext()