import customtkinter as ctk

from media.image_loader import ImageLoader
from services.brain_service import BrainService
from services.editorial_comparison_service import EditorialComparisonService
from services.human_feedback_service import HumanFeedbackService
from services.time_service import TimeService


class PhotoViewer(ctk.CTkToplevel):

    def __init__(self, parent, media_id, filename, filepath):

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
        self.media_id = media_id
        self.parent_window = parent
        self.brain = BrainService()
        self.feedback = HumanFeedbackService()
        self.editorial = EditorialComparisonService()
        self.analysis = None
        self.intelligence = None
        self.fire_service_intelligence = None
        self.effective_intelligence = None

        self.build_ui()
        self.load_analysis()

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
            pady=(20, 8)
        )

        self.mock_notice = ctk.CTkLabel(
            ai,
            text="",
            text_color="#f5c542",
            wraplength=300
        )

        self.mock_notice.pack(
            padx=20,
            pady=(0, 8)
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

        self.improve_button = ctk.CTkButton(
            ai,
            text="Improve Analysis",
            command=self.open_correction_dialog
        )

        self.improve_button.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.content_director_button = ctk.CTkButton(
            ai,
            text="Open in Content Director",
            command=self.open_content_director
        )

        self.content_director_button.pack(
            fill="x",
            padx=20,
            pady=5
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

        self.analysis_text = ctk.CTkTextbox(
            ai,
            height=420
        )

        self.analysis_text.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.analysis_text.configure(state="disabled")
        self.update_mock_notice()

    ##########################################################

    def analyze_photo(self):

        self.analyze_button.configure(
            state="disabled"
        )

        self.status.configure(
            text="Status: Analyzing..."
        )

        self.brain.analyze_photo(
            self.media_id,
            self.filepath,
            force=self.analysis is not None,
            callback=self.analysis_complete,
            error_callback=self.analysis_failed,
            progress_callback=self.analysis_progress
        )

    ##########################################################

    def load_analysis(self):

        analysis = self.brain.get_analysis(self.media_id)

        if analysis is None:
            return

        self.show_analysis(analysis)

    ##########################################################

    def analysis_complete(self, analysis):

        self.after(
            0,
            lambda: self.show_analysis(analysis)
        )

    ##########################################################

    def analysis_failed(self, error):

        self.after(
            0,
            lambda: self.show_error(error)
        )

    ##########################################################

    def analysis_progress(self, progress):

        status = progress.get("status", "")
        queued = progress.get("queued", 0)
        running = progress.get("running", 0)

        self.after(
            0,
            lambda: self.status.configure(
                text=f"Status: {status} ({queued} queued, {running} running)"
            )
        )

    ##########################################################

    def show_analysis(self, analysis):

        self.analysis = analysis
        self.effective_intelligence = self.brain.get_effective_intelligence(
            self.media_id
        )
        self.intelligence = self.effective_intelligence.get(
            "media_intelligence"
        )
        self.fire_service_intelligence = (
            self.effective_intelligence.get("fire_service_intelligence")
        )
        self.update_mock_notice(analysis)

        failure = analysis.get("failure_reason", "")

        if failure:
            self.show_provider_failure(analysis)
            return

        self.status.configure(
            text="Status: Analyzed"
        )

        self.analyze_button.configure(
            state="normal",
            text="Analyze Again"
        )

        self.facebook_button.configure(state="normal")
        self.instagram_button.configure(state="normal")
        self.both_button.configure(state="normal")

        lines = [
            analysis.get("description", ""),
            "",
            f"Scene: {analysis.get('scene_type', '')}",
            f"Activity: {analysis.get('activity', '')}",
            f"People: {analysis.get('people_count', 0)}",
            "",
            "Apparatus: " + self.format_list(analysis.get("apparatus")),
            "Equipment: " + self.format_list(analysis.get("equipment")),
            "Keywords: " + self.format_list(analysis.get("keywords")),
            "",
            f"Community Score: {analysis.get('community_score', 0)}",
            f"Recruitment Score: {analysis.get('recruitment_score', 0)}",
            f"Education Score: {analysis.get('education_score', 0)}",
            f"Technical Score: {analysis.get('technical_score', 0)}",
            f"Overall Score: {analysis.get('overall_score', 0)}",
            "",
            self.analysis_provider_label(analysis),
            f"Model: {analysis.get('model', '')}",
            f"Duration: {analysis.get('analysis_duration', 0):.2f}s",
            f"Retries: {analysis.get('retry_count', 0)}",
            f"Failure: {analysis.get('failure_reason', '')}",
            (
                "Analyzed: " +
                self.local_time(
                    analysis.get("last_analyzed") or
                    analysis.get("analyzed_at", "")
                )
            )
        ]

        intelligence_lines = self.intelligence_lines()

        if intelligence_lines:
            lines.extend(
                [
                    "",
                    "Media Intelligence"
                ] + intelligence_lines
            )

        communications_lines = self.communications_intelligence_lines()

        if communications_lines:
            lines.extend(
                [
                    "",
                    "Communications Intelligence"
                ] + communications_lines
            )

        fire_service_lines = self.fire_service_intelligence_lines()

        if fire_service_lines:
            lines.extend(
                [
                    "",
                    "Fire Service Intelligence"
                ] + fire_service_lines
            )

        correction_lines = self.correction_history_lines()

        if correction_lines:
            lines.extend(
                [
                    "",
                    "Human Corrections"
                ] + correction_lines
            )

        editorial_lines = self.editorial_strategy_lines()

        if editorial_lines:
            lines.extend(
                [
                    "",
                    "Editorial Strategies"
                ] + editorial_lines
            )

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", "\n".join(lines))
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def open_correction_dialog(self):

        CorrectionDialog(
            self,
            self.media_id,
            self.filename,
            self.feedback,
            on_saved=self.load_analysis,
            open_media_callback=self.open_suggested_media
        )

    ##########################################################

    def open_suggested_media(self, item):

        PhotoViewer(
            self,
            item["id"],
            item["filename"],
            item["path"]
        )

    ##########################################################

    def open_content_director(self):

        root = self.parent_window.winfo_toplevel()

        if hasattr(root, "show_content_director"):
            root.show_content_director()
            self.destroy()
            return

        if hasattr(root, "show_page"):
            root.show_page("content_director")
            self.destroy()

    ##########################################################

    def show_error(self, error):

        self.update_mock_notice()

        self.status.configure(
            text="Status: Provider failure"
        )

        self.analyze_button.configure(
            state="normal"
        )

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert(
            "1.0",
            f"Provider failure:\n{error}"
        )
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def show_provider_failure(self, analysis):

        self.update_mock_notice(analysis)

        self.status.configure(
            text="Status: Provider failure"
        )

        self.analyze_button.configure(
            state="normal",
            text="Analyze Again"
        )

        lines = [
            "Provider failure",
            "",
            analysis.get("failure_reason", ""),
            "",
            self.analysis_provider_label(analysis),
            f"Model: {analysis.get('model', '')}",
            f"Duration: {analysis.get('analysis_duration', 0):.2f}s",
            f"Retries: {analysis.get('retry_count', 0)}",
            (
                "Last Attempt: " +
                self.local_time(
                    analysis.get("last_analyzed") or
                    analysis.get("analyzed_at", "")
                )
            )
        ]

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", "\n".join(lines))
        self.analysis_text.configure(state="disabled")

    ##########################################################

    def format_list(self, value):

        if not value:
            return "None"

        return ", ".join(str(item) for item in value)

    ##########################################################

    def format_label(self, value):

        return str(value or "").replace(
            "_",
            " "
        ).title()

    ##########################################################

    def update_mock_notice(self, analysis=None):

        provider = ""
        model = ""
        description = ""

        if not analysis:
            self.mock_notice.configure(
                text=""
            )
            return

        provider = analysis.get("provider", "")
        model = analysis.get("model", "")
        description = analysis.get("description", "")

        if (
            provider == "mock" or
            model.startswith("mock") or
            description.startswith("MOCK TEST ANALYSIS")
        ):
            self.mock_notice.configure(
                text="Mock provider active - test data only"
            )
        else:
            self.mock_notice.configure(
                text=""
            )

    ##########################################################

    def analysis_provider_label(self, analysis):

        provider = analysis.get("provider", "")
        model = analysis.get("model", "")
        description = analysis.get("description", "")

        if (
            provider == "mock" or
            model.startswith("mock") or
            description.startswith("MOCK TEST ANALYSIS")
        ):
            return "Analysis provider: mock - test data"

        if provider:
            return f"Analysis provider: {provider}"

        return "Analysis provider: unknown"

    ##########################################################

    def local_time(self, value):

        return TimeService.format_local(value) or str(value or "")

    ##########################################################

    def intelligence_lines(self):

        if not self.intelligence:
            return []

        top_tags = (
            self.intelligence.get("content_tags") or []
        )[:8]

        return [
            f"Scene: {self.intelligence.get('normalized_scene', '')}",
            f"Incident: {self.intelligence.get('incident_type', '')}",
            f"Activity: {self.intelligence.get('primary_activity', '')}",
            "Top Tags: " + self.format_list(top_tags),
            (
                "Recommended Uses: " +
                self.format_list(
                    self.intelligence.get("recommended_uses")
                )
            )
        ]

    ##########################################################

    def communications_intelligence_lines(self):

        if not self.intelligence:
            return []

        if not self.intelligence.get("communications_score"):
            return []

        categories = self.intelligence.get("communications_category_scores") or {}
        platforms = self.intelligence.get("platform_suitability") or {}
        category_lines = [
            f"{self.format_label(key)}: {value}"
            for key, value in sorted(
                categories.items(),
                key=lambda item: item[1],
                reverse=True
            )[:6]
        ]
        platform_lines = [
            f"{self.format_label(key)}: {value}"
            for key, value in sorted(
                platforms.items(),
                key=lambda item: item[1],
                reverse=True
            )
        ]

        return [
            f"Overall Score: {self.intelligence.get('communications_score', 0)}",
            "Category Breakdown: " + self.format_list(category_lines),
            (
                "Suggested Campaigns: " +
                self.format_list(self.intelligence.get("suggested_campaigns"))
            ),
            (
                "Suggested Platforms: " +
                self.format_list(platform_lines)
            ),
            (
                "Suggested Audience: " +
                self.format_list(self.intelligence.get("suggested_audience"))
            ),
            (
                "Suggested Time of Year: " +
                str(self.intelligence.get("suggested_time_of_year", ""))
            ),
            (
                "Reasoning: " +
                self.format_list(self.intelligence.get("communications_reasoning"))
            )
        ]

    ##########################################################

    def fire_service_intelligence_lines(self):

        fire_service = getattr(
            self,
            "fire_service_intelligence",
            None
        )

        if not fire_service:
            return []

        personnel = fire_service.get("personnel") or {}

        return [
            f"Incident: {fire_service.get('incident_classification', '')}",
            f"Activity: {fire_service.get('operational_activity', '')}",
            f"Operational Context: {fire_service.get('operational_context', '')}",
            (
                "Operational Skills: " +
                self.format_list(fire_service.get("operational_skills"))
            ),
            (
                "Communications Intent: " +
                self.format_list(fire_service.get("communications_intent"))
            ),
            f"Confidence: {fire_service.get('operational_confidence', 0)}",
            (
                "Personnel: " +
                f"firefighters {fire_service.get('firefighter_count', 0)}, " +
                f"civilians {fire_service.get('civilian_count', 0)}, " +
                f"group {fire_service.get('group_size', '')}, " +
                f"officer {'yes' if fire_service.get('officer_presence') else 'unknown'}, " +
                f"children {'yes' if fire_service.get('children_present') else 'unknown'}"
            ),
            "PPE: " + self.format_list(fire_service.get("ppe")),
            "Equipment: " + self.format_list(fire_service.get("equipment")),
            "Apparatus: " + self.format_list(fire_service.get("apparatus")),
            (
                "Communications Uses: " +
                self.format_list(fire_service.get("communications_uses"))
            ),
            (
                "Reasoning: " +
                self.format_list(
                    (
                        fire_service.get("operational_reasoning") or
                        fire_service.get("reasoning")
                    )
                )
            ),
            (
                "Evidence: " +
                self.format_list(
                    self.fire_reasoning_evidence_lines(
                        fire_service.get("reasoning_evidence")
                    )
                )
            )
        ]

    ##########################################################

    def fire_reasoning_evidence_lines(self, evidence):

        lines = []

        for item in evidence or []:

            if isinstance(item, dict):
                reason = item.get(
                    "reason",
                    item.get("relationship", "")
                )
                evidence = item.get(
                    "evidence",
                    item.get("entity", "")
                )
                lines.append(
                    (
                        f"{item.get('confidence', 0)} - "
                        f"{reason}: "
                        f"{evidence}"
                    )
                )
            else:
                lines.append(str(item))

        return lines

    ##########################################################

    def correction_history_lines(self):

        if not self.effective_intelligence:
            return []

        lines = []
        corrections = self.effective_intelligence.get("corrections") or []
        history = self.effective_intelligence.get("correction_history") or []

        if corrections:
            lines.append(
                f"Active corrections: {len(corrections)}"
            )

        for row in history[:8]:
            lines.append(
                (
                    f"{self.local_time(row.get('created_at', ''))} | "
                    f"{row.get('correction_source', '')} | "
                    f"{row.get('field_name', '')} | "
                    f"{self.format_value(row.get('previous_value'))} -> "
                    f"{self.format_value(row.get('new_value'))}"
                )
            )

        return lines

    ##########################################################

    def editorial_strategy_lines(self):

        try:
            comparison = self.editorial.latest(
                self.media_id
            )

        except Exception:
            return []

        if not comparison:
            return []

        best = comparison.get("recommended_strategy") or {}
        alternatives = comparison.get("alternative_strategies") or []

        if not best:
            return []

        lines = [
            (
                "Top Strategy: " +
                f"{best.get('title', '')} "
                f"({best.get('confidence', 0)}%)"
            ),
            (
                "Alternatives: " +
                self.format_list(
                    [
                        item.get("title", "")
                        for item in alternatives[:2]
                    ]
                )
            ),
            f"Confidence: {comparison.get('confidence', 0)}",
            "Why: " + (
                comparison.get("debate_summary") or
                comparison.get("comparison_summary", "")
            )
        ]

        return lines

    ##########################################################

    def format_value(self, value):

        if isinstance(value, list):
            return self.format_list(value)

        return str(value or "")


class CorrectionDialog(ctk.CTkToplevel):

    FIELD_LABELS = {
        "people_count": "People Count",
        "incident_classification": "Incident",
        "primary_activity": "Activity",
        "operational_context": "Operational Context",
        "ppe": "PPE",
        "equipment": "Equipment",
        "apparatus": "Apparatus",
        "operational_skills": "Operational Skills",
        "communications_uses": "Communications Uses",
        "campaigns": "Campaigns",
        "notes": "Notes"
    }

    def __init__(
        self,
        parent,
        media_id,
        filename,
        feedback_service,
        on_saved=None,
        open_media_callback=None
    ):

        super().__init__(parent)

        self.title(f"Improve Analysis - {filename}")
        self.geometry("900x760")
        self.transient(parent.winfo_toplevel())
        self.lift()

        self.media_id = media_id
        self.feedback = feedback_service
        self.on_saved = on_saved
        self.open_media_callback = open_media_callback
        self.effective = self.feedback.effective_media_intelligence(media_id)
        self.entries = {}
        self.original_values = {}

        self.build_ui()

    ##########################################################

    def build_ui(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="Improve Analysis",
            font=("Segoe UI", 24, "bold")
        )
        header.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 8)
        )

        body = ctk.CTkScrollableFrame(self)
        body.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 12)
        )
        body.grid_columnconfigure(1, weight=1)

        row = 0

        for field, label in self.FIELD_LABELS.items():
            current = self.effective.get(field)
            inferred = self.feedback.inferred_value(
                self.media_id,
                field
            )
            self.original_values[field] = current

            ctk.CTkLabel(
                body,
                text=label
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=10,
                pady=(8, 2)
            )

            entry = ctk.CTkEntry(body)
            entry.insert(
                0,
                self.value_to_text(current)
            )
            entry.grid(
                row=row,
                column=1,
                sticky="ew",
                padx=10,
                pady=(8, 2)
            )
            self.entries[field] = entry

            ctk.CTkLabel(
                body,
                text="Inferred: " + self.value_to_text(inferred),
                text_color="#a8b3c7",
                wraplength=760,
                justify="left"
            ).grid(
                row=row + 1,
                column=1,
                sticky="w",
                padx=10,
                pady=(0, 6)
            )

            row += 2

        selector = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        selector.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 8)
        )
        selector.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            selector,
            text="Selected Field"
        ).grid(
            row=0,
            column=0,
            padx=(0, 8)
        )

        self.selected_field = ctk.StringVar(value="people_count")
        field_menu = ctk.CTkOptionMenu(
            selector,
            values=list(self.FIELD_LABELS.keys()),
            variable=self.selected_field
        )
        field_menu.grid(
            row=0,
            column=1,
            sticky="w"
        )

        controls = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        controls.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 10)
        )

        ctk.CTkButton(
            controls,
            text="Save Corrections",
            command=self.save
        ).pack(
            side="left",
            padx=(0, 8)
        )

        ctk.CTkButton(
            controls,
            text="Reset Field",
            command=self.reset_selected
        ).pack(
            side="left",
            padx=(0, 8)
        )

        ctk.CTkButton(
            controls,
            text="Restore Previous",
            command=self.restore_previous
        ).pack(
            side="left",
            padx=(0, 8)
        )

        ctk.CTkButton(
            controls,
            text="Close",
            command=self.destroy
        ).pack(
            side="right"
        )

        self.status = ctk.CTkLabel(
            self,
            text=""
        )
        self.status.grid(
            row=4,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 8)
        )

        self.suggestions = ctk.CTkScrollableFrame(
            self,
            height=120
        )
        self.suggestions.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )

    ##########################################################

    def save(self):

        saved = 0

        for field, entry in self.entries.items():
            value = entry.get().strip()
            original = self.value_to_text(
                self.original_values.get(field)
            )

            if value == original:
                continue

            self.feedback.save_correction(
                self.media_id,
                field,
                value,
                correction_source="Jonathan",
                notes=self.entries.get("notes").get().strip()
                if self.entries.get("notes")
                else ""
            )
            saved += 1

        self.effective = self.feedback.effective_media_intelligence(
            self.media_id
        )
        self.status.configure(
            text=f"Saved {saved} correction(s). Similar media may need the same correction."
        )
        self.render_suggestions(
            self.effective.get("similar_review_suggestions") or []
        )

        if self.on_saved:
            self.on_saved()

    ##########################################################

    def reset_selected(self):

        field = self.selected_field.get()
        self.feedback.reset_field(
            self.media_id,
            field,
            correction_source="Jonathan"
        )
        inferred = self.feedback.inferred_value(
            self.media_id,
            field
        )
        self.entries[field].delete(0, "end")
        self.entries[field].insert(
            0,
            self.value_to_text(inferred)
        )
        self.status.configure(
            text=f"{field} reset to inferred value."
        )

        if self.on_saved:
            self.on_saved()

    ##########################################################

    def restore_previous(self):

        field = self.selected_field.get()
        history = [
            row
            for row in self.feedback.history_for_media(self.media_id)
            if row.get("field_name") == field
        ]

        if not history:
            self.status.configure(
                text="No previous value found for selected field."
            )
            return

        previous = history[0].get("previous_value")
        self.entries[field].delete(0, "end")
        self.entries[field].insert(
            0,
            self.value_to_text(previous)
        )
        self.status.configure(
            text=f"Restored previous value for {field}. Save to apply."
        )

    ##########################################################

    def render_suggestions(self, rows):

        for child in self.suggestions.winfo_children():
            child.destroy()

        ctk.CTkLabel(
            self.suggestions,
            text="Similar Media Suggestions",
            font=("Segoe UI", 14, "bold")
        ).pack(
            anchor="w",
            padx=8,
            pady=(8, 4)
        )

        if not rows:
            ctk.CTkLabel(
                self.suggestions,
                text="No similar media found."
            ).pack(
                anchor="w",
                padx=8,
                pady=4
            )
            return

        for item in rows[:8]:
            button = ctk.CTkButton(
                self.suggestions,
                text=item["filename"],
                command=lambda value=item: self.open_suggestion(value)
            )
            button.pack(
                fill="x",
                padx=8,
                pady=3
            )

    ##########################################################

    def open_suggestion(self, item):

        if self.open_media_callback:
            self.open_media_callback(item)

    ##########################################################

    def value_to_text(self, value):

        if isinstance(value, list):
            return ", ".join(str(item) for item in value)

        return str(value or "")
