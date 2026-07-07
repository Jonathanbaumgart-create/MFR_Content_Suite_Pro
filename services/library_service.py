from pathlib import Path

from core.app_context import context


DEFAULT_LIBRARY = Path.home() / "Pictures"


class LibraryService:

    def __init__(self):
        self.db = context.database

    ###########################################################

    def initialize_default_library(self):

        if not DEFAULT_LIBRARY.exists():
            return

        if self.db.library_exists(str(DEFAULT_LIBRARY)):
            return

        self.db.add_library(
            name="Pictures",
            path=str(DEFAULT_LIBRARY)
        )

    ###########################################################

    def get_libraries(self):

        return self.db.get_libraries()