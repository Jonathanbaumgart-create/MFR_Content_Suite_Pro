import customtkinter as ctk

from media.image_loader import ImageLoader


class PhotoViewer(ctk.CTkToplevel):

    def __init__(self, parent, filename, filepath):

        super().__init__(parent)

        self.title(filename)

        self.geometry("1700x950")
        self.minsize(1200, 800)

        self.transient(parent.winfo_toplevel())
        self.lift()
        self.focus_force()

        self.attributes("-topmost", True)
        self.after(250, lambda: self.attributes("-topmost", False))

        self.filename = filename
        self.filepath = filepath

        self.build_ui()

    ##########################################################

    def build_ui(self):

        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=1)

        self.grid_rowconfigure(0, weight=1)

        #######################################################
        # IMAGE PANEL
        #######################################################

        image_frame = ctk.CTkFrame(self)

        image_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(15, 5),
            pady=15
        )

        title = ctk.CTkLabel(
            image_frame,
            text=self.filename,
            font=("Segoe UI", 22, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        self.image = ImageLoader.load_image(
            self.filepath,
            size=(1200, 800)
        )

        preview = ctk.CTkLabel(
            image_frame,
            image=self.image,
            text=""
        )

        preview.pack(
            expand=True,
            padx=20,
            pady=20
        )

        #######################################################
        # AI PANEL
        #######################################################

        ai = ctk.CTkFrame(
            self,
            width=350
        )

        ai.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=(5, 15),
            pady=15
        )

        ai.grid_propagate(False)

        heading = ctk.CTkLabel(
            ai,
            text="AI Assistant",
            font=("Segoe UI", 22, "bold")
        )

        heading.pack(
            pady=(20, 15)
        )

        self.status = ctk.CTkLabel(
            ai,
            text="Status: Not analyzed"
        )

        self.status.pack(
            pady=10
        )

        self.analyze_button = ctk.CTkButton(
            ai,
            text="Analyze Photo",
            command=self.analyze_photo
        )

        self.analyze_button.pack(
            fill="x",
            padx=20,
            pady=10
        )

        self.facebook_button = ctk.CTkButton(
            ai,
            text="Generate Facebook",
            state="disabled"
        )

        self.facebook_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.instagram_button = ctk.CTkButton(
            ai,
            text="Generate Instagram",
            state="disabled"
        )

        self.instagram_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.both_button = ctk.CTkButton(
            ai,
            text="Generate Both",
            state="disabled"
        )

        self.both_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        ctk.CTkTextbox(
            ai,
            height=420
        ).pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

    ##########################################################

    def analyze_photo(self):

        self.status.configure(
            text="Status: AI coming next..."
        )