from config.ai_config import AI_CONFIG
from core.app_context import context
from services.communications_director import CommunicationsDirector
from services.communications_reasoning_service import CommunicationsReasoningService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("application")


class OperationsService:

    def __init__(
        self,
        database=None,
        job_manager=None,
        knowledge_service=None,
        director=None,
        reasoning_service=None
    ):

        self.db = database or context.database
        self.jobs = job_manager or context.job_manager
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.director = director or CommunicationsDirector(
            database=self.db,
            job_manager=self.jobs
        )
        self.reasoning = reasoning_service or CommunicationsReasoningService(
            database=self.db,
            director=self.director,
            knowledge_service=self.knowledge
        )

    ############################################################

    def snapshot(self):

        library = self.library_processing()
        queue = self.queue_health()
        provider = self.provider_health()
        knowledge = self.knowledge_health()
        communications = self.communications_readiness()
        attention = self.attention_items(
            library,
            queue,
            provider,
            knowledge,
            communications
        )

        report = {
            "library_processing": library,
            "queue_health": queue,
            "provider_health": provider,
            "knowledge_health": knowledge,
            "communications_readiness": communications,
            "attention_items": attention
        }

        logger.info(
            "Operations snapshot generated attention=%s provider=%s coverage=%s",
            len(attention),
            provider.get("active_provider", ""),
            library.get("analysis_coverage_percentage", 0)
        )

        return report

    ############################################################

    def library_processing(self):

        total = self.db.media_count()
        analyzed = self.db.analyzed_media_count()
        intelligence = self.db.media_intelligence_count()
        unanalyzed = self.db.media_needing_analysis_count()
        missing_intelligence = self.db.media_needing_intelligence_count()

        return {
            "total_media_scanned": total,
            "ai_analyzed_count": analyzed,
            "media_intelligence_count": intelligence,
            "unanalyzed_count": unanalyzed,
            "intelligence_missing_count": missing_intelligence,
            "analysis_coverage_percentage": self._percentage(
                analyzed,
                total
            ),
            "intelligence_coverage_percentage": self._percentage(
                intelligence,
                total
            )
        }

    ############################################################

    def queue_health(self):

        progress = self.jobs.progress() if self.jobs else {}

        return {
            "queued_jobs": progress.get("queued", 0),
            "running_jobs": progress.get("running", 0),
            "completed_jobs": progress.get("completed", 0),
            "failed_jobs": progress.get("failed", 0),
            "canceled_jobs": progress.get("canceled", 0),
            "status": (
                "Paused"
                if progress.get("paused")
                else "Running"
            )
        }

    ############################################################

    def provider_health(self):

        active = AI_CONFIG.get(
            "default_provider",
            "mock"
        )
        failure = self.db.last_provider_failure()
        success = self.db.last_successful_analysis()
        warning = ""

        if active == "mock":
            warning = "Mock provider active - test data only"

        status = "Mock testing only" if active == "mock" else "Ready"

        if failure and not success:
            status = "Provider failures detected"

        return {
            "active_provider": active,
            "mock_warning": warning,
            "last_provider_failure": failure,
            "last_successful_analysis": success,
            "provider_status": status
        }

    ############################################################

    def knowledge_health(self):

        stats = self.knowledge.statistics()
        profile = self.knowledge.profile()
        required = (
            "department_name",
            "short_name",
            "community",
            "province",
            "voice"
        )
        complete = sum(
            1
            for key in required
            if profile.get(key)
        )

        return {
            "department_profile_completeness": self._percentage(
                complete,
                len(required)
            ),
            "programs_count": stats.get("programs", 0),
            "apparatus_count": stats.get("apparatus", 0),
            "annual_events_count": stats.get("events", 0),
            "locations_count": stats.get("locations", 0),
            "partners_count": stats.get("partners", 0),
            "imported_documents_count": stats.get("documents_imported", 0),
            "knowledge_completeness_score": stats.get(
                "knowledge_completeness_score",
                0
            ),
            "program_timing_gaps": self._program_timing_gaps()
        }

    ############################################################

    def communications_readiness(self):

        insights = self.director.library_insights()
        gaps = self.reasoning.content_gaps(
            insights=insights
        )
        unused = insights.get(
            "unused_high_value_media",
            []
        )
        intelligence_count = insights.get(
            "media_with_intelligence",
            0
        )

        return {
            "todays_brief_status": (
                "Ready"
                if intelligence_count
                else "Waiting for Media Intelligence"
            ),
            "recommendations_generated": self.db.recommendation_history_count(),
            "content_gaps": gaps,
            "weak_areas": [
                gap.get("name", "")
                for gap in gaps
                if gap.get("severity") in ("High", "Medium") or gap.get("count", 0) < 3
            ],
            "high_value_unused_media_count": len(unused),
            "recommendation_history_count": self.db.recommendation_history_count()
        }

    ############################################################

    def attention_items(
        self,
        library,
        queue,
        provider,
        knowledge,
        communications
    ):

        items = []

        if provider.get("active_provider") == "mock":
            items.append("Mock provider active")

        if library.get("unanalyzed_count", 0):
            items.append(
                f"{library['unanalyzed_count']} media items still need AI analysis"
            )

        if library.get("intelligence_missing_count", 0):
            items.append(
                f"{library['intelligence_missing_count']} analyzed media items need intelligence indexing"
            )

        if provider.get("last_provider_failure"):
            items.append("Provider failures detected")

        for gap in knowledge.get("program_timing_gaps", []):
            items.append(
                f"Knowledge base missing program timing: {gap}"
            )

        travelling = self._knowledge_item_by_name(
            "programs",
            "Travelling Sparky"
        )

        if travelling:
            status = self.knowledge.program_status(
                travelling
            )

            if not status["active"]:
                items.append(status["reason"])

        if communications.get("content_gaps"):
            items.append("Content gaps detected")

        if queue.get("failed_jobs", 0):
            items.append(
                f"{queue['failed_jobs']} background jobs have failed"
            )

        return self._unique(items)

    ############################################################

    def _program_timing_gaps(self):

        missing = []

        for program in self.knowledge.items("programs"):

            if not program.get("active"):
                continue

            if (
                program.get("active_months") or
                program.get("season") or
                program.get("campaign_window")
            ):
                continue

            missing.append(
                program.get("name", "")
            )

        return missing

    ############################################################

    def _knowledge_item_by_name(self, table, name):

        target = self._token(name)

        for item in self.knowledge.items(table):

            if self._token(item.get("name")) == target:
                return item

        return None

    ############################################################

    def _percentage(self, value, total):

        if not total:
            return 0

        return int((value / total) * 100)

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )

    ############################################################

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
