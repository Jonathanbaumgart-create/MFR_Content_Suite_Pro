import re

from services.context_engine import ContextEngine
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("intelligence")


class FireServiceIntelligenceService:

    def __init__(
        self,
        database=None,
        knowledge_service=None,
        context_engine=None,
        memory_service=None
    ):

        self.db = database
        self.knowledge = knowledge_service
        self.context_engine = context_engine or ContextEngine()
        self.memory = memory_service

        if self.db is not None and self.knowledge is None:
            self.knowledge = KnowledgeService(
                database=self.db
            )

    ############################################################

    def generate(
        self,
        analysis,
        media_intelligence=None,
        department_knowledge=None,
        communications_memory=None,
        communications_context=None
    ):

        media_intelligence = media_intelligence or {}
        department_knowledge = department_knowledge or self._knowledge_snapshot()
        communications_memory = communications_memory or {}
        communications_context = communications_context or self._context_snapshot()
        text = self._combined_text(
            analysis,
            media_intelligence,
            department_knowledge,
            communications_context
        )

        ppe = self._detect_terms(
            text,
            (
                ("structural_ppe", ("turnout gear", "bunker gear", "structural ppe")),
                ("wildland_ppe", ("wildland gear", "wildland ppe")),
                ("scba", ("scba", "air pack", "breathing apparatus")),
                ("helmet", ("helmet", "fire helmet")),
                ("gloves", ("gloves", "fire gloves")),
                ("hood", ("hood", "balaclava")),
                ("pass_device", ("pass device", "pass alarm")),
                ("high_visibility_vest", ("high visibility", "hi-vis", "safety vest")),
                ("eye_protection", ("eye protection", "safety glasses")),
                ("turnout_gear", ("turnout", "turnout gear", "bunker gear"))
            ),
            "unknown_ppe"
        )
        equipment = self._detect_terms(
            text,
            (
                ("ground_ladder", ("ground ladder",)),
                ("aerial_ladder", ("aerial ladder", "ladder truck", "aerial platform")),
                ("attack_hose", ("attack hose", "attack line", "hose line")),
                ("supply_hose", ("supply hose", "supply line")),
                ("nozzle", ("nozzle",)),
                ("hydrant", ("hydrant",)),
                ("portable_pump", ("portable pump",)),
                ("chainsaw", ("chainsaw", "chain saw")),
                ("ventilation_fan", ("ventilation fan", "positive pressure fan")),
                ("thermal_imaging_camera", ("thermal imaging camera", "thermal camera", "tic")),
                ("medical_bag", ("medical bag", "trauma bag", "first aid bag")),
                ("stokes_basket", ("stokes basket", "rescue basket")),
                ("life_safety_rope", ("life safety rope", "rope rescue", "rescue rope")),
                ("rescue_equipment", ("rescue equipment", "rescue gear")),
                ("extrication_tools", ("extrication", "jaws", "cutter", "spreader")),
                ("water_rescue_equipment", ("water rescue", "throw bag")),
                ("traffic_control", ("traffic control", "traffic cones", "road flares"))
            ),
            "unknown_equipment"
        )
        apparatus = self._detect_terms(
            text,
            (
                ("engine", ("engine",)),
                ("pumper", ("pumper",)),
                ("rescue", ("rescue truck", "rescue apparatus", "squad")),
                ("ladder", ("ladder truck", "aerial")),
                ("tanker", ("tanker", "tender")),
                ("command", ("command", "command vehicle")),
                ("utility", ("utility", "utility truck")),
                ("brush_truck", ("brush truck", "wildland truck", "brush unit")),
                ("ambulance", ("ambulance", "ems")),
                ("police", ("police", "rcmp")),
                ("public_works", ("public works",))
            ),
            "unknown"
        )
        personnel = self._personnel(
            analysis,
            text,
            ppe
        )
        incident = self._incident_classification(
            text,
            media_intelligence
        )
        activity = self._operational_activity(
            text,
            media_intelligence,
            ppe,
            equipment
        )
        communications_uses = self._communications_uses(
            text,
            media_intelligence,
            personnel,
            ppe,
            equipment,
            apparatus,
            incident,
            activity,
            department_knowledge,
            communications_memory
        )
        reasoning = self._reasoning(
            personnel,
            ppe,
            equipment,
            apparatus,
            incident,
            activity,
            communications_uses
        )

        result = {
            "media_id": analysis.get("media_id") or media_intelligence.get("media_id"),
            "firefighter_count": personnel["firefighter_count"],
            "civilian_count": personnel["civilian_count"],
            "officer_presence": personnel["officer_presence"],
            "children_present": personnel["children_present"],
            "group_size": personnel["group_size"],
            "personnel": personnel,
            "ppe": ppe,
            "equipment": equipment,
            "apparatus": apparatus,
            "incident_classification": incident,
            "operational_activity": activity,
            "communications_uses": communications_uses,
            "reasoning": reasoning,
            "source_model": analysis.get("model", "")
        }

        try:
            from services.fire_reasoning_service import FireReasoningService

            operational = FireReasoningService(
                database=self.db,
                knowledge_service=self.knowledge,
                context_engine=self.context_engine,
                memory_service=self.memory
            ).evaluate(
                media_intelligence=media_intelligence,
                fire_service_intelligence=result,
                department_knowledge=department_knowledge,
                communications_memory=communications_memory,
                communications_context=communications_context
            )
            result.update(operational)

        except Exception as ex:
            logger.error(
                "Fire operational reasoning failed media_id=%s",
                result["media_id"],
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )
            result.update(
                {
                    "operational_context": incident if incident else "unknown",
                    "operational_skills": [activity] if activity else ["unknown"],
                    "communications_intent": communications_uses,
                    "operational_confidence": 50,
                    "reasoning_evidence": [],
                    "operational_reasoning": reasoning
                }
            )

        logger.info(
            "Generated fire service intelligence media_id=%s incident=%s activity=%s",
            result["media_id"],
            incident,
            activity
        )

        return result

    ############################################################

    def generate_and_save(self, media_id, analysis, media_intelligence=None):

        if self.db is None:
            raise RuntimeError("FireServiceIntelligenceService requires a database")

        media_intelligence = media_intelligence or self.db.get_media_intelligence(
            media_id
        )
        result = self.generate(
            analysis,
            media_intelligence=media_intelligence
        )
        self.db.save_fire_service_intelligence(
            media_id,
            result
        )

        return self.db.get_fire_service_intelligence(media_id)

    ############################################################

    def _personnel(self, analysis, text, ppe):

        count = self._to_int(analysis.get("people_count"))
        firefighter_terms = re.search(
            r"\b(firefighter|firefighters|crew|officer|chief)\b",
            text
        )
        ppe_detected = bool(set(ppe) - {"unknown_ppe"})

        if count <= 0 and (firefighter_terms or ppe_detected):
            count = 1

        civilian_count = self._count_from_text(
            text,
            ("civilian", "civilians", "resident", "residents")
        )
        officer_presence = bool(
            re.search(r"\b(officer|captain|chief|incident command|command)\b", text)
        )
        children_present = bool(
            re.search(r"\b(child|children|kids|students|school)\b", text)
        )

        return {
            "firefighter_count": count,
            "civilian_count": civilian_count,
            "officer_presence": officer_presence,
            "children_present": children_present,
            "group_size": self._group_size(count)
        }

    ############################################################

    def _incident_classification(self, text, media_intelligence):

        existing = self._slug(media_intelligence.get("incident_type"))
        scene = self._slug(media_intelligence.get("normalized_scene"))

        if scene == "training_tower" or "training tower" in text:
            return "training"

        if self._known(existing):
            return existing

        rules = (
            ("structure_fire", ("structure fire", "house fire", "building fire")),
            ("vehicle_fire", ("vehicle fire", "car fire")),
            ("mvc", ("mvc", "collision", "crash", "vehicle accident")),
            ("medical", ("medical", "patient", "ems", "ambulance")),
            ("hazmat", ("hazmat", "hazardous material", "spill")),
            ("wildland", ("wildland", "grass fire", "brush fire")),
            ("training", ("training", "drill", "training tower", "exercise")),
            ("public_education", ("public education", "school", "prevention")),
            ("inspection", ("inspection", "inspect")),
            ("recruitment", ("recruitment", "join", "volunteer")),
            ("community_event", ("community event", "open house", "parade")),
            ("maintenance", ("maintenance", "equipment check", "cleaning")),
            ("station_life", ("station life", "fire hall", "apparatus bay")),
            ("ceremony", ("ceremony", "award", "recognition"))
        )

        return self._first_match(text, rules, "unknown")

    ############################################################

    def _operational_activity(self, text, media_intelligence, ppe, equipment):

        existing = self._slug(media_intelligence.get("primary_activity"))

        if self._known(existing):
            return existing

        if "turnout_gear" in ppe and "training tower" in text:
            return "training_evolution"

        if "ground_ladder" in equipment or "aerial_ladder" in equipment:
            if "turnout_gear" in ppe or "helmet" in ppe:
                return "ladder_operations"

        rules = (
            ("fire_attack", ("fire attack", "attack line", "hose line")),
            ("pump_operations", ("pump operation", "pump panel", "pumping")),
            ("search", ("search", "primary search")),
            ("ventilation", ("ventilation", "vent fan")),
            ("ladder_operations", ("ladder operation", "ground ladder", "aerial")),
            ("extrication", ("extrication", "jaws", "cutter", "spreader")),
            ("water_shuttle", ("water shuttle", "tanker shuttle")),
            ("incident_command", ("incident command", "command post")),
            ("rehab", ("rehab", "rehabilitation")),
            ("training_evolution", ("training evolution", "training", "drill")),
            ("equipment_maintenance", ("equipment maintenance", "equipment check")),
            ("inspection", ("inspection", "inspect")),
            ("public_education", ("public education", "school", "prevention"))
        )

        return self._first_match(text, rules, "unknown")

    ############################################################

    def _communications_uses(
        self,
        text,
        media_intelligence,
        personnel,
        ppe,
        equipment,
        apparatus,
        incident,
        activity,
        knowledge,
        memory
    ):

        uses = list(media_intelligence.get("recommended_uses") or [])

        if incident == "training" or activity == "training_evolution":
            uses.extend(
                [
                    "training",
                    "training_tuesday",
                    "recruitment",
                    "officer_development",
                    "annual_report",
                    "technical_education"
                ]
            )

        if personnel["firefighter_count"] > 0:
            uses.extend(
                [
                    "volunteer_spotlight",
                    "recruitment"
                ]
            )

        if personnel["children_present"] or "school" in text:
            uses.extend(
                [
                    "community_education",
                    "public_education"
                ]
            )

        if "hydrant" in equipment:
            uses.append("hydrant_heroes")

        if "school" in text or "sparky" in text:
            uses.append("travelling_sparky")

        if incident in ("public_education", "inspection"):
            uses.extend(
                [
                    "fire_prevention_week",
                    "community_education"
                ]
            )

        if apparatus and apparatus != ["unknown"]:
            uses.extend(
                [
                    "website_banner",
                    "annual_report"
                ]
            )

        if "posted_before" in memory and not memory.get("posted_before"):
            uses.append("throwback_thursday")

        for item in self._knowledge_items(knowledge):
            name = self._slug(item.get("name"))

            if name and name in text.replace(" ", "_"):
                uses.append(name)

        if not uses:
            uses.append("website_banner")

        return self._unique(uses)

    ############################################################

    def _reasoning(
        self,
        personnel,
        ppe,
        equipment,
        apparatus,
        incident,
        activity,
        communications_uses
    ):

        reasons = [
            "Interpreted from stored Vision AI output and Media Intelligence only."
        ]

        if personnel["firefighter_count"] > 0:
            reasons.append(
                f"Detected firefighter presence count={personnel['firefighter_count']}."
            )

        if set(ppe) - {"unknown_ppe"}:
            reasons.append(
                "PPE signals support firefighter terminology: " +
                ", ".join(ppe[:5]) +
                "."
            )

        if set(equipment) - {"unknown_equipment"}:
            reasons.append(
                "Equipment signals detected: " +
                ", ".join(equipment[:5]) +
                "."
            )

        if apparatus != ["unknown"]:
            reasons.append(
                "Apparatus signals detected: " +
                ", ".join(apparatus[:5]) +
                "."
            )

        reasons.append(
            f"Classified as {incident} with activity {activity}."
        )
        reasons.append(
            "Communications uses: " +
            ", ".join(communications_uses[:6]) +
            "."
        )

        return reasons

    ############################################################

    def _combined_text(self, analysis, intelligence, knowledge, context):

        parts = [
            analysis.get("description", ""),
            analysis.get("scene_type", ""),
            analysis.get("activity", ""),
            self._list_text(analysis.get("apparatus")),
            self._list_text(analysis.get("equipment")),
            self._list_text(analysis.get("keywords")),
            intelligence.get("normalized_scene", ""),
            intelligence.get("incident_type", ""),
            intelligence.get("primary_activity", ""),
            self._list_text(intelligence.get("apparatus_tags")),
            self._list_text(intelligence.get("equipment_tags")),
            self._list_text(intelligence.get("ppe_tags")),
            self._list_text(intelligence.get("content_tags")),
            self._list_text(intelligence.get("recommended_uses")),
        ]

        return " ".join(str(part).lower() for part in parts if part)

    ############################################################

    def _detect_terms(self, text, rules, unknown):

        values = []

        for value, terms in rules:

            if any(term in text for term in terms):
                values.append(value)

        return self._unique(values) or [unknown]

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

    def _first_match(self, text, rules, default):

        for value, terms in rules:

            if any(term in text for term in terms):
                return value

        return default

    ############################################################

    def _count_from_text(self, text, words):

        if not any(word in text for word in words):
            return 0

        match = re.search(r"\b(\d+)\s+(?:" + "|".join(words) + r")\b", text)

        if match:
            return self._to_int(match.group(1))

        return 1

    ############################################################

    def _group_size(self, count):

        if count <= 0:
            return "unknown"

        if count == 1:
            return "single"

        if count <= 2:
            return "small_group"

        if count <= 6:
            return "crew"

        return "large_group"

    ############################################################

    def _list_text(self, values):

        if isinstance(values, str):
            return values

        return " ".join(str(value) for value in (values or []))

    ############################################################

    def _to_int(self, value):

        if isinstance(value, str):
            match = re.search(r"-?\d+", value)

            if match:
                value = match.group(0)

        try:
            return int(value)
        except Exception:
            return 0

    ############################################################

    def _slug(self, value):

        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)

        return value.strip("_")

    ############################################################

    def _known(self, value):

        return value not in (
            "",
            "none",
            "no",
            "n_a",
            "na",
            "null",
            "unknown",
            "unspecified",
            "not_applicable"
        )

    ############################################################

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:

            value = self._slug(value)

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
