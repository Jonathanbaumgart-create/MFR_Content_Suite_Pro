import customtkinter as ctk
from tkinter import filedialog
import threading

from media.scanner import MediaScanner
from database.db_manager import DatabaseManager


class ScanPage(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent)

        self.db = DatabaseManager()

        title = ctk.CTkLabel(
            self,
            text="Media Scanner",
            font=("Segoe UI", 30, "bold")
        )
        title.pack(anchor="w", padx=20, pady=(20, 10))

        self.folder_label = ctk.CTkLabel(
            self,
            text="No folder selected."
        )
        self.folder_label.pack(anchor="w", padx=20)

        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=20, pady=20)
        self.progress.set(0)

        self.status = ctk.CTkLabel(
            self,
            text="Ready"
        )
        self.status.pack(anchor="w", padx=20)

        self.scan_button = ctk.CTkButton(
            self,
            text="Scan Folder",
            command=self.choose_folder
        )

        self.scan_button.pack(padx=20, pady=20)

    ##########################################################

    def choose_folder(self):

        folder = filedialog.askdirectory()

        if not folder:
            return

        self.folder_label.configure(text=folder)

        threading.Thread(
            target=self.scan_folder,
            args=(folder,),
            daemon=True
        ).start()

    ##########################################################

    def scan_folder(self, folder):

        scanner = MediaScanner()

        media = scanner.scan_folder(folder)

        total = len(media)

        if total == 0:
            self.status.configure(text="No media found.")
            return

        for index, item in enumerate(media, start=1):

            self.db.add_media(item)

            self.progress.set(index / total)

            self.status.configure(
                text=f"Indexed {index:,} / {total:,}"
            )

        self.status.configure(
            text=f"Finished indexing {total:,} media files."
        )