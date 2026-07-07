import customtkinter as ctk


class DashboardPage(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent)

        self.build_page()

    def build_page(self):

        title = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=("Segoe UI", 30, "bold")
        )

        title.pack(anchor="w", pady=(0, 5))

        subtitle = ctk.CTkLabel(
            self,
            text="Welcome to MFR Content Suite Professional",
            font=("Segoe UI", 16)
        )

        subtitle.pack(anchor="w", pady=(0, 25))

        self.create_cards()

    def create_cards(self):

        container = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        container.pack(fill="x")

        for i in range(4):
            container.grid_columnconfigure(i, weight=1)

        cards = [

            ("Photos", "0"),
            ("Videos", "0"),
            ("Collections", "0"),
            ("AI Processed", "0")

        ]

        for column, (title, value) in enumerate(cards):

            card = ctk.CTkFrame(
                container,
                height=140
            )

            card.grid(
                row=0,
                column=column,
                padx=10,
                sticky="nsew"
            )

            heading = ctk.CTkLabel(
                card,
                text=title,
                font=("Segoe UI", 18, "bold")
            )

            heading.pack(pady=(20, 5))

            count = ctk.CTkLabel(
                card,
                text=value,
                font=("Segoe UI", 42)
            )

            count.pack()