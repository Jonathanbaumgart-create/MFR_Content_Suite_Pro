import customtkinter as ctk

from core.app_context import context
from services.logging_service import LoggingService
from services.operations_service import OperationsService


logger = LoggingService.get_logger("application")


class OperationsPage(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        self.service = OperationsService()
        self.future = None
        self._destroyed = False

        self.build_page()
        self.refresh()

    ##########################################################

    def build_page(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(20, 10)
        )
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Operations",
            font=("Segoe UI", 30, "bold")
        )

        title.grid(
            row=0,
            column=0,
            sticky="w"
        )

        refresh = ctk.CTkButton(
            header,
            text="Refresh",
            command=self.refresh
        )

        refresh.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.status = ctk.CTkLabel(
            self,
            text="Loading operations health..."
        )

        self.status.grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 10)
        )

        self.content = ctk.CTkScrollableFrame(self)

        self.content.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 20)
        )

    ##########################################################

    def refresh(self):

        if self._destroyed:
            return

        self.status.configure(
            text="Loading operations health..."
        )
        self.render_loading()

        self.future = context.job_manager.submit(
            self.service.snapshot
        )

        logger.info("Operations health refresh queued")
        self.after(150, self.check_future)

    ##########################################################

    def check_future(self):

        if self._destroyed or self.future is None:
            return

        if not self.future.done():
            self.after(150, self.check_future)
            return

        try:
            report = self.future.result()

        except Exception as ex:
            logger.error(
                "Operations health refresh failed",
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            self.status.configure(
                text=f"Operations error: {ex}"
            )
            self.render_error(str(ex))
            return

        self.status.configure(
            text="Operations health loaded."
        )
        self.render_report(report)

    ##########################################################

    def render_loading(self):

        self.clear_content()
        label = ctk.CTkLabel(
            self.content,
            text="Checking library, queue, provider, knowledge, and communications readiness..."
        )
        label.pack(
            anchor="w",
            padx=10,
            pady=20
        )

    ##########################################################

    def render_error(self, message):

        self.clear_content()
        label = ctk.CTkLabel(
            self.content,
            text=message,
            wraplength=1000,
            justify="left"
        )
        label.pack(
            anchor="w",
            padx=10,
            pady=20
        )

    ##########################################################

    def render_report(self, report):

        self.clear_content()
        self.add_section(
            "Library Processing",
            self.format_library(report["library_processing"])
        )
        self.add_section(
            "Queue Health",
            self.format_queue(report["queue_health"])
        )
        self.add_section(
            "Provider Health",
            self.format_provider(report["provider_health"])
        )
        self.add_section(
            "Knowledge Health",
            self.format_knowledge(report["knowledge_health"])
        )
        self.add_section(
            "Communications Readiness",
            self.format_communications(report["communications_readiness"])
        )
        self.add_section(
            "Attention Items",
            report.get("attention_items") or ["No urgent attention items."]
        )

    ##########################################################

    def add_section(self, title, lines):

        frame = ctk.CTkFrame(self.content)
        frame.pack(
            fill="x",
            padx=10,
            pady=(0, 12)
        )

        label = ctk.CTkLabel(
            frame,
            text=title,
            font=("Segoe UI", 18, "bold")
        )
        label.pack(
            anchor="w",
            padx=12,
            pady=(10, 4)
        )

        for line in lines:
            item = ctk.CTkLabel(
                frame,
                text=str(line),
                justify="left",
                wraplength=1050
            )
            item.pack(
                anchor="w",
                padx=12,
                pady=2
            )

    ##########################################################

    def format_library(self, data):

        return [
            f"Total media scanned: {data['total_media_scanned']}",
            f"AI analyzed count: {data['ai_analyzed_count']}",
            f"Media Intelligence count: {data['media_intelligence_count']}",
            f"Unanalyzed count: {data['unanalyzed_count']}",
            f"Intelligence missing count: {data['intelligence_missing_count']}",
            f"Analysis coverage: {data['analysis_coverage_percentage']}%",
            f"Intelligence coverage: {data['intelligence_coverage_percentage']}%"
        ]

    ##########################################################

    def format_queue(self, data):

        return [
            f"Queued jobs: {data['queued_jobs']}",
            f"Running jobs: {data['running_jobs']}",
            f"Completed jobs: {data['completed_jobs']}",
            f"Failed jobs: {data['failed_jobs']}",
            f"Status: {data['status']}"
        ]

    ##########################################################

    def format_provider(self, data):

        failure = data.get("last_provider_failure") or {}
        success = data.get("last_successful_analysis") or {}
        lines = [
            f"Active provider: {data['active_provider']}",
            f"Configured model: {data.get('configured_model', '')}",
            f"Provider status: {data['provider_status']}",
            data.get("mock_warning", ""),
            "Last provider failure: " + (
                failure.get("failure_reason", "None")
                if failure
                else "None"
            ),
            "Last successful analysis: " + (
                success.get("last_analyzed", "None")
                if success
                else "None"
            ),
            "Recommended action: " + (
                data.get("recommended_action") or "None"
            )
        ]

        return [
            line
            for line in lines
            if line
        ]

    ##########################################################

    def format_knowledge(self, data):

        return [
            f"Department profile completeness: {data['department_profile_completeness']}%",
            f"Programs: {data['programs_count']}",
            f"Apparatus: {data['apparatus_count']}",
            f"Annual events: {data['annual_events_count']}",
            f"Locations: {data['locations_count']}",
            f"Partners: {data['partners_count']}",
            f"Imported documents: {data['imported_documents_count']}",
            f"Knowledge completeness score: {data['knowledge_completeness_score']}%"
        ]

    ##########################################################

    def format_communications(self, data):

        weak = data.get("weak_areas") or []

        return [
            f"Today's brief status: {data['todays_brief_status']}",
            f"Recommendations generated: {data['recommendations_generated']}",
            f"Average Communications Score: {data.get('average_communications_score', 0)}",
            f"Media Missing Communications Scores: {data.get('media_missing_communications_scores', 0)}",
            f"Communications Readiness: {data.get('communications_readiness', '')}",
            "Highest Scoring Media: " + self.highest_media_text(data),
            f"Content gaps: {len(data.get('content_gaps') or [])}",
            "Weak areas: " + (", ".join(weak[:5]) if weak else "None"),
            f"High-value unused media count: {data['high_value_unused_media_count']}",
            f"Recommendation history count: {data['recommendation_history_count']}"
        ]

    ##########################################################

    def highest_media_text(self, data):

        rows = data.get("highest_scoring_media") or []

        if not rows:
            return "None"

        return ", ".join(
            f"{row['filename']} ({row['communications_score']})"
            for row in rows[:3]
        )

    ##########################################################

    def clear_content(self):

        for child in self.content.winfo_children():
            child.destroy()

    ##########################################################

    def destroy(self):

        self._destroyed = True
        super().destroy()
