import customtkinter as ctk

from gui.ai_dashboard_page import AIDashboardPage
from gui.dashboard_page import DashboardPage
from gui.gallery_page import GalleryPage
from gui.scan_page import ScanPage


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("MFR Content Suite Professional")
        self.geometry("1600x900")
        self.minsize(1200, 800)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.current_page = None

        self.build_ui()

    ##########################################################

    def build_ui(self):

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ######################################################
        # Sidebar
        ######################################################

        self.sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="ns"
        )

        title = ctk.CTkLabel(
            self.sidebar,
            text="MFR Content Suite",
            font=("Segoe UI", 24, "bold")
        )

        title.pack(
            pady=(25, 5)
        )

        version = ctk.CTkLabel(
            self.sidebar,
            text="Professional v1",
            font=("Segoe UI", 14)
        )

        version.pack(
            pady=(0, 25)
        )

        ######################################################
        # Workspace
        ######################################################

        self.workspace = ctk.CTkFrame(
            self,
            corner_radius=0
        )

        self.workspace.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.workspace.grid_rowconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(0, weight=1)

        ######################################################
        # Navigation
        ######################################################

        navigation = [

            ("Dashboard", self.show_dashboard),

            ("Scanner", self.show_scanner),

            ("Gallery", self.show_gallery),

            ("Videos", self.not_implemented),

            ("Search", self.not_implemented),

            ("Collections", self.not_implemented),

            ("AI", self.show_ai_dashboard),

            ("Analytics", self.not_implemented),

            ("Settings", self.not_implemented)

        ]

        for text, command in navigation:

            button = ctk.CTkButton(
                self.sidebar,
                text=text,
                height=42,
                command=command
            )

            button.pack(
                fill="x",
                padx=15,
                pady=5
            )

        self.show_dashboard()

    ##########################################################

    def clear_page(self):

        if self.current_page is not None:

            self.current_page.destroy()

            self.current_page = None

    ##########################################################

    def show_dashboard(self):

        self.clear_page()

        self.current_page = DashboardPage(
            self.workspace
        )

        self.current_page.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=25,
            pady=25
        )

    ##########################################################

    def show_gallery(self):

        self.clear_page()

        self.current_page = GalleryPage(
            self.workspace
        )

        self.current_page.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=25,
            pady=25
        )

    ##########################################################

    def show_scanner(self):

        self.clear_page()

        self.current_page = ScanPage(
            self.workspace
        )

        self.current_page.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=25,
            pady=25
        )

    ##########################################################

    def show_ai_dashboard(self):

        self.clear_page()

        self.current_page = AIDashboardPage(
            self.workspace
        )

        self.current_page.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=25,
            pady=25
        )

    ##########################################################

    def not_implemented(self):

        self.clear_page()

        frame = ctk.CTkFrame(self.workspace)

        frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=25,
            pady=25
        )

        label = ctk.CTkLabel(
            frame,
            text="Coming Soon",
            font=("Segoe UI", 30, "bold")
        )

        label.pack(
            expand=True
        )

        self.current_page = frame
