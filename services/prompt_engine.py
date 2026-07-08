import json

from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class PromptEngine:

    SECTION_TITLES = (
        "Department Identity",
        "Community",
        "Communication Goal",
        "Audience",
        "Writing Style",
        "Season",
        "Current Context",
        "Media Intelligence Summary",
        "Department Knowledge",
        "Communications Memory",
        "Writing Pattern Summary",
        "Recommendation Reasoning",
        "Platform Instructions"
    )

    WRITING_OBJECTIVES = (
        "natural",
        "community focused",
        "trust building",
        "conversational",
        "positive",
        "educational",
        "shareable",
        "emotionally engaging"
    )

    def build_all(self, request):

        platforms = request.get("platforms") or [
            "facebook",
            "instagram",
            "linkedin"
        ]
        dna = self.editorial_dna(
            request.get("communications_memory", {}),
            request.get("writing_patterns", {})
        )
        prompts = {}

        for platform in platforms:
            prompts[platform] = self.build_prompt(
                request,
                platform,
                dna
            )

        logger.info(
            "Prompt engine built prompts platforms=%s opportunity=%s",
            ",".join(platforms),
            request.get("opportunity_type", "")
        )

        return {
            "prompts": prompts,
            "editorial_dna": dna,
            "prompt_sections": list(self.SECTION_TITLES)
        }

    def build_prompt(self, request, platform, editorial_dna=None):

        editorial_dna = editorial_dna or self.editorial_dna(
            request.get("communications_memory", {}),
            request.get("writing_patterns", {})
        )
        context = self._mapping(
            request.get("context", {})
        )
        recommendation = request.get("recommendation", {})
        knowledge = request.get("department_knowledge", {})
        memory = request.get("communications_memory", {})
        media = request.get("media_intelligence", [])
        preferences = request.get("learning_preferences", {})
        opportunity = request.get("opportunity_type", "")

        sections = [
            self._section(
                "Department Identity",
                self._department_identity(knowledge)
            ),
            self._section(
                "Community",
                self._community(knowledge)
            ),
            self._section(
                "Communication Goal",
                self._goal(recommendation, opportunity)
            ),
            self._section(
                "Audience",
                self._audience(opportunity, knowledge)
            ),
            self._section(
                "Writing Style",
                self._writing_style(recommendation, preferences, editorial_dna)
            ),
            self._section(
                "Season",
                self._string_value(context.get("season"))
            ),
            self._section(
                "Current Context",
                self._context_summary(context)
            ),
            self._section(
                "Media Intelligence Summary",
                self._media_summary(media)
            ),
            self._section(
                "Department Knowledge",
                self._knowledge_summary(knowledge)
            ),
            self._section(
                "Communications Memory",
                self._memory_summary(memory)
            ),
            self._section(
                "Writing Pattern Summary",
                self._json(editorial_dna)
            ),
            self._section(
                "Recommendation Reasoning",
                self._reasoning(recommendation)
            ),
            self._section(
                "Platform Instructions",
                self.platform_rules(platform)
            )
        ]

        prompt = """
You are the local writing assistant for Morden Fire & Rescue.

Write public social media copy using only the supplied local data. Do not
inspect images. Do not invent incident details, dates, injuries, locations,
causes, names, outcomes, or partner involvement. If a fact is not supplied,
omit it.

Write toward these objectives:
%s

Avoid stock AI phrasing, internal field labels, keyword stuffing, repeated
department naming, and generic reminder language. Do not mention the writing
system, providers, prompts, databases, scores, or internal service names.

Return only valid JSON using this structure:
{
  "facebook_caption": "",
  "instagram_caption": "",
  "linkedin_caption": "",
  "short_version": "",
  "long_version": "",
  "call_to_action": "",
  "facebook_hashtags": [],
  "instagram_hashtags": [],
  "hashtags": [],
  "emoji_suggestions": [],
  "reasoning": []
}

Source brief:
%s
""" % (
            "\n".join(f"- {item}" for item in self.WRITING_OBJECTIVES),
            "\n\n".join(sections)
        )

        return prompt.strip()

    def editorial_dna(self, communications_memory=None, writing_patterns=None):

        memory = communications_memory or {}
        patterns = writing_patterns or {}
        average_length = self._number(
            memory.get("average_caption_length"),
            160
        )
        average_hashtags = self._number(
            memory.get("average_hashtags"),
            3
        )
        average_emojis = self._number(
            memory.get("average_emojis"),
            3
        )
        openings = self._list(
            memory.get("common_openings")
        )[:5]
        ctas = self._list(
            memory.get("common_ctas")
        )[:5]
        hashtags = self._list(
            memory.get("top_hashtags")
        )[:8]

        return {
            "average_caption_length": average_length,
            "preferred_opening_styles": openings or [
                "warm community opening",
                "direct public-safety lead"
            ],
            "preferred_cta_styles": ctas or [
                "encourage a simple safety action",
                "invite community participation"
            ],
            "emoji_frequency": average_emojis,
            "hashtag_frequency": average_hashtags,
            "paragraph_length": patterns.get(
                "paragraph_length",
                "short readable paragraphs"
            ),
            "writing_tone": patterns.get(
                "writing_tone",
                "professional, warm, community focused"
            ),
            "storytelling_tendency": patterns.get(
                "storytelling_tendency",
                "moderate"
            ),
            "educational_tendency": patterns.get(
                "educational_tendency",
                "strong when safety guidance is present"
            ),
            "humor_frequency": patterns.get(
                "humor_frequency",
                "low"
            ),
            "recognition_style": patterns.get(
                "recognition_style",
                "specific, appreciative, and team focused"
            ),
            "recruitment_style": patterns.get(
                "recruitment_style",
                "service minded and approachable"
            ),
            "public_education_style": patterns.get(
                "public_education_style",
                "clear, practical, and calm"
            ),
            "top_hashtags": hashtags,
            "campaigns": self._list(memory.get("campaigns"))[:5]
        }

    def platform_rules(self, platform):

        platform = str(platform or "").lower()

        if platform == "instagram":
            return (
                "Instagram: visual, conversational, and community oriented. "
                "Use 4 to 6 relevant emojis and up to 5 hashtags. Keep the "
                "caption easy to scan and avoid large hashtag blocks."
            )

        if platform == "linkedin":
            return (
                "LinkedIn: professional, leadership focused, and suitable for "
                "community partnerships. Use minimal emojis and no more than "
                "3 hashtags. Keep the tone polished and public-service minded."
            )

        return (
            "Facebook: storytelling, medium length, and easy for residents to "
            "share. Use 3 to 4 relevant emojis and up to 5 hashtags. Lead with "
            "community value and end with a clear call to action."
        )

    def _section(self, title, body):

        return f"{title}\n{body or 'No local data supplied.'}"

    def _department_identity(self, knowledge):

        profile = knowledge.get("profile", {}) if isinstance(knowledge, dict) else {}
        department = (
            profile.get("department_name") or
            profile.get("name") or
            "Morden Fire & Rescue"
        )
        mission = profile.get("mission_statement") or profile.get("mission") or ""
        values = self._list(profile.get("core_values") or profile.get("values"))

        parts = [department]

        if mission:
            parts.append(mission)

        if values:
            parts.append("Values: " + ", ".join(values[:6]))

        return "\n".join(parts)

    def _community(self, knowledge):

        values = []

        for key in (
            "response_area",
            "locations",
            "community_partners"
        ):
            values.extend(
                self._names(knowledge.get(key, []))
            )

        return ", ".join(self._unique(values)[:12])

    def _goal(self, recommendation, opportunity):

        return "\n".join(
            item
            for item in (
                recommendation.get("title", ""),
                recommendation.get("summary", ""),
                recommendation.get("caption_theme", ""),
                opportunity
            )
            if item
        )

    def _audience(self, opportunity, knowledge):

        programs = knowledge.get("programs", []) if isinstance(knowledge, dict) else []
        audiences = []

        for program in programs:
            if isinstance(program, dict) and program.get("audience"):
                audiences.append(program["audience"])

        if audiences:
            return ", ".join(self._unique(audiences)[:8])

        if "recruit" in str(opportunity).lower():
            return "prospective firefighters, families, and community supporters"

        return "residents, local families, community partners, and followers"

    def _writing_style(self, recommendation, preferences, editorial_dna):

        values = [
            recommendation.get("writing_style", ""),
            recommendation.get("caption_theme", ""),
            editorial_dna.get("writing_tone", "")
        ]
        preferred = self._list(preferences.get("preferred_content_themes"))

        if preferred:
            values.append("Preferred themes: " + ", ".join(preferred[:5]))

        return "\n".join(item for item in values if item)

    def _context_summary(self, context):

        keys = (
            "date",
            "day_of_week",
            "active_themes",
            "upcoming_themes",
            "priority_context",
            "suggested_opportunities",
            "explanation"
        )

        return self._json(
            {
                key: context.get(key)
                for key in keys
                if context.get(key)
            }
        )

    def _media_summary(self, media):

        summaries = []

        for item in self._list(media)[:5]:
            if not isinstance(item, dict):
                continue

            summaries.append(
                {
                    "filename": item.get("filename", ""),
                    "incident_type": item.get("incident_type", ""),
                    "primary_activity": item.get("primary_activity", ""),
                    "content_tags": item.get("content_tags", []),
                    "content_themes": item.get("content_themes", []),
                    "recommended_uses": item.get("recommended_uses", []),
                    "intelligence_score": item.get("intelligence_score", "")
                }
            )

        return self._json(summaries)

    def _knowledge_summary(self, knowledge):

        if not isinstance(knowledge, dict):
            return self._string_value(knowledge)

        summary = {}

        for key in (
            "programs",
            "apparatus",
            "annual_events",
            "locations",
            "response_area",
            "community_partners"
        ):
            names = self._names(
                knowledge.get(key, [])
            )

            if names:
                summary[key] = names[:10]

        profile = knowledge.get("profile", {})

        if isinstance(profile, dict):
            for key in (
                "preferred_terminology",
                "standard_abbreviations",
                "common_hashtags",
                "preferred_writing_style"
            ):
                if profile.get(key):
                    summary[key] = profile[key]

        return self._json(summary)

    def _memory_summary(self, memory):

        return self._json(
            {
                "common_openings": self._list(memory.get("common_openings"))[:5],
                "common_ctas": self._list(memory.get("common_ctas"))[:5],
                "top_hashtags": self._list(memory.get("top_hashtags"))[:8],
                "campaigns": self._list(memory.get("campaigns"))[:5]
            }
        )

    def _reasoning(self, recommendation):

        reasoning = self._list(
            recommendation.get("reasoning")
        )

        if reasoning:
            return "\n".join(f"- {item}" for item in reasoning[:8])

        return recommendation.get("reason", "")

    def _names(self, values):

        names = []

        for item in self._list(values):

            if isinstance(item, dict):
                name = item.get("name") or item.get("title")
            else:
                name = item

            if name:
                names.append(str(name))

        return names

    def _json(self, value):

        return json.dumps(
            value,
            ensure_ascii=True,
            default=str,
            indent=2
        )

    def _string_value(self, value):

        if hasattr(value, "to_dict"):
            return self._json(
                value.to_dict()
            )

        if isinstance(value, (list, tuple, set)):
            return ", ".join(str(item) for item in value if item)

        if isinstance(value, dict):
            return self._json(value)

        return str(value or "")

    def _mapping(self, value):

        if hasattr(value, "to_dict"):
            return value.to_dict()

        if isinstance(value, dict):
            return value

        return {}

    def _list(self, value):

        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        if isinstance(value, set):
            return list(value)

        return [value]

    def _number(self, value, default):

        try:
            return round(float(value), 1)

        except (TypeError, ValueError):
            return default

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:
            key = str(value).lower()

            if not value or key in seen:
                continue

            seen.add(key)
            unique.append(value)

        return unique
