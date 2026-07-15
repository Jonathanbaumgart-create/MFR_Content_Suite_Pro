import os
import subprocess
import time

import customtkinter as ctk

from media.image_dimensions import ImageDimensions


class PackageMediaPanel(ctk.CTkFrame):

    PRIMARY_SIZE = (260, 170)
    SUPPORT_SIZE = (122, 88)
    MAX_SUPPORTING = 8

    def __init__(
        self,
        parent,
        media_package,
        thumbnail_service,
        open_callback=None,
        reveal_callback=None,
        copy_callback=None,
        replace_callback=None,
        exclude_callback=None,
        preview_callback=None,
        compact=False
    ):

        super().__init__(
            parent,
            corner_radius=8
        )
        self.media_package = media_package or {}
        self.thumbnail_service = thumbnail_service
        self.open_callback = open_callback
        self.reveal_callback = reveal_callback
        self.copy_callback = copy_callback
        self.replace_callback = replace_callback
        self.exclude_callback = exclude_callback
        self.preview_callback = preview_callback
        self.compact = compact
        self.images = {}
        self.metrics = {
            "initial_render_seconds": 0,
            "primary_thumbnail_seconds": 0,
            "supporting_thumbnail_seconds": 0,
            "thumbnail_count": 0
        }

        started = time.perf_counter()
        self.build()
        self.metrics["initial_render_seconds"] = round(
            time.perf_counter() - started,
            4
        )

    ############################################################

    def build(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        primary_photo = (
            self.media_package.get("primary_photo")
            or self.media_package.get("best_photo")
            or {}
        )
        primary_video = (
            self.media_package.get("primary_video")
            or self.media_package.get("best_video")
            or {}
        )

        if self.compact:
            asset = primary_photo or primary_video
            self._compact_card(asset)
            return

        self._primary_card(
            "Primary Hero Photo",
            primary_photo,
            row=0,
            column=0,
            role="primary_photo"
        )
        self._primary_card(
            "Primary Video",
            primary_video,
            row=0,
            column=1,
            role="primary_video"
        )
        self._supporting_strip(
            "Supporting Photos",
            (
                self.media_package.get("gallery_photos")
                or self.media_package.get("supporting_photos")
                or []
            ),
            row=1
        )
        self._supporting_strip(
            "Supporting Videos",
            (
                self.media_package.get("gallery_videos")
                or self.media_package.get("supporting_videos")
                or []
            ),
            row=2
        )

    ############################################################

    def _compact_card(self, asset):

        if not asset:
            ctk.CTkLabel(
                self,
                text="No asset selected.",
                text_color="#a8a8a8"
            ).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
            return

        label = self._thumbnail_label(
            self,
            asset,
            self.SUPPORT_SIZE,
            row=0,
            column=0
        )
        label.bind(
            "<Button-1>",
            lambda _event, item=asset: self._preview(item)
        )
        ctk.CTkLabel(
            self,
            text=self._short_asset_text(asset),
            font=("Segoe UI", 10),
            wraplength=150,
            justify="center"
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

    ############################################################

    def _primary_card(self, title, asset, row, column, role):

        card = ctk.CTkFrame(self, corner_radius=6)
        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=8,
            pady=8
        )
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        if not asset:
            ctk.CTkLabel(
                card,
                text="No asset selected.",
                text_color="#a8a8a8"
            ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
            return

        image_label = self._thumbnail_label(
            card,
            asset,
            self.PRIMARY_SIZE,
            row=1,
            column=0
        )
        image_label.bind(
            "<Button-1>",
            lambda _event, item=asset: self._preview(item)
        )

        ctk.CTkLabel(
            card,
            text=self._asset_details(asset, include_reason=True),
            wraplength=310,
            justify="left"
        ).grid(row=2, column=0, sticky="ew", padx=10, pady=(6, 6))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))

        self._button(
            actions,
            "Open",
            lambda item=asset: self._open(item),
            column=0
        )
        self._button(
            actions,
            "Reveal",
            lambda item=asset: self._reveal(item),
            column=1
        )
        self._button(
            actions,
            "Copy Path",
            lambda item=asset: self._copy(item),
            column=2
        )
        self._button(
            actions,
            "Replace",
            lambda item=asset, item_role=role: self._replace(item, item_role),
            column=0,
            row=1
        )
        self._button(
            actions,
            "Unsuitable",
            lambda item=asset: self._exclude(item),
            column=1,
            row=1
        )

    ############################################################

    def _supporting_strip(self, title, assets, row):

        frame = ctk.CTkFrame(self, corner_radius=6)
        frame.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=8,
            pady=(0, 8)
        )
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text=title,
            font=("Segoe UI", 13, "bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        strip = ctk.CTkScrollableFrame(
            frame,
            height=148,
            orientation="horizontal"
        )
        strip.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        bounded = list(assets or [])[:self.MAX_SUPPORTING]

        if not bounded:
            ctk.CTkLabel(
                strip,
                text="No supporting assets selected.",
                text_color="#a8a8a8"
            ).grid(row=0, column=0, padx=8, pady=8)
            return

        for column, asset in enumerate(bounded):
            self._supporting_card(strip, asset, column)

    def _supporting_card(self, parent, asset, column):

        card = ctk.CTkFrame(parent, width=150, height=136, corner_radius=6)
        card.grid(row=0, column=column, padx=6, pady=6)
        card.grid_propagate(False)

        label = self._thumbnail_label(
            card,
            asset,
            self.SUPPORT_SIZE,
            row=0,
            column=0
        )
        label.bind(
            "<Button-1>",
            lambda _event, item=asset: self._preview(item)
        )
        ctk.CTkLabel(
            card,
            text=self._short_asset_text(asset),
            font=("Segoe UI", 10),
            wraplength=132,
            justify="center"
        ).grid(row=1, column=0, padx=6, pady=(3, 0))
        ctk.CTkButton(
            card,
            text="Exclude",
            width=74,
            height=24,
            command=lambda item=asset: self._exclude(item)
        ).grid(row=2, column=0, padx=6, pady=(3, 5))

    ############################################################

    def _thumbnail_label(self, parent, asset, size, row, column):

        label = ctk.CTkLabel(
            parent,
            text=self._placeholder_text(asset),
            width=size[0],
            height=size[1],
            fg_color="#1f1f1f",
            corner_radius=6
        )
        label.grid(
            row=row,
            column=column,
            padx=10,
            pady=(4, 4)
        )
        self.metrics["thumbnail_count"] += 1
        self._load_thumbnail(asset, label, size)
        return label

    def _load_thumbnail(self, asset, label, size):

        path = asset.get("path", "")
        requested_at = time.perf_counter()

        if not path or not self.thumbnail_service:
            label.configure(text="No Preview")
            return

        def ready(media_path, image):
            try:
                self.after(
                    0,
                    lambda: self._show_thumbnail(
                        label,
                        image,
                        size,
                        requested_at,
                        asset
                    )
                )
            except Exception:
                pass

        self.thumbnail_service.load_thumbnail(
            path,
            ready
        )

    def _show_thumbnail(self, label, image, size, requested_at, asset):

        try:
            if not label.winfo_exists():
                return
        except Exception:
            return

        elapsed = round(time.perf_counter() - requested_at, 4)

        if asset.get("selected_as", "").startswith("primary"):
            self.metrics["primary_thumbnail_seconds"] = elapsed
        else:
            self.metrics["supporting_thumbnail_seconds"] = max(
                self.metrics.get("supporting_thumbnail_seconds", 0),
                elapsed
            )

        if image is None:
            label.configure(text="No Preview", image=None)
            return

        fitted = ImageDimensions.fit_size(
            image.size,
            size
        )
        ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=fitted
        )
        self.images[asset.get("media_id")] = ctk_image
        label.configure(
            image=ctk_image,
            text=""
        )

    ############################################################

    def _asset_details(self, asset, include_reason=False):

        lines = [
            asset.get("filename", ""),
            (
                f"{self._badge(asset)} | trust {asset.get('trust_state', '')} | "
                f"score {asset.get('media_score', asset.get('communications_score', 0))}"
            ),
            (
                f"story relevance {asset.get('topic_relevance_score', 0)} | "
                f"platform fit {asset.get('platform_fit_score', 0)}"
            )
        ]

        if asset.get("media_type") == "video":
            lines.append(
                f"duration {self._duration(asset)} | orientation {asset.get('orientation', 'unknown')}"
            )

        if include_reason:
            lines.append(asset.get("why_selected", ""))

        return "\n".join(line for line in lines if line)

    def _short_asset_text(self, asset):

        return "\n".join(
            line
            for line in (
                self._badge(asset),
                asset.get("filename", ""),
                asset.get("trust_state", ""),
                f"score {asset.get('media_score', 0)}"
            )
            if line
        )

    def _badge(self, asset):

        media_type = str(asset.get("media_type") or "media").upper()
        role = str(asset.get("selected_as") or "").replace("_", " ").title()

        if media_type == "VIDEO":
            duration = self._duration(asset)
            return f"VIDEO {duration} {role}".strip()

        return f"PHOTO {role}".strip()

    def _duration(self, asset):

        seconds = int(float(asset.get("duration_seconds") or 0))

        if seconds <= 0:
            return ""

        return f"{seconds // 60}:{seconds % 60:02d}"

    def _placeholder_text(self, asset):

        if asset.get("media_type") == "video":
            return "Loading video thumbnail..."

        return "Loading thumbnail..."

    ############################################################

    def _button(self, parent, text, command, column=0, row=0):

        ctk.CTkButton(
            parent,
            text=text,
            width=78,
            height=26,
            command=command
        ).grid(row=row, column=column, sticky="w", padx=(0, 6), pady=(0, 5))

    def _open(self, asset):

        if self.open_callback:
            self.open_callback(asset)

    def _reveal(self, asset):

        if self.reveal_callback:
            self.reveal_callback(asset)
            return

        path = asset.get("path", "")

        if path and os.path.exists(path):
            subprocess.Popen(
                ["explorer", "/select,", path]
            )

    def _copy(self, asset):

        if self.copy_callback:
            self.copy_callback(asset)

    def _replace(self, asset, role):

        if self.replace_callback:
            self.replace_callback(asset, role)

    def _exclude(self, asset):

        if self.exclude_callback:
            self.exclude_callback(asset)

    def _preview(self, asset):

        if self.preview_callback:
            self.preview_callback(asset)
