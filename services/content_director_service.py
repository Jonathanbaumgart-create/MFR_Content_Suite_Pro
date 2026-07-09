from datetime import datetime

from core.app_context import context
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class ContentDirectorService:

    OPPORTUNITY_TYPES = (
        "heat_warning",
        "winter_weather",
        "smoke_alarm",
        "recruitment",
        "training",
        "community",
        "apparatus",
        "fire_prevention",
        "storm_safety",
        "general_engagement"
    )

    PROMPT_RULES = (
        ("heat_warning", ("heat", "hot", "summer", "hydration", "cool down")),
        ("winter_weather", ("winter", "snow", "ice", "cold", "blizzard")),
        ("smoke_alarm", ("smoke alarm", "smoke detector", "alarm")),
        ("recruitment", ("recruit", "recruitment", "volunteer", "join")),
        ("training", ("training", "drill", "exercise")),
        ("community", ("community", "open house", "parade", "event")),
        ("apparatus", ("apparatus", "engine", "ladder", "truck", "rescue")),
        ("fire_prevention", ("fire prevention", "prevention week", "fire safety")),
        ("storm_safety", ("storm", "wind", "power outage", "thunderstorm"))
    )

    PROFILES = {
        "heat_warning": {
            "label": "Heat Warning",
            "keywords": (
                "heat",
                "summer",
                "hydration",
                "safety",
                "public_education",
                "safety_message",
                "community"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Heat safety reminder",
            "hashtags": ("#HeatSafety", "#FireSafety", "#CommunitySafety"),
            "cta": "Check on neighbours, stay hydrated, and call 911 for emergencies.",
            "tone": "Public safety"
        },
        "winter_weather": {
            "label": "Winter Weather",
            "keywords": (
                "winter",
                "snow",
                "ice",
                "cold",
                "safety",
                "public_education",
                "safety_message"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Winter safety reminder",
            "hashtags": ("#WinterSafety", "#FireSafety", "#CommunitySafety"),
            "cta": "Clear exits, drive for conditions, and keep emergency routes open.",
            "tone": "Public safety"
        },
        "smoke_alarm": {
            "label": "Smoke Alarm",
            "keywords": (
                "smoke_alarm",
                "smoke",
                "alarm",
                "detector",
                "prevention",
                "public_education",
                "safety_message"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Smoke alarm reminder",
            "hashtags": ("#SmokeAlarms", "#FirePrevention", "#FireSafety"),
            "cta": "Test your alarms and replace batteries when needed.",
            "tone": "Educational"
        },
        "recruitment": {
            "label": "Recruitment",
            "keywords": (
                "recruitment",
                "recruit",
                "volunteer",
                "join",
                "training",
                "crew",
                "community"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Recruitment post",
            "hashtags": ("#JoinMFR", "#FirefighterRecruitment", "#ServeYourCommunity"),
            "cta": "Learn how you can serve your community with Morden Fire & Rescue.",
            "tone": "Inviting"
        },
        "training": {
            "label": "Training",
            "keywords": (
                "training",
                "drill",
                "exercise",
                "technical_training",
                "hose",
                "scba",
                "crew"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Training highlight",
            "hashtags": ("#FireTraining", "#Preparedness", "#Teamwork"),
            "cta": "Follow along for more behind-the-scenes training updates.",
            "tone": "Professional"
        },
        "community": {
            "label": "Community",
            "keywords": (
                "community",
                "community_outreach",
                "open_house",
                "parade",
                "event",
                "social_media"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Community engagement",
            "hashtags": ("#Community", "#Morden", "#MordenFireRescue"),
            "cta": "Stay connected with Morden Fire & Rescue for local safety updates.",
            "tone": "Community"
        },
        "apparatus": {
            "label": "Apparatus",
            "keywords": (
                "apparatus",
                "engine",
                "ladder",
                "rescue",
                "tanker",
                "brush",
                "station"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Apparatus feature",
            "hashtags": ("#FireApparatus", "#MordenFireRescue", "#EmergencyServices"),
            "cta": "Watch for crews and give emergency vehicles room to work.",
            "tone": "Informational"
        },
        "fire_prevention": {
            "label": "Fire Prevention",
            "keywords": (
                "fire_prevention",
                "prevention",
                "public_education",
                "education",
                "safety",
                "safety_message"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Fire prevention reminder",
            "hashtags": ("#FirePrevention", "#FireSafety", "#CommunitySafety"),
            "cta": "Make fire safety part of your routine at home and at work.",
            "tone": "Educational"
        },
        "storm_safety": {
            "label": "Storm Safety",
            "keywords": (
                "storm",
                "wind",
                "weather",
                "public_education",
                "safety",
                "safety_message"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Storm safety reminder",
            "hashtags": ("#StormSafety", "#Preparedness", "#CommunitySafety"),
            "cta": "Secure loose items, prepare for outages, and avoid downed lines.",
            "tone": "Public safety"
        },
        "general_engagement": {
            "label": "General Engagement",
            "keywords": (
                "community",
                "social_media",
                "training",
                "public_education",
                "crew"
            ),
            "platforms": ("Facebook", "Instagram"),
            "theme": "Community update",
            "hashtags": ("#MordenFireRescue", "#CommunitySafety", "#FireService"),
            "cta": "Follow Morden Fire & Rescue for updates and safety reminders.",
            "tone": "Community"
        }
    }

    def __init__(self, database=None):

        self.db = database or context.database
        self.knowledge = KnowledgeService(
            database=self.db
        )

    ############################################################

    def interpret_prompt(self, prompt):

        text = self._normalize(prompt)
        matches = []

        for opportunity, terms in self.PROMPT_RULES:

            if any(term in text for term in terms):
                matches.append(opportunity)

        if not matches:
            matches.append("general_engagement")

        return matches

    ############################################################

    def daily_opportunities(self, today=None):

        today = today or datetime.now()
        month = today.month
        opportunities = []

        if month in (12, 1, 2):
            opportunities.append("winter_weather")

        if month in (6, 7, 8):
            opportunities.append("heat_warning")

        if month == 10:
            opportunities.append("fire_prevention")

        opportunities.extend(
            (
                "recruitment",
                "community"
            )
        )

        return [
            {
                "type": opportunity,
                "label": self.PROFILES[opportunity]["label"],
                "prompt": self.PROFILES[opportunity]["theme"]
            }
            for opportunity in self._unique(opportunities)
        ]

    ############################################################

    def recommend(self, prompt="", opportunity_types=None, limit=5):

        opportunities = opportunity_types or self.interpret_prompt(prompt)

        candidates = self.db.content_director_candidates(
            limit=max(500, limit * 50)
        )

        recommendations = []

        for candidate in candidates:

            scored = self._score_candidate(
                candidate,
                opportunities
            )

            if scored["score"] <= 0:
                continue

            scored["captions"] = self.draft_captions(
                scored,
                opportunities
            )

            recommendations.append(scored)

        recommendations.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        logger.info(
            "Content Director request prompt=%s opportunities=%s candidates=%s results=%s",
            prompt,
            opportunities,
            len(candidates),
            len(recommendations[:limit])
        )

        return {
            "prompt": prompt,
            "opportunity_types": opportunities,
            "recommendations": recommendations[:limit]
        }

    ############################################################

    def draft_captions(self, recommendation, opportunity_types):

        opportunity = self._primary_opportunity(opportunity_types)
        profile = self.PROFILES[opportunity]
        strategy = self.knowledge.caption_strategy(
            self._communication_opportunity(opportunity),
            profile["theme"]
        )
        cta = self.knowledge.call_to_action(
            self._communication_opportunity(opportunity),
            profile["cta"]
        )
        reason = recommendation.get("reason", "")
        filename = recommendation.get("filename", "this media")

        facebook = (
            f"{strategy}: {cta} "
            f"This library item was recommended because {reason.lower()}."
        )

        instagram = (
            f"{strategy}. "
            f"{cta}"
        )

        return {
            "facebook_caption": facebook,
            "instagram_caption": instagram,
            "hashtags": list(profile["hashtags"]),
            "call_to_action": cta,
            "tone_label": profile["tone"],
            "source_filename": filename
        }

    ############################################################

    def _score_candidate(self, candidate, opportunity_types):

        score = min(
            50,
            int(candidate.get("intelligence_score") or 0) * 0.5
        )
        reasons = []
        matched_terms = set()

        searchable = self._candidate_terms(candidate)

        for opportunity in opportunity_types:

            profile = self.PROFILES.get(
                opportunity,
                self.PROFILES["general_engagement"]
            )

            for term in profile["keywords"]:

                term = self._normalize_token(term)

                if term in searchable:
                    matched_terms.add(term)

            score += self._field_score(
                candidate.get("recommended_uses"),
                profile["keywords"],
                24,
                "recommended use",
                reasons
            )
            score += self._field_score(
                candidate.get("content_themes"),
                profile["keywords"],
                18,
                "theme",
                reasons
            )
            score += self._field_score(
                candidate.get("content_tags"),
                profile["keywords"],
                14,
                "tag",
                reasons
            )
            score += self._field_score(
                [candidate.get("incident_type")],
                profile["keywords"],
                12,
                "incident",
                reasons
            )
            score += self._field_score(
                [candidate.get("primary_activity")],
                profile["keywords"],
                10,
                "activity",
                reasons
            )
            score += self._field_score(
                (
                    candidate.get("apparatus_tags", []) +
                    candidate.get("equipment_tags", []) +
                    candidate.get("ppe_tags", [])
                ),
                profile["keywords"],
                8,
                "equipment or apparatus",
                reasons
            )

        if matched_terms:
            reasons.append(
                "matched " + ", ".join(sorted(matched_terms)[:5])
            )

        if not reasons:
            reasons.append("it has a useful intelligence score")

        primary = self._primary_opportunity(opportunity_types)
        profile = self.PROFILES[primary]

        return {
            "media_id": candidate.get("media_id"),
            "path": candidate.get("path"),
            "filename": candidate.get("filename"),
            "media_type": candidate.get("media_type"),
            "score": round(score, 1),
            "reason": "; ".join(self._unique(reasons))[:240],
            "suggested_platforms": list(profile["platforms"]),
            "suggested_caption_theme": profile["theme"],
            "opportunity_type": primary
        }

    ############################################################

    def _field_score(self, values, keywords, weight, label, reasons):

        values = {
            self._normalize_token(value)
            for value in (values or [])
            if value
        }
        keywords = {
            self._normalize_token(value)
            for value in keywords
        }

        matches = values & keywords

        if not matches:
            return 0

        reasons.append(
            f"{label} match: {', '.join(sorted(matches)[:3])}"
        )

        return weight

    ############################################################

    def _candidate_terms(self, candidate):

        terms = []

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "search_text"
        ):
            terms.append(candidate.get(key, ""))

        for key in (
            "apparatus_tags",
            "equipment_tags",
            "ppe_tags",
            "people_tags",
            "content_tags",
            "content_themes",
            "recommended_uses"
        ):
            terms.extend(candidate.get(key) or [])

        fire_service = self._fire_service_intelligence(
            candidate.get("media_id")
        )

        if fire_service:
            for key in (
                "incident_classification",
                "operational_activity",
                "group_size"
            ):
                terms.append(fire_service.get(key, ""))

            for key in (
                "ppe",
                "equipment",
                "apparatus",
                "communications_uses"
            ):
                terms.extend(fire_service.get(key) or [])

        return {
            self._normalize_token(term)
            for term in terms
            if term
        }

    ############################################################

    def _fire_service_intelligence(self, media_id):

        if not media_id:
            return None

        try:
            return self.db.get_fire_service_intelligence(media_id)

        except Exception:
            return None

    ############################################################

    def _primary_opportunity(self, opportunity_types):

        for opportunity in opportunity_types:

            if opportunity in self.PROFILES:
                return opportunity

        return "general_engagement"

    ############################################################

    def _communication_opportunity(self, opportunity):

        mapping = {
            "fire_prevention": "fire_prevention_week",
            "smoke_alarm": "smoke_alarm_reminder",
            "apparatus": "apparatus_showcase",
            "training": "training_highlight",
            "community": "community_appreciation",
            "winter_weather": "holiday_safety"
        }

        return mapping.get(
            opportunity,
            opportunity
        )

    ############################################################

    def _normalize(self, value):

        return str(value or "").strip().lower()

    ############################################################

    def _normalize_token(self, value):

        return self._normalize(value).replace(
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
