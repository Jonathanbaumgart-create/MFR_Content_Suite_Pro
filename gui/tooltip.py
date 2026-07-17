import customtkinter as ctk


class ToolTip:

    def __init__(self, widget, text, delay_ms=450):

        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.after_id = None
        self.window = None

        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    ############################################################

    def schedule(self, _event=None):

        self.hide()
        self.after_id = self.widget.after(
            self.delay_ms,
            self.show
        )

    ############################################################

    def show(self):

        self.after_id = None

        if self.window is not None:
            return

        self.window = ctk.CTkToplevel(self.widget)
        self.window.withdraw()
        self.window.overrideredirect(True)
        label = ctk.CTkLabel(
            self.window,
            text=self.text,
            fg_color="#263245",
            text_color="#f5f7fb",
            corner_radius=6,
            padx=8,
            pady=5
        )
        label.pack()
        self.window.update_idletasks()
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        width = max(160, self.window.winfo_width())
        height = max(32, self.window.winfo_height())
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()
        x = min(max(0, x), max(0, screen_width - width))
        y = min(max(0, y), max(0, screen_height - height - 40))
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.deiconify()

    ############################################################

    def hide(self, _event=None):

        if self.after_id is not None:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
