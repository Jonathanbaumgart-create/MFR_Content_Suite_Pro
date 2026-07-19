import time

from core.app_context import context
from services.communications_memory_service import CommunicationsMemoryService
from services.current_context_service import CurrentContextService
from services.logging_service import LoggingService
from services.media_package_service import MediaPackageService
from services.media_priority_service import MediaPriorityService
from services.seasonal_communications_service import SeasonalCommunicationsService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class DailyCommunicationsOfficerService:

    PACKAGE_COUNT = 3

    def __init__(
        self,
        database=None,
        media_package_service=None,
        memory_service=None,
        context_service=None,
        seasonal_service=None,
        priority_service=None
    ):

        self.db = database or context.database
        self.media_packages = media_package_service or MediaPackageService(
            database=self.db
        )
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.context = context_service or CurrentContextService()
        self.seasonal = seasonal_service or SeasonalCommunicationsService(
            database=self.db
        )
        self.priority = priority_service or MediaPriorityService(
            database=self.db
        )
        self.last_metrics = {}

    ############################################################

    def generate(self, now=None, force=False):

        started = time.perf_counter()
        local_now = TimeService.to_local(now or TimeService.utc_now())
        context_snapshot = self.context.current_context(
            now=local_now,
            force=force
        )
        metrics = self._summary_metrics()
        priority_media = self.priority.candidates(
            preset="last_30_days",
            limit=80,
            include_photos=True,
            include_videos=True,
            only_unanalyzed=False,
            include_failed=False,
            force=True
        )
        options = self._option_candidates(
            priority_media,
            context_snapshot,
            local_now
        )
        packages = []

        for index, option in enumerate(options[:self.PACKAGE_COUNT], start=1):
            packages.append(
                self._complete_package(
                    index,
                    option,
                    context_snapshot,
                    local_now
                )
            )

        while len(packages) < self.PACKAGE_COUNT:
            packages.append(
                self._complete_package(
                    len(packages) + 1,
                    self._fallback_option(len(packages), context_snapshot),
                    context_snapshot,
                    local_now
                )
            )

        elapsed = round(time.perf_counter() - started, 3)
        brief = {
            "title": "AI Communications Officer Daily Post Packages",
            "brief_stage": "daily_packages_ready",
            "generated_at": TimeService.utc_now_iso(),
            "current_date": local_now.strftime("%A, %B %d, %Y"),
            "summary": metrics,
            "daily_post_packages": packages[:self.PACKAGE_COUNT],
            "top_three_communication_opportunities": packages[:self.PACKAGE_COUNT],
            "top_story": packages[0] if packages else {},
            "secondary_stories": packages[1:],
            "communications_memory_status": self._memory_status(),
            "why_today_matters": packages[0].get("why_today", "") if packages else "",
            "confidence": packages[0].get("confidence", 0) if packages else 0,
            "todays_new_media": {
                "added_today": metrics.get("new_media_today", 0),
                "photos": metrics.get("new_photos_today", 0),
                "videos": metrics.get("new_videos_today", 0)
            },
            "review_queue": {
                "size": metrics.get("review_queue_size", 0),
                "approved": metrics.get("approved_media_count", 0),
                "corrected": metrics.get("corrected_media_count", 0),
                "failed": metrics.get("failed_analysis_count", 0)
            },
            "videos_awaiting_review": metrics.get("videos_awaiting_review", 0),
            "communications_gaps": [],
            "risks_and_limitations": [
                "Daily packages are generated from stored local intelligence before deep vision analysis.",
                "Review required before publishing."
            ],
            "offline_ready": True,
            "ai_enhancement_status": (
                "Daily packages use stored intelligence and deterministic "
                "writing first; deep vision is demand-driven."
            ),
            "generation_seconds": elapsed
        }
        self.last_metrics = {
            "daily_package_seconds": elapsed,
            "package_count": len(packages),
            "provider_calls": 0,
            "stage1_target_seconds": 2,
            "stage2_target_seconds": 5
        }
        logger.info(
            "Daily communications packages generated count=%s elapsed=%s",
            len(packages),
            elapsed
        )
        return brief

    ############################################################

    def _option_candidates(self, priority_media, context_snapshot, local_now):

        options = []

        recent_ids = [
            item.get("id") or item.get("media_id")
            for item in (priority_media or [])[:8]
            if item.get("id") or item.get("media_id")
        ]
        if recent_ids:
            options.append({
                "title": "Recent MFR Activity",
                "strategy": "Recent Activity",
                "opportunity_type": "recent_activity",
                "why_today_matters": (
                    "Recently added or recently captured media is available "
                    "for a timely MFR update."
                ),
                "topic": "recent MFR activity",
                "best_asset_ids": recent_ids[:3],
                "supporting_asset_ids": recent_ids[3:8],
                "recommended_platforms": ["Facebook", "Instagram"],
                "confidence": 76
            })

        active_themes = context_snapshot.get("active_themes") or []
        if active_themes:
            options.append({
                "title": self._title(active_themes[0]),
                "strategy": "Seasonal Safety",
                "opportunity_type": self._opportunity_type(active_themes[0]),
                "why_today_matters": (
                    f"{self._title(active_themes[0])} is active in "
                    f"{context_snapshot.get('season', 'today')} context."
                ),
                "topic": active_themes[0],
                "recommended_platforms": ["Facebook", "Instagram"],
                "confidence": 74
            })

        options.append({
            "title": "Recruitment and Readiness",
            "strategy": "Recruitment",
            "opportunity_type": "recruitment",
            "why_today_matters": (
                "Recruitment and readiness messaging remains useful when "
                "recent activity is limited or deep analysis is slow."
            ),
            "topic": "recruitment training volunteer",
            "recommended_platforms": ["Facebook", "Instagram"],
            "confidence": 68
        })
        return self._distinct_options(options)

    ############################################################

    def _summary_metrics(self):

        try:
            metrics = self.db.communications_officer_metrics()
        except Exception:
            metrics = {}

        try:
            recent = self.db.recent_media_counts(since_days=1)
        except Exception:
            recent = {}

        metrics.update({
            "new_media_today": recent.get("total", 0),
            "new_photos_today": recent.get("photos", 0),
            "new_videos_today": recent.get("videos", 0)
        })
        return metrics

    def _memory_status(self):

        try:
            metrics = self.db.communications_memory_metrics()
        except Exception:
            metrics = {}

        count = metrics.get("communications_count") or metrics.get("total_posts") or 0
        return {
            "available": bool(count),
            "communication_count": count,
            "status": (
                f"Communications Memory available with {count:,} record(s)."
                if count
                else "Communications Memory unavailable or empty."
            )
        }

    def _complete_package(self, index, option, context_snapshot, local_now):

        option = dict(option or {})
        title = option.get("title") or f"Daily Option {index}"
        option.setdefault("recommended_platforms", ["Facebook", "Instagram"])
        option.setdefault("opportunity_type", "general_engagement")
        option.setdefault("topic", title)
        option.setdefault("strategy", option.get("editorial_angle", "Community"))
        option.setdefault("why_today_matters", option.get("why_today", ""))
        option.setdefault("confidence", 65)
        memory = self.seasonal.around_this_time(
            topic=option.get("topic") or title,
            current_date=local_now.date(),
            limit=3
        )
        media_package = (
            self.media_packages.build_package(
                option,
                platforms=["Facebook", "Instagram"],
                include_mock=False,
                candidate_limit=40,
                persist=False
            )
            if self._has_candidate_media(option)
            else self._text_first_media_package(option)
        )
        facebook = self._facebook_caption(option, context_snapshot, memory)
        instagram_tags = self._hashtags(option, context_snapshot, platform="instagram")
        instagram = self._instagram_caption(option, instagram_tags)
        warnings = self._warnings(media_package, option)

        package = {
            **option,
            "option_number": index,
            "option_title": title,
            "title": title,
            "strategy": option.get("strategy", ""),
            "why_today": option.get("why_today_matters", ""),
            "why_today_matters": option.get("why_today_matters", ""),
            "confidence": int(option.get("confidence", 0) or 0),
            "supporting_activity": option.get("supporting_activity", {}),
            "historical_mfr_evidence": memory,
            "historical_evidence_summary": memory.get("summary", ""),
            "last_related_publication": memory.get("last_related_post", ""),
            "repetition_risk": (
                "covered_this_year"
                if memory.get("current_year_already_communicated")
                else "normal"
            ),
            "primary_media": (
                media_package.get("primary_photo") or
                media_package.get("primary_video") or {}
            ),
            "alternative_media": (
                (media_package.get("gallery_photos") or []) +
                (media_package.get("gallery_videos") or [])
            )[:6],
            "media_package": media_package,
            "media_trust_state": self._media_trust(media_package),
            "recommended_format": self._recommended_format(media_package),
            "facebook_caption": facebook,
            "instagram_caption": instagram,
            "instagram_hashtags": instagram_tags,
            "warnings": warnings,
            "copy_facebook": facebook,
            "copy_instagram": instagram,
            "open_media_enabled": bool(
                media_package.get("primary_photo") or
                media_package.get("primary_video")
            ),
            "change_media_enabled": True,
            "regenerate_option_enabled": True,
            "create_publication_draft_enabled": True,
            "review_required_before_publishing": True,
            "source_signals": [
                "Operational Activity",
                "Filesystem Intelligence",
                "Communications Memory",
                "Seasonal Context",
                "Media Package ranking"
            ],
            "positive_factors": self._positive_factors(media_package, memory),
            "negative_factors": warnings,
            "confidence_limitations": self._confidence_limitations(media_package)
        }
        return package

    ############################################################

    def _facebook_caption(self, option, context_snapshot, memory):

        title = option.get("title", "Community update")
        why = option.get("why_today_matters", "")
        historical = memory.get("summary", "")

        lines = [
            f"{self._emoji(option)} {title}",
            "",
            why or (
                "This is a timely opportunity to share a useful Morden Fire "
                "and Rescue update with the community."
            )
        ]

        if historical:
            lines.extend([
                "",
                "This timing is informed by previous MFR communications around this season."
            ])

        lines.extend([
            "",
            "Review the selected media before publishing, then keep the message clear, local, and useful.",
            "",
            "Stay safe and look out for each other, Morden."
        ])
        return "\n".join(lines)

    def _instagram_caption(self, option, hashtags):

        return (
            f"{self._emoji(option)} {option.get('title', 'MFR update')}\n\n"
            f"{option.get('why_today_matters', 'A timely community update from Morden Fire & Rescue.')}\n\n"
            "Review media before publishing.\n\n" +
            " ".join(hashtags[:5])
        )

    def _hashtags(self, option, context_snapshot, platform="instagram"):

        values = [
            "#MordenFireRescue",
            "#Morden",
            "#CommunitySafety"
        ]
        text = " ".join(
            str(value or "")
            for value in (
                option.get("title"),
                option.get("topic"),
                option.get("opportunity_type"),
                context_snapshot.get("season")
            )
        ).lower()

        if "recruit" in text:
            values.append("#Recruitment")
        if "training" in text:
            values.append("#Training")
        if "heat" in text or "summer" in text:
            values.append("#HeatSafety")
        if "fire prevention" in text or "smoke" in text:
            values.append("#FirePrevention")
        if "water" in text:
            values.append("#WaterSafety")

        return self._unique(values)[:5]

    ############################################################

    def _fallback_option(self, index, context_snapshot):

        fallbacks = [
            ("Current Safety Reminder", "Safety Campaign", "community safety"),
            ("Community Trust Update", "Community Trust", "community engagement"),
            ("Volunteer Recruitment", "Recruitment", "recruitment")
        ]
        title, strategy, topic = fallbacks[index % len(fallbacks)]
        return {
            "title": title,
            "strategy": strategy,
            "opportunity_type": topic.replace(" ", "_"),
            "topic": topic,
            "why_today_matters": (
                f"{title} is a useful fallback for "
                f"{context_snapshot.get('season', 'current')} communications."
            ),
            "confidence": 58,
            "recommended_platforms": ["Facebook", "Instagram"]
        }

    def _has_candidate_media(self, option):

        return bool(
            option.get("best_asset_ids") or
            option.get("supporting_asset_ids") or
            option.get("recommended_media") or
            option.get("media_package")
        )

    def _text_first_media_package(self, option):

        return {
            "package_id": "",
            "story_title": option.get("title", ""),
            "primary_photo": {},
            "gallery_photos": [],
            "primary_video": {},
            "gallery_videos": [],
            "media_count": 0,
            "story_strength": int(option.get("confidence", 0) or 0),
            "communications_score": int(option.get("confidence", 0) or 0),
            "editorial_angle": option.get("strategy", ""),
            "reasons": [
                "No strongly matched stored media was required for this option."
            ],
            "diversity_reasoning": [
                "Text/graphic-first fallback avoids unrelated media."
            ]
        }

    def _warnings(self, media_package, option):

        warnings = ["Review required before publishing."]

        if not self._has_media(media_package):
            warnings.append(
                "No strongly matched media found; use as text/graphic-first post."
            )

        if option.get("repetition_risk") == "covered_this_year":
            warnings.append("Related topic appears to have been covered this year.")

        return warnings

    def _positive_factors(self, media_package, memory):

        factors = []

        if self._has_media(media_package):
            factors.append("Relevant media package available.")

        if memory.get("matching_years"):
            factors.append(
                "Historical MFR communication timing evidence available."
            )

        factors.append("Does not require deep vision analysis before appearing.")
        return factors

    def _confidence_limitations(self, media_package):

        limitations = [
            "Final media and captions require human review before publishing."
        ]

        if not self._has_media(media_package):
            limitations.append("Media evidence is weak or unavailable.")

        return limitations

    def _media_trust(self, media_package):

        media = (
            media_package.get("primary_photo") or
            media_package.get("primary_video") or {}
        )
        return media.get("trust_state") or media.get("review_status") or "unreviewed"

    def _recommended_format(self, media_package):

        if media_package.get("primary_video"):
            return "Reel/video package"
        if media_package.get("primary_photo"):
            return "Photo post or carousel"
        return "Text/graphic-first post"

    def _has_media(self, media_package):

        return bool(
            media_package.get("primary_photo") or
            media_package.get("primary_video")
        )

    def _distinct_options(self, options):

        seen = set()
        result = []

        for option in options:
            key = str(option.get("title", "")).lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(option)

        return result

    def _title(self, value):

        return str(value or "").replace("_", " ").title()

    def _opportunity_type(self, value):

        return str(value or "general_engagement").lower().replace(" ", "_")

    def _emoji(self, option):

        text = " ".join(
            str(value or "")
            for value in (
                option.get("title"),
                option.get("opportunity_type"),
                option.get("topic")
            )
        ).lower()

        if "heat" in text or "summer" in text:
            return "☀️"
        if "recruit" in text:
            return "🚒"
        if "training" in text:
            return "🧑‍🚒"
        if "water" in text:
            return "💧"
        if "fire" in text:
            return "🔥"
        return "🚒"

    def _unique(self, values):

        seen = set()
        result = []

        for value in values:
            key = str(value).lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)

        return result
