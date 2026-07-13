from datetime import datetime, time, timedelta, timezone
import threading
import time as perf_time

from core.app_context import context
from services.communications_memory_service import CommunicationsMemoryService
from services.editorial_recommendation_service import EditorialRecommendationService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.media_priority_service import MediaPriorityService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationsOfficerService:

    RECOMMENDATION_LIMIT = 10
    PACKAGE_ASSET_LIMIT = 20

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
        self.last_metrics = {}

    ############################################################

    def generate(self, now=None):

        started = perf_time.perf_counter()
        ran_on_main_thread = threading.current_thread() is threading.main_thread()
        now = now or TimeService.utc_now()
        local_now = TimeService.to_local(now) or now
        yesterday_start, yesterday_end = self._previous_local_day_bounds(
            local_now
        )
        generated_at = TimeService.utc_now_iso()

        metrics = self.db.communications_officer_metrics(
            since_utc=yesterday_start.isoformat(timespec="seconds")
        )
        metrics["new_media_added_yesterday"] = self.db.media_added_count_between(
            yesterday_start.isoformat(timespec="seconds"),
            yesterday_end.isoformat(timespec="seconds")
        )
        memory_status = self._memory_status(metrics)
        priority_snapshot = self.priority.preview("today")

        editorial_recommendations = self.editorial.generate_recommendations(
            limit=self.RECOMMENDATION_LIMIT,
            as_of=local_now
        )
        opportunities = self._rank_opportunities(
            editorial_recommendations,
            memory_status,
            priority_snapshot
        )

        top_story = opportunities[0] if opportunities else self._empty_story()
        secondary = opportunities[1:4]

        brief = {
            "title": "AI Communications Officer Morning Brief",
            "generated_at": generated_at,
            "current_date": local_now.strftime("%A, %B %d, %Y"),
            "summary": {
                "new_media_added_yesterday": metrics["new_media_added_yesterday"],
                "media_analyzed_since_last_session": metrics["media_analyzed_since"],
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
            "recommended_media_package": top_story.get("media_package", {}),
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
                "Communications Memory",
                "Media Priority",
                "Human Review trust states",
                "Reviewed Media Intelligence"
            ],
            "confidence_limitations": self._brief_limitations(
                opportunities,
                metrics,
                memory_status
            )
        }

        elapsed = round(perf_time.perf_counter() - started, 3)
        self.last_metrics = {
            "total_seconds": elapsed,
            "recommendation_count": len(editorial_recommendations),
            "opportunity_count": len(opportunities),
            "ran_on_main_thread": ran_on_main_thread,
            "editorial_metrics": getattr(self.editorial, "last_metrics", {})
        }

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

        package = self._media_package(
            recommendation,
            selected_assets
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
            "uses_reviewed_media": bool(reviewed_assets),
            "timing_active": timing["active"],
            "timing_reason": timing["reason"],
            "reviewed_media_count": len(reviewed_assets),
            "unreviewed_media_count": max(0, len(selected_assets) - len(reviewed_assets))
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
            "latest_post": latest,
            "days_since_latest_post": days_since,
            "recommendation_history_count": metrics.get(
                "recommendation_history_count",
                0
            )
        }

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
            for item in self.knowledge.items(table):
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
