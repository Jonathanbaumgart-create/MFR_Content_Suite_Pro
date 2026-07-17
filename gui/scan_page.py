import threading
from pathlib import Path

import customtkinter as ctk

from gui.window_placement import WindowPlacement
from services.scan_service import ScanService

# Default media library
DEFAULT_LIBRARY = Path(r"E:\Jonathan\Pictures")


class ScanPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.service = ScanService()
        self.pictures_folder = DEFAULT_LIBRARY
        self.last_report_path = None
        self.report_window = None

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

        self.report_button = ctk.CTkButton(
            self,
            text="View Scan Report",
            command=self.open_scan_report,
            state="disabled"
        )

        self.report_button.pack(
            padx=20,
            pady=(0, 20)
        )

    ###########################################################

    def start_scan(self):

        if not self.pictures_folder.exists():

            self.status.configure(
                text=f"Folder not found: {self.pictures_folder}"
            )

            return

        self.scan_button.configure(state="disabled")
        self.report_button.configure(state="disabled")
        self.last_report_path = None

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

            stats = self.service.scan(
                str(self.pictures_folder),
                self.update_progress
            )

            self.after(
                0,
                lambda: self.scan_complete(stats)
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

    def scan_complete(self, stats):

        self.progress.set(1)
        self.last_report_path = stats.get("report_path")

        self.status.configure(
            text=(
                "Scan complete. "
                f"{stats['inserted']:,} new, "
                f"{stats['duplicates']:,} duplicates, "
                f"{stats['failed']:,} failed, "
                f"{stats['skipped']:,} skipped."
            )
        )

        self.scan_button.configure(
            state="normal"
        )

        if self.last_report_path:
            self.report_button.configure(
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

    ###########################################################

    def open_scan_report(self):

        if not self.last_report_path:
            return

        report_path = Path(self.last_report_path)

        if not report_path.exists():
            self.status.configure(
                text=f"Report not found: {report_path}"
            )
            return

        if (
            self.report_window is not None and
            self.report_window.winfo_exists()
        ):
            self.report_window.lift()
            self.report_window.focus_force()
            return

        try:
            report_text = report_path.read_text(
                encoding="utf-8"
            )
        except Exception as ex:
            self.status.configure(
                text=f"Could not read report: {ex}"
            )
            return

        self.report_window = ctk.CTkToplevel(self)
        self.report_window.title("Scan Report")
        self.report_window.minsize(700, 500)
        self.report_window.transient(self.winfo_toplevel())
        WindowPlacement.center_window(
            self.report_window,
            900,
            700,
            parent=self
        )

        self.report_window.grid_columnconfigure(0, weight=1)
        self.report_window.grid_rowconfigure(1, weight=1)

        heading = ctk.CTkLabel(
            self.report_window,
            text=str(report_path),
            font=("Segoe UI", 16, "bold")
        )

        heading.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(20, 10)
        )

        textbox = ctk.CTkTextbox(
            self.report_window,
            wrap="none"
        )

        textbox.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 15)
        )

        textbox.insert(
            "1.0",
            report_text
        )

        textbox.configure(
            state="disabled"
        )

        close_button = ctk.CTkButton(
            self.report_window,
            text="Close",
            command=self.close_scan_report
        )

        close_button.grid(
            row=2,
            column=0,
            pady=(0, 20)
        )

        self.report_window.protocol(
            "WM_DELETE_WINDOW",
            self.close_scan_report
        )

        self.report_window.lift()
        self.report_window.focus_force()

    ###########################################################

    def close_scan_report(self):

        if (
            self.report_window is not None and
            self.report_window.winfo_exists()
        ):
            self.report_window.destroy()

        self.report_window = None
        self.winfo_toplevel().lift()
        self.winfo_toplevel().focus_force()
