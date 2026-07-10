from datetime import datetime
import threading
import time

from core.app_context import context
from services.communications_reasoning_service import CommunicationsReasoningService
from services.editorial_recommendation_service import EditorialRecommendationService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class DailyBriefService:

    def __init__(
        self,
        database=None,
        reasoning_service=None,
        knowledge_service=None,
        editorial_recommendation_service=None
    ):

        self.db = database or context.database
        self.reasoning = reasoning_service or CommunicationsReasoningService(
            database=self.db
        )
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.editorial_recommendations = (
            editorial_recommendation_service or
            EditorialRecommendationService(
                database=self.db
            )
        )
        self.last_metrics = {}

    ############################################################

    def generate(self, now=None):

        started = time.perf_counter()
        ran_on_main_thread = threading.current_thread() is threading.main_thread()
        now = now or datetime.now()
        generated_at = TimeService.utc_now_iso()
        step = time.perf_counter()
        reasoning_brief = self.reasoning.todays_communications_brief()
        reasoning_seconds = round(time.perf_counter() - step, 3)
        top = reasoning_brief.get("top_recommendation")
        additional = reasoning_brief.get("additional_opportunities", [])[:3]
        context_snapshot = reasoning_brief.get("context_snapshot", {})
        step = time.perf_counter()
        library_health = self._library_health(reasoning_brief)
        library_health_seconds = round(time.perf_counter() - step, 3)
        processing_status = reasoning_brief.get("processing_status", {})
        learning = self._recent_learning(reasoning_brief)
        step = time.perf_counter()
        editorial_recommendations = self.editorial_recommendations.generate_recommendations(
            limit=5,
            as_of=now
        )
        editorial_seconds = round(time.perf_counter() - step, 3)

        brief = {
            "title": "Daily Communications Brief",
            "greeting": self._greeting(now),
            "current_date": now.strftime("%A, %B %d, %Y"),
            "generated_at": generated_at,
            "current_context": {
                "season": context_snapshot.get("season", ""),
                "active_themes": context_snapshot.get("active_themes", []),
                "upcoming_themes": context_snapshot.get("upcoming_themes", []),
                "priority_context": context_snapshot.get("priority_context", []),
                "explanation": context_snapshot.get("explanation", "")
            },
            "top_recommendation": self._recommendation_package(top),
            "additional_opportunities": [
                self._opportunity_summary(item)
                for item in additional
            ],
            "library_health_summary": library_health,
            "recommendation_confidence": (
                top.get("confidence", 0)
                if top
                else 0
            ),
            "suggested_posting_time": (
                top.get("best_posting_time", "")
                if top
                else ""
            ),
            "upcoming_campaigns": reasoning_brief.get(
                "upcoming_opportunities",
                []
            ),
            "content_gaps": reasoning_brief.get("content_gaps", []),
            "processing_status": processing_status,
            "recent_learning": learning,
            "editorial_recommendations": editorial_recommendations,
            "source_brief": reasoning_brief
        }

        logger.info(
            (
                "Daily Brief generated top=%s confidence=%s "
                "opportunities=%s editorial_recommendations=%s gaps=%s "
                "elapsed=%s reasoning_seconds=%s editorial_seconds=%s "
                "main_thread=%s"
            ),
            (top or {}).get("opportunity_type", ""),
            brief["recommendation_confidence"],
            len(brief["additional_opportunities"]),
            len(editorial_recommendations),
            len(brief["content_gaps"]),
            round(time.perf_counter() - started, 3),
            reasoning_seconds,
            editorial_seconds,
            ran_on_main_thread
        )
        self.last_metrics = {
            "total_seconds": round(time.perf_counter() - started, 3),
            "reasoning_seconds": reasoning_seconds,
            "library_health_seconds": library_health_seconds,
            "editorial_seconds": editorial_seconds,
            "editorial_metrics": getattr(
                self.editorial_recommendations,
                "last_metrics",
                {}
            ),
            "ran_on_main_thread": ran_on_main_thread
        }

        return brief

    ############################################################

    def _recommendation_package(self, recommendation):

        if not recommendation:
            return {
                "title": "No recommendation available",
                "summary": "Media Intelligence is not ready yet.",
                "reasoning": [],
                "recommended_media": [],
                "facebook_caption": "",
                "instagram_caption": "",
                "suggested_platforms": [],
                "suggested_posting_time": "",
                "estimated_engagement": "Limited"
            }

        return {
            "title": recommendation.get("title", ""),
            "summary": recommendation.get("summary", ""),
            "reasoning": recommendation.get("reasoning", []),
            "recommended_media": recommendation.get("recommended_media", []),
            "facebook_caption": self._facebook_caption(recommendation),
            "instagram_caption": self._instagram_caption(recommendation),
            "suggested_platforms": recommendation.get(
                "recommended_platforms",
                []
            ),
            "suggested_posting_time": recommendation.get(
                "best_posting_time",
                ""
            ),
            "estimated_engagement": recommendation.get(
                "estimated_engagement",
                ""
            ),
            "confidence": recommendation.get("confidence", 0),
            "opportunity_type": recommendation.get("opportunity_type", "")
        }

    ############################################################

    def _opportunity_summary(self, recommendation):

        return {
            "title": recommendation.get("title", ""),
            "summary": recommendation.get("summary", ""),
            "confidence": recommendation.get("confidence", 0),
            "suggested_posting_time": recommendation.get(
                "best_posting_time",
                ""
            ),
            "suggested_platforms": recommendation.get(
                "recommended_platforms",
                []
            ),
            "estimated_engagement": recommendation.get(
                "estimated_engagement",
                ""
            ),
            "reasoning": recommendation.get("reasoning", [])[:3],
            "recommended_media": recommendation.get("recommended_media", [])[:1],
            "opportunity_type": recommendation.get("opportunity_type", "")
        }

    ############################################################

    def _library_health(self, reasoning_brief):

        health = reasoning_brief.get("library_health", {})
        processing = reasoning_brief.get("processing_status", {})
        knowledge_stats = self.knowledge.statistics()
        media_scanned = health.get("total_media", 0)
        intelligence = health.get("media_with_intelligence", 0)
        coverage = 0

        if media_scanned:
            coverage = int((intelligence / media_scanned) * 100)

        return {
            "media_scanned": media_scanned,
            "media_analyzed": health.get("analyzed_media", 0),
            "media_intelligence_coverage": coverage,
            "knowledge_completeness": knowledge_stats.get(
                "knowledge_completeness_score",
                0
            ),
            "recommendation_confidence": (
                reasoning_brief.get("top_recommendation", {}) or {}
            ).get("confidence", 0),
            "items_awaiting_analysis": processing.get(
                "media_requiring_analysis",
                0
            ),
            "items_awaiting_intelligence": processing.get(
                "media_requiring_intelligence",
                0
            )
        }

    ############################################################

    def _recent_learning(self, reasoning_brief):

        preferences = reasoning_brief.get("communication_preferences", {})
        analytics = reasoning_brief.get("learning_analytics", {})
        learning = []
        summary = preferences.get("summary", [])

        if summary:
            learning.append(
                "You've recently preferred " +
                ", ".join(summary[:3]) +
                " recommendations."
            )

        posting_times = preferences.get("posting_times", [])

        if posting_times:
            learning.append(
                f"{posting_times[0]} posts have been selected most often."
            )

        accepted = analytics.get("most_accepted_opportunity_type")

        if accepted:
            learning.append(
                f"{accepted} recommendations are being accepted."
            )

        if not learning:
            learning.append(
                "Learning will improve as recommendations are opened, saved, accepted, or dismissed."
            )

        return learning

    ############################################################

    def _facebook_caption(self, recommendation):

        cta = recommendation.get("call_to_action", "")
        theme = recommendation.get("caption_strategy", "")
        reason = self._top_media_reason(recommendation)

        return (
            f"{theme}. {cta} "
            f"Recommended today because {reason.lower()}."
        ).strip()

    ############################################################

    def _instagram_caption(self, recommendation):

        cta = recommendation.get("call_to_action", "")
        theme = recommendation.get("caption_strategy", "")
        hashtags = " ".join(recommendation.get("hashtags", [])[:6])

        return (
            f"{theme}. {cta} {hashtags}"
        ).strip()

    ############################################################

    def _top_media_reason(self, recommendation):

        media = recommendation.get("recommended_media") or []

        if media:
            return media[0].get(
                "reason",
                "it matches today's stored Media Intelligence"
            )

        return "it matches today's stored Media Intelligence"

    ############################################################

    def _greeting(self, now):

        profile = self.knowledge.profile()
        department = profile.get(
            "department_name",
            "Morden Fire & Rescue"
        )

        if now.hour < 12:
            greeting = "Good morning"
        elif now.hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        return f"{greeting}. Here is today's communications brief for {department}."
