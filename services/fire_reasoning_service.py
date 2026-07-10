import re

from services.context_engine import ContextEngine
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("intelligence")


class FireReasoningService:

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

    ############################################################

    def evaluate(
        self,
        media_intelligence=None,
        fire_service_intelligence=None,
        department_knowledge=None,
        communications_memory=None,
        communications_context=None,
        recommendation_learning=None
    ):

        media_intelligence = media_intelligence or {}
        fire_service_intelligence = fire_service_intelligence or {}
        department_knowledge = department_knowledge or self._knowledge_snapshot()
        communications_memory = communications_memory or {}
        communications_context = communications_context or self._context_snapshot()
        recommendation_learning = recommendation_learning or {}

        terms = self._terms(
            media_intelligence,
            fire_service_intelligence,
            department_knowledge,
            communications_context,
            recommendation_learning
        )
        evidence = []
        skills = []
        intents = []

        operational_context = self._base_context(
            media_intelligence,
            fire_service_intelligence,
            terms
        )
        confidence = 45 if operational_context == "unknown" else 65

        def infer(context, skill, intent, score, reason, evidence_text):
            nonlocal operational_context, confidence

            if context and (
                operational_context == "unknown" or
                score >= confidence
            ):
                operational_context = context

            if skill:
                skills.append(skill)

            for value in intent or ():
                intents.append(value)

            confidence = max(confidence, score)
            evidence.append(
                {
                    "evidence": evidence_text,
                    "confidence": score,
                    "reason": reason
                }
            )

        if self._has(terms, "turnout_gear", "structural_ppe", "helmet") and self._has(
            terms,
            "ground_ladder",
            "aerial_ladder",
            "ladder_operations"
        ) and self._has(terms, "training_tower", "training_ground"):
            infer(
                "training",
                "ladder_operations",
                (
                    "training_tuesday",
                    "recruitment",
                    "officer_development",
                    "technical_education",
                    "annual_report"
                ),
                92,
                "Likely ladder evolution.",
                "Firefighter PPE with ladder activity at a training tower or training ground."
            )

        if self._has(terms, "turnout_gear", "structural_ppe", "helmet") and self._has(
            terms,
            "attack_hose",
            "supply_hose",
            "hose",
            "hose_line_training"
        ) and self._has(terms, "training_tower", "training_ground", "training"):
            infer(
                "training",
                "fire_attack",
                (
                    "training_tuesday",
                    "recruitment",
                    "technical_education",
                    "internal_training"
                ),
                88,
                "Likely hose evolution.",
                "Turnout gear and hose work appear in a training setting."
            )

        if self._has(terms, "scba") and self._has(terms, "training_tower"):
            infer(
                "training",
                "search",
                (
                    "training_tuesday",
                    "officer_development",
                    "technical_education",
                    "internal_training"
                ),
                90,
                "Likely SCBA confidence training.",
                "SCBA appears with a training tower context."
            )

        if self._has(terms, "hydrant", "supply_hose", "supply_line"):
            infer(
                None,
                "water_supply",
                (
                    "technical_education",
                    "annual_report"
                ),
                78,
                "Water supply work is likely.",
                "Hydrant or supply hose evidence is present."
            )

        if self._has(terms, "extrication_tools"):
            infer(
                "training" if "training" in terms else "emergency_response",
                "extrication",
                (
                    "training_tuesday",
                    "technical_education",
                    "annual_report"
                ),
                82,
                "Extrication skill is indicated.",
                "Extrication tool evidence is present."
            )

        if self._has(terms, "ventilation_fan", "ventilation"):
            infer(
                None,
                "ventilation",
                (
                    "technical_education",
                    "internal_training"
                ),
                76,
                "Ventilation skill is indicated.",
                "Ventilation equipment or activity evidence is present."
            )

        if self._has(terms, "command", "officer", "incident_command"):
            infer(
                None,
                "incident_command",
                (
                    "officer_development",
                    "annual_report"
                ),
                80,
                "Command or officer presence is indicated.",
                "Command, chief, captain, or officer evidence is present."
            )

        if (
            fire_service_intelligence.get("incident_classification") == "public_education" or
            self._has(terms, "children", "school", "smoke_alarm")
        ):
            infer(
                "public_education",
                "public_education",
                (
                    "community_education",
                    "fire_prevention_week",
                    "website_feature"
                ),
                86,
                "Public education context is likely.",
                "Children, school, prevention, or public education evidence is present."
            )

        if self._has(terms, "community", "open_house", "parade", "community_event"):
            infer(
                "community_event",
                "community_engagement",
                (
                    "community_education",
                    "recognition",
                    "website_feature"
                ),
                74,
                "Community engagement context is likely.",
                "Community event evidence is present."
            )

        if self._has(terms, "medical_bag", "medical", "patient", "ems", "ambulance"):
            infer(
                "medical",
                "rehab",
                (
                    "annual_report",
                    "historical_archive"
                ),
                74,
                "Medical or rehab context is possible.",
                "Medical, patient, EMS, or medical bag evidence is present."
            )

        if self._has(terms, "water_rescue_equipment", "stokes_basket", "life_safety_rope"):
            infer(
                "water_rescue" if "water_rescue_equipment" in terms else operational_context,
                "water_rescue" if "water_rescue_equipment" in terms else "rit",
                (
                    "technical_education",
                    "annual_report"
                ),
                78,
                "Rescue skill evidence is present.",
                "Rope, rescue basket, or water rescue equipment evidence is present."
            )

        if self._has(terms, "wildland", "brush_truck", "wildland_ppe"):
            infer(
                "wildland",
                "fire_attack",
                (
                    "news_release",
                    "annual_report",
                    "historical_archive"
                ),
                80,
                "Wildland context is likely.",
                "Wildland, brush truck, or wildland PPE evidence is present."
            )

        if self._has(terms, "hazmat"):
            infer(
                "hazmat",
                "incident_command",
                (
                    "news_release",
                    "historical_archive"
                ),
                76,
                "HazMat context is indicated.",
                "Hazardous material evidence is present."
            )

        if self._has(terms, "maintenance", "equipment_maintenance"):
            infer(
                "maintenance",
                "equipment_maintenance",
                (
                    "behind_the_scenes",
                    "internal_training"
                ),
                72,
                "Maintenance context is indicated.",
                "Equipment maintenance evidence is present."
            )

        if self._has(terms, "station_life", "fire_hall", "apparatus_bay"):
            infer(
                "station_life",
                "community_engagement",
                (
                    "volunteer_spotlight",
                    "website_feature"
                ),
                68,
                "Station life context is likely.",
                "Fire hall or apparatus bay evidence is present."
            )

        if self._has(terms, "ceremony", "award", "recognition"):
            infer(
                "ceremony",
                "community_engagement",
                (
                    "recognition",
                    "volunteer_spotlight",
                    "annual_report"
                ),
                80,
                "Ceremony or recognition context is likely.",
                "Ceremony, award, or recognition evidence is present."
            )

        if not skills:
            skills = self._default_skills(operational_context, terms)

        intents.extend(
            self._default_intents(
                operational_context,
                fire_service_intelligence,
                terms
            )
        )

        if not evidence:
            evidence.append(
                {
                    "evidence": "No strong operational combination detected.",
                    "confidence": confidence,
                    "reason": "Stored intelligence did not provide enough specific operational signals."
                }
            )

        result = {
            "operational_context": operational_context,
            "operational_skills": self._unique(skills or ["unknown"]),
            "communications_intent": self._unique(intents or ["historical_archive"]),
            "operational_confidence": min(100, confidence),
            "reasoning_evidence": evidence,
            "operational_reasoning": self._reasoning_lines(
                operational_context,
                skills,
                intents,
                evidence
            )
        }

        logger.info(
            "Generated fire operational reasoning context=%s confidence=%s",
            result["operational_context"],
            result["operational_confidence"]
        )

        return result

    ############################################################

    def _base_context(self, media_intelligence, fire_service, terms):

        value = self._token(fire_service.get("incident_classification"))

        mapping = {
            "structure_fire": "emergency_response",
            "vehicle_fire": "emergency_response",
            "mvc": "emergency_response",
            "medical": "medical",
            "hazmat": "hazmat",
            "wildland": "wildland",
            "training": "training",
            "public_education": "public_education",
            "inspection": "inspection",
            "recruitment": "recruitment",
            "community_event": "community_event",
            "maintenance": "maintenance",
            "station_life": "station_life",
            "ceremony": "ceremony"
        }

        if value in mapping:
            return mapping[value]

        incident = self._token(media_intelligence.get("incident_type"))

        if incident in mapping:
            return mapping[incident]

        if self._has(terms, "investigation", "fire_investigation"):
            return "investigation"

        return "unknown"

    ############################################################

    def _default_skills(self, context, terms):

        skills = []

        if context == "public_education":
            skills.append("public_education")

        if context == "community_event":
            skills.append("community_engagement")

        if context == "inspection":
            skills.append("inspection")

        if context == "maintenance":
            skills.append("equipment_maintenance")

        if context == "emergency_response":
            skills.append("incident_command")

        if self._has(terms, "attack_hose", "hose"):
            skills.append("fire_attack")

        if self._has(terms, "hydrant"):
            skills.append("water_supply")

        return skills

    ############################################################

    def _default_intents(self, context, fire_service, terms):

        intents = list(fire_service.get("communications_uses") or [])

        if context == "training":
            intents.extend(
                [
                    "training_tuesday",
                    "recruitment",
                    "technical_education"
                ]
            )

        if context == "emergency_response":
            intents.extend(
                [
                    "news_release",
                    "annual_report",
                    "historical_archive"
                ]
            )

        if context == "public_education":
            intents.extend(
                [
                    "community_education",
                    "fire_prevention_week"
                ]
            )

        if context == "recruitment":
            intents.extend(
                [
                    "recruitment",
                    "volunteer_spotlight"
                ]
            )

        if context == "ceremony":
            intents.extend(
                [
                    "recognition",
                    "annual_report"
                ]
            )

        if self._has(terms, "firefighter", "crew"):
            intents.append("volunteer_spotlight")

        return intents

    ############################################################

    def _reasoning_lines(self, context, skills, intents, evidence):

        lines = [
            f"Operational context inferred as {context}.",
            "Operational skills: " + ", ".join(self._unique(skills or ["unknown"])) + ".",
            "Communications intent: " + ", ".join(self._unique(intents or ["historical_archive"])) + "."
        ]

        for item in evidence[:4]:
            lines.append(
                (
                    f"Confidence {item['confidence']}: {item['reason']} "
                    f"Evidence: {item['evidence']}"
                )
            )

        return lines

    ############################################################

    def _terms(
        self,
        media_intelligence,
        fire_service,
        knowledge,
        context,
        learning
    ):

        values = []

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "search_text"
        ):
            values.append(media_intelligence.get(key, ""))

        for key in (
            "apparatus_tags",
            "equipment_tags",
            "ppe_tags",
            "people_tags",
            "content_tags",
            "content_themes",
            "recommended_uses"
        ):
            values.extend(media_intelligence.get(key) or [])

        for key in (
            "incident_classification",
            "operational_activity",
            "group_size"
        ):
            values.append(fire_service.get(key, ""))

        for key in (
            "ppe",
            "equipment",
            "apparatus",
            "communications_uses"
        ):
            values.extend(fire_service.get(key) or [])

        terms = set()

        for value in values:
            token = self._token(value)

            if token:
                terms.add(token)

            for part in re.split(r"[\s,;/]+", str(value or "").lower()):
                token = self._token(part)

                if token:
                    terms.add(token)

        if "training_tower" in terms:
            terms.add("training_ground")

        return terms

    ############################################################

    def _knowledge_snapshot(self):

        if not self.knowledge:
            return {}

        try:
            return self.knowledge.snapshot()

        except Exception:
            return {}

    ############################################################

    def _context_snapshot(self):

        try:
            return self.context_engine.snapshot()

        except Exception:
            return None

    ############################################################

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

    ############################################################

    def _has(self, terms, *values):

        return bool(terms & {self._token(value) for value in values})

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )

    ############################################################

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:
            value = self._token(value)

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
