import customtkinter as ctk

from gui.main_window import MainWindow
from services.logging_service import LoggingService


logger = LoggingService.get_logger("application")


def main():

    logger.info("Starting MFR Content Suite Professional")

    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
