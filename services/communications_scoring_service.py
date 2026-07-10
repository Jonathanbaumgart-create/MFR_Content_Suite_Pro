from services.context_engine import ContextEngine
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class CommunicationsScoringService:

    CATEGORY_KEYS = (
        "storytelling_potential",
        "community_engagement",
        "educational_value",
        "recruitment_value",
        "recognition_value",
        "emergency_response_value",
        "public_education_value",
        "seasonal_relevance",
        "visual_impact",
        "trust_building",
        "emotional_impact"
    )

    PLATFORM_KEYS = (
        "facebook",
        "instagram",
        "linkedin",
        "annual_report",
        "website"
    )

    def __init__(
        self,
        database=None,
        knowledge_service=None,
        context_engine=None,
        memory_service=None,
        learning_service=None
    ):

        self.db = database
        self.knowledge = knowledge_service
        self.context_engine = context_engine or ContextEngine()
        self.memory = memory_service
        self.learning = learning_service

        if self.db is not None and self.knowledge is None:
            self.knowledge = KnowledgeService(
                database=self.db
            )
        self.graph = None

    ############################################################

    def score_media(self, intelligence, media=None):

        context = self.context_engine.snapshot()
        knowledge = self.knowledge.snapshot() if self.knowledge else {}
        memory = self._media_memory(
            intelligence.get("media_id")
        )
        preferences = self._learning_preferences()
        terms = self._terms(intelligence)

        category_scores = {
            "storytelling_potential": self._storytelling_score(intelligence, terms),
            "community_engagement": self._keyword_score(
                terms,
                ("community", "event", "children", "school", "family", "open_house"),
                42
            ),
            "educational_value": self._keyword_score(
                terms,
                ("education", "public_education", "training", "safety", "prevention"),
                38
            ),
            "recruitment_value": self._keyword_score(
                terms,
                (
                    "recruitment",
                    "training",
                    "crew",
                    "firefighter",
                    "volunteer",
                    "training_tuesday",
                    "volunteer_spotlight",
                    "officer_development"
                ),
                35
            ),
            "recognition_value": self._keyword_score(
                terms,
                ("recognition", "award", "volunteer", "community", "crew"),
                30
            ),
            "emergency_response_value": self._keyword_score(
                terms,
                ("structure_fire", "vehicle_collision", "wildland_fire", "rescue", "medical", "incident"),
                32
            ),
            "public_education_value": self._keyword_score(
                terms,
                (
                    "smoke_alarm",
                    "fire_prevention",
                    "public_education",
                    "school",
                    "safety",
                    "community_education",
                    "hydrant_heroes",
                    "travelling_sparky",
                    "technical_education"
                ),
                36
            ),
            "seasonal_relevance": self._seasonal_score(terms, context),
            "visual_impact": self._visual_score(intelligence, terms),
            "trust_building": self._trust_score(terms),
            "emotional_impact": self._emotional_score(terms)
        }
        self._apply_learning_preferences(
            category_scores,
            terms,
            preferences
        )
        platform_scores = self._platform_scores(
            category_scores,
            terms,
            preferences
        )
        overall = self._overall_score(
            category_scores,
            platform_scores
        )
        evergreen = self._evergreen_score(terms, category_scores)
        time_sensitive = self._time_sensitive_score(terms, context)
        historical = self._historical_score(terms, memory)
        uniqueness = self._uniqueness_score(intelligence, memory)
        frequency_risk = self._frequency_risk(memory)
        suggested_campaigns = self._campaigns(terms, knowledge, context)
        suggested_audience = self._audience(terms, knowledge)
        suggested_platform = self._suggested_platform(platform_scores)
        suggested_time = self._suggested_time(terms, context)
        reasoning = self._reasoning(
            category_scores,
            platform_scores,
            terms,
            context,
            memory,
            preferences
        )

        score = {
            "communications_score": overall,
            "communications_category_scores": category_scores,
            "platform_suitability": platform_scores,
            "storytelling_score": category_scores["storytelling_potential"],
            "community_engagement_score": category_scores["community_engagement"],
            "educational_value_score": category_scores["educational_value"],
            "recruitment_value_score": category_scores["recruitment_value"],
            "recognition_value_score": category_scores["recognition_value"],
            "emergency_response_value_score": category_scores["emergency_response_value"],
            "public_education_value_score": category_scores["public_education_value"],
            "seasonal_relevance_score": category_scores["seasonal_relevance"],
            "visual_impact_score": category_scores["visual_impact"],
            "trust_building_score": category_scores["trust_building"],
            "emotional_impact_score": category_scores["emotional_impact"],
            "evergreen_score": evergreen,
            "time_sensitive_score": time_sensitive,
            "historical_importance_score": historical,
            "uniqueness_score": uniqueness,
            "posting_frequency_risk": frequency_risk,
            "suggested_campaigns": suggested_campaigns,
            "suggested_audience": suggested_audience,
            "suggested_platform": suggested_platform,
            "suggested_time_of_year": suggested_time,
            "communications_reasoning": reasoning
        }

        logger.info(
            "Scored media communications value media_id=%s score=%s platform=%s",
            intelligence.get("media_id"),
            overall,
            suggested_platform
        )

        return score

    ############################################################

    def score_and_save(self, media_id):

        if self.db is None:
            raise RuntimeError("CommunicationsScoringService requires a database")

        intelligence = self.db.get_media_intelligence(media_id)

        if not intelligence:
            return None

        score = self.score_media(
            intelligence
        )
        self.db.save_communications_scores(
            media_id,
            score
        )

        return self.db.get_media_intelligence(media_id)

    ############################################################

    def rebuild_missing(self, limit=None, progress_callback=None):

        if self.db is None:
            raise RuntimeError("CommunicationsScoringService requires a database")

        rows = self.db.get_media_needing_communications_scores(limit)
        total = len(rows)
        completed = 0
        failed = 0

        for row in rows:
            media_id = row.get("media_id")

            try:
                self.score_and_save(
                    media_id
                )
                completed += 1

            except Exception as ex:
                failed += 1
                logger.error(
                    "Communications scoring failed media_id=%s",
                    media_id,
                    exc_info=(
                        type(ex),
                        ex,
                        ex.__traceback__
                    )
                )

            if progress_callback:
                progress_callback(
                    {
                        "status": "scoring communications value",
                        "total": total,
                        "completed": completed,
                        "failed": failed
                    }
                )

        return {
            "total": total,
            "completed": completed,
            "failed": failed
        }

    ############################################################

    def _storytelling_score(self, intelligence, terms):

        score = int(intelligence.get("intelligence_score") or 0) * 0.45

        if intelligence.get("primary_activity"):
            score += 15

        if "crew" in terms or "people" in terms:
            score += 12

        if terms & {"community", "children", "training", "rescue"}:
            score += 18

        return self._clamp(score)

    def _keyword_score(self, terms, keywords, base):

        matches = terms & set(keywords)

        return self._clamp(
            base + len(matches) * 14
        )

    def _seasonal_score(self, terms, context):

        active = {
            self._token(value)
            for value in getattr(context, "active_themes", [])
        }
        suggested = {
            self._token(value)
            for value in getattr(context, "suggested_opportunities", [])
        }
        matches = terms & (active | suggested)

        score = 35 + len(matches) * 16

        if terms & {"heat_safety", "winter_safety", "fire_prevention", "water_safety"}:
            score += 18

        return self._clamp(score)

    def _visual_score(self, intelligence, terms):

        score = 45

        if intelligence.get("apparatus_tags"):
            score += 12

        if intelligence.get("people_tags"):
            score += 12

        if intelligence.get("ppe_tags"):
            score += 10

        if terms & {
            "community",
            "training",
            "fireground",
            "apparatus",
            "structural_ppe",
            "turnout_gear",
            "ladder_operations",
            "training_evolution"
        }:
            score += 12

        return self._clamp(score)

    def _trust_score(self, terms):

        return self._clamp(
            40 +
            len(terms & {"community", "safety", "public_education", "training", "prevention"}) * 13
        )

    def _emotional_score(self, terms):

        return self._clamp(
            32 +
            len(terms & {"community", "children", "recognition", "crew", "volunteer", "rescue"}) * 15
        )

    def _platform_scores(self, categories, terms, preferences=None):

        preferences = preferences or {}
        preferred_platforms = {
            self._token(value)
            for value in preferences.get("platforms", [])
        }

        scores = {
            "facebook": self._clamp(
                categories["storytelling_potential"] * 0.4 +
                categories["community_engagement"] * 0.35 +
                categories["emotional_impact"] * 0.25
            ),
            "instagram": self._clamp(
                categories["visual_impact"] * 0.45 +
                categories["community_engagement"] * 0.25 +
                categories["emotional_impact"] * 0.3
            ),
            "linkedin": self._clamp(
                categories["trust_building"] * 0.35 +
                categories["recognition_value"] * 0.25 +
                categories["educational_value"] * 0.25 +
                categories["recruitment_value"] * 0.15
            ),
            "annual_report": self._clamp(
                categories["storytelling_potential"] * 0.45 +
                categories["trust_building"] * 0.35 +
                categories["emergency_response_value"] * 0.2
            ),
            "website": self._clamp(
                categories["educational_value"] * 0.3 +
                categories["public_education_value"] * 0.3 +
                categories["trust_building"] * 0.25 +
                categories["visual_impact"] * 0.15
            )
        }

        for platform in scores:

            if platform in preferred_platforms:
                scores[platform] = self._clamp(
                    scores[platform] + 5
                )

        return scores

    def _overall_score(self, categories, platforms):

        weights = {
            "storytelling_potential": 0.15,
            "community_engagement": 0.14,
            "educational_value": 0.1,
            "recruitment_value": 0.08,
            "recognition_value": 0.07,
            "emergency_response_value": 0.08,
            "public_education_value": 0.1,
            "seasonal_relevance": 0.08,
            "visual_impact": 0.09,
            "trust_building": 0.07,
            "emotional_impact": 0.04
        }
        score = sum(
            categories[key] * value
            for key, value in weights.items()
        )
        score += max(platforms.values()) * 0.08

        return self._clamp(score)

    def _evergreen_score(self, terms, categories):

        score = (
            categories["educational_value"] * 0.35 +
            categories["trust_building"] * 0.25 +
            categories["community_engagement"] * 0.2 +
            categories["public_education_value"] * 0.2
        )

        if terms & {"incident", "structure_fire", "vehicle_collision"}:
            score -= 15

        return self._clamp(score)

    def _time_sensitive_score(self, terms, context):

        score = 25
        active = {
            self._token(value)
            for value in getattr(context, "active_themes", [])
        }

        if terms & active:
            score += 35

        if terms & {"heat_safety", "storm_safety", "fire_prevention", "holiday_safety"}:
            score += 30

        if terms & {"incident", "emergency_response", "structure_fire"}:
            score += 15

        return self._clamp(score)

    def _historical_score(self, terms, memory):

        score = 35

        if terms & {"incident", "structure_fire", "rescue", "apparatus", "recognition"}:
            score += 25

        if not memory.get("posted_before"):
            score += 10

        return self._clamp(score)

    def _uniqueness_score(self, intelligence, memory):

        score = 55

        if intelligence.get("apparatus_tags"):
            score += 10

        if intelligence.get("primary_activity"):
            score += 10

        if not memory.get("posted_before"):
            score += 15

        return self._clamp(score)

    def _frequency_risk(self, memory):

        count = int(memory.get("post_count") or 0)

        if count <= 0:
            return 0

        return self._clamp(
            25 + count * 18
        )

    def _campaigns(self, terms, knowledge, context):

        campaigns = []

        if terms & {"fire_prevention", "smoke_alarm", "public_education"}:
            campaigns.append("Fire Prevention")

        if terms & {"recruitment", "training", "training_tuesday", "officer_development", "technical_education"}:
            campaigns.append("Recruitment")

        if terms & {"training_tuesday", "technical_education", "officer_development"}:
            campaigns.append("Training")

        if terms & {"community", "children", "school"}:
            campaigns.append("Community Engagement")

        if terms & {"heat_safety"}:
            campaigns.append("Summer Heat Safety")

        if terms & {"storm_safety"}:
            campaigns.append("Storm Safety")

        for theme in getattr(context, "active_themes", [])[:3]:
            label = self._label(theme)

            if label and label not in campaigns:
                campaigns.append(label)

        for item in self._knowledge_items(knowledge):
            item_terms = {
                self._token(value)
                for value in item.get("tags", [])
            }
            name = item.get("name", "")

            if name and terms & item_terms and name not in campaigns:
                campaigns.append(name)

        return campaigns[:6] or ["General Engagement"]

    def _audience(self, terms, knowledge):

        audience = []

        if terms & {"children", "school", "public_education"}:
            audience.append("Families and students")

        if terms & {"recruitment", "training"}:
            audience.append("Prospective firefighters")

        if terms & {"officer_development", "technical_education", "internal_training"}:
            audience.append("Fire service members")

        if terms & {"community", "safety", "prevention"}:
            audience.append("Morden residents")

        if terms & {"technical", "apparatus", "training"}:
            audience.append("Community partners")

        for item in self._knowledge_items(knowledge):

            if not item.get("audience"):
                continue

            item_terms = {
                self._token(value)
                for value in item.get("tags", [])
            }

            if terms & item_terms and item["audience"] not in audience:
                audience.append(item["audience"])

        return audience[:4] or ["General public"]

    def _suggested_platform(self, platform_scores):

        return max(
            platform_scores,
            key=platform_scores.get
        )

    def _suggested_time(self, terms, context):

        if terms & {"heat_safety", "water_safety"}:
            return "Summer"

        if terms & {"winter_safety", "carbon_monoxide"}:
            return "Winter"

        if terms & {"fire_prevention", "smoke_alarm"}:
            return "September to October"

        if terms & {"recruitment", "training"}:
            return "Any time"

        return self._label(getattr(context, "season", "")) or "Any time"

    def _reasoning(self, categories, platforms, terms, context, memory, preferences):

        reasons = [
            (
                "Communications score is based on stored Media Intelligence, "
                "department knowledge, context, communications memory, and "
                "recommendation learning signals."
            )
        ]
        strongest = sorted(
            categories.items(),
            key=lambda item: item[1],
            reverse=True
        )[:3]

        reasons.append(
            "Strongest communications factors: " +
            ", ".join(f"{self._label(key)} {value}" for key, value in strongest) +
            "."
        )

        reasons.append(
            "Best platform fit: " +
            self._label(self._suggested_platform(platforms)) +
            "."
        )

        if terms & {"community", "children", "school"}:
            reasons.append(
                "Community-facing signals support trust and engagement."
            )

        if terms & {"training", "recruitment"}:
            reasons.append(
                "Training and recruitment signals support staffing and behind-the-scenes storytelling."
            )

        if terms & {
            "ladder_operations",
            "fire_attack",
            "search",
            "water_supply",
            "technical_education",
            "officer_development"
        }:
            reasons.append(
                "Fire Service Intelligence adds operational reasoning for technical and communications value."
            )

        if memory.get("posted_before"):
            reasons.append(
                f"Communications Memory shows prior use {memory.get('post_count')} time(s)."
            )
        else:
            reasons.append(
                "Communications Memory shows no prior use, which improves freshness."
            )

        if preferences.get("summary"):
            reasons.append(
                "Recommendation Learning slightly favors: " +
                ", ".join(preferences["summary"][:3]) +
                "."
            )

        return reasons

    def _media_memory(self, media_id):

        if not self.memory or not media_id:
            return {}

        try:
            return self.memory.media_memory(
                media_id
            )

        except Exception:
            return {}

    def _learning_preferences(self):

        if not self.learning:
            return {}

        try:
            return self.learning.preferences()

        except Exception:
            return {}

    def _apply_learning_preferences(self, categories, terms, preferences):

        if not preferences:
            return

        theme_preferences = {
            self._token(value)
            for value in preferences.get("content_themes", [])
        }
        activity_preferences = {
            self._token(value)
            for value in preferences.get("activities", [])
        }
        type_preferences = {
            self._token(value)
            for value in preferences.get("recommendation_types", [])
        }
        preference_terms = theme_preferences | activity_preferences | type_preferences

        if not terms & preference_terms:
            return

        for key in (
            "storytelling_potential",
            "community_engagement",
            "educational_value",
            "recruitment_value"
        ):
            categories[key] = self._clamp(
                categories[key] + 4
            )

    def _knowledge_items(self, knowledge):

        for key in (
            "programs",
            "annual_events",
            "community_partners",
            "apparatus",
            "locations"
        ):
            for item in knowledge.get(key, []):
                yield item

    def _terms(self, intelligence):

        terms = set()

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "search_text"
        ):
            for value in str(intelligence.get(key, "")).replace(",", " ").split():
                terms.add(self._token(value))

        for key in (
            "apparatus_tags",
            "equipment_tags",
            "ppe_tags",
            "people_tags",
            "content_tags",
            "content_themes",
            "recommended_uses"
        ):
            for value in intelligence.get(key) or []:
                terms.add(self._token(value))

        fire_service = intelligence.get("fire_service_intelligence") or {}

        for key in (
            "incident_classification",
            "operational_activity",
            "operational_context",
            "group_size"
        ):
            terms.add(self._token(fire_service.get(key)))

        for key in (
            "ppe",
            "equipment",
            "apparatus",
            "communications_uses",
            "operational_skills",
            "communications_intent",
            "operational_reasoning"
        ):
            for value in fire_service.get(key) or []:
                terms.add(self._token(value))

        terms = {
            term
            for term in terms
            if term
        }
        terms |= self._graph_terms(terms)

        return terms

    def _graph_terms(self, terms):

        if not terms or not self.db:
            return set()

        try:
            if self.graph is None:
                from services.knowledge_graph_service import KnowledgeGraphService

                self.graph = KnowledgeGraphService(
                    database=self.db,
                    knowledge_service=self.knowledge
                )

            context = self.graph.reasoning_context(list(terms))
            values = set()

            for key in (
                "operational_skills",
                "communications_intent",
                "campaigns"
            ):
                values.update(
                    self._token(value)
                    for value in context.get(key, [])
                )

            for rows in context.get("expanded_terms", {}).values():
                values.update(
                    self._token(row.get("name", ""))
                    for row in rows
                )

            return {
                value
                for value in values
                if value
            }

        except Exception:
            return set()

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )

    def _label(self, value):

        return str(value or "").replace(
            "_",
            " "
        ).title()

    def _clamp(self, value):

        try:
            value = round(float(value))

        except (TypeError, ValueError):
            value = 0

        return max(
            0,
            min(100, int(value))
        )
