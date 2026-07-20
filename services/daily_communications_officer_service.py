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
    BANNED_PUBLIC_PHRASES = (
        "Review media before publishing",
        "Review the selected media before publishing",
        "selected media",
        "media trust",
        "confidence",
        "provider",
        "model",
        "review status",
        "technical warnings",
        "#MordenFireRescue"
    )

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
                "title": "Behind the Scenes: Recent MFR Activity",
                "strategy": "Behind-the-scenes",
                "opportunity_type": "recent_activity",
                "why_today_matters": (
                    "Fresh local media gives MFR a chance to show the community "
                    "the everyday preparation, teamwork, and service behind the department."
                ),
                "topic": "recent MFR activity",
                "content_family": "human_team_personality",
                "intended_audience": "Morden residents and followers who enjoy seeing the people behind the work",
                "tone_options": [
                    "Behind-the-scenes",
                    "Community-focused",
                    "Human-interest"
                ],
                "best_asset_ids": recent_ids[:3],
                "supporting_asset_ids": recent_ids[3:8],
                "recommended_platforms": ["Facebook", "Instagram"],
                "confidence": 76
            })

        active_themes = context_snapshot.get("active_themes") or []
        if active_themes:
            options.append({
                "title": self._title(active_themes[0]),
                "strategy": "Community-focused",
                "opportunity_type": self._opportunity_type(active_themes[0]),
                "why_today_matters": (
                    f"{self._title(active_themes[0])} is timely right now, "
                    "and a clear local reminder can help people make safer choices today."
                ),
                "topic": active_themes[0],
                "content_family": "community_public_service",
                "intended_audience": "Residents looking for practical seasonal safety reminders",
                "tone_options": [
                    "Community-focused",
                    "Educational",
                    "Direct"
                ],
                "recommended_platforms": ["Facebook", "Instagram"],
                "confidence": 74
            })

        options.append({
            "title": "Recruitment and Readiness",
            "strategy": "Recruitment",
            "opportunity_type": "recruitment",
            "why_today_matters": (
                "Recruitment works best when people can see the skills, teamwork, "
                "and commitment that go into serving Morden."
            ),
            "topic": "recruitment training volunteer",
            "content_family": "recruitment",
            "intended_audience": "Potential volunteers and community members curious about joining",
            "tone_options": [
                "Recruitment",
                "Professional",
                "Action-focused"
            ],
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
        media_facts = self._media_facts(media_package)
        option["media_facts"] = media_facts
        facebook = self._facebook_caption(
            option,
            context_snapshot,
            memory,
            media_facts
        )
        instagram_tags = self._hashtags(option, context_snapshot, platform="instagram")
        instagram = self._instagram_caption(option, instagram_tags, media_facts)
        warnings = self._warnings(media_package, option)
        graphic_brief = self._graphic_brief(option, context_snapshot)

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
            "content_angle": self._content_angle(option, media_facts),
            "content_family": option.get("content_family", "community_public_service"),
            "intended_audience": option.get("intended_audience", "Morden residents"),
            "tone_options": option.get("tone_options") or ["Community-focused"],
            "best_fit_today": index == 1,
            "graphic_brief": graphic_brief,
            "text_graphic_first": not self._has_media(media_package),
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

    def _facebook_caption(self, option, context_snapshot, memory, media_facts):

        family = option.get("content_family", "")
        topic = self._plain_topic(option)
        media_line = self._media_public_line(media_facts)
        historical = memory.get("summary", "")
        cta = self._call_to_action(option)

        if family == "recruitment":
            lines = [
                "Ever thought about serving your community in a hands-on way?",
                "",
                (
                    "Volunteer firefighting is built on training, teamwork, and "
                    "people willing to step forward when their neighbours need help."
                ),
                media_line or (
                    "This is a good time to show what preparation and readiness look like at MFR."
                ),
                "",
                "If you have questions about volunteering, reach out and learn what it takes to be part of the team."
            ]
        elif "heat" in topic or "summer" in topic:
            lines = [
                "Heat can become dangerous quickly.",
                "",
                (
                    "Drink water often, take breaks in the shade or a cool space, "
                    "check on neighbours and family members, and never leave people "
                    "or pets in a parked vehicle."
                ),
                "",
                "Small choices can prevent a medical emergency.",
                "Stay cool and look out for each other, Morden."
            ]
        elif family == "human_team_personality":
            lines = [
                "A lot of fire-service work happens before the public ever sees it.",
                "",
                media_line or (
                    "Training, checking equipment, preparing the trucks, and working as a team "
                    "are all part of staying ready for the next call."
                ),
                "",
                "It is the steady, behind-the-scenes work that keeps the department ready for Morden."
            ]
        elif family == "visual_action":
            lines = [
                "Some moments show the work better than words can.",
                "",
                media_line or (
                    "Action, coordination, and repetition are all part of building reliable fire-service skills."
                ),
                "",
                "This is the kind of practical readiness that happens one drill, one task, and one team effort at a time."
            ]
        else:
            lines = [
                f"{self._emoji(option)} A timely reminder for Morden.",
                "",
                option.get("why_today_matters", "") or (
                    "A clear local message can help people make safer choices."
                ),
                "",
                cta
            ]

        if historical:
            lines.extend([
                "",
                "MFR has shared similar seasonal reminders around this time in past years, so this keeps the message familiar without repeating old details."
            ])

        return self._clean_public_copy("\n".join(line for line in lines if line is not None))

    def _instagram_caption(self, option, hashtags, media_facts):

        family = option.get("content_family", "")
        topic = self._plain_topic(option)
        hook = self._instagram_hook(option, media_facts)

        if family == "recruitment":
            body = (
                "Training, teamwork, and service all start with people willing "
                "to step forward."
            )
        elif "heat" in topic or "summer" in topic:
            body = (
                "Hydrate, check on each other, avoid the hottest part of the day, "
                "and never leave anyone in a parked vehicle."
            )
        elif family == "human_team_personality":
            body = (
                "A look at the preparation and teamwork that keeps the department ready."
            )
        elif family == "visual_action":
            body = (
                "The work is built one repetition, one task, and one team effort at a time."
            )
        else:
            body = option.get("why_today_matters", "A timely community update for Morden.")

        caption = "\n\n".join([
            f"{self._emoji(option)} {hook}",
            body,
            " ".join(hashtags[:5])
        ])
        return self._clean_public_copy(caption)

    def _hashtags(self, option, context_snapshot, platform="instagram"):

        values = ["#Morden"]
        text = " ".join(
            str(value or "")
            for value in (
                option.get("title"),
                option.get("topic"),
                option.get("opportunity_type")
            )
        ).lower()

        if "recruit" in text:
            values.extend(["#VolunteerFirefighter", "#FirefighterTraining"])
        if "training" in text:
            values.append("#FirefighterTraining")
        if "heat" in text or "summer" in text:
            values.append("#HeatSafety")
        if "fire prevention" in text or "smoke" in text:
            values.extend(["#FireSafety", "#PublicEducation"])
        if "water" in text:
            values.append("#WaterSafety")
        if "technical" in text or "rescue" in text:
            values.append("#TechnicalRescue")

        values.append("#CommunitySafety")

        return self._unique(values)[:5]

    ############################################################

    def _fallback_option(self, index, context_snapshot):

        fallbacks = [
            ("Current Safety Reminder", "Community-focused", "community safety"),
            ("Behind the Scenes at MFR", "Behind-the-scenes", "behind the scenes"),
            ("Volunteer Recruitment", "Recruitment", "recruitment")
        ]
        title, strategy, topic = fallbacks[index % len(fallbacks)]
        return {
            "title": title,
            "strategy": strategy,
            "opportunity_type": topic.replace(" ", "_"),
            "topic": topic,
            "why_today_matters": (
                f"{title} can stand on its own as a timely "
                f"{context_snapshot.get('season', 'current')} post when no specific media fits."
            ),
            "content_family": (
                "human_team_personality"
                if "behind" in topic
                else "recruitment" if "recruit" in topic
                else "community_public_service"
            ),
            "intended_audience": "Morden residents",
            "tone_options": [strategy, "Community-focused"],
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
            "text_graphic_first": True,
            "graphic_brief": (
                "Create a simple MFR-branded graphic using the topic as the headline, "
                "one practical takeaway, and a clear local call to action."
            ),
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

    def _media_facts(self, media_package):

        primary = (
            media_package.get("primary_photo") or
            media_package.get("primary_video") or {}
        )
        alternatives = (
            (media_package.get("gallery_photos") or []) +
            (media_package.get("gallery_videos") or [])
        )[:6]
        if not primary:
            return {
                "has_media": False,
                "public_description": "",
                "primary": {},
                "alternatives": alternatives
            }

        tags = []
        for key in (
            "primary_activity",
            "incident_type",
            "normalized_scene"
        ):
            if primary.get(key):
                tags.append(primary.get(key))
        for key in ("content_tags", "content_themes", "recommended_uses"):
            tags.extend(primary.get(key) or [])

        description = self._public_media_description(tags, primary)
        return {
            "has_media": True,
            "public_description": description,
            "primary": primary,
            "alternatives": alternatives
        }

    def _public_media_description(self, tags, primary):

        text = " ".join(str(value or "") for value in tags).lower()

        if "training" in text:
            return "The attached media can support a story about training, preparation, and practical skill-building."
        if "recruit" in text:
            return "The attached media can help show the teamwork and commitment behind volunteer service."
        if "community" in text or "education" in text:
            return "The attached media can support a community-facing post with a clear local connection."
        if "apparatus" in text or "equipment" in text:
            return "The attached media can show equipment, apparatus, and the work that keeps the department ready."
        if primary.get("media_type") == "video":
            return "The attached video can support a more visual, action-first post."

        return "The attached media gives this post a real local visual anchor."

    def _media_public_line(self, media_facts):

        if not media_facts.get("has_media"):
            return ""

        return media_facts.get("public_description", "")

    def _graphic_brief(self, option, context_snapshot):

        return {
            "headline": option.get("title", "MFR Update"),
            "visual_direction": (
                "Use a simple MFR-branded graphic with one clear message, "
                "high contrast text, and no unrelated photo."
            ),
            "key_message": option.get("why_today_matters", ""),
            "season": context_snapshot.get("season", "")
        }

    def _content_angle(self, option, media_facts):

        if media_facts.get("has_media"):
            return media_facts.get("public_description", "")

        return (
            "Text/graphic-first recommendation with no unrelated media attached."
        )

    def _plain_topic(self, option):

        return " ".join(
            str(value or "")
            for value in (
                option.get("title"),
                option.get("topic"),
                option.get("opportunity_type")
            )
        ).lower()

    def _call_to_action(self, option):

        text = self._plain_topic(option)

        if "recruit" in text:
            return "Reach out if you have ever wondered what it takes to volunteer."
        if "heat" in text:
            return "Check on someone who may need a cool place or a reminder to drink water."
        if "water" in text:
            return "Wear the life jacket, watch the weather, and stay close to your group."

        return "Share the reminder with someone who may find it useful today."

    def _instagram_hook(self, option, media_facts):

        text = self._plain_topic(option)

        if media_facts.get("has_media"):
            if "recruit" in text:
                return "Teamwork starts before the call."
            if "training" in text:
                return "A quick look at readiness in motion."
            if "heat" in text:
                return "Stay cool, Morden."
            return "A local look behind the scenes."

        if "heat" in text:
            return "Heat safety matters."
        if "recruit" in text:
            return "Ready to serve?"

        return "A timely reminder for Morden."

    def _clean_public_copy(self, text):

        cleaned = str(text or "")

        for phrase in self.BANNED_PUBLIC_PHRASES:
            cleaned = cleaned.replace(phrase, "")

        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")

        return cleaned.strip()

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
