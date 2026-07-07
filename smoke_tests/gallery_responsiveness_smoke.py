import time
from pathlib import Path
import sys

import customtkinter as ctk


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui.main_window import MainWindow


def main():

    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = MainWindow()

    try:
        app.update()
        app.show_gallery()

        start = time.time()
        state = {
            "last": start,
            "max_gap": 0,
            "ticks": 0
        }

        def heartbeat():
            now = time.time()
            state["max_gap"] = max(
                state["max_gap"],
                now - state["last"]
            )
            state["last"] = now
            state["ticks"] += 1
            app.after(
                20,
                heartbeat
            )

        app.after(
            20,
            heartbeat
        )
        app.after(
            4000,
            app.quit
        )
        app.mainloop()

        ticks = state["ticks"]
        max_gap = state["max_gap"]

        assert ticks > 20, ticks
        assert max_gap < 1.0, max_gap

    finally:
        app.destroy()

    print(
        f"gallery responsiveness smoke passed ticks={ticks} "
        f"max_gap={max_gap:.3f}s"
    )


if __name__ == "__main__":
    main()
