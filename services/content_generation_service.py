import time

from core.app_context import context
from services.communications_intelligence_service import CommunicationsIntelligenceService
from services.context_engine import ContextEngine
from services.communications_memory_service import CommunicationsMemoryService
from services.decision_explainability_service import DecisionExplainabilityService
from services.editorial_review_service import EditorialReviewService
from services.human_feedback_service import HumanFeedbackService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.writing_service import WritingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class ContentGenerationService:

    GENERATION_VERSION = "multi-platform-v1"
    PLATFORMS = (
        "facebook",
        "instagram",
        "linkedin",
        "website",
        "news_release",
        "newsletter"
    )

    WRITING_STYLES = {
        "community": {
            "label": "Community",
            "lead": "A community-focused update",
            "tone": "friendly and local"
        },
        "educational": {
            "label": "Educational",
            "lead": "A public education update",
            "tone": "clear and helpful"
        },
        "recruitment": {
            "label": "Recruitment",
            "lead": "A recruitment-focused message",
            "tone": "inviting and service-minded"
        },
        "incident_recap": {
            "label": "Incident Recap",
            "lead": "A concise incident recap",
            "tone": "factual and careful"
        },
        "recognition": {
            "label": "Recognition",
            "lead": "A recognition post",
            "tone": "appreciative and professional"
        },
        "apparatus_feature": {
            "label": "Apparatus Feature",
            "lead": "An apparatus feature",
            "tone": "informational and operational"
        },
        "training": {
            "label": "Training",
            "lead": "A training highlight",
            "tone": "professional and behind-the-scenes"
        },
        "safety_campaign": {
            "label": "Safety Campaign",
            "lead": "A community safety update",
            "tone": "public-safety focused"
        },
        "holiday": {
            "label": "Holiday",
            "lead": "A seasonal safety message",
            "tone": "warm and safety-focused"
        },
        "behind_the_scenes": {
            "label": "Behind The Scenes",
            "lead": "A behind-the-scenes look",
            "tone": "approachable and informative"
        }
    }

    STYLE_BY_OPPORTUNITY = {
        "community_appreciation": "community",
        "general_engagement": "community",
        "smoke_alarm_reminder": "educational",
        "water_safety": "educational",
        "heat_warning": "safety_campaign",
        "storm_safety": "safety_campaign",
        "fire_prevention_week": "safety_campaign",
        "recruitment": "recruitment",
        "volunteer_recognition": "recognition",
        "apparatus_showcase": "apparatus_feature",
        "training_highlight": "training",
        "holiday_safety": "holiday",
        "behind_the_scenes": "behind_the_scenes",
        "throwback_thursday": "community",
        "on_this_day": "community"
    }

    DEFAULT_TEMPLATES = (
        {
            "name": "Facebook Standard",
            "writing_style": "community",
            "platform": "facebook",
            "body": "{lead}: {summary} {cta}"
        },
        {
            "name": "Instagram Standard",
            "writing_style": "community",
            "platform": "instagram",
            "body": "{headline}. {short_version} {hashtags}"
        },
        {
            "name": "LinkedIn Standard",
            "writing_style": "community",
            "platform": "linkedin",
            "body": "{headline}: {long_version}"
        }
    )

    def __init__(
        self,
        database=None,
        knowledge_service=None,
        context_engine=None,
        writing_service=None,
        memory_service=None,
        editorial_review_service=None
    ):

        self.db = database or context.database
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.context_engine = context_engine or ContextEngine()
        self.writing = writing_service or WritingService()
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.communications_intelligence = CommunicationsIntelligenceService(
            database=self.db,
            memory_service=self.memory,
            knowledge_service=self.knowledge
        )
        self.human_feedback = HumanFeedbackService(
            database=self.db
        )
        self.explainability = DecisionExplainabilityService(
            database=self.db,
            memory_service=self.memory
        )
        self.editorial_review = (
            editorial_review_service or EditorialReviewService()
        )
        self.ensure_default_templates()

    ############################################################

    def generate_package(
        self,
        recommendation,
        context_snapshot=None,
        opportunity_type=None,
        writing_style=None,
        editorial_strategy=None
    ):

        if self._is_communication_package(recommendation):
            return self.generate_from_package(
                recommendation
            )

        opportunity_type = opportunity_type or recommendation.get(
            "opportunity_type",
            "general_engagement"
        )
        editorial_strategy = editorial_strategy or recommendation.get(
            "selected_editorial_strategy"
        )
        if editorial_strategy:
            recommendation = dict(recommendation)
            recommendation["caption_strategy"] = editorial_strategy.get(
                "caption_direction",
                recommendation.get("caption_strategy", "")
            )
            recommendation["call_to_action"] = editorial_strategy.get(
                "call_to_action",
                recommendation.get("call_to_action", "")
            )
            recommendation["recommended_platforms"] = editorial_strategy.get(
                "recommended_platforms",
                recommendation.get("recommended_platforms", [])
            )
            opportunity_type = self._opportunity_from_strategy(
                editorial_strategy.get("strategy_type", ""),
                opportunity_type
            )
        writing_style = writing_style or self.style_for_opportunity(
            opportunity_type
        )
        context_snapshot = context_snapshot or self.context_engine.snapshot()
        profile = self.WRITING_STYLES.get(
            writing_style,
            self.WRITING_STYLES["community"]
        )
        knowledge = self.knowledge.snapshot()
        writing_memory = self.memory.writing_memory()
        media = self._media_context(
            recommendation.get("recommended_media", [])
        )
        terms = self._department_terms(
            knowledge,
            recommendation,
            media
        )
        facebook_hashtags = self._platform_hashtags(
            recommendation,
            media,
            "facebook"
        )
        instagram_hashtags = self._platform_hashtags(
            recommendation,
            media,
            "instagram"
        )
        hashtags = self._unique(
            facebook_hashtags + instagram_hashtags
        )
        emojis = self._emoji_suggestions(
            writing_style,
            media,
            opportunity_type
        )
        cta = recommendation.get(
            "call_to_action",
            ""
        )
        headline = self._headline(
            recommendation,
            profile,
            terms
        )
        short_version = self._short_version(
            recommendation,
            media,
            terms,
            profile,
            context_snapshot
        )
        long_version = self._long_version(
            recommendation,
            media,
            terms,
            profile,
            context_snapshot
        )
        reasoning = self._reasoning(
            recommendation,
            media,
            terms,
            context_snapshot,
            writing_style
        )
        reasoning.extend(
            self._memory_reasoning(
                writing_memory
            )
        )

        package = {
            "headline": headline,
            "facebook_caption": self._facebook_caption(
                headline,
                short_version,
                cta,
                facebook_hashtags,
                emojis
            ),
            "instagram_caption": self._instagram_caption(
                headline,
                short_version,
                cta,
                instagram_hashtags,
                emojis
            ),
            "linkedin_caption": self._linkedin_caption(
                headline,
                long_version,
                cta
            ),
            "short_version": short_version,
            "long_version": long_version,
            "call_to_action": cta,
            "hashtags": hashtags,
            "facebook_hashtags": facebook_hashtags,
            "instagram_hashtags": instagram_hashtags,
            "emoji_suggestions": emojis,
            "suggested_posting_time": recommendation.get(
                "best_posting_time",
                ""
            ),
            "suggested_media": media,
            "reasoning": reasoning,
            "writing_style": profile["label"],
            "opportunity_type": opportunity_type,
            "editorial_strategy": editorial_strategy or {},
            "source_note": (
                "Generated from stored Department Knowledge, Context, "
                "Recommendation data, and Media Intelligence only. "
                "No Vision AI is used for writing."
            )
        }

        package = self.writing.generate(
            {
                "recommendation": recommendation,
                "media_intelligence": media,
                "department_knowledge": knowledge,
                "communications_memory": writing_memory,
                "context": context_snapshot,
                "opportunity_type": opportunity_type,
                "platforms": [
                    "facebook",
                    "instagram",
                    "linkedin"
                ],
                "base_package": package
            }
        )
        status = self.writing.status()
        package["writing_provider"] = status.get("active_provider", "")
        package["writing_model"] = status.get("active_model", "")
        package["writing_fallback_used"] = status.get("fallback_used", False)
        package["writing_provider_error"] = status.get("last_error", "")
        review = self.editorial_review.review_package(
            package
        )
        package["editorial_review"] = review
        package["editorial_score"] = review.get(
            "overall_score",
            0
        )

        logger.info(
            (
                "Generated communication package opportunity=%s style=%s "
                "media=%s writing_provider=%s fallback=%s editorial_score=%s"
            ),
            opportunity_type,
            writing_style,
            len(media),
            package["writing_provider"],
            package["writing_fallback_used"],
            package["editorial_score"]
        )

        return package

    ############################################################

    def generate_from_package(
        self,
        communication_package,
        platforms=None,
        include_mock=False
    ):

        started = time.perf_counter()
        package = dict(communication_package or {})
        platforms = [
            platform
            for platform in (platforms or self.PLATFORMS)
            if platform in self.PLATFORMS
        ]

        if not platforms:
            platforms = list(self.PLATFORMS)

        source = self._package_source(
            package,
            include_mock=include_mock
        )
        source["communications_intelligence"] = (
            self.communications_intelligence.profile()
        )
        outputs = {}

        for platform in platforms:
            outputs[platform] = self._platform_output(
                platform,
                package,
                source
            )

        word_counts = {
            platform: self._word_count(output.get("copy_text", ""))
            for platform, output in outputs.items()
        }
        generated = {
            "source_package": package,
            "facebook": outputs.get("facebook", {}),
            "instagram": outputs.get("instagram", {}),
            "linkedin": outputs.get("linkedin", {}),
            "website": outputs.get("website", {}),
            "news_release": outputs.get("news_release", {}),
            "newsletter": outputs.get("newsletter", {}),
            "copy_buttons": {
                platform: output.get("copy_text", "")
                for platform, output in outputs.items()
            },
            "word_counts": word_counts,
            "estimated_reading_time": {
                platform: self._reading_time(words)
                for platform, words in word_counts.items()
            },
            "generation_timestamp": TimeService.utc_now_iso(),
            "generation_version": self.GENERATION_VERSION,
            "communications_intelligence": self._profile_summary(
                source.get("communications_intelligence", {})
            ),
            "department_voice_match": {
                platform: self.communications_intelligence.voice_match(
                    output.get("copy_text", ""),
                    platform,
                    profile=source.get("communications_intelligence", {})
                )
                for platform, output in outputs.items()
            },
            "internal_warning": self._internal_warning(package),
            "writing_provider": "deterministic",
            "writing_model": self.GENERATION_VERSION,
            "writing_fallback_used": False,
            "writing_provider_error": "",
            "performance": {
                "total_seconds": round(time.perf_counter() - started, 3),
                "platform_count": len(outputs)
            }
        }
        generated["generated_content_audit"] = (
            self.explainability.audit_generated_content(
                generated,
                persist=False
            )
        )
        logger.info(
            "Generated multi-platform content package platforms=%s elapsed=%s",
            len(outputs),
            generated["performance"]["total_seconds"]
        )

        return generated

    ############################################################

    def regenerate_platform(self, generated_package, platform):

        platform = str(platform or "").lower()

        if platform not in self.PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")

        package = dict(generated_package or {})
        source_package = package.get("source_package", {})
        source = self._package_source(source_package)
        source["communications_intelligence"] = (
            self.communications_intelligence.profile()
        )
        output = self._platform_output(
            platform,
            source_package,
            source,
            variant="regenerated"
        )
        package[platform] = output
        package.setdefault("copy_buttons", {})[platform] = output.get(
            "copy_text",
            ""
        )
        package.setdefault("word_counts", {})[platform] = self._word_count(
            output.get("copy_text", "")
        )
        package.setdefault("estimated_reading_time", {})[platform] = self._reading_time(
            package["word_counts"][platform]
        )
        package.setdefault("department_voice_match", {})[platform] = (
            self.communications_intelligence.voice_match(
                output.get("copy_text", ""),
                platform,
                profile=source.get("communications_intelligence", {})
            )
        )
        package["communications_intelligence"] = self._profile_summary(
            source.get("communications_intelligence", {})
        )
        package["generation_timestamp"] = TimeService.utc_now_iso()
        package["generation_version"] = self.GENERATION_VERSION
        package["generated_content_audit"] = (
            self.explainability.audit_generated_content(
                package,
                platform=platform,
                persist=False
            )
        )

        return package

    ############################################################

    def _package_source(self, package, include_mock=False):

        media_package = package.get("media_package", {}) or {}
        media = []

        for key in (
            "primary_photo",
            "primary_video"
        ):
            item = media_package.get(key) or {}

            if item:
                media.append(item)

        for key in (
            "gallery_photos",
            "gallery_videos"
        ):
            media.extend(media_package.get(key) or [])

        filtered = []

        for item in media:
            if item.get("trust_state") in ("rejected_real", "failed"):
                continue

            if item.get("review_status") == "rejected":
                continue

            if item.get("provider") == "mock" and not include_mock:
                continue

            filtered.append(item)

        corrections = []

        for item in filtered[:8]:
            media_id = item.get("media_id")

            if not media_id:
                continue

            try:
                corrections.extend(
                    self.human_feedback.corrections_for_media(media_id)
                )
            except Exception:
                continue

        return {
            "media": filtered,
            "media_package": media_package,
            "platform_media_guidance": package.get(
                "platform_media_guidance",
                media_package.get("platform_media_guidance", {})
            ),
            "knowledge": self.knowledge.snapshot(),
            "memory": self.memory.writing_memory(),
            "corrections": corrections[:12],
            "context": self.context_engine.snapshot()
        }

    def _platform_output(self, platform, package, source, variant="standard"):

        builders = {
            "facebook": self._facebook_output,
            "instagram": self._instagram_output,
            "linkedin": self._linkedin_output,
            "website": self._website_output,
            "news_release": self._news_release_output,
            "newsletter": self._newsletter_output
        }
        output = builders[platform](
            package,
            source,
            variant=variant
        )
        output["word_count"] = self._word_count(
            output.get("copy_text", "")
        )
        output["estimated_reading_time"] = self._reading_time(
            output["word_count"]
        )
        output["platform"] = platform
        output["department_voice_guidance"] = self._voice_guidance(
            platform,
            source
        )
        output["media_guidance"] = self._media_guidance(
            platform,
            source
        )

        return output

    def _facebook_output(self, package, source, variant="standard"):

        headline = package.get("headline", "")
        story = self._story(package)
        today = package.get("why_today_matters", "")
        cta = self._profile_cta(
            package.get("suggested_cta", ""),
            package,
            source,
            "facebook"
        )
        hashtags = self._profile_hashtags(
            package,
            source,
            "facebook"
        )
        emoji = "🚒" if variant == "standard" else "🔥"
        text = "\n\n".join(
            self._clean_lines(
                [
                    f"{emoji} {headline}",
                    story,
                    today,
                    cta,
                    " ".join(hashtags)
                ]
            )
        )

        return {
            "title": "Facebook Post",
            "copy_text": text,
            "hashtags": hashtags,
            "cta": cta,
            "notes": self._notes_with_voice(
                "Community storytelling, moderate length, conversation-oriented.",
                platform="facebook",
                source=source
            )
        }

    def _instagram_output(self, package, source, variant="standard"):

        media = source.get("media", [])
        visual = self._visual_line(media)
        story = self._story(package)
        cta = self._profile_cta(
            package.get("suggested_cta", ""),
            package,
            source,
            "instagram"
        )
        hashtags = self._profile_hashtags(
            package,
            source,
            "instagram"
        )
        text = "\n\n".join(
            self._clean_lines(
                [
                    f"📸 {package.get('headline', '')}",
                    visual,
                    story,
                    cta,
                    " ".join(hashtags)
                ]
            )
        )

        return {
            "title": "Instagram Caption",
            "copy_text": text,
            "hashtags": hashtags,
            "cta": cta,
            "notes": self._notes_with_voice(
                "Visual-first caption with platform-appropriate hashtags.",
                platform="instagram",
                source=source
            )
        }

    def _linkedin_output(self, package, source, variant="standard"):

        headline = package.get("headline", "")
        story = self._story(package)
        audience = ", ".join(package.get("audience", [])[:2])
        cta = self._profile_cta(
            package.get("suggested_cta", ""),
            package,
            source,
            "linkedin"
        )
        text = "\n\n".join(
            self._clean_lines(
                [
                    headline,
                    story,
                    (
                        "This package is best framed around leadership, "
                        f"volunteerism, emergency services readiness, and service to {audience or 'the community'}."
                    ),
                    cta,
                    " ".join(self._profile_hashtags(package, source, "linkedin")[:3])
                ]
            )
        )

        return {
            "title": "LinkedIn Post",
            "copy_text": text,
            "hashtags": self._profile_hashtags(package, source, "linkedin")[:3],
            "cta": cta,
            "notes": self._notes_with_voice(
                "Professional post focused on leadership and public service.",
                platform="linkedin",
                source=source
            )
        }

    def _website_output(self, package, source, variant="standard"):

        headline = package.get("headline", "")
        story = self._story(package)
        evidence = self._evidence_summary(package)
        cta = self._profile_cta(
            package.get("suggested_cta", ""),
            package,
            source,
            "website"
        )
        text = "\n\n".join(
            self._clean_lines(
                [
                    headline,
                    "Overview",
                    story,
                    "Why It Matters",
                    package.get("why_today_matters", ""),
                    "Media Evidence",
                    evidence,
                    "Next Step",
                    cta
                ]
            )
        )

        return {
            "title": "Website Article",
            "copy_text": text,
            "hashtags": [],
            "cta": cta,
            "notes": self._notes_with_voice(
                "SEO-friendly headings and readable paragraphs.",
                platform="website",
                source=source
            )
        }

    def _news_release_output(self, package, source, variant="standard"):

        headline = package.get("headline", "")
        story = self._story(package)
        text = "\n\n".join(
            self._clean_lines(
                [
                    headline,
                    "MORDEN, Man. - [Date] - " + story,
                    "Quote placeholder: [Insert approved spokesperson quote.]",
                    "Contact placeholder: [Insert approved department contact.]"
                ]
            )
        )

        return {
            "title": "News Release",
            "copy_text": text,
            "hashtags": [],
            "cta": "For more information, follow official Morden Fire & Rescue updates.",
            "notes": self._notes_with_voice(
                "Journalistic structure with dateline and placeholders.",
                platform="news_release",
                source=source
            )
        }

    def _newsletter_output(self, package, source, variant="standard"):

        story = self._story(package)
        cta = self._profile_cta(
            package.get("suggested_cta", ""),
            package,
            source,
            "newsletter"
        )
        text = "\n\n".join(
            self._clean_lines(
                [
                    package.get("headline", ""),
                    story,
                    "Community takeaway: " + (
                        package.get("why_today_matters", "") or
                        "This story supports local awareness and preparedness."
                    ),
                    cta
                ]
            )
        )

        return {
            "title": "Newsletter Article",
            "copy_text": text,
            "hashtags": [],
            "cta": cta,
            "notes": self._notes_with_voice(
                "Friendly community summary.",
                platform="newsletter",
                source=source
            )
        }

    ############################################################

    def _profile_summary(self, profile):

        return {
            "sample_count": profile.get("sample_count", 0),
            "learning_confidence": profile.get("learning_confidence", 0),
            "department_voice": profile.get("department_voice", ""),
            "profile_freshness": profile.get("profile_freshness", ""),
            "last_profile_update": profile.get("last_profile_update", ""),
            "explainability": profile.get("explainability", {})
        }

    def _voice_guidance(self, platform, source):

        profile = source.get("communications_intelligence", {}) or {}
        platform_profile = (
            profile.get("platform_profiles", {}) or {}
        ).get(platform, {})

        if not platform_profile or not platform_profile.get("sample_count"):
            return "Insufficient approved communications history for this platform."

        return (
            f"Department voice: {profile.get('department_voice', '')} "
            f"{self.format_platform(platform)} profile is based on "
            f"{platform_profile.get('sample_count', 0)} approved communications; "
            f"average emojis {platform_profile.get('average_emojis', 0)}, "
            f"average hashtags {platform_profile.get('average_hashtags', 0)}."
        )

    def _notes_with_voice(self, note, platform, source):

        guidance = self._voice_guidance(platform, source)

        if guidance:
            return f"{note} {guidance}"

        return note

    ############################################################

    def _media_guidance(self, platform, source):

        media_package = source.get("media_package", {}) or {}
        guidance = source.get("platform_media_guidance", {}) or {}
        platform_label = self.format_platform(platform)
        platform_item = (
            guidance.get(platform_label)
            or guidance.get(platform)
            or guidance.get(platform.lower())
            or {}
        )
        primary = self._media_by_id(
            source.get("media", []),
            platform_item.get("primary_media_id")
        )

        if not primary:
            primary = (
                media_package.get("primary_video")
                if platform == "instagram" and media_package.get("primary_video")
                else media_package.get("primary_photo")
            ) or media_package.get("primary_video") or {}

        support_ids = set(platform_item.get("supporting_media_ids") or [])
        support = [
            item
            for item in source.get("media", [])
            if item.get("media_id") in support_ids
        ]

        if not support:
            support = (
                list(media_package.get("gallery_photos") or []) +
                list(media_package.get("gallery_videos") or [])
            )[:4]

        return {
            "platform": platform,
            "primary_media_id": primary.get("media_id"),
            "primary_filename": primary.get("filename", ""),
            "primary_path": primary.get("path", ""),
            "supporting_media": [
                {
                    "media_id": item.get("media_id"),
                    "filename": item.get("filename", ""),
                    "path": item.get("path", ""),
                    "selected_as": item.get("selected_as", "")
                }
                for item in support[:4]
            ],
            "why": (
                platform_item.get("reason")
                or primary.get("why_selected", "")
                or "Use the selected primary media for this platform."
            ),
            "internal_only": True
        }

    def _media_by_id(self, media, media_id):

        if not media_id:
            return {}

        for item in media:
            if item.get("media_id") == media_id:
                return item

        return {}

    def format_platform(self, platform):

        return str(platform or "").replace("_", " ").title()

    def _profile_cta(self, current, package, source, platform):

        current = str(current or "").strip()
        profile = source.get("communications_intelligence", {}) or {}
        campaign_profile = self._matching_campaign_profile(
            package,
            profile
        )
        common = campaign_profile.get("common_ctas", []) or []

        if not common:
            return current

        generic = (
            "stay connected with morden fire & rescue",
            "for more information, follow official"
        )

        if current and not any(item in current.lower() for item in generic):
            return current

        learned = str(common[0] or "").strip()

        if not learned or self._word_count(learned) > 18:
            return current

        return learned

    def _matching_campaign_profile(self, package, profile):

        text = " ".join(
            str(package.get(key, ""))
            for key in (
                "headline",
                "primary_story",
                "editorial_angle",
                "why_today_matters"
            )
        ).lower()

        for name, campaign in (
            profile.get("campaign_profiles", {}) or {}
        ).items():
            if campaign.get("sample_count", 0) <= 0:
                continue

            if name.lower() in text:
                return campaign

        return {}

    def _profile_hashtags(self, package, source, platform):

        hashtags = self._hashtags_for(
            package,
            platform
        )
        profile = source.get("communications_intelligence", {}) or {}
        platform_profile = (
            profile.get("platform_profiles", {}) or {}
        ).get(platform, {})
        average = platform_profile.get("average_hashtags", 0)

        if not average:
            return hashtags

        target = max(1, min(5, round(average)))

        return hashtags[:target]

    ############################################################

    def _is_communication_package(self, value):

        return (
            isinstance(value, dict) and
            "writing_strategy" in value and
            "media_package" in value and
            "package_scoring" in value
        )

    def _story(self, package):

        return (
            package.get("primary_story")
            or package.get("summary")
            or package.get("headline")
            or "This package is ready for communications review."
        )

    def _visual_line(self, media):

        if not media:
            return "Use the strongest approved or corrected visual from this package."

        roles = [
            str(item.get("selected_as") or item.get("media_type") or "media").replace(
                "_",
                " "
            )
            for item in media[:3]
        ]

        return "Visual focus: " + ", ".join(roles)

    def _evidence_summary(self, package):

        evidence = package.get("supporting_evidence") or []

        if evidence:
            safe = []

            for item in evidence[:4]:
                text = str(item)

                if ".jpg" in text.lower() or ".jpeg" in text.lower() or ".png" in text.lower() or ".mp4" in text.lower():
                    continue

                if "effective description:" in text.lower():
                    text = text.split(":", 1)[-1].strip()

                safe.append(text)

            if safe:
                return " ".join(safe)

        return package.get("trust_label", "Evidence should be reviewed before publishing.")

    def _hashtags_for(self, package, platform):

        base = list(package.get("suggested_hashtags") or [])
        platform_defaults = {
            "facebook": ["#MordenFireRescue", "#CommunitySafety"],
            "instagram": ["#Morden", "#FireService", "#Community"],
            "linkedin": ["#PublicSafety", "#CommunityService", "#Volunteerism"]
        }

        for tag in platform_defaults.get(platform, []):
            if tag not in base:
                base.append(tag)

        return base[:5]

    def _internal_warning(self, package):

        trust = (
            package.get("trust_label", "") +
            " " +
            package.get("trust_level", "")
        ).lower()

        if "fallback" in trust or "unreviewed" in trust:
            return "Review AI-generated facts before publishing."

        return ""

    def _word_count(self, value):

        return len(
            [
                word
                for word in str(value or "").split()
                if word.strip()
            ]
        )

    def _reading_time(self, words):

        words = max(0, int(words or 0))

        if words <= 0:
            return "0 min"

        return f"{max(1, round(words / 220))} min"

    def _clean_lines(self, values):

        return [
            str(value).strip()
            for value in values
            if str(value or "").strip()
        ]

    ############################################################

    def style_for_opportunity(self, opportunity_type):

        return self.STYLE_BY_OPPORTUNITY.get(
            opportunity_type,
            "community"
        )

    ############################################################

    def _opportunity_from_strategy(self, strategy_type, default):

        mapping = {
            "community_education": "smoke_alarm_reminder",
            "recruitment": "recruitment",
            "community_trust": "community_appreciation",
            "training_highlight": "training_highlight",
            "volunteer_recognition": "volunteer_recognition",
            "technical_education": "training_highlight",
            "incident_recap": "general_engagement",
            "apparatus_feature": "apparatus_showcase",
            "public_education": "fire_prevention_week",
            "seasonal_safety": "holiday_safety",
            "behind_the_scenes": "behind_the_scenes",
            "historical_throwback": "throwback_thursday",
            "annual_report": "general_engagement",
            "website_feature": "general_engagement"
        }

        return mapping.get(
            strategy_type,
            default
        )

    ############################################################

    def ensure_default_templates(self):

        if self.db.content_templates():
            return

        for template in self.DEFAULT_TEMPLATES:
            self.db.save_content_template(template)

    ############################################################

    def templates(self, writing_style=None, platform=None):

        return self.db.content_templates(
            writing_style=writing_style,
            platform=platform
        )

    ############################################################

    def _media_context(self, recommended_media):

        media_context = []

        for item in recommended_media or []:
            intelligence = self.db.get_media_intelligence(
                item.get("media_id")
            )
            intelligence = intelligence or {}
            media_context.append(
                {
                    "media_id": item.get("media_id"),
                    "filename": item.get("filename", ""),
                    "path": item.get("path", ""),
                    "reason": item.get("reason", ""),
                    "intelligence_score": item.get(
                        "intelligence_score",
                        intelligence.get("intelligence_score", 0)
                    ),
                    "incident_type": intelligence.get("incident_type", ""),
                    "primary_activity": intelligence.get("primary_activity", ""),
                    "content_tags": intelligence.get("content_tags", []),
                    "content_themes": intelligence.get("content_themes", []),
                    "recommended_uses": intelligence.get("recommended_uses", []),
                    "apparatus_tags": intelligence.get("apparatus_tags", []),
                    "equipment_tags": intelligence.get("equipment_tags", []),
                    "ppe_tags": intelligence.get("ppe_tags", []),
                    "search_text": intelligence.get("search_text", "")
                }
            )

        return media_context

    ############################################################

    def _department_terms(self, knowledge, recommendation, media):

        terms = []
        profile = knowledge.get("profile", {})

        for value in (
            profile.get("department_name"),
            profile.get("short_name"),
            profile.get("community")
        ):
            self._append_unique(terms, value)

        source_text = " ".join(
            [
                recommendation.get("title", ""),
                recommendation.get("caption_strategy", ""),
                recommendation.get("call_to_action", ""),
                " ".join(recommendation.get("reasoning", [])),
                " ".join(
                    " ".join(item.get(field, []) if isinstance(item.get(field), list) else [item.get(field, "")])
                    for item in media
                    for field in (
                        "content_tags",
                        "content_themes",
                        "recommended_uses",
                        "search_text"
                    )
                )
            ]
        ).lower()

        for table in (
            "community_partners",
            "response_area",
            "locations",
            "programs",
            "apparatus",
            "annual_events"
        ):
            for item in knowledge.get(table, []):
                name = item.get("name", "")
                tags = " ".join(item.get("tags", []))

                if (
                    name.lower() in source_text or
                    any(tag.lower() in source_text for tag in item.get("tags", [])) or
                    table in ("locations", "response_area", "community_partners")
                ):
                    self._append_unique(terms, name)
                    if tags:
                        pass

        return terms[:12]

    ############################################################

    def _headline(self, recommendation, profile, terms):

        title = recommendation.get(
            "title",
            profile["lead"]
        )
        department = terms[0] if terms else "Morden Fire & Rescue"

        return f"{department}: {title}"

    ############################################################

    def _short_version(self, recommendation, media, terms, profile, context_snapshot):

        opportunity = recommendation.get("opportunity_type", "")

        if opportunity == "heat_warning":
            return (
                "Heat can become dangerous quickly, especially for children, "
                "seniors, outdoor workers, and anyone without access to a cool "
                "space.\n\n"
                "Drink water often, check on neighbours and family members, "
                "avoid strenuous activity during the hottest part of the day, "
                "and never leave people or pets in a parked vehicle.\n\n"
                "Small actions can prevent a medical emergency."
            )

        if opportunity in ("storm_safety", "holiday_safety", "fire_prevention_week"):
            return (
                f"{profile['lead']} for Morden residents.\n\n"
                "Take a few minutes to prepare, talk through your plan, and "
                "look out for the people around you."
            )

        if opportunity in ("recruitment", "training_highlight"):
            return (
                "Training, teamwork, and service are at the heart of the fire "
                "department.\n\n"
                "If serving your community has been on your mind, this is a "
                "good time to learn more."
            )

        if self._media_match_score(recommendation, media) < 2:
            return (
                f"{profile['lead']} for the Morden community.\n\n"
                "We are sharing this as a timely reminder to stay prepared, "
                "stay connected, and look out for one another."
            )

        return (
            f"{profile['lead']} for the Morden community.\n\n"
            f"{self._media_detail(media)}"
        ).strip()

    ############################################################

    def _long_version(
        self,
        recommendation,
        media,
        terms,
        profile,
        context_snapshot
    ):

        active_context = self._context_text(
            context_snapshot
        )
        detail = self._short_version(
            recommendation,
            media,
            terms,
            profile,
            context_snapshot
        )
        reason = " ".join(
            recommendation.get("reasoning", [])[:2]
        )

        return (
            f"{detail} "
            f"{active_context} "
            f"{reason}"
        ).strip()

    ############################################################

    def _media_detail(self, media):

        if not media:
            return "This message can stand on its own as a public-safety post."

        top = media[0]
        activity = self._format_label(
            top.get("primary_activity", "")
        ).lower()
        incident = self._format_label(
            top.get("incident_type", "")
        ).lower()

        if activity and activity not in ("", "unknown"):
            return (
                "The media supports a simple, public-facing story about " +
                activity + "."
            )

        if incident and incident not in ("", "unknown"):
            return (
                "The media supports a simple, public-facing story connected "
                "to " + incident + "."
            )

        return "The media can support a broader community-safety message."

    ############################################################

    def _facebook_caption(self, headline, short_version, cta, hashtags, emojis):

        emoji_prefix = " ".join(emojis[:2])
        close = "Stay safe and look out for each other, Morden."

        return self._clean(
            (
                f"{emoji_prefix} {short_version}\n\n"
                f"{close}\n\n"
                f"{cta}\n\n"
                f"{' '.join(hashtags[:5])}"
            )
        )

    ############################################################

    def _instagram_caption(self, headline, short_version, cta, hashtags, emojis):

        emoji_prefix = " ".join(emojis[:4])

        return self._clean(
            (
                f"{emoji_prefix} {short_version}\n\n"
                f"{cta}\n\n"
                f"{' '.join(hashtags[:5])}"
            )
        )

    ############################################################

    def _linkedin_caption(self, headline, long_version, cta):

        return self._clean(
            f"{headline}\n\n{long_version}\n\n{cta}"
        )

    ############################################################

    def _platform_hashtags(self, recommendation, media, platform):

        opportunity = recommendation.get("opportunity_type", "")
        tags = []
        defaults = {
            "heat_warning": [
                "#HeatSafety",
                "#MordenFireRescue",
                "#CommunitySafety",
                "#SummerSafety",
                "#Morden"
            ],
            "storm_safety": [
                "#StormSafety",
                "#MordenFireRescue",
                "#CommunitySafety",
                "#EmergencyPreparedness",
                "#Morden"
            ],
            "recruitment": [
                "#MordenFireRescue",
                "#Recruitment",
                "#JoinTheTeam",
                "#CommunityService",
                "#Morden"
            ],
            "training_highlight": [
                "#MordenFireRescue",
                "#Training",
                "#FireService",
                "#CommunitySafety",
                "#Morden"
            ],
            "fire_prevention_week": [
                "#FirePrevention",
                "#MordenFireRescue",
                "#CommunitySafety",
                "#FireSafety",
                "#Morden"
            ]
        }

        for tag in defaults.get(opportunity, []):
            self._append_unique(tags, tag)

        for tag in recommendation.get("hashtags", []):
            self._append_unique(tags, tag)

        for item in media:
            for value in (
                item.get("content_tags", []) +
                item.get("content_themes", []) +
                item.get("recommended_uses", [])
            ):
                if len(tags) >= 5:
                    break

                if not self._tag_allowed(value, opportunity):
                    continue

                tag = "#" + "".join(
                    part.capitalize()
                    for part in str(value).replace("-", "_").split("_")
                    if part
                )
                self._append_unique(tags, tag)

        if "#MordenFireRescue" not in tags:
            self._append_unique(tags, "#MordenFireRescue")

        return self._unique(tags)[:5]

    ############################################################

    def _emoji_suggestions(self, writing_style, media, opportunity_type=""):

        if opportunity_type == "heat_warning":
            return [
                "\u2600\ufe0f",
                "\U0001f4a7",
                "\U0001f3e0",
                "\U0001f692"
            ]

        suggestions = {
            "community": ["\U0001f91d", "\u2764\ufe0f", "\U0001f341"],
            "educational": ["\u2705", "\U0001f3e0", "\U0001f6a8"],
            "recruitment": ["\U0001fa96", "\U0001f91d", "\U0001f9d1\u200d\U0001f692"],
            "incident_recap": ["\u2139\ufe0f", "\U0001f692"],
            "recognition": ["\u2b50", "\U0001f44f", "\u2764\ufe0f"],
            "apparatus_feature": ["\U0001f692", "\U0001f6e0\ufe0f", "\u2699\ufe0f"],
            "training": ["\U0001fa96", "\U0001f6e0\ufe0f", "\U0001f91d"],
            "safety_campaign": ["\u26a0\ufe0f", "\u2705", "\U0001f3e0"],
            "holiday": ["\U0001f4c5", "\U0001f56f\ufe0f", "\u2705"],
            "behind_the_scenes": ["\U0001fa96", "\U0001f3e2", "\U0001f91d"]
        }.get(
            writing_style,
            ["\U0001f91d", "\u2705"]
        )

        if any("water" in item for item in self._media_terms(media)):
            suggestions.append("\U0001f4a7")

        return self._unique(suggestions)[:5]

    ############################################################

    def _media_match_score(self, recommendation, media):

        if not media:
            return 0

        source = " ".join(
            [
                recommendation.get("opportunity_type", ""),
                recommendation.get("title", ""),
                recommendation.get("caption_theme", ""),
                " ".join(recommendation.get("recommended_uses", [])),
                " ".join(recommendation.get("hashtags", []))
            ]
        ).lower()
        score = 0

        for term in self._media_terms(media):
            plain = term.replace("_", " ").lower()

            if term in source or plain in source:
                score += 1

        return score

    ############################################################

    def _tag_allowed(self, value, opportunity):

        token = self._token(value)

        if token in (
            "engine",
            "hose",
            "scba",
            "helmet",
            "turnout_gear",
            "apparatus",
            "equipment",
            "social_media"
        ):
            return False

        if token == "hydrant_heroes" and opportunity != "hydrant_heroes":
            return False

        return token in (
            "community",
            "community_safety",
            "fire_safety",
            "public_education",
            "recruitment",
            "training",
            "heat_safety",
            "summer_safety",
            "storm_safety",
            "fire_prevention",
            "smoke_alarm",
            "water_safety"
        )

    ############################################################

    def _reasoning(
        self,
        recommendation,
        media,
        terms,
        context_snapshot,
        writing_style
    ):

        reasoning = [
            "Package generated without Vision AI or external APIs.",
            "Uses stored recommendation reasoning and Media Intelligence only.",
            f"Writing style selected: {self.WRITING_STYLES[writing_style]['label']}."
        ]

        if terms:
            reasoning.append(
                "Department knowledge used: " + ", ".join(terms[:8]) + "."
            )

        if media:
            reasoning.append(
                f"Suggested media count: {len(media)}."
            )

        context_text = self._context_text(
            context_snapshot
        )

        if context_text:
            reasoning.append(context_text)

        reasoning.extend(
            recommendation.get("reasoning", [])[:3]
        )

        return self._unique(reasoning)

    ############################################################

    def _context_text(self, snapshot):

        values = []

        if hasattr(snapshot, "active_themes"):
            values = snapshot.active_themes[:4]
        elif isinstance(snapshot, dict):
            values = snapshot.get("active_themes", [])[:4]

        if not values:
            return ""

        return (
            "Current context: " +
            ", ".join(self._format_label(value) for value in values) +
            "."
        )

    ############################################################

    def _memory_reasoning(self, writing_memory):

        if not writing_memory:
            return []

        reasoning = []

        if writing_memory.get("common_openings"):
            reasoning.append(
                (
                    "Communications Memory considered common opening-hook "
                    "patterns without copying previous posts."
                )
            )

        if writing_memory.get("common_ctas"):
            reasoning.append(
                "Communications Memory considered historical CTA style."
            )

        if writing_memory.get("top_hashtags"):
            reasoning.append(
                "Communications Memory considered historically used hashtags."
            )

        if writing_memory.get("campaigns"):
            reasoning.append(
                "Communications Memory considered known campaign history."
            )

        return reasoning

    ############################################################

    def _term_text(self, terms):

        if not terms:
            return "Morden Fire & Rescue"

        return ", ".join(terms[:6])

    ############################################################

    def _media_terms(self, media):

        terms = []

        for item in media:
            for key in (
                "content_tags",
                "content_themes",
                "recommended_uses",
                "equipment_tags",
                "apparatus_tags"
            ):
                terms.extend(item.get(key) or [])

        return [
            self._token(term)
            for term in terms
            if term
        ]

    ############################################################

    def _format_label(self, value):

        return str(value or "").replace(
            "_",
            " "
        ).title()

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )

    ############################################################

    def _clean(self, value):

        return "\n\n".join(
            " ".join(line.strip().split())
            for line in str(value or "").splitlines()
            if line.strip()
        )

    ############################################################

    def _append_unique(self, values, value):

        if value and value not in values:
            values.append(value)

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
