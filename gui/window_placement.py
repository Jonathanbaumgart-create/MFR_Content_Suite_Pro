class WindowPlacement:

    @staticmethod
    def center_window(window, width=None, height=None, parent=None):

        try:
            if width is None or height is None:
                window.update_idletasks()
                width, height = WindowPlacement._geometry_size(window)

            width = max(1, int(width or window.winfo_width() or 900))
            height = max(1, int(height or window.winfo_height() or 700))
            screen_width = max(1, window.winfo_screenwidth())
            screen_height = max(1, window.winfo_screenheight())
            work_height = max(1, screen_height - WindowPlacement.taskbar_allowance(screen_height))

            if parent is not None:
                try:
                    parent.update_idletasks()
                    parent_x = parent.winfo_rootx()
                    parent_y = parent.winfo_rooty()
                    parent_width = max(1, parent.winfo_width())
                    parent_height = max(1, parent.winfo_height())
                    x = parent_x + (parent_width - width) // 2
                    y = parent_y + (parent_height - height) // 2
                except Exception:
                    x = (screen_width - width) // 2
                    y = (work_height - height) // 2
            else:
                x = (screen_width - width) // 2
                y = (work_height - height) // 2

            x = min(max(0, x), max(0, screen_width - width))
            y = min(max(0, y), max(0, work_height - height))
            geometry = f"{width}x{height}+{x}+{y}"
            try:
                window.update()
            except Exception:
                pass
            try:
                window.wm_geometry(geometry)
            except Exception:
                window.geometry(geometry)
            window.update_idletasks()
            current_width, current_height = WindowPlacement._geometry_size(window)
            if current_width != width or current_height != height:
                try:
                    window.update()
                except Exception:
                    pass
        except Exception:
            if width and height:
                window.geometry(f"{int(width)}x{int(height)}")

    ############################################################

    @staticmethod
    def center_existing(window, parent=None):

        width, height = WindowPlacement._geometry_size(window)
        WindowPlacement.center_window(
            window,
            width=width,
            height=height,
            parent=parent
        )

    ############################################################

    @staticmethod
    def _geometry_size(window):

        geometry = str(window.geometry() or "")
        size = geometry.split("+", 1)[0]

        if "x" in size:
            width, height = size.split("x", 1)
            try:
                return int(width), int(height)
            except Exception:
                pass

        return window.winfo_width(), window.winfo_height()

    ############################################################

    @staticmethod
    def taskbar_allowance(screen_height):

        return max(40, min(96, int(screen_height * 0.055)))
