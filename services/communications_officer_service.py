from datetime import datetime, time, timedelta, timezone
import threading
import time as perf_time

from core.app_context import context
from services.cache_invalidation_service import CacheInvalidationService
from services.communications_learning_service import CommunicationsLearningService
from services.communications_memory_service import CommunicationsMemoryService
from services.editorial_recommendation_service import EditorialRecommendationService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.media_priority_service import MediaPriorityService
from services.media_package_service import MediaPackageService
from services.current_context_service import CurrentContextService
from services.operational_activity_service import OperationalActivityService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationsOfficerService:

    RECOMMENDATION_LIMIT = 10
    MORNING_BRIEF_RECOMMENDATION_LIMIT = 5
    MORNING_BRIEF_CANDIDATE_LIMIT = 160
    PACKAGE_ASSET_LIMIT = 20
    CACHE_TTL_SECONDS = 300

    def __init__(
        self,
        database=None,
        editorial_service=None,
        memory_service=None,
        knowledge_service=None,
        priority_service=None
    ):

        self.db = database or context.database
        self.editorial = editorial_service or EditorialRecommendationService(
            database=self.db
        )
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.priority = priority_service or MediaPriorityService(
            database=self.db
        )
        self.media_packages = MediaPackageService(
            database=self.db
        )
        self.learning = CommunicationsLearningService(database=self.db)
        self.context_service = CurrentContextService()
        self.operational = OperationalActivityService(
            database=self.db,
            memory_service=self.memory,
            context_service=self.context_service
        )
        self.last_metrics = {}
        self._brief_cache = None

    ############################################################

    def generate_fast(self, now=None, force=False):

        started = perf_time.perf_counter()
        ran_on_main_thread = threading.current_thread() is threading.main_thread()
        now = now or TimeService.utc_now()
        local_now = TimeService.to_local(now) or now
        yesterday_start, yesterday_end = self._previous_local_day_bounds(
            local_now
        )
        generated_at = TimeService.utc_now_iso()
        profile = {}
        stage_status = {}
        metrics = {}
        session_id = None
        session_started_at = TimeService.utc_now_iso()
        previous_session = {}
        since_source = "no_previous_home_session_yesterday_fallback"

        try:
            step = perf_time.perf_counter()
            session_id = self.db.create_home_session(session_started_at)
            previous_session = self.db.latest_completed_home_session(
                before_session_id=session_id
            )
            profile["home_session_lookup_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )
            since_utc = yesterday_start.isoformat(timespec="seconds")

            if previous_session.get("completed_at"):
                since_utc = previous_session["completed_at"]
                since_source = "previous_completed_home_session"

            step = perf_time.perf_counter()
            current_context = self.context_service.current_context(
                now=local_now,
                force=force
            )
            profile["stage1_current_context_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )
            stage_status["current_context"] = "loaded"

            step = perf_time.perf_counter()
            metrics = self.db.communications_officer_metrics(
                since_utc=since_utc
            )
            metrics["media_analyzed_since"] = self.db.media_analyzed_count_since(
                since_utc
            )
            metrics["new_media_added_yesterday"] = self.db.media_added_count_between(
                yesterday_start.isoformat(timespec="seconds"),
                yesterday_end.isoformat(timespec="seconds")
            )
            profile["stage1_metrics_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )
            stage_status["metrics"] = "loaded"

            step = perf_time.perf_counter()
            priority_snapshot = self.priority.preview("today")
            profile["stage1_priority_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            step = perf_time.perf_counter()
            activity_clusters = self.operational.clusters_for_window(
                days=30,
                limit=80,
                now=local_now
            )
            operational_opportunities = self.operational.communication_opportunities(
                limit=3,
                clusters=activity_clusters,
                current_context=current_context
            )
            communications_gaps = self.operational.communications_gaps(
                clusters=activity_clusters,
                current_context=current_context
            )
            profile["stage1_operational_activity_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )
            profile["operational_activity_clusters"] = len(activity_clusters)
            profile["operational_opportunities"] = len(operational_opportunities)
            stage_status["recent_activity"] = "loaded"

            step = perf_time.perf_counter()
            metrics.update(self.db.communications_memory_metrics())
            memory_status = self._memory_status(metrics)
            self._attach_historical_evidence(
                operational_opportunities,
                activity_clusters
            )
            profile["stage2_memory_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )
            stage_status["historical_memory"] = "loaded"
            stage_status["editorial_recommendations"] = "not_started_fast_brief"
            stage_status["package_enrichment"] = "not_started_fast_brief"

            opportunities = [
                self._operational_story(item)
                for item in operational_opportunities
            ]
            opportunities.sort(
                key=lambda item: (
                    item.get("priority_score", 0),
                    1 if item.get("uses_reviewed_media") else 0,
                    item.get("confidence", 0)
                ),
                reverse=True
            )
            top_story = opportunities[0] if opportunities else self._empty_story()
            secondary = opportunities[1:4]
            limitations = self._operational_limitations(
                current_context,
                activity_clusters,
                operational_opportunities
            )
            limitations.append(
                "Editorial recommendations and package enrichment are deferred so recent activity can load quickly."
            )
            brief = {
                "title": "AI Communications Officer Morning Brief",
                "brief_stage": "partial",
                "loaded_stages": [
                    "current_context",
                    "recent_activity",
                    "historical_memory"
                ],
                "pending_stages": [
                    "editorial_recommendations",
                    "package_enrichment"
                ],
                "stage_status": stage_status,
                "generated_at": generated_at,
                "current_date": local_now.strftime("%A, %B %d, %Y"),
                "session": {
                    "session_id": session_id,
                    "started_at": session_started_at,
                    "previous_completed_at": previous_session.get("completed_at", ""),
                    "analyzed_since_source": since_source,
                    "analyzed_since_utc": since_utc
                },
                "summary": {
                    "new_media_added_yesterday": metrics.get("new_media_added_yesterday", 0),
                    "media_analyzed_since_last_session": metrics.get("media_analyzed_since", 0),
                    "media_analyzed_since_source": since_source,
                    "review_queue_size": metrics.get("review_queue_size", 0),
                    "approved_media_count": metrics.get("approved_media_count", 0),
                    "corrected_media_count": metrics.get("corrected_media_count", 0),
                    "failed_analysis_count": metrics.get("failed_analysis_count", 0),
                    "videos_awaiting_review": metrics.get("videos_awaiting_review", 0)
                },
                "top_story": top_story,
                "secondary_stories": secondary,
                "top_three_communication_opportunities": opportunities[:3],
                "best_communication_opportunities": operational_opportunities,
                "highest_confidence_editorial_recommendation": {},
                "recommended_publishing_platforms": top_story.get("recommended_platforms", []),
                "communications_memory_status": memory_status,
                "communications_learning": {
                    "available": False,
                    "sample_count": 0,
                    "learning_confidence": 0,
                    "limitations": [
                        "Learning summary deferred in fast brief."
                    ]
                },
                "recommended_media_package": top_story.get("media_package", {}),
                "recommended_videos": self._recommended_videos(
                    top_story.get("media_package", {})
                ),
                "estimated_audience": top_story.get("estimated_audience", []),
                "confidence": top_story.get("confidence", 0),
                "why_today_matters": top_story.get("why_today_matters", ""),
                "review_queue": {
                    "size": metrics.get("review_queue_size", 0),
                    "approved": metrics.get("approved_media_count", 0),
                    "corrected": metrics.get("corrected_media_count", 0),
                    "failed": metrics.get("failed_analysis_count", 0)
                },
                "todays_new_media": {
                    "added_today": priority_snapshot.get("total", 0),
                    "photos": priority_snapshot.get("photos", 0),
                    "videos": priority_snapshot.get("videos", 0),
                    "unanalyzed": priority_snapshot.get("unanalyzed", 0)
                },
                "videos_awaiting_review": metrics.get("videos_awaiting_review", 0),
                "source_signals": [
                    "Operational Activity Intelligence",
                    "Communications Memory",
                    "Media Priority",
                    "Human Review trust states",
                    "Current Context"
                ],
                "current_context": current_context,
                "recent_mfr_activity": activity_clusters[:6],
                "communications_gaps": communications_gaps,
                "risks_and_limitations": limitations,
                "confidence_limitations": limitations
            }
            elapsed = round(perf_time.perf_counter() - started, 3)
            profile["total_service_seconds"] = elapsed
            profile["tk_render_seconds"] = 0
            self.last_metrics = {
                "total_seconds": elapsed,
                "cache_hit": False,
                "brief_stage": "partial",
                "opportunity_count": len(opportunities),
                "ran_on_main_thread": ran_on_main_thread,
                "profile": profile,
                "stage_status": stage_status,
                "session_id": session_id
            }
            self.db.complete_home_session(
                session_id,
                status="partial",
                completed_at=TimeService.utc_now_iso(),
                duration_seconds=elapsed,
                summary=brief.get("summary", {}),
                metrics=self.last_metrics
            )
            self._brief_cache = {
                "local_date": local_now.date().isoformat(),
                "created_at": perf_time.perf_counter(),
                "invalidation_sequence": (
                    CacheInvalidationService.latest().get("sequence", 0)
                ),
                "brief": brief,
                "_metrics": self.last_metrics
            }
            logger.info(
                "Fast Morning Brief generated stage=partial activities=%s opportunities=%s elapsed=%s",
                len(activity_clusters),
                len(opportunities),
                elapsed
            )
            return brief

        except Exception:
            elapsed = round(perf_time.perf_counter() - started, 3)
            logger.exception(
                "Fast Morning Brief failed stage_status=%s elapsed=%s",
                stage_status,
                elapsed
            )
            if session_id:
                self.db.complete_home_session(
                    session_id,
                    status="failed",
                    completed_at=TimeService.utc_now_iso(),
                    duration_seconds=elapsed,
                    metrics={"profile": profile, "stage_status": stage_status}
                )
            raise

    ############################################################

    def generate(self, now=None, force=False):

        started = perf_time.perf_counter()
        ran_on_main_thread = threading.current_thread() is threading.main_thread()
        now = now or TimeService.utc_now()
        local_now = TimeService.to_local(now) or now
        cached = self._cached_brief(local_now)

        if cached and not force:
            self.last_metrics = {
                **cached.get("_metrics", {}),
                "cache_hit": True,
                "total_seconds": round(perf_time.perf_counter() - started, 3),
                "ran_on_main_thread": ran_on_main_thread
            }
            return cached["brief"]

        yesterday_start, yesterday_end = self._previous_local_day_bounds(
            local_now
        )
        generated_at = TimeService.utc_now_iso()
        profile = {}
        session_id = None
        session_started_at = TimeService.utc_now_iso()
        previous_session = {}
        since_source = "no_previous_home_session_yesterday_fallback"

        try:
            step = perf_time.perf_counter()
            session_id = self.db.create_home_session(session_started_at)
            previous_session = self.db.latest_completed_home_session(
                before_session_id=session_id
            )
            profile["home_session_lookup_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            since_utc = yesterday_start.isoformat(timespec="seconds")

            if previous_session.get("completed_at"):
                since_utc = previous_session["completed_at"]
                since_source = "previous_completed_home_session"

            step = perf_time.perf_counter()
            metrics = self.db.communications_officer_metrics(
                since_utc=since_utc
            )
            profile["communications_metrics_query_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            step = perf_time.perf_counter()
            metrics["media_analyzed_since"] = self.db.media_analyzed_count_since(
                since_utc
            )
            profile["analyzed_since_session_query_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            step = perf_time.perf_counter()
            metrics["new_media_added_yesterday"] = self.db.media_added_count_between(
                yesterday_start.isoformat(timespec="seconds"),
                yesterday_end.isoformat(timespec="seconds")
            )
            profile["yesterday_media_query_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            step = perf_time.perf_counter()
            metrics.update(self.db.communications_memory_metrics())
            memory_status = self._memory_status(metrics)
            profile["communications_memory_query_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            step = perf_time.perf_counter()
            priority_snapshot = self.priority.preview("today")
            profile["media_priority_query_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            step = perf_time.perf_counter()
            current_context = self.context_service.current_context(
                now=local_now
            )
            profile["current_context_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            step = perf_time.perf_counter()
            activity_clusters = self.operational.clusters_for_window(
                days=30,
                limit=120,
                now=local_now
            )
            operational_opportunities = self.operational.communication_opportunities(
                limit=3,
                clusters=activity_clusters,
                current_context=current_context
            )
            communications_gaps = self.operational.communications_gaps(
                clusters=activity_clusters,
                current_context=current_context
            )
            profile["operational_activity_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )
            profile["operational_activity_clusters"] = len(activity_clusters)
            profile["operational_opportunities"] = len(operational_opportunities)

            step = perf_time.perf_counter()
            editorial_recommendations = self.editorial.generate_recommendations(
                limit=self.MORNING_BRIEF_RECOMMENDATION_LIMIT,
                candidate_limit=self.MORNING_BRIEF_CANDIDATE_LIMIT,
                context="morning_brief",
                as_of=local_now
            )
            editorial_seconds = round(perf_time.perf_counter() - step, 3)
            editorial_metrics = getattr(self.editorial, "last_metrics", {})
            profile["editorial_recommendation_seconds"] = editorial_seconds
            profile["editorial_candidate_generation_seconds"] = editorial_metrics.get(
                "candidate_seconds",
                0
            )
            profile["editorial_scoring_seconds"] = editorial_metrics.get(
                "scoring_seconds",
                0
            )
            profile["editorial_diversity_pruning_count"] = editorial_metrics.get(
                "diversity_pruned_count",
                0
            )

            step = perf_time.perf_counter()
            self._active_profile = profile
            try:
                opportunities = self._rank_opportunities(
                    editorial_recommendations,
                    memory_status,
                    priority_snapshot
                )
            finally:
                self._active_profile = None
            opportunities = self._merge_operational_opportunities(
                opportunities,
                operational_opportunities
            )
            profile["media_package_lookup_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )
            profile.setdefault("department_knowledge_lookup_seconds", 0)

            step = perf_time.perf_counter()
            top_story = opportunities[0] if opportunities else self._empty_story()
            secondary = opportunities[1:4]

            profile["home_dto_construction_seconds"] = round(
                perf_time.perf_counter() - step,
                3
            )

            brief = {
            "title": "AI Communications Officer Morning Brief",
            "generated_at": generated_at,
            "current_date": local_now.strftime("%A, %B %d, %Y"),
            "session": {
                "session_id": session_id,
                "started_at": session_started_at,
                "previous_completed_at": previous_session.get("completed_at", ""),
                "analyzed_since_source": since_source,
                "analyzed_since_utc": since_utc
            },
            "summary": {
                "new_media_added_yesterday": metrics["new_media_added_yesterday"],
                "media_analyzed_since_last_session": metrics["media_analyzed_since"],
                "media_analyzed_since_source": since_source,
                "review_queue_size": metrics["review_queue_size"],
                "approved_media_count": metrics["approved_media_count"],
                "corrected_media_count": metrics["corrected_media_count"],
                "failed_analysis_count": metrics["failed_analysis_count"],
                "videos_awaiting_review": metrics["videos_awaiting_review"]
            },
            "top_story": top_story,
            "secondary_stories": secondary,
            "top_three_communication_opportunities": opportunities[:3],
            "highest_confidence_editorial_recommendation": (
                max(
                    opportunities,
                    key=lambda item: item.get("confidence", 0)
                )
                if opportunities
                else {}
            ),
            "recommended_publishing_platforms": top_story.get(
                "recommended_platforms",
                []
            ),
            "communications_memory_status": memory_status,
            "communications_learning": self._learning_brief(),
            "recommended_media_package": top_story.get("media_package", {}),
            "recommended_videos": self._recommended_videos(
                top_story.get("media_package", {})
            ),
            "estimated_audience": top_story.get("estimated_audience", []),
            "confidence": top_story.get("confidence", 0),
            "why_today_matters": top_story.get("why_today_matters", ""),
            "review_queue": {
                "size": metrics["review_queue_size"],
                "approved": metrics["approved_media_count"],
                "corrected": metrics["corrected_media_count"],
                "failed": metrics["failed_analysis_count"]
            },
            "todays_new_media": {
                "added_today": priority_snapshot.get("total", 0),
                "photos": priority_snapshot.get("photos", 0),
                "videos": priority_snapshot.get("videos", 0),
                "unanalyzed": priority_snapshot.get("unanalyzed", 0)
            },
            "videos_awaiting_review": metrics["videos_awaiting_review"],
            "source_signals": [
                "Editorial Recommendation Engine",
                "Operational Activity Intelligence",
                "Communications Memory",
                "Media Priority",
                "Human Review trust states",
                "Reviewed Media Intelligence",
                "Video Intelligence",
                "MFR historical performance learning"
            ],
            "current_context": current_context,
            "recent_mfr_activity": activity_clusters[:6],
            "best_communication_opportunities": operational_opportunities,
            "communications_gaps": communications_gaps,
            "risks_and_limitations": self._brief_limitations(
                opportunities,
                metrics,
                memory_status
            ) + self._operational_limitations(
                current_context,
                activity_clusters,
                operational_opportunities
            ),
            "confidence_limitations": self._brief_limitations(
                opportunities,
                metrics,
                memory_status
            )
            }

            elapsed = round(perf_time.perf_counter() - started, 3)
            profile["total_service_seconds"] = elapsed
            profile["tk_render_seconds"] = 0
            self.last_metrics = {
                "total_seconds": elapsed,
                "cache_hit": False,
                "recommendation_count": len(editorial_recommendations),
                "opportunity_count": len(opportunities),
                "ran_on_main_thread": ran_on_main_thread,
                "editorial_metrics": editorial_metrics,
                "profile": profile,
                "session_id": session_id
            }
            self.db.complete_home_session(
                session_id,
                status="completed",
                completed_at=TimeService.utc_now_iso(),
                duration_seconds=elapsed,
                summary=brief.get("summary", {}),
                metrics=self.last_metrics
            )
            self._brief_cache = {
                "local_date": local_now.date().isoformat(),
                "created_at": perf_time.perf_counter(),
                "invalidation_sequence": (
                    CacheInvalidationService.latest().get("sequence", 0)
                ),
                "brief": brief,
                "_metrics": self.last_metrics
            }

        except Exception:
            elapsed = round(perf_time.perf_counter() - started, 3)
            if session_id:
                self.db.complete_home_session(
                    session_id,
                    status="failed",
                    completed_at=TimeService.utc_now_iso(),
                    duration_seconds=elapsed,
                    metrics={"profile": profile}
                )
            raise

        logger.info(
            (
                "Communications Officer Morning Brief generated "
                "opportunities=%s top=%s elapsed=%s main_thread=%s"
            ),
            len(opportunities),
            top_story.get("title", ""),
            elapsed,
            ran_on_main_thread
        )

        return brief

    ############################################################

    def _cached_brief(self, local_now):

        cache = self._brief_cache or {}

        if not cache:
            return None

        if cache.get("local_date") != local_now.date().isoformat():
            return None

        age = perf_time.perf_counter() - cache.get("created_at", 0)

        if age > self.CACHE_TTL_SECONDS:
            return None

        if CacheInvalidationService.changed_since(
            cache.get("invalidation_sequence", 0),
            scopes=[
                "effective_intelligence",
                "communications_officer",
                "trust_metrics",
                "current_context",
                "communications_memory",
                "communication_package"
            ]
        ):
            return None

        return cache

    ############################################################

    def _rank_opportunities(
        self,
        recommendations,
        memory_status,
        priority_snapshot
    ):

        packaged = []
        fallback = []

        for recommendation in recommendations:
            opportunity = self._opportunity(
                recommendation,
                memory_status,
                priority_snapshot
            )

            if not opportunity:
                continue

            if opportunity["uses_reviewed_media"] and opportunity["timing_active"]:
                packaged.append(opportunity)
            else:
                fallback.append(opportunity)

        packaged.sort(
            key=self._opportunity_rank,
            reverse=True
        )
        fallback.sort(
            key=self._opportunity_rank,
            reverse=True
        )

        return (packaged or fallback)[:3]

    ############################################################

    def _merge_operational_opportunities(self, editorial, operational):

        merged = [
            self._operational_story(item)
            for item in (operational or [])
            if item
        ]
        merged.extend(editorial or [])
        merged = [
            item
            for item in merged
            if item
        ]
        merged.sort(
            key=lambda item: (
                item.get("priority_score", 0),
                1 if item.get("uses_reviewed_media") else 0,
                item.get("confidence", 0)
            ),
            reverse=True
        )
        return merged[:3]

    def _operational_story(self, opportunity):

        package = opportunity.get("media_package") or {}
        trust = opportunity.get("trust_level") or "fallback_unreviewed"

        return {
            "title": opportunity.get("title", ""),
            "summary": opportunity.get("summary", ""),
            "editorial_angle": opportunity.get("title", ""),
            "priority_score": opportunity.get("priority_score", 0),
            "confidence": opportunity.get("confidence", 0),
            "estimated_audience": ["Morden residents", "MFR followers"],
            "recommended_platforms": opportunity.get("recommended_platforms", []),
            "recommended_posting_window": "Today",
            "media_package": package,
            "why_today_matters": opportunity.get("why_now", ""),
            "why_public_would_care": opportunity.get("why_public_would_care", ""),
            "why_it_should_outperform": opportunity.get("why_it_should_outperform", ""),
            "positive_factors": opportunity.get("positive_factors", []),
            "negative_factors": opportunity.get("negative_factors", []),
            "confidence_limitations": opportunity.get("confidence_limitations", []),
            "source_signals": opportunity.get("source_signals", []),
            "trust_level": trust,
            "trust_label": opportunity.get("trust_label") or self._trust_label(trust),
            "trust_summary": (
                "Operational activity package from approved/corrected media."
                if opportunity.get("uses_reviewed_media")
                else "Operational activity package relies on limited unreviewed media."
            ),
            "uses_reviewed_media": opportunity.get("uses_reviewed_media", False),
            "timing_active": True,
            "timing_reason": opportunity.get("why_now", ""),
            "reviewed_media_count": (
                1 if opportunity.get("uses_reviewed_media") else 0
            ),
            "approved_media_count": 0,
            "corrected_media_count": 0,
            "unreviewed_media_count": (
                0 if opportunity.get("uses_reviewed_media") else package.get("media_count", 0)
            ),
            "supporting_recent_activity": opportunity.get("supporting_recent_activity", {}),
            "historical_matches": opportunity.get("historical_matches", []),
            "repetition_risk": opportunity.get("repetition_risk", ""),
            "suitable_media_count": opportunity.get("suitable_media_count", 0)
        }

    ############################################################

    def _opportunity(
        self,
        recommendation,
        memory_status,
        priority_snapshot
    ):

        asset_ids = self._unique(
            list(recommendation.get("best_asset_ids") or []) +
            list(recommendation.get("supporting_asset_ids") or [])
        )
        assets = self.db.communications_officer_assets(
            asset_ids,
            limit=self.PACKAGE_ASSET_LIMIT
        )
        usable_assets = [
            asset
            for asset in assets
            if not self._is_rejected_or_failed(asset)
        ]
        reviewed_assets = [
            asset
            for asset in usable_assets
            if self._is_reviewed(asset)
        ]
        selected_assets = reviewed_assets or usable_assets

        if not selected_assets:
            return None

        approved_count = sum(
            1
            for asset in selected_assets
            if (
                asset.get("trust_state") == "approved_real"
                or asset.get("review_status") == "approved"
            )
        )
        corrected_count = sum(
            1
            for asset in selected_assets
            if (
                asset.get("trust_state") == "corrected_real"
                or asset.get("review_status") == "corrected"
            )
        )
        unreviewed_count = sum(
            1
            for asset in selected_assets
            if not self._is_reviewed(asset)
        )
        trust_level = self._trust_level(
            approved_count,
            corrected_count,
            unreviewed_count
        )

        package = self.media_packages.build_package(
            {
                **recommendation,
                "recommended_media": selected_assets
            },
            platforms=recommendation.get("recommended_platforms", []),
            include_mock=False,
            candidate_limit=self.MORNING_BRIEF_CANDIDATE_LIMIT,
            persist=True
        )
        positive, negative = self._factor_groups(recommendation)
        confidence = self._confidence(
            recommendation,
            package,
            bool(reviewed_assets),
            memory_status
        )
        why_today = self._why_today_matters(
            recommendation,
            package,
            priority_snapshot
        )
        timing = self._timing_context(recommendation)
        public_care = self._why_public_cares(
            recommendation,
            package
        )
        outperform = self._why_outperforms(
            recommendation,
            package,
            memory_status
        )

        limitations = list(recommendation.get("confidence_limitations") or [])

        if not reviewed_assets:
            limitations.append(
                "No approved or corrected media was available; this is a fallback using unreviewed intelligence."
            )

        if not timing["active"]:
            limitations.append(timing["reason"])
            negative.append(timing["reason"])

        return {
            "title": recommendation.get("title", ""),
            "summary": recommendation.get("summary", ""),
            "editorial_angle": recommendation.get("editorial_angle", ""),
            "priority_score": recommendation.get("priority_score", 0),
            "confidence": confidence,
            "estimated_audience": recommendation.get("recommended_audiences", []),
            "recommended_platforms": recommendation.get("recommended_platforms", []),
            "recommended_posting_window": recommendation.get(
                "recommended_posting_window",
                ""
            ),
            "media_package": package,
            "why_today_matters": why_today,
            "why_public_would_care": public_care,
            "why_it_should_outperform": outperform,
            "positive_factors": positive,
            "negative_factors": negative,
            "confidence_limitations": limitations,
            "source_signals": self._source_signals(
                recommendation,
                package,
                memory_status,
                priority_snapshot
            ),
            "trust_level": trust_level,
            "trust_label": self._trust_label(trust_level),
            "trust_summary": self._trust_summary(
                approved_count,
                corrected_count,
                unreviewed_count
            ),
            "uses_reviewed_media": bool(reviewed_assets),
            "timing_active": timing["active"],
            "timing_reason": timing["reason"],
            "reviewed_media_count": len(reviewed_assets),
            "approved_media_count": approved_count,
            "corrected_media_count": corrected_count,
            "unreviewed_media_count": unreviewed_count
        }

    ############################################################

    def _media_package(self, recommendation, assets):

        photos = [
            asset
            for asset in assets
            if asset.get("media_type") == "image"
        ]
        videos = [
            asset
            for asset in assets
            if asset.get("media_type") == "video"
        ]
        ranked_photos = sorted(
            photos,
            key=self._asset_score,
            reverse=True
        )
        ranked_videos = sorted(
            videos,
            key=self._asset_score,
            reverse=True
        )
        all_scores = [
            int(asset.get("communications_score") or 0)
            for asset in assets
        ]

        return {
            "best_photo": self._asset_summary(ranked_photos[0]) if ranked_photos else {},
            "supporting_photos": [
                self._asset_summary(asset)
                for asset in ranked_photos[1:5]
            ],
            "best_video": self._asset_summary(ranked_videos[0]) if ranked_videos else {},
            "supporting_videos": [
                self._asset_summary(asset)
                for asset in ranked_videos[1:4]
            ],
            "story_strength": recommendation.get("story_strength", {}),
            "communications_score": (
                round(sum(all_scores) / len(all_scores), 1)
                if all_scores
                else 0
            ),
            "editorial_angle": recommendation.get("editorial_angle", ""),
            "recommended_platforms": recommendation.get("recommended_platforms", []),
            "confidence": recommendation.get("confidence_score", 0)
        }

    ############################################################

    def _asset_summary(self, asset):

        return {
            "media_id": asset.get("media_id"),
            "filename": asset.get("filename", ""),
            "media_type": asset.get("media_type", ""),
            "communications_score": asset.get("communications_score", 0),
            "intelligence_score": asset.get("intelligence_score", 0),
            "trust_state": asset.get("trust_state", ""),
            "review_status": asset.get("review_status", ""),
            "content_tags": asset.get("content_tags", [])[:6],
            "recommended_uses": asset.get("recommended_uses", [])[:5]
        }

    ############################################################

    def _trust_level(self, approved_count, corrected_count, unreviewed_count):

        if approved_count or corrected_count:
            if unreviewed_count:
                return "reviewed_with_unreviewed_support"

            return "reviewed"

        if unreviewed_count:
            return "fallback_unreviewed"

        return "unknown"

    def _trust_label(self, trust_level):

        labels = {
            "reviewed": "Reviewed evidence",
            "reviewed_with_unreviewed_support": "Reviewed evidence with limited unreviewed support",
            "fallback_unreviewed": "Fallback: unreviewed evidence",
            "unknown": "Trust state unknown"
        }

        return labels.get(trust_level, labels["unknown"])

    def _trust_summary(self, approved_count, corrected_count, unreviewed_count):

        parts = []

        if approved_count:
            parts.append(f"{approved_count} approved")

        if corrected_count:
            parts.append(f"{corrected_count} corrected")

        if unreviewed_count:
            parts.append(f"{unreviewed_count} unreviewed")

        if not parts:
            return "No trust-reviewed media in this package."

        return "Package evidence: " + ", ".join(parts) + "."

    ############################################################

    def _memory_status(self, metrics):

        latest = metrics.get("communications_memory_latest_post", "")
        latest_utc = TimeService.normalize_stored_timestamp(latest)
        days_since = None

        if latest_utc is not None:
            days_since = max(
                0,
                int((TimeService.utc_now() - latest_utc).total_seconds() / 86400)
            )

        if not metrics.get("communications_memory_posts"):
            status = "No imported communications memory yet"
        elif days_since is None:
            status = "Memory available; newest post date is unknown"
        elif days_since <= 30:
            status = "Fresh"
        elif days_since <= 90:
            status = "Usable"
        else:
            status = "Stale"

        return {
            "status": status,
            "total_posts": metrics.get("communications_memory_posts", 0),
            "historical_communications_imported": metrics.get(
                "historical_communications_imported",
                0
            ),
            "communication_deliveries": metrics.get("communication_deliveries", 0),
            "latest_post": latest,
            "first_post": metrics.get("communications_memory_first_post", ""),
            "latest_communication": metrics.get(
                "communications_memory_latest_communication",
                latest
            ),
            "engagement_records": metrics.get(
                "communications_memory_engagement_records",
                0
            ),
            "days_since_latest_post": days_since,
            "recommendation_history_count": metrics.get(
                "recommendation_history_count",
                0
            )
        }

    ############################################################

    def _learning_brief(self):

        try:
            summary = self.learning.dashboard()
        except Exception as ex:
            logger.warning(
                "Communications learning summary unavailable: %s",
                ex
            )
            return {
                "available": False,
                "sample_count": 0,
                "learning_confidence": 0,
                "limitations": [
                    "No communications performance learning is available yet."
                ]
            }

        return {
            "available": bool(summary.get("sample_count", 0)),
            "sample_count": summary.get("sample_count", 0),
            "learning_confidence": summary.get("learning_confidence", 0),
            "recent_successful_formats": summary.get(
                "recent_successful_formats",
                []
            )[:5],
            "topics_cooling_down": summary.get("topics_cooling_down", [])[:5],
            "topics_trending": summary.get("topics_trending", [])[:5],
            "campaign_opportunities": summary.get("campaign_health", {}),
            "reel_opportunities": summary.get("reel_performance", {}),
            "media_performance_summary": summary.get("media_performance", {}),
            "historical_comparisons": {
                "baseline_engagement_score": summary.get(
                    "baseline_engagement_score",
                    0
                )
            },
            "limitations": summary.get("learning_limitations", [])
        }

    ############################################################

    def _recommended_videos(self, media_package):

        media_package = media_package or {}
        videos = []

        for key in ("best_video", "primary_video"):
            video = media_package.get(key) or {}

            if video and video not in videos:
                videos.append(video)

        for key in ("supporting_videos", "gallery_videos"):
            for video in media_package.get(key) or []:
                if video and video not in videos:
                    videos.append(video)

        if not videos:
            videos = self._top_reviewed_reel_videos()

        return [
            {
                "media_id": video.get("media_id"),
                "filename": video.get("filename", ""),
                "reel_potential": video.get("reel_potential", 0),
                "why_selected": video.get("why_selected", ""),
                "clip_recommendations": video.get("clip_recommendations", []),
                "cover_recommendation": video.get("cover_recommendation", {})
            }
            for video in videos[:4]
        ]

    ############################################################

    def _top_reviewed_reel_videos(self, limit=4):

        try:
            rows = self.db.get_media_page(
                limit * 4,
                0,
                filter_key="highest_reel_potential"
            )
            ids = [
                row[0]
                for row in rows
                if row and row[0]
            ]
            assets = self.db.media_package_asset_rows(
                ids,
                limit=len(ids)
            )
        except Exception:
            return []

        reviewed = []
        for asset in assets:
            if (
                asset.get("media_type") == "video"
                and asset.get("reel_potential", 0)
                and (
                    asset.get("trust_state") in ("approved_real", "corrected_real")
                    or asset.get("review_status") in ("approved", "corrected")
                )
            ):
                reviewed.append(asset)

        reviewed.sort(
            key=lambda item: item.get("reel_potential", 0),
            reverse=True
        )
        return reviewed[:limit]

    ############################################################

    def _why_today_matters(self, recommendation, package, priority_snapshot):

        angle = recommendation.get("editorial_angle") or recommendation.get("category", "")
        score = package.get("communications_score", 0)
        new_count = priority_snapshot.get("total", 0)

        if new_count:
            return (
                f"{angle} is timely today because {new_count} newly added media item(s) are ready to review, "
                f"and this story has a communications score near {score}."
            )

        return (
            f"{angle} is the strongest available story today because reviewed media already supports it "
            f"with an average communications score near {score}."
        )

    def _why_public_cares(self, recommendation, package):

        audience = recommendation.get("recommended_audiences") or ["the community"]
        best = package.get("best_photo") or package.get("best_video") or {}
        tags = best.get("content_tags") or best.get("recommended_uses") or []

        if tags:
            evidence = ", ".join(str(tag) for tag in tags[:3])
            return (
                f"It connects with {', '.join(audience[:2])} through visible evidence around {evidence}."
            )

        return (
            f"It connects with {', '.join(audience[:2])} because the stored intelligence supports a clear public-facing story."
        )

    def _why_outperforms(self, recommendation, package, memory_status):

        story = package.get("story_strength") or {}
        story_score = story.get("overall", 0)
        memory = memory_status.get("status", "")
        priority = recommendation.get("priority_score", 0)

        return (
            f"It outranks the alternatives with priority {priority}, story strength {story_score}, "
            f"and Communications Memory status '{memory}'."
        )

    ############################################################

    def _factor_groups(self, recommendation):

        positive = []
        negative = []

        for factor in recommendation.get("reasoning_factors", []):
            text = (
                f"{factor.get('label', '')} "
                f"({factor.get('score', 0):+})"
            ).strip()

            if factor.get("direction") == "negative":
                negative.append(text)
            else:
                positive.append(text)

        return positive[:8], negative[:8]

    def _source_signals(
        self,
        recommendation,
        package,
        memory_status,
        priority_snapshot
    ):

        signals = list(recommendation.get("source_signals") or [])[:8]
        signals.extend([
            f"Best package communications score {package.get('communications_score', 0)}",
            f"Media Priority Added Today count {priority_snapshot.get('total', 0)}",
            f"Communications Memory status {memory_status.get('status', '')}",
            "Rejected and failed analyses were excluded.",
            "Approved and corrected media were preferred."
        ])

        return signals

    def _confidence(self, recommendation, package, reviewed, memory_status):

        confidence = int(recommendation.get("confidence_score") or 0)

        if reviewed:
            confidence += 6
        else:
            confidence -= 18

        if package.get("best_photo"):
            confidence += 4

        if package.get("best_video"):
            confidence += 3

        if memory_status.get("status") == "Fresh":
            confidence += 3
        elif memory_status.get("status") == "No imported communications memory yet":
            confidence -= 4

        return max(0, min(100, confidence))

    ############################################################

    def _brief_limitations(self, opportunities, metrics, memory_status):

        limitations = []

        if not opportunities:
            limitations.append(
                "No editorial recommendations were available from reviewed intelligence."
            )

        if metrics.get("review_queue_size", 0):
            limitations.append(
                f"{metrics['review_queue_size']} analysis item(s) still require review."
            )

        if memory_status.get("status") == "No imported communications memory yet":
            limitations.append(
                "Communications Memory is empty, so freshness and repetition signals are limited."
            )

        if not limitations:
            limitations.append(
                "Brief uses stored local intelligence only; no external context or live weather is included."
            )

        return limitations

    ############################################################

    def _operational_limitations(
        self,
        current_context,
        activity_clusters,
        operational_opportunities
    ):

        limitations = []

        if not activity_clusters:
            limitations.append(
                "No recent operational activity clusters were found in the bounded activity window."
            )

        if current_context.get("freshness") != "fresh":
            limitations.append(
                "Current context is unavailable or stale."
            )

        if not current_context.get("weather") and not current_context.get("alerts"):
            limitations.append(
                "Weather and alert providers are disabled or unavailable; no warnings were fabricated."
            )

        if not operational_opportunities:
            limitations.append(
                "No operational opportunity passed the media-topic compatibility gate."
            )

        for item in operational_opportunities or []:
            if not item.get("uses_reviewed_media"):
                limitations.append(
                    f"{item.get('title', 'An opportunity')} uses unreviewed evidence and should be reviewed before posting."
                )

        return self._unique(limitations)[:8]

    ############################################################

    def _attach_historical_evidence(self, opportunities, activity_clusters):

        clusters_by_id = {
            cluster.get("activity_id"): cluster
            for cluster in (activity_clusters or [])
        }

        for opportunity in opportunities or []:
            cluster = opportunity.get("supporting_recent_activity") or {}
            if cluster.get("activity_id") in clusters_by_id:
                cluster = clusters_by_id[cluster["activity_id"]]

            historical = cluster.get("historical_matches") or opportunity.get(
                "historical_matches",
                []
            )
            opportunity["historical_matches"] = historical[:3]
            opportunity["last_similar_mfr_post"] = (
                historical[0] if historical else {}
            )

    ############################################################

    def _empty_story(self):

        return {
            "title": "No reviewed communication opportunity is ready",
            "summary": "Analyze, review, approve, or correct media intelligence to unlock proactive recommendations.",
            "editorial_angle": "",
            "priority_score": 0,
            "confidence": 0,
            "estimated_audience": [],
            "recommended_platforms": [],
            "recommended_posting_window": "",
            "media_package": {},
            "why_today_matters": "There is not enough reviewed intelligence to recommend a public-facing story safely.",
            "why_public_would_care": "",
            "why_it_should_outperform": "",
            "positive_factors": [],
            "negative_factors": [],
            "confidence_limitations": [
                "No approved or corrected media package was available."
            ],
            "source_signals": []
        }

    ############################################################

    def _previous_local_day_bounds(self, local_now):

        local_zone = TimeService.local_timezone()
        yesterday = local_now.date() - timedelta(days=1)
        local_start = datetime.combine(
            yesterday,
            time.min,
            tzinfo=local_zone
        )
        local_end = local_start + timedelta(days=1)

        return (
            local_start.astimezone(timezone.utc),
            local_end.astimezone(timezone.utc)
        )

    ############################################################

    def _opportunity_rank(self, opportunity):

        package = opportunity.get("media_package") or {}

        return (
            1 if opportunity.get("uses_reviewed_media") else 0,
            1 if opportunity.get("timing_active", True) else 0,
            opportunity.get("priority_score", 0),
            opportunity.get("confidence", 0),
            package.get("communications_score", 0),
            1 if package.get("best_photo") else 0,
            1 if package.get("best_video") else 0
        )

    def _asset_score(self, asset):

        return (
            int(asset.get("communications_score") or 0),
            int(asset.get("storytelling_score") or 0),
            int(asset.get("intelligence_score") or 0),
            1 if self._is_reviewed(asset) else 0,
            asset.get("filename", "")
        )

    def _is_reviewed(self, asset):

        return (
            asset.get("trust_state") in ("approved_real", "corrected_real")
            or asset.get("review_status") in ("approved", "corrected")
        )

    def _is_rejected_or_failed(self, asset):

        return (
            bool(asset.get("failure_reason"))
            or asset.get("trust_state") in ("rejected_real", "failed")
            or asset.get("review_status") == "rejected"
        )

    ############################################################

    def _timing_context(self, recommendation):

        primary_text = " ".join(
            str(value)
            for value in (
                [recommendation.get("title", "")]
            )
        ).lower()
        today = TimeService.to_local(TimeService.utc_now_iso())

        primary = self._matched_program_timing(
            primary_text,
            today
        )

        if primary:
            return primary

        return {
            "active": True,
            "reason": "No out-of-season program timing constraint matched this recommendation."
        }

    def _matched_program_timing(self, text, today):

        if not text:
            return None

        for table in ("programs", "annual_events"):
            lookup_started = perf_time.perf_counter()
            items = self.knowledge.items(table)
            profile = getattr(self, "_active_profile", None)

            if profile is not None:
                profile["department_knowledge_lookup_seconds"] = round(
                    profile.get("department_knowledge_lookup_seconds", 0) +
                    (perf_time.perf_counter() - lookup_started),
                    3
                )

            for item in items:
                name = item.get("name", "")

                if not name:
                    continue

                if name.lower() not in text:
                    continue

                status = self.knowledge.program_status(
                    item,
                    today=today
                )

                return {
                    "active": bool(status.get("active")),
                    "reason": status.get("reason", "")
                }

        return None

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:
            if value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
