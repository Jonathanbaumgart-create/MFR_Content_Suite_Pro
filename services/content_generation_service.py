from core.app_context import context
from services.context_engine import ContextEngine
from services.communications_memory_service import CommunicationsMemoryService
from services.editorial_review_service import EditorialReviewService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.writing_service import WritingService


logger = LoggingService.get_logger("content")


class ContentGenerationService:

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
        writing_style=None
    ):

        opportunity_type = opportunity_type or recommendation.get(
            "opportunity_type",
            "general_engagement"
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

    def style_for_opportunity(self, opportunity_type):

        return self.STYLE_BY_OPPORTUNITY.get(
            opportunity_type,
            "community"
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
