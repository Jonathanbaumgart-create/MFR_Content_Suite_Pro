import threading
from pathlib import Path

import customtkinter as ctk

from services.scan_service import ScanService

# Default media library
DEFAULT_LIBRARY = Path(r"E:\Jonathan\Pictures")


class ScanPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.service = ScanService()
        self.pictures_folder = DEFAULT_LIBRARY

        self.build_page()

    ###########################################################

    def build_page(self):

        title = ctk.CTkLabel(
            self,
            text="Media Scanner",
            font=("Segoe UI", 30, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        description = ctk.CTkLabel(
            self,
            text="Scan your primary media library into the MFR Content Suite database.",
            justify="left"
        )

        description.pack(
            anchor="w",
            padx=20,
            pady=(0, 15)
        )

        self.folder = ctk.CTkLabel(
            self,
            text=f"Library: {self.pictures_folder}"
        )

        self.folder.pack(
            anchor="w",
            padx=20
        )

        self.progress = ctk.CTkProgressBar(self)

        self.progress.pack(
            fill="x",
            padx=20,
            pady=(20, 10)
        )

        self.progress.set(0)

        self.status = ctk.CTkLabel(
            self,
            text="Ready to scan."
        )

        self.status.pack(
            anchor="w",
            padx=20
        )

        self.scan_button = ctk.CTkButton(
            self,
            text="Scan Pictures Library",
            command=self.start_scan
        )

        self.scan_button.pack(
            padx=20,
            pady=20
        )

    ###########################################################

    def start_scan(self):

        if not self.pictures_folder.exists():

            self.status.configure(
                text=f"Folder not found: {self.pictures_folder}"
            )

            return

        self.scan_button.configure(state="disabled")

        self.progress.set(0)

        self.status.configure(
            text="Scanning library..."
        )

        threading.Thread(
            target=self.run_scan,
            daemon=True
        ).start()

    ###########################################################

    def run_scan(self):

        try:

            total = self.service.scan(
                str(self.pictures_folder),
                self.update_progress
            )

            self.after(
                0,
                lambda: self.scan_complete(total)
            )

        except Exception as e:

            self.after(
                0,
                lambda: self.scan_failed(str(e))
            )

    ###########################################################

    def update_progress(self, current, total):

        progress = current / total if total else 0

        self.after(
            0,
            lambda: self.progress.set(progress)
        )

        self.after(
            0,
            lambda: self.status.configure(
                text=f"Indexed {current:,} of {total:,} files..."
            )
        )

    ###########################################################

    def scan_complete(self, total):

        self.progress.set(1)

        self.status.configure(
            text=f"Scan complete. {total:,} media files indexed."
        )

        self.scan_button.configure(
            state="normal"
        )

    ###########################################################

    def scan_failed(self, message):

        self.progress.set(0)

        self.status.configure(
            text=f"Scan failed: {message}"
        )

        self.scan_button.configure(
            state="normal"
        )