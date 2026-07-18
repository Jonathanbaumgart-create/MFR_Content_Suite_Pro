from concurrent.futures import ThreadPoolExecutor

import customtkinter as ctk

from gui.photo_viewer import PhotoViewer
from media.image_dimensions import ImageDimensions
from media.preview_image_cache import PreviewImageCache
from services.gallery_analysis_inspector_service import GalleryAnalysisInspectorService


class GalleryAnalysisInspector(ctk.CTkFrame):

    EXPANDED_WIDTH = 420
    COLLAPSED_WIDTH = 128
    PREVIEW_BOX = (360, 220)
    collapsed_state = False

    TEXT_FIELDS = {
        "description": "Effective Description",
        "content_tags": "Topics",
        "primary_activity": "Activity/Event",
        "programs": "Program",
        "campaigns": "Campaign",
        "apparatus": "Apparatus",
        "equipment": "Equipment",
        "people_count": "People Count",
        "notes": "Notes"
    }

    ACTIVE_STATUSES = {
        "Queued",
        "Waiting",
        "Analyzing",
        "Extracting Frames",
        "Analyzing Frames",
        "Summarizing"
    }

    REVIEWABLE_STATUSES = {
        "Review Required",
        "Approved",
        "Corrected",
        "Rejected",
        "Failed",
        "Unsupported Provider",
        "Unanalyzed",
        "Reanalysis Requested"
    }

    def __init__(
        self,
        parent,
        service=None,
        next_callback=None,
        previous_callback=None,
        review_callback=None,
        reanalyze_callback=None
    ):

        super().__init__(
            parent,
            width=self.EXPANDED_WIDTH,
            corner_radius=8
        )
        self.grid_propagate(False)
        self.pack_propagate(False)

        self.service = service or GalleryAnalysisInspectorService()
        self.next_callback = next_callback
        self.previous_callback = previous_callback
        self.review_callback = review_callback
        self.reanalyze_callback = reanalyze_callback
        self.preview_cache = PreviewImageCache(max_items=4, max_dimension=900)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.media_id = None
        self.filename = ""
        self.filepath = ""
        self.media_type = ""
        self.payload = None
        self.load_token = 0
        self.pending_future = None
        self.preview_image = None
        self.correction_mode = False
        self.collapsed = bool(self.__class__.collapsed_state)
        self._destroyed = False
        self.entries = {}
        self.key_binding_id = None
        self.raw_expanded = False
        self.section_frames = []
        self.action_buttons = {}

        self.build()
        self.apply_collapsed_state()
        self.key_binding_id = self.winfo_toplevel().bind(
            "<Key>",
            self.handle_key,
            add="+"
        )

    ############################################################

    def build(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkFrame(
            self,
            fg_color="#20242b",
            corner_radius=8
        )
        self.header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=8,
            pady=(8, 6)
        )
        self.header.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(
            self.header,
            fg_color="transparent"
        )
        title_row.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=8,
            pady=(8, 2)
        )
        title_row.grid_columnconfigure(0, weight=1)

        self.title = ctk.CTkLabel(
            title_row,
            text="AI Analysis",
            font=("Segoe UI", 18, "bold")
        )
        self.title.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.collapse_button = ctk.CTkButton(
            title_row,
            text="Collapse",
            width=90,
            command=self.toggle_collapsed
        )
        self.collapse_button.grid(
            row=0,
            column=1,
            padx=(8, 0)
        )

        self.header_filename = ctk.CTkLabel(
            self.header,
            text="Select a Gallery item",
            anchor="w",
            wraplength=360,
            font=("Segoe UI", 13, "bold")
        )
        self.header_filename.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=8,
            pady=(0, 4)
        )

        self.header_status = ctk.CTkLabel(
            self.header,
            text="",
            anchor="w",
            justify="left",
            wraplength=360,
            font=("Segoe UI", 11)
        )
        self.header_status.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=8,
            pady=(0, 8)
        )

        self.content = ctk.CTkScrollableFrame(
            self,
            fg_color="#171a20"
        )
        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=8,
            pady=(0, 6)
        )
        self.content.grid_columnconfigure(0, weight=1)

        self.preview = ctk.CTkLabel(
            self.content,
            text="Select a Gallery item",
            width=self.PREVIEW_BOX[0],
            height=self.PREVIEW_BOX[1]
        )

        self.footer = ctk.CTkFrame(
            self,
            fg_color="#20242b",
            corner_radius=8
        )
        self.footer.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=8,
            pady=(0, 8)
        )
        self.footer.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.status = ctk.CTkLabel(
            self.footer,
            text="Ready",
            anchor="w",
            wraplength=390,
            font=("Segoe UI", 11)
        )
        self.status.grid(
            row=0,
            column=0,
            columnspan=4,
            sticky="ew",
            padx=8,
            pady=(8, 3)
        )

        self.build_footer_buttons()

    ############################################################

    def build_footer_buttons(self):

        buttons = (
            ("approve", "Approve", self.approve),
            ("correct", "Correct", self.enter_correction_mode),
            ("reject", "Reject", self.reject),
            ("reanalyze", "Reanalyze", self.reanalyze),
            ("previous", "Previous", self.previous_item),
            ("approve_next", "Approve & Next", self.approve_next),
            ("next", "Next", self.next_item),
            ("viewer", "Open Full Viewer", self.open_full_viewer),
            ("save", "Save Correction", self.save_correction),
            ("save_next", "Save & Next", self.save_correction_next),
            ("cancel", "Cancel", self.cancel_correction)
        )

        positions = {
            "approve": (1, 0),
            "correct": (1, 1),
            "reject": (1, 2),
            "reanalyze": (1, 3),
            "previous": (2, 0),
            "approve_next": (2, 1),
            "next": (2, 2),
            "viewer": (2, 3),
            "save": (3, 0),
            "save_next": (3, 1),
            "cancel": (3, 2)
        }

        for key, label, command in buttons:
            button = ctk.CTkButton(
                self.footer,
                text=label,
                command=command,
                height=30,
                width=92
            )
            row, column = positions[key]
            span = 2 if key == "viewer" else 1
            button.grid(
                row=row,
                column=column,
                columnspan=span,
                sticky="ew",
                padx=4,
                pady=3
            )
            self.action_buttons[key] = button

        self.action_buttons["save"].grid_remove()
        self.action_buttons["save_next"].grid_remove()
        self.action_buttons["cancel"].grid_remove()

    ############################################################

    def inspect_media(self, media_id, filename, filepath, media_type="image"):

        self.media_id = int(media_id)
        self.filename = filename or ""
        self.filepath = filepath or ""
        self.media_type = media_type or "image"
        self.load_token += 1
        token = self.load_token
        self.status.configure(text="Loading analysis...")
        self.header_filename.configure(text=self.filename or "Selected media")
        self.header_status.configure(text="Loading selected media...")
        self.clear_content()
        loading_section = self.section("Preview", 0)
        self.preview = ctk.CTkLabel(
            loading_section,
            text="Loading preview...",
            width=self.PREVIEW_BOX[0],
            height=self.PREVIEW_BOX[1]
        )
        self.preview.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=4,
            pady=(4, 8)
        )

        future = self.executor.submit(
            self._load_payload,
            token,
            self.media_id,
            self.filepath,
            self.media_type
        )
        self.pending_future = future
        self.after(
            50,
            lambda: self._poll_load_future(future, token)
        )

    ############################################################

    def _poll_load_future(self, future, token):

        if self._destroyed or token != self.load_token:
            return

        if not future.done():
            self.after(
                50,
                lambda: self._poll_load_future(future, token)
            )
            return

        self._finish_load(future, token)

    def _load_payload(self, token, media_id, filepath, media_type):

        payload = self.service.inspector_payload(media_id)
        preview = self.preview_cache.get(
            media_id,
            filepath,
            is_video=media_type == "video"
        )
        return {
            "token": token,
            "payload": payload,
            "preview": preview
        }

    def _finish_load(self, future, token):

        if self._destroyed or token != self.load_token:
            return

        try:
            result = future.result()
        except Exception as ex:
            self.status.configure(text=f"Inspector load failed: {ex}")
            return

        if result.get("token") != self.load_token:
            return

        self.payload = result["payload"]
        self.render_payload()
        self.render_preview(result.get("preview") or {})
        self.populate_corrections()
        self.status.configure(text="Ready")

    ############################################################

    def clear_content(self):

        for child in self.content.winfo_children():
            child.grid_forget()
            child.destroy()

        self.section_frames = []
        self.entries = {}

    def render_preview(self, entry):

        image = entry.get("image")
        error = entry.get("error")

        if not hasattr(self, "preview") or not self.preview.winfo_exists():
            return

        if error:
            self.preview.configure(
                image=None,
                text=f"Preview unavailable:\n{error}"
            )
            return

        if image is None:
            self.preview.configure(
                image=None,
                text="Preview unavailable"
            )
            return

        self.preview_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=ImageDimensions.fit_size(
                image.size,
                self.PREVIEW_BOX
            )
        )
        self.preview.configure(
            image=self.preview_image,
            text=""
        )

    def render_payload(self):

        self.clear_content()
        display = (self.payload or {}).get("display", {})
        video = (self.payload or {}).get("video", {}) or {}
        media = (self.payload or {}).get("media", {}) or {}

        status = self.readable(display.get("analysis_status"))
        provider = self.readable(display.get("provider")) or "Not analyzed"
        model = display.get("model", "") or ""
        confidence = self.format_confidence(display.get("confidence"))

        self.header_filename.configure(
            text=display.get("filename") or self.filename or "Selected media"
        )
        self.header_status.configure(
            text=(
                f"{self.readable(media.get('media_type') or self.media_type)} | "
                f"{self.readable(display.get('review_state'))} | "
                f"{provider}"
                + (f" / {model}" if model else "")
                + f" | Confidence: {confidence} | Status: {status}"
            )
        )

        row = 0
        preview_section = self.section("Preview", row)
        row += 1
        self.preview = ctk.CTkLabel(
            preview_section,
            text="Loading preview...",
            width=self.PREVIEW_BOX[0],
            height=self.PREVIEW_BOX[1]
        )
        self.preview.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=8,
            pady=8
        )

        self.text_section(
            "Effective Description",
            display.get("effective_description") or "No effective description available.",
            row
        )
        row += 1

        self.raw_section(row)
        row += 1

        self.rows_section(
            "Topic and Activity",
            (
                ("Topics", display.get("topics")),
                ("Activity/Event", display.get("activity")),
                ("Analysis Status", display.get("analysis_status")),
            ),
            row
        )
        row += 1

        self.rows_section(
            "Program/Campaign",
            (
                ("Program/Campaign", display.get("program_campaign")),
                ("Location", display.get("location")),
            ),
            row
        )
        row += 1

        self.rows_section(
            "Apparatus and Equipment",
            (
                ("Apparatus", display.get("apparatus")),
                ("Equipment", display.get("equipment")),
                ("People Count", display.get("people_count")),
            ),
            row
        )
        row += 1

        self.text_section(
            "Filesystem Intelligence",
            display.get("filesystem") or "No filesystem intelligence available.",
            row
        )
        row += 1

        self.text_section(
            "Correction History",
            (
                f"{display.get('human_correction_status', '')}\n"
                f"{display.get('correction_history_summary', '')}"
            ).strip() or "No correction history",
            row
        )
        row += 1

        if video or display.get("video_status"):
            video_status = display.get("video_status") or {}
            self.rows_section(
                "Video Intelligence",
                (
                    ("Status", video_status.get("state")),
                    ("Reason", video_status.get("reason")),
                    ("Duration", self.duration_text(video.get("duration_seconds"))),
                    ("Frames Sampled", video.get("analyzed_frame_count")),
                    ("Reel Score", video.get("reel_potential")),
                    ("Cover Frame", video.get("cover_recommendation")),
                    ("Clip Windows", video.get("clip_recommendations")),
                ),
                row
            )
            row += 1

        self.build_correction_section(row)
        self.update_action_state()

    ############################################################

    def section(self, title, row):

        frame = ctk.CTkFrame(
            self.content,
            fg_color="#20242b",
            corner_radius=8
        )
        frame.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=4,
            pady=(0, 8)
        )
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text=title,
            anchor="w",
            font=("Segoe UI", 13, "bold")
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=8,
            pady=(8, 4)
        )
        self.section_frames.append(frame)
        return frame

    def text_section(self, title, text, row):

        frame = self.section(title, row)
        ctk.CTkLabel(
            frame,
            text=self.readable(text) or "None",
            anchor="w",
            justify="left",
            wraplength=360
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=8,
            pady=(0, 8)
        )
        return frame

    def rows_section(self, title, rows, row):

        frame = self.section(title, row)
        index = 1
        for label, value in rows:
            text = self.format_value(value)
            if not text:
                continue
            ctk.CTkLabel(
                frame,
                text=label,
                anchor="w",
                font=("Segoe UI", 11, "bold"),
                text_color="#b9c7d8"
            ).grid(
                row=index,
                column=0,
                sticky="ew",
                padx=8,
                pady=(2, 0)
            )
            index += 1
            ctk.CTkLabel(
                frame,
                text=text,
                anchor="w",
                justify="left",
                wraplength=360
            ).grid(
                row=index,
                column=0,
                sticky="ew",
                padx=8,
                pady=(0, 5)
            )
            index += 1

        if index == 1:
            ctk.CTkLabel(
                frame,
                text="None",
                anchor="w"
            ).grid(
                row=1,
                column=0,
                sticky="ew",
                padx=8,
                pady=(0, 8)
            )

        return frame

    def raw_section(self, row):

        frame = self.section("Raw AI Description", row)
        self.raw_toggle = ctk.CTkButton(
            frame,
            text="Show Raw AI Description",
            width=170,
            command=self.toggle_raw_description
        )
        self.raw_toggle.grid(
            row=1,
            column=0,
            sticky="w",
            padx=8,
            pady=(0, 8)
        )
        self.raw_text = ctk.CTkLabel(
            frame,
            text=self.readable(
                ((self.payload or {}).get("display", {}) or {}).get(
                    "raw_description"
                )
            ) or "No raw description available.",
            anchor="w",
            justify="left",
            wraplength=360
        )
        if self.raw_expanded:
            self.raw_text.grid(
                row=2,
                column=0,
                sticky="ew",
                padx=8,
                pady=(0, 8)
            )
            self.raw_toggle.configure(text="Hide Raw AI Description")

    def build_correction_section(self, row):

        self.correction_frame = self.section("Inline Correction", row)
        self.correction_frame.grid_columnconfigure(1, weight=1)

        index = 1
        for field, label in self.TEXT_FIELDS.items():
            ctk.CTkLabel(
                self.correction_frame,
                text=label,
                anchor="w",
                font=("Segoe UI", 11, "bold")
            ).grid(
                row=index,
                column=0,
                sticky="w",
                padx=8,
                pady=3
            )
            entry = ctk.CTkEntry(self.correction_frame)
            entry.grid(
                row=index,
                column=1,
                sticky="ew",
                padx=8,
                pady=3
            )
            self.entries[field] = entry
            index += 1

        if not self.correction_mode:
            self.correction_frame.grid_remove()

    ############################################################

    def toggle_raw_description(self):

        self.raw_expanded = not self.raw_expanded
        if self.raw_expanded:
            self.raw_text.grid(
                row=2,
                column=0,
                sticky="ew",
                padx=8,
                pady=(0, 8)
            )
            self.raw_toggle.configure(text="Hide Raw AI Description")
        else:
            self.raw_text.grid_remove()
            self.raw_toggle.configure(text="Show Raw AI Description")

    def populate_corrections(self):

        if not self.entries:
            return

        display = (self.payload or {}).get("display", {})
        values = {
            "description": display.get("effective_description", ""),
            "content_tags": self.format_value(display.get("topics")),
            "primary_activity": self.readable(display.get("activity")),
            "programs": self.readable(display.get("program_campaign")),
            "campaigns": self.readable(display.get("program_campaign")),
            "apparatus": self.format_value(display.get("apparatus")),
            "equipment": self.format_value(display.get("equipment")),
            "people_count": display.get("people_count", 0),
            "notes": ""
        }

        for field, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, str(values.get(field, "")))

    ############################################################

    def approve(self):

        return self._review_action(
            lambda: self.service.approve(self.media_id),
            advance=False
        )

    def approve_next(self):

        return self._review_action(
            lambda: self.service.approve(self.media_id),
            advance=True
        )

    def reject(self):

        return self._review_action(
            lambda: self.service.reject(self.media_id),
            advance=True
        )

    def reanalyze(self):

        return self._review_action(
            lambda: self.service.request_reanalysis(self.media_id),
            advance=False,
            reanalyze=True
        )

    def _review_action(self, action, advance=False, reanalyze=False):

        if not self.media_id:
            return "break"

        if not self.actions_enabled():
            self.status.configure(text="Review actions are disabled while analysis is active.")
            return "break"

        try:
            result = action()
        except Exception as ex:
            self.status.configure(text=f"Action failed: {ex}")
            return "break"

        status = result.get("status", "")
        if self.review_callback:
            self.review_callback(self.media_id, status)

        if reanalyze and self.reanalyze_callback:
            self.reanalyze_callback(self.media_id)

        self.status.configure(text=f"Saved: {self.readable(status)}")

        if advance and self.next_callback:
            self.next_callback()
        else:
            self.inspect_media(
                self.media_id,
                self.filename,
                self.filepath,
                self.media_type
            )

        return "break"

    ############################################################

    def enter_correction_mode(self):

        if not self.actions_enabled():
            self.status.configure(text="Correction is disabled while analysis is active.")
            return "break"

        self.correction_mode = True
        if hasattr(self, "correction_frame"):
            self.correction_frame.grid()
        self.show_correction_buttons()
        self.status.configure(text="Correction mode")
        return "break"

    def cancel_correction(self):

        self.correction_mode = False
        if hasattr(self, "correction_frame"):
            self.correction_frame.grid_remove()
        self.hide_correction_buttons()
        self.populate_corrections()
        self.status.configure(text="Correction cancelled")
        return "break"

    def save_correction(self):

        return self._save_correction(advance=False)

    def save_correction_next(self):

        return self._save_correction(advance=True)

    def _save_correction(self, advance=False):

        if not self.media_id:
            return "break"

        corrections = {
            field: entry.get().strip()
            for field, entry in self.entries.items()
        }
        notes = corrections.get("notes", "")

        try:
            self.service.save_corrections(
                self.media_id,
                corrections,
                notes=notes
            )
        except Exception as ex:
            self.status.configure(text=f"Correction failed: {ex}")
            return "break"

        self.correction_mode = False
        if hasattr(self, "correction_frame"):
            self.correction_frame.grid_remove()
        self.hide_correction_buttons()

        if self.review_callback:
            self.review_callback(self.media_id, "corrected")

        if advance and self.next_callback:
            self.next_callback()
        else:
            self.inspect_media(
                self.media_id,
                self.filename,
                self.filepath,
                self.media_type
            )

        return "break"

    ############################################################

    def previous_item(self):

        if self.previous_callback:
            self.previous_callback()
        return "break"

    def next_item(self):

        if self.next_callback:
            self.next_callback()
        return "break"

    def open_full_viewer(self):

        if not self.media_id:
            return "break"

        PhotoViewer(
            self,
            self.media_id,
            self.filename,
            self.filepath
        )
        return "break"

    ############################################################

    def update_action_state(self):

        active = not self.actions_enabled()
        disabled = "disabled" if active or not self.media_id else "normal"
        review_disabled = "disabled" if active or not self.media_id else "normal"

        for key in ("approve", "correct", "reject", "approve_next"):
            self.action_buttons[key].configure(state=review_disabled)

        self.action_buttons["reanalyze"].configure(
            state="normal" if self.media_id else "disabled"
        )
        self.action_buttons["previous"].configure(
            state="normal" if self.media_id else "disabled"
        )
        self.action_buttons["next"].configure(
            state="normal" if self.media_id else "disabled"
        )
        self.action_buttons["viewer"].configure(
            state="normal" if self.media_id else "disabled"
        )

        if active:
            self.status.configure(
                text="Analysis is active. Review actions unlock when analysis completes."
            )
        else:
            self.status.configure(text="Ready")

    def actions_enabled(self):

        display = (self.payload or {}).get("display", {})
        status = self.readable(display.get("analysis_status"))
        return status not in self.ACTIVE_STATUSES

    def show_correction_buttons(self):

        self.action_buttons["save"].grid()
        self.action_buttons["save_next"].grid()
        self.action_buttons["cancel"].grid(
            row=3,
            column=2,
            columnspan=2,
            sticky="ew",
            padx=4,
            pady=3
        )

    def hide_correction_buttons(self):

        self.action_buttons["save"].grid_remove()
        self.action_buttons["save_next"].grid_remove()
        self.action_buttons["cancel"].grid_remove()

    ############################################################

    def toggle_collapsed(self):

        self.collapsed = not self.collapsed
        self.__class__.collapsed_state = self.collapsed
        self.apply_collapsed_state()

    def apply_collapsed_state(self):

        if self.collapsed:
            self.content.grid_remove()
            self.footer.grid_remove()
            self.header_filename.grid_remove()
            self.header_status.grid_remove()
            self.configure(width=self.COLLAPSED_WIDTH)
            self.collapse_button.configure(text="Expand")
        else:
            self.content.grid()
            self.footer.grid()
            self.header_filename.grid()
            self.header_status.grid()
            self.configure(width=self.EXPANDED_WIDTH)
            self.collapse_button.configure(text="Collapse")

    ############################################################

    def handle_key(self, event):

        if not self.media_id:
            return None

        widget = event.widget
        widget_class = ""
        try:
            widget_class = widget.winfo_class()
        except Exception:
            widget_class = ""

        if widget_class in ("Entry", "Text", "CTkEntry", "CTkTextbox"):
            return None

        key = str(event.keysym or "").lower()

        if key in ("right", "down"):
            return self.next_item()

        if key in ("left", "up"):
            return self.previous_item()

        if key == "space":
            return self.approve_next()

        if key == "a":
            return self.approve()

        if key == "c":
            return self.enter_correction_mode()

        if key == "r":
            return self.reject()

        if key == "n":
            return self.reanalyze()

        if key == "return" and self.correction_mode:
            self.status.configure(text="Use Save controls to submit corrections.")
            return "break"

        if key == "escape":
            if self.correction_mode:
                return self.cancel_correction()
            self.toggle_collapsed()
            return "break"

        return None

    ############################################################

    def format_value(self, value):

        if value is None:
            return ""

        if isinstance(value, dict):
            parts = []
            for key, item in value.items():
                if item in ("", None, [], {}):
                    continue
                parts.append(f"{self.readable(key)}: {self.format_value(item)}")
            return ", ".join(parts)

        if isinstance(value, (list, tuple, set)):
            return ", ".join(
                self.readable(item)
                for item in value
                if self.readable(item)
            )

        return self.readable(value)

    def readable(self, value):

        if value is None:
            return ""

        text = str(value).strip()
        if not text:
            return ""

        text = text.replace("_", " ").replace("-", " ")
        compact = " ".join(text.split())
        labels = {
            "unreviewed real": "Real - Review Required",
            "approved real": "Real - Approved",
            "corrected real": "Real - Corrected",
            "rejected real": "Real - Rejected",
            "review required": "Review Required",
            "mock test data": "Mock/Test Data",
            "not analyzed": "Unanalyzed"
        }
        lower = compact.lower()
        if lower in labels:
            return labels[lower]

        if compact.isupper():
            return compact

        return compact[:1].upper() + compact[1:]

    def format_confidence(self, value):

        try:
            score = float(value or 0)
        except Exception:
            return "Unknown"

        if score <= 1:
            return f"{round(score * 100):.0f}%"

        return f"{round(score):.0f}%"

    def duration_text(self, value):

        try:
            seconds = int(float(value or 0))
        except Exception:
            return ""

        if seconds <= 0:
            return ""

        minutes = seconds // 60
        remainder = seconds % 60
        return f"{minutes}:{remainder:02d}"

    ############################################################

    def destroy(self):

        self._destroyed = True
        self.load_token += 1
        if self.key_binding_id:
            try:
                self.winfo_toplevel().unbind(
                    "<Key>",
                    self.key_binding_id
                )
            except Exception:
                pass
        self.preview_cache.clear()
        self.executor.shutdown(wait=False, cancel_futures=True)
        super().destroy()
