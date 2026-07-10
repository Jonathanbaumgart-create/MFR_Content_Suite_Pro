from core.app_context import context
from services.communications_memory_service import CommunicationsMemoryService
from services.context_engine import ContextEngine
from services.human_feedback_service import HumanFeedbackService
from services.knowledge_graph_service import KnowledgeGraphService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.recommendation_learning_service import RecommendationLearningService


logger = LoggingService.get_logger("content")


class EditorialStrategyService:

    STRATEGIES = (
        {
            "strategy_type": "training_highlight",
            "title": "Training Highlight",
            "keywords": (
                "training",
                "training_tuesday",
                "ladder_operations",
                "hose",
                "scba",
                "drill",
                "training_evolution",
                "technical_education"
            ),
            "objective": "Show ongoing preparation and skill development.",
            "audience": "Community members and prospective firefighters",
            "message": "Morden Fire & Rescue trains regularly so crews are ready when the community needs them.",
            "platforms": ("Facebook", "Instagram", "Annual Report"),
            "window": "Evening or Training Tuesday",
            "cta": "Follow along for more behind-the-scenes training updates."
        },
        {
            "strategy_type": "recruitment",
            "title": "Recruitment",
            "keywords": (
                "recruitment",
                "volunteer",
                "firefighter",
                "crew",
                "training",
                "teamwork",
                "community_service"
            ),
            "objective": "Invite community-minded people to consider serving.",
            "audience": "Prospective firefighters",
            "message": "The fire service is built on training, teamwork, and people who want to help.",
            "platforms": ("Facebook", "Instagram"),
            "window": "Evening",
            "cta": "Learn more about serving with Morden Fire & Rescue."
        },
        {
            "strategy_type": "community_trust",
            "title": "Community Trust",
            "keywords": (
                "community",
                "trust_building",
                "public_education",
                "training",
                "recognition",
                "children",
                "families"
            ),
            "objective": "Build confidence in the department through visible readiness and service.",
            "audience": "Morden residents",
            "message": "Local crews are part of the community and prepare to serve it well.",
            "platforms": ("Facebook", "Website"),
            "window": "Afternoon",
            "cta": "Stay connected for safety reminders and department updates."
        },
        {
            "strategy_type": "community_education",
            "title": "Community Education",
            "keywords": (
                "community_education",
                "public_education",
                "safety",
                "prevention",
                "school",
                "children",
                "smoke_alarm"
            ),
            "objective": "Turn the media into a useful public safety teaching moment.",
            "audience": "Families and residents",
            "message": "A simple safety reminder can help prevent emergencies.",
            "platforms": ("Facebook", "Instagram", "Website"),
            "window": "Morning",
            "cta": "Take a moment today to check one safety item at home."
        },
        {
            "strategy_type": "public_education",
            "title": "Public Education",
            "keywords": (
                "public_education",
                "fire_prevention",
                "hydrant_heroes",
                "travelling_sparky",
                "education",
                "safety"
            ),
            "objective": "Support a prevention or safety campaign.",
            "audience": "Residents, students, and families",
            "message": "Fire safety works best when the whole community understands it.",
            "platforms": ("Facebook", "Instagram", "Website"),
            "window": "Morning",
            "cta": "Talk through this safety topic with your household."
        },
        {
            "strategy_type": "technical_education",
            "title": "Technical Education",
            "keywords": (
                "technical_education",
                "ladder_operations",
                "pump_operations",
                "scba",
                "attack_hose",
                "equipment",
                "apparatus"
            ),
            "objective": "Explain fire-service work in a public-safe, educational way.",
            "audience": "Residents and community partners",
            "message": "Firefighting depends on trained people, specialized equipment, and coordinated operations.",
            "platforms": ("Facebook", "LinkedIn", "Website"),
            "window": "Afternoon",
            "cta": "Watch for crews training and give them room to work safely."
        },
        {
            "strategy_type": "incident_recap",
            "title": "Incident Recap",
            "keywords": (
                "structure_fire",
                "vehicle_fire",
                "mvc",
                "emergency_response",
                "incident",
                "medical",
                "hazmat"
            ),
            "objective": "Share a careful, factual response update when appropriate.",
            "audience": "Morden residents and local partners",
            "message": "When emergencies happen, crews respond with care and coordination.",
            "platforms": ("Facebook", "Website"),
            "window": "Timely, after facts are confirmed",
            "cta": "For emergencies, call 911."
        },
        {
            "strategy_type": "apparatus_feature",
            "title": "Apparatus Feature",
            "keywords": (
                "apparatus",
                "engine",
                "pumper",
                "ladder",
                "rescue",
                "tanker",
                "brush_truck"
            ),
            "objective": "Help the public understand department equipment and capability.",
            "audience": "Residents and apparatus-interested followers",
            "message": "Apparatus and equipment support safe, effective emergency response.",
            "platforms": ("Facebook", "Instagram", "Website"),
            "window": "Afternoon",
            "cta": "Give emergency vehicles space when crews are responding."
        },
        {
            "strategy_type": "seasonal_safety",
            "title": "Seasonal Safety",
            "keywords": (
                "heat_safety",
                "winter_safety",
                "water_safety",
                "storm_safety",
                "fire_prevention_week",
                "carbon_monoxide"
            ),
            "objective": "Connect the media to a timely seasonal safety reminder.",
            "audience": "Morden residents",
            "message": "Current seasonal risks are easier to manage when people prepare early.",
            "platforms": ("Facebook", "Instagram"),
            "window": "Morning",
            "cta": "Prepare now and check on neighbours who may need support."
        },
        {
            "strategy_type": "volunteer_recognition",
            "title": "Volunteer Recognition",
            "keywords": (
                "recognition",
                "volunteer",
                "firefighter",
                "crew",
                "community_service",
                "teamwork"
            ),
            "objective": "Recognize the people behind the service.",
            "audience": "Community members and department supporters",
            "message": "The department's strength comes from people who step up for their community.",
            "platforms": ("Facebook", "Instagram", "LinkedIn"),
            "window": "Evening",
            "cta": "Join us in thanking local firefighters for their service."
        },
        {
            "strategy_type": "behind_the_scenes",
            "title": "Behind the Scenes",
            "keywords": (
                "station_life",
                "maintenance",
                "training",
                "equipment",
                "apparatus",
                "crew"
            ),
            "objective": "Show everyday preparation without turning it into a technical post.",
            "audience": "General followers",
            "message": "Preparedness includes many small tasks that happen before the emergency.",
            "platforms": ("Facebook", "Instagram"),
            "window": "Evening",
            "cta": "Follow Morden Fire & Rescue for more local updates."
        },
        {
            "strategy_type": "historical_throwback",
            "title": "Historical / Throwback",
            "keywords": (
                "historical",
                "throwback_thursday",
                "archive",
                "apparatus",
                "ceremony",
                "annual_report"
            ),
            "objective": "Use the media as a memory or archive story.",
            "audience": "Long-time residents and department supporters",
            "message": "Department history is part of the community's story.",
            "platforms": ("Facebook", "Instagram"),
            "window": "Thursday",
            "cta": "Share your memories if this brings one to mind."
        },
        {
            "strategy_type": "annual_report",
            "title": "Annual Report",
            "keywords": (
                "annual_report",
                "training",
                "emergency_response",
                "public_education",
                "recognition",
                "community"
            ),
            "objective": "Support year-end reporting and department accountability.",
            "audience": "Council, partners, residents, and department leadership",
            "message": "This media helps document the department's service and readiness.",
            "platforms": ("Annual Report", "LinkedIn", "Website"),
            "window": "Year-end planning",
            "cta": "Use this asset when summarizing department work."
        },
        {
            "strategy_type": "website_feature",
            "title": "Website Feature",
            "keywords": (
                "website",
                "public_education",
                "apparatus",
                "training",
                "community",
                "recruitment"
            ),
            "objective": "Use the media as durable website-supporting content.",
            "audience": "Residents looking for department information",
            "message": "The media can support a clear, durable department information page.",
            "platforms": ("Website", "Facebook"),
            "window": "Any time",
            "cta": "Keep this asset available for future web updates."
        }
    )

    def __init__(
        self,
        database=None,
        feedback_service=None,
        knowledge_service=None,
        context_engine=None,
        memory_service=None,
        learning_service=None,
        graph_service=None
    ):

        self.db = database or context.database
        self.feedback = feedback_service or HumanFeedbackService(
            database=self.db
        )
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.context_engine = context_engine or ContextEngine()
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.learning = learning_service or RecommendationLearningService(
            database=self.db
        )
        self.graph = graph_service or KnowledgeGraphService(
            database=self.db,
            knowledge_service=self.knowledge
        )

    ############################################################

    def generate_for_media(self, media_id, limit=5, persist=True):

        effective = self.feedback.effective_media_intelligence(media_id)
        media = effective.get("media_intelligence") or {}
        fire = effective.get("fire_service_intelligence") or {}
        analysis = effective.get("analysis") or {}
        context_snapshot = self.context_engine.snapshot()
        memory = self.memory.media_memory(media_id)
        preferences = self.learning.preferences()
        terms = self._terms(effective)
        graph_context = self.graph.reasoning_context(list(terms))
        terms |= self._graph_terms(graph_context)

        strategies = []

        for profile in self.STRATEGIES:
            strategy = self._build_strategy(
                media_id,
                profile,
                effective,
                media,
                fire,
                analysis,
                context_snapshot,
                memory,
                preferences,
                terms,
                graph_context
            )

            if strategy["confidence"] > 0:
                strategies.append(strategy)

        strategies.sort(
            key=lambda item: (
                item["confidence"],
                item["communications_score"]
            ),
            reverse=True
        )

        strategies = self._ensure_distinct_minimum(
            strategies,
            media_id,
            media,
            fire,
            analysis,
            context_snapshot,
            memory,
            terms,
            graph_context
        )
        strategies = strategies[:limit]

        if persist and self.db:
            self.db.save_editorial_strategies(
                media_id,
                strategies
            )

        logger.info(
            "Generated editorial strategies media_id=%s strategies=%s top=%s",
            media_id,
            len(strategies),
            strategies[0]["strategy_type"] if strategies else ""
        )

        return strategies

    ############################################################

    def strategies_for_media(self, media_id, generate_if_missing=True, limit=5):

        rows = self.db.editorial_strategies_for_media(
            media_id,
            limit=limit
        )

        if rows or not generate_if_missing:
            return rows

        return self.generate_for_media(
            media_id,
            limit=limit,
            persist=True
        )

    ############################################################

    def _build_strategy(
        self,
        media_id,
        profile,
        effective,
        media,
        fire,
        analysis,
        context_snapshot,
        memory,
        preferences,
        terms,
        graph_context
    ):

        profile_terms = {
            self._token(value)
            for value in profile["keywords"]
        }
        matches = sorted(terms & profile_terms)
        category = self._category_score(
            media,
            profile["strategy_type"]
        )
        score = int(media.get("communications_score") or media.get("intelligence_score") or 0)
        score = int(score * 0.45) + category

        if matches:
            score += min(30, len(matches) * 6)

        active = {
            self._token(value)
            for value in getattr(context_snapshot, "active_themes", [])
        }
        suggested = {
            self._token(value)
            for value in getattr(context_snapshot, "suggested_opportunities", [])
        }

        if profile_terms & (active | suggested):
            score += 10

        if not memory.get("posted_before"):
            score += 6
        else:
            score -= min(18, int(memory.get("post_count") or 0) * 6)

        score += self._learning_adjustment(
            profile["strategy_type"],
            preferences
        )

        confidence = self._clamp(score)
        evidence = self._supporting_evidence(
            matches,
            media,
            fire,
            effective,
            graph_context,
            context_snapshot,
            memory
        )
        risks = self._risks(
            profile["strategy_type"],
            media,
            fire,
            memory
        )
        limitations = self._limitations(
            analysis,
            media,
            fire,
            effective
        )
        reasoning = self._reasoning(
            profile,
            matches,
            media,
            fire,
            context_snapshot,
            memory,
            evidence
        )

        return {
            "strategy_id": f"{media_id}:{profile['strategy_type']}",
            "strategy_type": profile["strategy_type"],
            "title": profile["title"],
            "objective": profile["objective"],
            "target_audience": profile["audience"],
            "core_message": profile["message"],
            "reasoning": reasoning,
            "confidence": confidence,
            "communications_score": self._clamp(
                media.get("communications_score") or confidence
            ),
            "recommended_platforms": list(profile["platforms"]),
            "recommended_posting_window": profile["window"],
            "recommended_media": [
                {
                    "media_id": media_id,
                    "filename": media.get("filename", ""),
                    "path": media.get("path", "")
                }
            ],
            "caption_direction": self._caption_direction(
                profile,
                media,
                fire
            ),
            "call_to_action": profile["cta"],
            "risks": risks,
            "limitations": limitations,
            "supporting_evidence": evidence
        }

    ############################################################

    def _ensure_distinct_minimum(
        self,
        strategies,
        media_id,
        media,
        fire,
        analysis,
        context_snapshot,
        memory,
        terms,
        graph_context
    ):

        if len(strategies) >= 3:
            return strategies

        existing = {
            item["strategy_type"]
            for item in strategies
        }

        fallback_types = (
            "community_trust",
            "annual_report",
            "website_feature",
            "behind_the_scenes"
        )

        for strategy_type in fallback_types:
            if strategy_type in existing:
                continue

            profile = next(
                item
                for item in self.STRATEGIES
                if item["strategy_type"] == strategy_type
            )
            strategy = self._build_strategy(
                media_id,
                profile,
                {"analysis": analysis, "media_intelligence": media, "fire_service_intelligence": fire},
                media,
                fire,
                analysis,
                context_snapshot,
                memory,
                {},
                terms,
                graph_context
            )
            strategy["confidence"] = max(
                25,
                min(strategy["confidence"], 58)
            )
            strategy["limitations"].append(
                "Alternative strategy included for planning comparison."
            )
            strategies.append(strategy)
            existing.add(strategy_type)

            if len(strategies) >= 3:
                break

        strategies.sort(
            key=lambda item: (
                item["confidence"],
                item["communications_score"]
            ),
            reverse=True
        )

        return strategies

    ############################################################

    def _category_score(self, media, strategy_type):

        mapping = {
            "community_education": "educational_value_score",
            "public_education": "public_education_value_score",
            "seasonal_safety": "seasonal_relevance_score",
            "recruitment": "recruitment_value_score",
            "training_highlight": "educational_value_score",
            "technical_education": "educational_value_score",
            "community_trust": "trust_building_score",
            "volunteer_recognition": "recognition_value_score",
            "annual_report": "storytelling_score",
            "website_feature": "trust_building_score",
            "incident_recap": "emergency_response_value_score",
            "apparatus_feature": "visual_impact_score",
            "behind_the_scenes": "storytelling_score",
            "historical_throwback": "historical_importance_score"
        }

        return int(media.get(mapping.get(strategy_type, ""), 0) or 0) // 3

    ############################################################

    def _terms(self, effective):

        values = []
        analysis = effective.get("analysis") or {}
        media = effective.get("media_intelligence") or {}
        fire = effective.get("fire_service_intelligence") or {}

        for key in (
            "description",
            "scene_type",
            "activity"
        ):
            values.extend(
                self._split(analysis.get(key))
            )

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "search_text",
            "suggested_platform",
            "suggested_time_of_year"
        ):
            values.extend(
                self._split(media.get(key))
            )

        for key in (
            "apparatus_tags",
            "equipment_tags",
            "ppe_tags",
            "people_tags",
            "content_tags",
            "content_themes",
            "recommended_uses",
            "suggested_campaigns",
            "suggested_audience",
            "communications_reasoning"
        ):
            values.extend(media.get(key) or [])

        for key in (
            "incident_classification",
            "operational_activity",
            "operational_context",
            "group_size"
        ):
            values.extend(
                self._split(fire.get(key))
            )

        for key in (
            "personnel",
            "ppe",
            "equipment",
            "apparatus",
            "communications_uses",
            "operational_skills",
            "communications_intent",
            "operational_reasoning"
        ):
            values.extend(fire.get(key) or [])

        for key in (
            "personnel_types",
            "operational_skills",
            "ppe",
            "equipment",
            "apparatus",
            "communications_uses",
            "campaigns"
        ):
            values.extend(effective.get(key) or [])

        return {
            self._token(value)
            for value in values
            if value
        }

    ############################################################

    def _graph_terms(self, graph_context):

        terms = []

        for key in (
            "operational_skills",
            "communications_intent",
            "campaigns"
        ):
            terms.extend(graph_context.get(key) or [])

        for rows in graph_context.get("expanded_terms", {}).values():
            terms.extend(
                row.get("name", "")
                for row in rows
            )

        return {
            self._token(value)
            for value in terms
            if value
        }

    ############################################################

    def _learning_adjustment(self, strategy_type, preferences):

        preferred = {
            self._token(value)
            for value in preferences.get("recommendation_types", [])
        }

        if self._token(strategy_type) in preferred:
            return 5

        return 0

    ############################################################

    def _supporting_evidence(
        self,
        matches,
        media,
        fire,
        effective,
        graph_context,
        context_snapshot,
        memory
    ):

        evidence = []

        if media.get("communications_score"):
            evidence.append(
                f"Communications score {media['communications_score']}."
            )

        if matches:
            evidence.append(
                "Relevant signals: " +
                ", ".join(self._label(value) for value in matches[:6]) +
                "."
            )

        if fire.get("operational_context"):
            evidence.append(
                "Operational context: " +
                self._label(fire.get("operational_context")) +
                "."
            )

        if fire.get("operational_skills"):
            evidence.append(
                "Operational skills: " +
                ", ".join(self._label(value) for value in fire["operational_skills"][:4]) +
                "."
            )

        if graph_context.get("reasoning"):
            evidence.extend(graph_context["reasoning"][:2])

        active = getattr(
            context_snapshot,
            "active_themes",
            []
        )

        if active:
            evidence.append(
                "Current context includes " +
                ", ".join(self._label(value) for value in active[:3]) +
                "."
            )

        if effective.get("is_human_corrected"):
            evidence.append(
                "Human-corrected intelligence is being used."
            )

        if not memory.get("posted_before"):
            evidence.append(
                "Communications Memory shows no prior post for this media."
            )

        return self._unique(evidence)

    ############################################################

    def _risks(self, strategy_type, media, fire, memory):

        risks = []

        if strategy_type == "incident_recap":
            risks.append(
                "Use only if incident details are confirmed outside the media intelligence."
            )

        if memory.get("posted_before"):
            risks.append(
                "This media has appeared before, so avoid repeating a recent message."
            )

        if int(media.get("intelligence_score") or 0) < 50:
            risks.append(
                "Media intelligence confidence is limited."
            )

        if fire.get("operational_confidence") and fire["operational_confidence"] < 60:
            risks.append(
                "Operational inference confidence is limited."
            )

        return self._unique(risks)

    ############################################################

    def _limitations(self, analysis, media, fire, effective):

        limitations = [
            "Strategy is generated from stored intelligence only; no Vision AI is called."
        ]

        if (
            analysis.get("provider") == "mock" or
            str(analysis.get("model", "")).startswith("mock") or
            str(media.get("source_model", "")).startswith("mock")
        ):
            limitations.append(
                "Mock provider active - test data only."
            )

        if not fire:
            limitations.append(
                "Fire Service Intelligence is not available for this media."
            )

        if not media.get("communications_score"):
            limitations.append(
                "Communications score is not available yet."
            )

        if effective.get("correction_count"):
            limitations.append(
                f"{effective['correction_count']} human correction(s) affect this strategy."
            )

        return self._unique(limitations)

    ############################################################

    def _reasoning(
        self,
        profile,
        matches,
        media,
        fire,
        context_snapshot,
        memory,
        evidence
    ):

        lines = [
            f"{profile['title']} fits because the asset can support: {profile['objective']}",
            profile["message"]
        ]

        if matches:
            lines.append(
                "Signals support this strategy: " +
                ", ".join(self._label(value) for value in matches[:5]) +
                "."
            )

        if media.get("communications_score"):
            lines.append(
                f"Communications Intelligence score is {media['communications_score']}."
            )

        if fire.get("operational_reasoning"):
            lines.extend(fire["operational_reasoning"][:2])

        if profile["strategy_type"] in getattr(context_snapshot, "suggested_opportunities", []):
            lines.append(
                "This aligns with today's context window."
            )

        if memory.get("posted_before"):
            lines.append(
                f"Communications Memory shows prior use {memory.get('post_count', 0)} time(s)."
            )
        else:
            lines.append(
                "Freshness is strong because this media has not been posted before."
            )

        lines.extend(evidence[:3])

        return self._unique(lines)

    ############################################################

    def _caption_direction(self, profile, media, fire):

        activity = fire.get("operational_activity") or media.get("primary_activity")
        incident = fire.get("incident_classification") or media.get("incident_type")

        if activity and activity != "unknown":
            return (
                f"Lead with {self._label(activity).lower()} as a human, public-facing story. "
                "Avoid unsupported incident details."
            )

        if incident and incident != "unknown":
            return (
                f"Use the {self._label(incident).lower()} context carefully without inventing details."
            )

        return (
            profile["message"] +
            " Keep the caption broad if visual intelligence is limited."
        )

    ############################################################

    def _split(self, value):

        return [
            part.strip()
            for part in str(value or "").replace(",", " ").replace("_", " ").split()
            if part.strip()
        ]

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )

    ############################################################

    def _label(self, value):

        return str(value or "").replace(
            "_",
            " "
        ).title()

    ############################################################

    def _clamp(self, value):

        try:
            value = int(round(float(value)))
        except Exception:
            value = 0

        return max(0, min(100, value))

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
