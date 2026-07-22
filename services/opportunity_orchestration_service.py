import time
from datetime import timedelta

from core.app_context import context
from services.benchmark_communications_service import BenchmarkCommunicationsService
from services.communications_learning_service import CommunicationsLearningService
from services.communications_memory_service import CommunicationsMemoryService
from services.current_context_service import CurrentContextService
from services.daily_communications_officer_service import DailyCommunicationsOfficerService
from services.event_collection_service import EventCollectionService
from services.helmet_camera_service import HelmetCameraService
from services.logging_service import LoggingService
from services.media_package_service import MediaPackageService
from services.media_priority_service import MediaPriorityService
from services.package_review_service import PackageReviewService
from services.seasonal_communications_service import SeasonalCommunicationsService
from services.time_service import TimeService
from services.editorial_writing_service import EditorialWritingService


logger = LoggingService.get_logger("content")


class OpportunityOrchestrationService:
    """Shared daily opportunity source for Home and Content Director."""

    TOP_PACKAGE_LIMIT = 3
    BROADER_LIMIT = 9
    SEARCH_GROUP_LIMIT = 6

    def __init__(
        self,
        database=None,
        daily_service=None,
        event_service=None,
        memory_service=None,
        package_service=None,
        seasonal_service=None,
        priority_service=None,
        helmet_service=None,
        context_service=None,
        learning_service=None,
        benchmark_service=None,
        review_service=None
    ):

        self.db = database or context.database
        self.daily = daily_service or DailyCommunicationsOfficerService(
            database=self.db
        )
        self.events = event_service or EventCollectionService(database=self.db)
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.media_packages = package_service or MediaPackageService(
            database=self.db
        )
        self.seasonal = seasonal_service or SeasonalCommunicationsService(
            database=self.db
        )
        self.priority = priority_service or MediaPriorityService(
            database=self.db
        )
        self.helmet = helmet_service or HelmetCameraService(database=self.db)
        self.context = context_service or CurrentContextService()
        self.learning = learning_service or CommunicationsLearningService(
            database=self.db
        )
        self.benchmarks = benchmark_service or BenchmarkCommunicationsService(
            database=self.db
        )
        self.review = review_service or PackageReviewService(database=self.db)
        self.writer = EditorialWritingService()
        self.last_metrics = {}

    ############################################################

    def command_center(self, horizon="today", force=False, broader_limit=None):

        started = time.perf_counter()
        shell_started = time.perf_counter()
        local_now = TimeService.to_local(TimeService.utc_now())
        context_snapshot = self.context.current_context(now=local_now, force=force)
        metrics = self._safe_metrics()
        memory_status = self._memory_status(metrics)
        shell_seconds = round(time.perf_counter() - shell_started, 3)

        package_started = time.perf_counter()
        daily_brief = self.daily.generate(force=force)
        top_packages = self._quality_packages(
            daily_brief.get("daily_post_packages") or []
        )[:self.TOP_PACKAGE_LIMIT]
        for package in top_packages:
            try:
                self.daily.freshness.record_exposure(
                    package,
                    page="Home"
                )
            except Exception:
                logger.warning(
                    "Home recommendation exposure recording failed",
                    exc_info=True
                )
        package_seconds = round(time.perf_counter() - package_started, 3)

        recent_events = self.recent_activity(limit=8)
        broader = self._merge_packages(
            top_packages,
            self._light_opportunities(
                recent_events,
                [],
                broader_limit or self.BROADER_LIMIT
            ),
            broader_limit or self.BROADER_LIMIT
        )
        ready_media = self.ready_to_publish_media(limit=12)
        helmet = self.helmet_opportunities(limit=5)
        gaps = self.communications_gaps(
            top_packages,
            recent_events,
            ready_media,
            helmet,
            metrics
        )
        upcoming = self.upcoming_programs(limit=8)
        broader = self._merge_packages(
            broader,
            self._light_opportunities(
                [],
                upcoming,
                broader_limit or self.BROADER_LIMIT
            ),
            broader_limit or self.BROADER_LIMIT
        )
        publishing = self.publication_workflow_status()
        freshness = self.data_freshness(metrics, recent_events, helmet)
        attention = self.attention_required(
            top_packages,
            recent_events,
            gaps,
            helmet,
            freshness
        )
        workflow = self.daily_workflow_status(top_packages, publishing)
        horizons = self.planning_horizons(
            top_packages,
            recent_events,
            ready_media,
            upcoming,
            publishing
        )

        elapsed = round(time.perf_counter() - started, 3)
        result = {
            "title": "Communications Command Center",
            "generated_at": TimeService.utc_now_iso(),
            "current_date": local_now.strftime("%A, %B %d, %Y"),
            "horizon": horizon,
            "context": context_snapshot,
            "daily_brief": daily_brief,
            "top_packages": top_packages,
            "top_three_packages": top_packages,
            "top_three_communication_opportunities": top_packages,
            "recommendations": [
                self.package_to_opportunity(package)
                for package in broader
            ],
            "recent_mfr_activity": recent_events,
            "ready_to_publish_media": ready_media,
            "helmet_camera_opportunities": helmet,
            "communications_gaps": gaps,
            "upcoming_programs": upcoming,
            "publishing_workflow": publishing,
            "daily_workflow": workflow,
            "data_freshness": freshness,
            "attention_required": attention,
            "planning_horizons": horizons,
            "knowledge_provider_health": self.knowledge_provider_health(metrics),
            "communications_memory_status": memory_status,
            "status": "ready" if top_packages else "needs_reviewed_media",
            "offline_ready": True,
            "source_service": "OpportunityOrchestrationService",
            "metrics": {
                "shell_seconds": shell_seconds,
                "top_package_seconds": package_seconds,
                "total_seconds": elapsed,
                "provider_calls": 0,
                "bounded": True
            }
        }
        self.last_metrics = result["metrics"]
        logger.info(
            "Command Center generated packages=%s events=%s gaps=%s elapsed=%s",
            len(top_packages),
            len(recent_events),
            len(gaps),
            elapsed
        )
        return result

    ############################################################

    def opportunities(self, limit=9, include_daily=True, force=False):

        limit = self._bounded(limit, 1, 25)
        packages = []

        if include_daily:
            packages.extend(
                self._quality_packages(
                    (self.daily.generate(force=force) or {}).get("daily_post_packages") or []
                )
            )

        existing_ids = {
            package.get("event_id") or package.get("package_id") or package.get("title")
            for package in packages
        }
        for event in self.recent_activity(limit=12):
            event_id = event.get("event_id") or event.get("title")
            if event_id in existing_ids:
                continue
            option = self._event_option(event)
            if not option:
                continue
            package = self._package_from_option(option)
            if package:
                packages.append(package)
                existing_ids.add(event_id)
            if len(packages) >= limit:
                break

        for upcoming in self.upcoming_programs(limit=8):
            if len(packages) >= limit:
                break
            option = self._program_option(upcoming)
            package = self._package_from_option(option)
            if package:
                packages.append(package)

        return self._diverse_packages(packages)[:limit]

    def _light_opportunities(self, events, upcoming, limit):

        rows = []
        for event in events or []:
            rows.append({
                "title": event.get("title", ""),
                "package_id": event.get("event_id") or event.get("title", ""),
                "event_id": event.get("event_id", ""),
                "why_today": event.get("priority_reason", ""),
                "why_today_matters": event.get("priority_reason", ""),
                "confidence": event.get("content_potential", 0),
                "content_family": event.get("story_family", "recent_activity"),
                "opportunity_type": event.get("activity_type", "recent_activity"),
                "recommended_platforms": ["Facebook", "Instagram"],
                "facebook_caption": "",
                "instagram_caption": "",
                "quality_gate": {"passed": True, "checks": {"lightweight": True}},
                "source_signals": ["Event collections"],
                "positive_factors": [event.get("priority_reason", "")],
                "confidence_limitations": ["Open in Content Director to build full package."]
            })
            if len(rows) >= limit:
                return rows

        for program in upcoming or []:
            rows.append({
                "title": program.get("title", ""),
                "package_id": "program:" + program.get("title", ""),
                "why_today": program.get("typical_historical_timing", ""),
                "why_today_matters": program.get("typical_historical_timing", ""),
                "confidence": 62,
                "content_family": "community_public_service",
                "opportunity_type": program.get("title", "").lower().replace(" ", "_"),
                "recommended_platforms": ["Facebook", "Instagram"],
                "facebook_caption": "",
                "instagram_caption": "",
                "quality_gate": {"passed": True, "checks": {"lightweight": True}},
                "source_signals": ["Seasonal communications"],
                "positive_factors": [program.get("recommended_lead_time", "")],
                "confidence_limitations": ["Build a package before publishing."]
            })
            if len(rows) >= limit:
                break
        return rows

    ############################################################

    def search(self, query, limit=None):

        started = time.perf_counter()
        query = str(query or "").strip()
        limit = self._bounded(limit or self.SEARCH_GROUP_LIMIT, 1, 12)
        groups = {
            "Post Opportunities": self._search_opportunities(query, limit),
            "Historical MFR Posts": self._search_memory(query, limit),
            "Events": self._search_events(query, limit),
            "Photos": self._search_media(query, "image", limit),
            "Videos": self._search_media(query, "video", limit),
            "Helmet Camera Clips": self._search_helmet(query, limit),
            "Publication History": self._search_publication_history(query, limit),
            "Benchmarks": self._search_benchmarks(query, limit),
            "Learning Evidence": self._search_learning(query, limit)
        }
        total = sum(len(items) for items in groups.values())
        result = {
            "query": query,
            "groups": groups,
            "total_results": total,
            "bounded": True,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "actions": [
                "Create Post Package",
                "Open in Content Director",
                "View Historical Posts",
                "View Related Media",
                "View Event Diagnostics",
                "Create Reel Package",
                "Create Publication Draft"
            ]
        }
        logger.info(
            "Command Center search query=%s total=%s elapsed=%s",
            query,
            total,
            result["elapsed_seconds"]
        )
        return result

    ############################################################

    def create_publication_draft(self, package):

        package = dict(package or {})
        package.setdefault("version", "command-center-draft-v1")
        package.setdefault("story_title", package.get("title", ""))
        package.setdefault("headline", package.get("title", ""))
        package.setdefault("generated_at", TimeService.utc_now_iso())
        row_id = self.db.save_communication_package_history(package)
        decision = self.review.record_decision(
            package,
            "create_publication_draft",
            metadata={
                "command_center": True,
                "history_id": row_id
            }
        )
        return {
            "persisted": True,
            "history_id": row_id,
            "decision": decision.get("decision", {}),
            "status": "draft",
            "automatic_publish": False
        }

    ############################################################

    def recent_activity(self, limit=8):

        rows = []
        for event in self.events.top_collections(limit=limit, source_limit=500):
            summary = self.events.event_summary(event)
            media = (
                summary.get("strongest_media")
                or summary.get("carousel_candidates")
                or []
            )
            best = (
                event.get("best_photo")
                or (media[0] if media else {})
            )
            date_range = summary.get("when_it_occurred") or {}
            rows.append({
                **summary,
                "activity_type": event.get("activity_type", ""),
                "story_family": event.get("activity_type", ""),
                "date": date_range.get("end") or date_range.get("start") or "",
                "photo_count": event.get("photo_count", 0),
                "video_count": event.get("video_count", 0),
                "helmet_camera_count": self._helmet_count(media),
                "communication_status": event.get("communication_status", "draft_candidate"),
                "best_media": best,
                "event_trust": (
                    event.get("event_integrity", {}).get("event_usability_state", "")
                ),
                "content_potential": event.get("confidence", 0),
                "actions": [
                    "View Event",
                    "Build Post",
                    "Mark Not for Social"
                ],
                "priority_reason": self._event_priority_reason(event)
            })
        return rows[:limit]

    def ready_to_publish_media(self, limit=12):

        rows = []
        try:
            candidates = self.priority.candidates(
                preset="last_30_days",
                limit=max(20, limit * 4),
                include_photos=True,
                include_videos=True,
                only_unanalyzed=False,
                include_failed=False,
                force=True
            )
        except Exception:
            candidates = []

        for item in candidates:
            trust = item.get("trust_state") or item.get("review_status") or "inferred"
            if trust in ("rejected_real", "failed"):
                continue
            rows.append({
                "media_id": item.get("media_id") or item.get("id"),
                "filename": item.get("filename", ""),
                "path": item.get("path", ""),
                "media_type": item.get("media_type", ""),
                "event": item.get("event_title") or item.get("primary_activity") or item.get("incident_type", ""),
                "content_family": item.get("content_family") or item.get("recommended_use") or item.get("primary_activity", ""),
                "trust": trust,
                "usage_status": "unused_or_not_recently_used",
                "why_selected": self._media_reason(item),
                "communications_score": item.get("communications_score") or item.get("intelligence_score") or 0,
                "actions": [
                    "Build Post",
                    "Open Gallery",
                    "Reject Candidate"
                ]
            })
            if len(rows) >= limit:
                break
        return rows

    def helmet_opportunities(self, limit=5):

        results = []
        try:
            segments = self.db.helmet_camera_segments(limit=limit * 4)
        except Exception:
            segments = []

        for segment in segments:
            media_id = segment.get("media_id")
            package = self.helmet.reel_package(media_id, segment)
            semantic_ready = package.get("semantic_status") == "completed_provider"
            item = {
                "media_id": media_id,
                "filename": package.get("filename", ""),
                "source_video": package.get("source_path", ""),
                "start_seconds": package.get("clip_start", 0),
                "end_seconds": package.get("clip_end", 0),
                "actual_visible_activity": package.get("accessibility_description") or package.get("posting_angle", ""),
                "reel_potential": segment.get("reel_score") or segment.get("technical_score") or 0,
                "classification": package.get("content_family", ""),
                "audience": package.get("target_audience", ""),
                "tone": package.get("on_screen_text_plan", [""])[1] if package.get("on_screen_text_plan") else "",
                "hook": package.get("hook_text", ""),
                "risks": package.get("risk_warnings", []),
                "semantic_status": package.get("semantic_status", ""),
                "ready_to_publish": bool(semantic_ready and not package.get("risk_warnings")),
                "technical_label": (
                    "Semantic review completed"
                    if semantic_ready
                    else "Semantic review not completed"
                ),
                "actions": [
                    "Preview Clip",
                    "Create Reel Package",
                    "Open Helmet Cam"
                ]
            }
            if item["ready_to_publish"] or len(results) < limit:
                results.append(item)
            if len(results) >= limit:
                break
        return results

    ############################################################

    def communications_gaps(self, packages, events, ready_media, helmet, metrics):

        gaps = []
        memory_latest = metrics.get("communications_memory_latest_post", "")
        if events:
            uncommunicated = [
                event for event in events
                if event.get("communication_status") != "published"
            ]
            if uncommunicated:
                event = uncommunicated[0]
                gaps.append({
                    "title": "Recent event not yet communicated",
                    "evidence": f"{event.get('title', '')} has {event.get('photo_count', 0)} photo(s) and {event.get('video_count', 0)} video(s).",
                    "urgency": "high",
                    "suggested_action": "Build a package while the event is still fresh.",
                    "action": "Build Package"
                })

        if metrics.get("review_queue_size", 0) > 0:
            gaps.append({
                "title": "Review queue is blocking stronger packages",
                "evidence": f"{metrics.get('review_queue_size', 0)} item(s) still need review.",
                "urgency": "medium",
                "suggested_action": "Review the best package media first, not the whole library.",
                "action": "Open Review Queue"
            })

        if not any(item.get("ready_to_publish") for item in helmet):
            gaps.append({
                "title": "No Reel-ready Helmet Camera clip",
                "evidence": "Helmet Camera candidates need semantic review before public Reel use.",
                "urgency": "medium",
                "suggested_action": "Run or review semantic screening for top technical clips.",
                "action": "Open Helmet Cam"
            })

        if ready_media and not packages:
            gaps.append({
                "title": "Strong unused media has no approved story package",
                "evidence": f"{len(ready_media)} high-value media candidate(s) are available.",
                "urgency": "high",
                "suggested_action": "Create a package from the best unused media.",
                "action": "Build Package"
            })

        if not memory_latest:
            gaps.append({
                "title": "Communications Memory has no recent published baseline",
                "evidence": "No recent historical post date is available.",
                "urgency": "low",
                "suggested_action": "Import or review historical communications when convenient.",
                "action": "Open Communications Memory"
            })

        return gaps[:6]

    def upcoming_programs(self, limit=8):

        local_today = TimeService.local_date(TimeService.utc_now_iso())
        active = self.context.current_context(now=TimeService.to_local(TimeService.utc_now())).get("active_themes", [])
        upcoming = self.context.current_context(now=TimeService.to_local(TimeService.utc_now())).get("upcoming_themes", [])
        named = [
            "Fire Prevention Week",
            "Water Safety Wednesday",
            "Hydrant Heroes",
            "Fire Chief of the Day",
            "Canada Day",
            "Safe Grad",
            "Recruitment",
            "Ice Safety",
            "Heating Safety",
            "Wildfire Smoke",
            "Grass-fire Prevention"
        ]
        rows = []
        for name in named:
            signal = self.seasonal.around_this_time(
                topic=name,
                current_date=local_today,
                limit=3
            )
            in_context = any(name.lower() in str(value).lower() for value in active + upcoming)
            rows.append({
                "title": name,
                "typical_historical_timing": signal.get("summary", ""),
                "last_published_date": signal.get("last_related_post", ""),
                "current_year_status": (
                    "already covered"
                    if signal.get("current_year_already_communicated")
                    else "open"
                ),
                "media_availability": "search available",
                "recommended_lead_time": "Now" if in_context else "Plan ahead",
                "build_action": "Build Package",
                "historical_signal": signal
            })
            if len(rows) >= limit:
                break
        return rows

    def publication_workflow_status(self):

        try:
            history = self.db.communication_package_history(limit=10)
            decisions = self.db.package_review_decisions(limit=100)
        except Exception:
            history = []
            decisions = []

        counts = {
            "drafts": len(history),
            "approved": sum(1 for item in decisions if item.get("decision_type") == "approve_package"),
            "scheduled": sum(1 for item in decisions if item.get("decision_type") == "mark_scheduled"),
            "published_this_week": sum(1 for item in decisions if item.get("decision_type") == "mark_published"),
            "needs_follow_up": sum(1 for item in decisions if item.get("decision_type") == "create_publication_draft"),
            "reuse_warnings": 0
        }
        return {
            "counts": counts,
            "recent_drafts": history[:5],
            "recent_decisions": decisions[:8],
            "actions": [
                "Open Draft",
                "Mark Approved",
                "Mark Scheduled",
                "Mark Published",
                "Add Post URL",
                "Duplicate for another platform",
                "Archive"
            ]
        }

    def daily_workflow_status(self, packages, publishing):

        decisions = publishing.get("recent_decisions", [])
        reviewed = sum(
            1 for item in decisions
            if item.get("decision_type") in ("approve_package", "reject_media", "correct_event")
        )
        return {
            "title": "Today's Communications Workflow",
            "steps": [
                "Review Top 3 Opportunities",
                "Approve or replace media",
                "Review Facebook and Instagram captions",
                "Create publication draft",
                "Mark scheduled or published"
            ],
            "generated": len(packages),
            "reviewed": reviewed,
            "draft_created": publishing.get("counts", {}).get("drafts", 0),
            "scheduled": publishing.get("counts", {}).get("scheduled", 0),
            "completion_label": (
                f"{len(packages)} opportunities generated, {reviewed} reviewed, "
                f"{publishing.get('counts', {}).get('drafts', 0)} draft(s) created."
            )
        }

    def data_freshness(self, metrics, events, helmet):

        memory_latest = metrics.get("communications_memory_latest_post", "")
        return {
            "media_scan_last_run": "Available from scanner logs",
            "communications_memory_last_import": memory_latest or "Not available",
            "current_context_retrieval": TimeService.utc_now_iso(),
            "event_collection_refresh": events[0].get("date", "") if events else "",
            "publication_data_freshness": memory_latest or "",
            "helmet_camera_scan_last_run": "Available" if helmet else "No candidates found",
            "learning_data_status": self._learning_status(),
            "benchmark_data_status": self._benchmark_status(),
            "provider_availability": "Deep vision not required for Command Center load",
            "warnings": [
                warning for warning in (
                    "Communications Memory is empty" if not memory_latest else "",
                    "No Reel-ready Helmet Camera clip" if helmet and not any(item.get("ready_to_publish") for item in helmet) else ""
                )
                if warning
            ]
        }

    def attention_required(self, packages, events, gaps, helmet, freshness):

        items = []
        for package in packages:
            if not self._has_media(package):
                items.append({
                    "reason": "Package missing reliable media",
                    "affected": package.get("title", ""),
                    "action": "Change Media"
                })
            if package.get("warnings"):
                items.append({
                    "reason": "; ".join(package.get("warnings")[:2]),
                    "affected": package.get("title", ""),
                    "action": "Review Package"
                })

        for gap in gaps[:3]:
            items.append({
                "reason": gap.get("title", ""),
                "affected": gap.get("evidence", ""),
                "action": gap.get("action", "Build Package")
            })

        for item in helmet:
            if not item.get("ready_to_publish"):
                items.append({
                    "reason": "Helmet Camera clip needs semantic review",
                    "affected": item.get("filename", ""),
                    "action": "Open Helmet Cam"
                })
                break

        for warning in freshness.get("warnings", []):
            items.append({
                "reason": warning,
                "affected": "Command Center",
                "action": "Review Details"
            })

        return items[:8]

    def planning_horizons(self, packages, events, ready_media, upcoming, publishing):

        return {
            "Today": packages[:3],
            "This Week": events[:5],
            "Upcoming": upcoming[:5],
            "Evergreen": ready_media[:5],
            "Recently Published": publishing.get("recent_drafts", [])[:5]
        }

    ############################################################

    def package_to_opportunity(self, package):

        media_package = package.get("media_package") or {}
        media = []
        for key in ("primary_photo", "primary_video"):
            if media_package.get(key):
                media.append(media_package[key])
        for key in ("gallery_photos", "gallery_videos"):
            media.extend(media_package.get(key) or [])

        return {
            "id": package.get("package_id") or package.get("event_id") or package.get("title", ""),
            "title": package.get("title", ""),
            "description": package.get("why_today", package.get("why_today_matters", "")),
            "reasoning": package.get("positive_factors", []),
            "priority": package.get("priority", "High" if package.get("option_number") == 1 else "Medium"),
            "confidence": package.get("confidence", 0),
            "recommended_media": media,
            "recommended_platforms": package.get("recommended_platforms", ["Facebook", "Instagram"]),
            "best_posting_time": package.get("suggested_posting_time", "Today"),
            "caption_theme": package.get("content_angle", ""),
            "hashtags": package.get("instagram_hashtags", []),
            "call_to_action": package.get("suggested_cta", ""),
            "estimated_engagement": package.get("estimated_engagement", "Moderate"),
            "opportunity_type": package.get("opportunity_type", ""),
            "content_family": package.get("content_family", ""),
            "facebook_caption": package.get("facebook_caption", ""),
            "instagram_caption": package.get("instagram_caption", ""),
            "daily_package": package,
            "event_diagnostics": package.get("event_diagnostics", {}),
            "package_review": package.get("package_review", {}),
            "source_service": "OpportunityOrchestrationService"
        }

    ############################################################

    def _search_opportunities(self, query, limit):

        packages = self.opportunities(limit=limit, include_daily=True, force=False)
        return [
            self._search_result(
                "post_opportunity",
                package.get("title", ""),
                package.get("why_today") or package.get("why_today_matters", ""),
                package,
                [
                    "Create Post Package",
                    "Open in Content Director",
                    "Create Publication Draft"
                ]
            )
            for package in packages
            if self._matches(query, package)
        ][:limit]

    def _search_memory(self, query, limit):

        return [
            self._search_result(
                "historical_post",
                item.get("headline") or item.get("campaign") or item.get("caption", "")[:60],
                item.get("caption") or item.get("original_text", ""),
                item,
                ["View Historical Posts", "Create Post Package"]
            )
            for item in self.memory.search(query, limit=limit)
        ][:limit]

    def _search_events(self, query, limit):

        return [
            self._search_result(
                "event",
                event.get("title", ""),
                event.get("what_occurred") or event.get("priority_reason", ""),
                event,
                ["View Event Diagnostics", "Build Post"]
            )
            for event in self.recent_activity(limit=max(limit, 8))
            if self._matches(query, event)
        ][:limit]

    def _search_media(self, query, media_type, limit):

        rows = []
        try:
            rows = self.db.search_intelligence(query, limit=limit * 4)
        except Exception:
            rows = []
        results = []
        for row in rows:
            item_type = row.get("media_type") or row.get("type") or ""
            if media_type and item_type and item_type != media_type:
                continue
            results.append(
                self._search_result(
                    "photo" if media_type == "image" else "video",
                    row.get("filename", ""),
                    row.get("search_text") or row.get("primary_activity", ""),
                    row,
                    ["View Related Media", "Create Post Package"]
                )
            )
            if len(results) >= limit:
                break
        return results

    def _search_helmet(self, query, limit):

        return [
            self._search_result(
                "helmet_clip",
                item.get("filename", ""),
                item.get("actual_visible_activity") or item.get("technical_label", ""),
                item,
                ["Create Reel Package", "Open Helmet Cam"]
            )
            for item in self.helmet_opportunities(limit=max(limit, 5))
            if self._matches(query, item) or "helmet" in query.lower()
        ][:limit]

    def _search_publication_history(self, query, limit):

        try:
            rows = self.db.communication_package_history(limit=limit * 2)
        except Exception:
            rows = []
        return [
            self._search_result(
                "publication_history",
                row.get("story_title", ""),
                row.get("created_at", ""),
                row,
                ["Open Draft", "Duplicate for another platform"]
            )
            for row in rows
            if self._matches(query, row)
        ][:limit]

    def _search_benchmarks(self, query, limit):

        try:
            rows = self.benchmarks.search(filters={"search": query}, limit=limit)
        except Exception:
            rows = []
        return [
            self._search_result(
                "benchmark",
                row.get("headline") or row.get("topic") or row.get("source_department", ""),
                row.get("original_text", ""),
                row,
                ["View Benchmark Inspiration"]
            )
            for row in rows
        ][:limit]

    def _search_learning(self, query, limit):

        try:
            rows = self.learning.records(limit=limit * 2)
        except Exception:
            rows = []
        return [
            self._search_result(
                "learning_evidence",
                row.get("topic") or row.get("campaign") or row.get("platform", ""),
                row.get("caption", ""),
                row,
                ["View Learning Evidence"]
            )
            for row in rows
            if self._matches(query, row)
        ][:limit]

    ############################################################

    def _safe_metrics(self):

        try:
            metrics = self.db.communications_officer_metrics()
        except Exception:
            metrics = {}
        try:
            metrics.update(self.db.communications_memory_metrics())
        except Exception:
            pass
        return metrics

    def _memory_status(self, metrics):

        count = metrics.get("communications_memory_posts", 0)
        latest = metrics.get("communications_memory_latest_post", "")
        return {
            "available": bool(count),
            "communication_count": count,
            "latest_post": latest,
            "status": (
                f"Communications Memory active with {count:,} record(s)."
                if count
                else "Communications Memory has no imported records yet."
            )
        }

    def knowledge_provider_health(self, metrics):

        try:
            knowledge = self.db.knowledge_statistics()
        except Exception:
            knowledge = {}
        return {
            "knowledge_completeness": knowledge.get("knowledge_completeness_score", 0),
            "programs": knowledge.get("programs", 0),
            "apparatus": knowledge.get("apparatus", 0),
            "provider_status": "Deep vision not used for Command Center load",
            "mock_warning": False,
            "provider_action": "Use AI Dashboard for provider diagnostics"
        }

    def _quality_packages(self, packages):

        results = []
        for package in packages:
            quality = package.get("quality_gate") or {}
            if quality and not quality.get("passed", False):
                continue
            if not package.get("facebook_caption") or not package.get("instagram_caption"):
                continue
            if self._public_text_has_metadata(package.get("facebook_caption", "")):
                continue
            package = dict(package)
            package.setdefault("communication_status", "draft_ready")
            package.setdefault("publication_status", "not_published")
            package.setdefault("platform_plan", self.platform_plan(package))
            package.setdefault("story_support", self.story_support(package))
            package.setdefault("reel_support", self.reel_support(package))
            results.append(package)
        return results

    def _diverse_packages(self, packages):

        selected = []
        used_families = set()
        used_events = set()
        deferred = []
        for package in packages:
            family = package.get("content_family") or package.get("opportunity_type") or ""
            event_id = package.get("event_id") or ""
            if family in used_families or (event_id and event_id in used_events):
                deferred.append(package)
                continue
            selected.append(package)
            if family:
                used_families.add(family)
            if event_id:
                used_events.add(event_id)
        selected.extend(deferred)
        return selected

    def _merge_packages(self, primary, secondary, limit):

        results = []
        seen = set()
        for package in list(primary or []) + list(secondary or []):
            key = (
                package.get("package_id")
                or package.get("event_id")
                or package.get("title")
            )
            if key in seen:
                continue
            results.append(package)
            seen.add(key)
            if len(results) >= limit:
                break
        return results

    def platform_plan(self, package):

        media_package = package.get("media_package") or {}
        has_video = bool(media_package.get("primary_video") or media_package.get("gallery_videos"))
        has_multiple_photos = len(media_package.get("gallery_photos") or []) >= 2
        if has_video and "Reel" in str(package.get("recommended_format", "")):
            mix = ["Instagram Reel", "Facebook Reel"]
        elif has_video:
            mix = ["Facebook + Instagram", "Reel candidate"]
        elif has_multiple_photos:
            mix = ["Facebook", "Instagram carousel", "Instagram Story"]
        else:
            mix = package.get("recommended_platforms") or ["Facebook", "Instagram"]
        return {
            "recommended_channel_mix": mix,
            "evidence": [
                package.get("recommended_format", ""),
                package.get("content_family", ""),
                "platform-specific captions already prepared"
            ],
            "same_copy_for_all_platforms": False
        }

    def story_support(self, package):

        return {
            "instagram_story_image": self._has_media(package),
            "story_caption": self._shorten(package.get("instagram_caption", ""), 160),
            "story_cta": "Learn more from Morden Fire & Rescue.",
            "suggested_sequence": [
                "Hero visual",
                "One clear public-facing point",
                "Simple follow-up action"
            ]
        }

    def reel_support(self, package):

        media_package = package.get("media_package") or {}
        video = media_package.get("primary_video") or {}
        if not video:
            return {
                "eligible": False,
                "reason": "No primary video is attached."
            }
        return {
            "eligible": True,
            "hook": package.get("title", ""),
            "cover_frame_recommendation": video.get("filename", ""),
            "instagram_reel_caption": package.get("instagram_caption", ""),
            "facebook_reel_caption": package.get("facebook_caption", ""),
            "on_screen_text_plan": [
                package.get("title", ""),
                package.get("content_angle", ""),
                "Morden"
            ],
            "trimming_notes": "Review clip length and privacy before publishing.",
            "accessibility_description": video.get("description", ""),
            "posting_angle": package.get("content_angle", "")
        }

    def _event_option(self, event):

        media = event.get("strongest_media") or event.get("carousel_candidates") or []
        media_ids = [
            item.get("media_id") or item.get("id")
            for item in media
            if item.get("media_id") or item.get("id")
        ]
        if not media_ids:
            return {}
        return {
            "title": event.get("title", "Recent MFR Activity"),
            "strategy": event.get("story_family") or "Community-focused",
            "opportunity_type": event.get("activity_type") or "recent_activity",
            "why_today_matters": (
                f"{event.get('title', 'This recent activity')} has coherent local media and is still timely."
            ),
            "topic": " ".join(event.get("visible_activities") or [event.get("title", "")]),
            "content_family": event.get("story_family") or "recent_activity",
            "recommended_platforms": ["Facebook", "Instagram"],
            "confidence": event.get("content_potential", 70),
            "best_asset_ids": media_ids[:3],
            "supporting_asset_ids": media_ids[3:8],
            "allowed_media_ids": media_ids[:12],
            "strict_asset_ids": True,
            "event_id": event.get("event_id", ""),
            "event_collection": event,
            "event_diagnostics": event
        }

    def _program_option(self, program):

        return {
            "title": program.get("title", "Seasonal Opportunity"),
            "strategy": "Community-focused",
            "opportunity_type": program.get("title", "").lower().replace(" ", "_"),
            "why_today_matters": program.get("typical_historical_timing") or "This seasonal topic is worth planning now.",
            "topic": program.get("title", ""),
            "content_family": "community_public_service",
            "recommended_platforms": ["Facebook", "Instagram"],
            "confidence": 64,
            "graphic_first_reason": "Seasonal planning opportunity from Communications Memory and current context."
        }

    def _package_from_option(self, option):

        if not option:
            return {}
        try:
            media_package = self.media_packages.build_package(
                option,
                platforms=["Facebook", "Instagram"],
                include_mock=False,
                candidate_limit=40,
                persist=False
            )
        except Exception:
            media_package = {}
        package = dict(option)
        copy = self._fallback_copy(option, media_package)
        has_media = self._has_media({"media_package": media_package})
        package.update({
            "option_title": option.get("title", ""),
            "why_today": option.get("why_today_matters", ""),
            "media_package": media_package,
            "primary_media": media_package.get("primary_photo") or media_package.get("primary_video") or {},
            "facebook_caption": copy.get("facebook", ""),
            "instagram_caption": copy.get("instagram", ""),
            "instagram_hashtags": copy.get("instagram_hashtags", []),
            "facebook_hashtags": copy.get("facebook_hashtags", []),
            "selected_teaching_point": copy.get("selected_teaching_point", ""),
            "teaching_point": copy.get("selected_teaching_point", ""),
            "hook_type": copy.get("hook_type", ""),
            "recommended_tone": copy.get("recommended_tone", ""),
            "scroll_stop_score": copy.get("scroll_stop_score", {}),
            "caption_quality": copy.get("quality", {}),
            "quality_gate": {
                "passed": bool(copy.get("quality", {}).get("passed") and has_media),
                "checks": {
                    "editorial_writer": True,
                    "verified_media": has_media
                },
                "blocking_issues": (
                    ([] if has_media else ["No verified media available for this topic."])
                    + list((copy.get("quality") or {}).get("blocking_issues") or [])
                )
            },
            "package_review": {"actions": ["Review media", "Approve Package"]},
            "warnings": [] if has_media else ["Package needs reliable media before publishing."],
            "recommended_format": "Facebook + Instagram",
            "historical_mfr_evidence": self.seasonal.around_this_time(topic=option.get("topic", ""), limit=3),
            "positive_factors": ["Bounded event and memory search", "Local media package ranking"],
            "confidence_limitations": ["Review before publishing"]
        })
        return package

    ############################################################

    def _search_result(self, result_type, title, summary, raw, actions):

        return {
            "type": result_type,
            "title": self._shorten(title, 90),
            "summary": self._shorten(summary, 220),
            "actions": actions,
            "raw": raw
        }

    def _matches(self, query, item):

        if not query:
            return True
        text = self._searchable_text(item)
        return all(part in text for part in query.lower().split() if part)

    def _searchable_text(self, item):

        if isinstance(item, dict):
            parts = []
            for value in item.values():
                if isinstance(value, (str, int, float)):
                    parts.append(str(value))
                elif isinstance(value, list):
                    parts.extend(str(part) for part in value[:10])
                elif isinstance(value, dict):
                    parts.append(self._searchable_text(value))
            return " ".join(parts).lower()
        return str(item or "").lower()

    def _public_text_has_metadata(self, text):

        lower = str(text or "").lower()
        banned = (
            "selected media",
            "stored tags",
            "incident type:",
            "activity:",
            "supported by",
            "a safety campaign message",
            "a practical reminder",
            "morden fire & rescue, mfr"
        )
        return any(term in lower for term in banned)

    def _has_media(self, package):

        media_package = package.get("media_package") or {}
        return bool(
            package.get("primary_media")
            or media_package.get("primary_photo")
            or media_package.get("primary_video")
            or media_package.get("gallery_photos")
            or media_package.get("gallery_videos")
        )

    def _media_reason(self, item):

        score = item.get("communications_score") or item.get("intelligence_score") or item.get("score") or 0
        reason = item.get("reason") or item.get("primary_activity") or item.get("incident_type") or ""
        return f"Communications score {score}. {reason}".strip()

    def _event_priority_reason(self, event):

        integrity = event.get("event_integrity") or {}
        return (
            f"{event.get('confidence', 0)}% content potential with "
            f"{integrity.get('event_usability_state', 'unknown')} event trust."
        )

    def _helmet_count(self, media):

        return sum(
            1 for item in media
            if "helmet" in str(item.get("path", "") + item.get("filename", "")).lower()
        )

    def _learning_status(self):

        try:
            summary = self.learning.summary()
        except Exception:
            summary = {}
        return (
            f"{summary.get('sample_count', 0)} learning record(s)"
            if summary
            else "No learning summary available"
        )

    def _benchmark_status(self):

        try:
            insights = self.benchmarks.insights()
            return f"{insights.get('record_count', 0)} benchmark record(s)"
        except Exception:
            return "No benchmark records available"

    def _fallback_copy(self, option, media_package=None):

        topic = option.get("title", "MFR update")
        media_package = media_package or {}
        media = []
        for key in ("primary_photo", "primary_video", "gallery_photos", "gallery_videos"):
            item = media_package.get(key)
            if isinstance(item, dict):
                media.append(item)
            elif isinstance(item, list):
                media.extend(value for value in item if isinstance(value, dict))
        fact_sheet = self.writer.topic_fact_sheet(
            topic=topic,
            current_relevance=option.get("why_today_matters", ""),
            media=media,
            known_facts=[
                option.get("why_today_matters", ""),
                option.get("topic", ""),
                option.get("content_family", "")
            ],
            platforms=["Facebook", "Instagram"]
        )
        fact_sheet["verified_media"] = media
        fact_sheet["verified_media_ids"] = [
            item.get("media_id") or item.get("id")
            for item in media
            if item.get("media_id") or item.get("id")
        ]
        fact_sheet["requires_verified_media"] = True
        return self.writer.generate_from_fact_sheet(
            fact_sheet,
            option=option,
            tone="standard"
        )

    def _shorten(self, text, length):

        text = " ".join(str(text or "").split())
        if len(text) <= length:
            return text
        return text[: max(0, length - 3)].rstrip() + "..."

    def _bounded(self, value, low, high):

        try:
            value = int(value)
        except Exception:
            value = low
        return max(low, min(value, high))
