import re

from services.logging_service import LoggingService


logger = LoggingService.get_logger("intelligence")


class MediaIntelligenceService:

    def __init__(self, database=None):

        self.db = database

    ############################################################

    def generate(self, analysis):

        text = self._analysis_text(analysis)
        words = self._word_set(text)

        apparatus = self._collect_terms(
            analysis.get("apparatus"),
            text,
            {
                "apparatus": ("apparatus", "fire apparatus"),
                "engine": ("engine", "pumper", "truck"),
                "ladder": ("ladder truck", "aerial", "platform"),
                "rescue": ("rescue", "squad"),
                "tanker": ("tanker", "tender"),
                "brush": ("brush", "wildland"),
                "ambulance": ("ambulance", "ems")
            }
        )

        equipment = self._collect_terms(
            analysis.get("equipment"),
            text,
            {
                "hose": ("hose", "attack line", "supply line"),
                "ladder": ("ladder",),
                "scba": ("scba", "air pack"),
                "ppe": ("ppe", "personal protective equipment"),
                "rope": ("rope", "rope rescue"),
                "rescue_equipment": ("rescue equipment", "rescue gear"),
                "training_tower": ("training tower",),
                "nozzle": ("nozzle",),
                "hydrant": ("hydrant",),
                "extrication_tools": ("extrication", "jaws", "cutter"),
                "thermal_camera": ("thermal camera", "tic")
            }
        )

        ppe = self._collect_terms(
            [],
            text,
            {
                "helmet": ("helmet",),
                "turnout_gear": ("turnout", "bunker gear"),
                "ppe": ("ppe", "personal protective equipment"),
                "scba": ("scba", "air pack"),
                "gloves": ("gloves",),
                "boots": ("boots",),
                "high_visibility": ("hi-vis", "high visibility")
            }
        )

        normalized_scene = self._scene(analysis, text)
        incident_type = self._incident_type(text, normalized_scene)
        primary_activity = self._primary_activity(analysis, text)
        people_count = self._effective_people_count(analysis, text)
        people_tags = self._people_tags(people_count)
        content_tags = self._content_tags(
            analysis,
            text,
            words,
            normalized_scene,
            incident_type,
            primary_activity
        )
        content_themes = self._content_themes(analysis, text)
        recommended_uses = self._recommended_uses(
            analysis,
            normalized_scene,
            incident_type,
            content_themes
        )

        if analysis.get("media_context") == "video":
            content_tags = self._unique(
                content_tags + [
                    "video",
                    "short_form_video",
                    "manual_footage_review"
                ]
            )
            recommended_uses = self._unique(
                recommended_uses + [
                    "short_form_video",
                    "candidate_for_reel",
                    "manual_footage_review"
                ]
            )

        all_tags = self._unique(
            apparatus +
            equipment +
            ppe +
            people_tags +
            content_tags +
            content_themes +
            recommended_uses
        )

        search_text = " ".join(
            self._clean_text(part)
            for part in (
                analysis.get("description", ""),
                analysis.get("scene_type", ""),
                analysis.get("activity", ""),
                self._list_text(analysis.get("keywords")),
                " ".join(all_tags),
                normalized_scene,
                incident_type,
                primary_activity
            )
            if part
        )

        intelligence = {
            "normalized_scene": normalized_scene,
            "incident_type": incident_type,
            "primary_activity": primary_activity,
            "apparatus_tags": apparatus,
            "equipment_tags": equipment,
            "ppe_tags": ppe,
            "people_tags": people_tags,
            "content_tags": all_tags,
            "content_themes": content_themes,
            "recommended_uses": recommended_uses,
            "search_text": search_text,
            "intelligence_score": self._score(analysis, all_tags),
            "source_model": analysis.get("model", "")
        }

        logger.info(
            "Generated media intelligence media_id=%s scene=%s incident=%s",
            analysis.get("media_id"),
            normalized_scene,
            incident_type
        )

        return intelligence

    ############################################################

    def generate_and_save(self, media_id, analysis):

        if self.db is None:
            raise RuntimeError("MediaIntelligenceService requires a database")

        intelligence = self.generate(analysis)

        self.db.save_media_intelligence(
            media_id,
            intelligence
        )

        try:
            from services.fire_service_intelligence_service import (
                FireServiceIntelligenceService
            )

            FireServiceIntelligenceService(
                database=self.db
            ).generate_and_save(
                media_id,
                analysis,
                media_intelligence=intelligence
            )

        except Exception as ex:
            logger.error(
                "Fire service intelligence failed media_id=%s",
                media_id,
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )

        try:
            from services.communications_memory_service import CommunicationsMemoryService
            from services.communications_scoring_service import (
                CommunicationsScoringService
            )
            from services.recommendation_learning_service import (
                RecommendationLearningService
            )

            CommunicationsScoringService(
                database=self.db,
                memory_service=CommunicationsMemoryService(database=self.db),
                learning_service=RecommendationLearningService(database=self.db)
            ).score_and_save(
                media_id
            )

        except Exception as ex:
            logger.error(
                "Communications scoring failed media_id=%s",
                media_id,
                exc_info=(
                    type(ex),
                    ex,
                    ex.__traceback__
                )
            )

        return self.db.get_media_intelligence(media_id)

    ############################################################

    def rebuild_missing(self, limit=None, progress_callback=None):

        if self.db is None:
            raise RuntimeError("MediaIntelligenceService requires a database")

        analyses = self.db.get_media_needing_intelligence(limit)
        total = len(analyses)
        completed = 0
        failed = 0

        for analysis in analyses:

            media_id = analysis.get("media_id")

            try:
                self.generate_and_save(
                    media_id,
                    analysis
                )
                completed += 1

            except Exception as ex:
                failed += 1
                logger.error(
                    "Media intelligence rebuild failed media_id=%s",
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
                        "status": "building intelligence",
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

    def _scene(self, analysis, text):

        scene = self._slug(analysis.get("scene_type"))

        if self._known(scene):
            return scene

        rules = (
            ("training_tower", ("training tower",)),
            ("training", ("training", "drill", "exercise")),
            ("public_education", ("education", "school", "prevention")),
            ("community", ("community", "parade", "open house", "event")),
            ("recruitment", ("recruit", "volunteer", "join")),
            ("emergency_response", ("fire", "collision", "rescue", "medical")),
            ("station", ("station", "apparatus bay"))
        )

        return self._first_match(text, rules, "unknown")

    ############################################################

    def _incident_type(self, text, scene):

        rules = (
            ("structure_fire", ("structure fire", "house fire", "building fire")),
            ("vehicle_collision", ("collision", "mvc", "crash", "vehicle accident")),
            ("wildland_fire", ("wildland", "grass fire", "brush fire")),
            ("medical", ("medical", "patient", "ems")),
            ("rescue", ("rescue", "extrication", "rope rescue")),
            ("hazmat", ("hazmat", "hazardous material", "spill")),
            ("training", ("training", "drill", "exercise")),
            ("public_education", ("education", "school", "prevention")),
            ("community_event", ("community", "parade", "open house"))
        )

        incident = self._first_match(text, rules, "")

        if incident:
            return incident

        if scene in ("training", "public_education", "community", "recruitment"):
            return scene

        return "unknown"

    ############################################################

    def _primary_activity(self, analysis, text):

        activity = self._slug(analysis.get("activity"))

        if self._known(activity):
            return activity

        rules = (
            ("rope_rescue_training", ("rope rescue training", "rope training")),
            ("hose_line_training", ("hose line training", "hose-line training")),
            ("fire_suppression", ("fire suppression", "attack line", "extinguish")),
            ("ventilation", ("ventilation", "venting")),
            ("search_and_rescue", ("search", "rescue")),
            ("extrication", ("extrication", "jaws", "cutter")),
            ("water_supply", ("hydrant", "supply line")),
            ("public_education", ("education", "school", "prevention")),
            ("training", ("training", "drill", "exercise")),
            ("community_outreach", ("community", "parade", "open house")),
            ("recruitment", ("recruit", "join", "volunteer"))
        )

        return self._first_match(text, rules, "unknown")

    ############################################################

    def _content_tags(
        self,
        analysis,
        text,
        words,
        scene,
        incident,
        activity
    ):

        tags = [
            scene,
            incident,
            activity
        ]

        keywords = analysis.get("keywords") or []
        tags.extend(self._slug(item) for item in keywords)

        if words & {"snow", "winter", "ice"}:
            tags.append("winter")

        if words & {"summer", "heat", "sunny"}:
            tags.append("summer")

        if words & {"night", "dark", "evening"}:
            tags.append("night")

        if words & {"day", "daytime", "morning"}:
            tags.append("daytime")

        if "safety" in words:
            tags.append("safety")

        term_rules = (
            ("firefighter", ("firefighter", "firefighters")),
            ("helmet", ("helmet",)),
            ("scba", ("scba", "air pack")),
            ("ppe", ("ppe", "turnout", "bunker gear")),
            ("ladder", ("ladder",)),
            ("hose", ("hose", "attack line", "supply line")),
            ("rope", ("rope",)),
            ("training_tower", ("training tower",)),
            ("apparatus", ("apparatus", "engine", "pumper", "truck")),
            ("rescue_equipment", ("rescue equipment", "rescue gear"))
        )

        for tag, terms in term_rules:

            if any(term in text for term in terms):
                tags.append(tag)

        return self._unique(tags)

    ############################################################

    def _content_themes(self, analysis, text):

        themes = []

        score_rules = (
            ("community", "community_score", 60),
            ("recruitment", "recruitment_score", 60),
            ("public_education", "education_score", 60),
            ("technical_training", "technical_score", 60)
        )

        for theme, key, threshold in score_rules:

            if self._to_int(analysis.get(key)) >= threshold:
                themes.append(theme)

        text_rules = (
            ("safety", ("safety", "prevention")),
            ("community", ("community", "open house", "parade")),
            ("recruitment", ("recruit", "volunteer", "join")),
            ("public_education", ("education", "school", "prevention")),
            ("training", ("training", "drill", "exercise"))
        )

        for theme, terms in text_rules:

            if any(term in text for term in terms):
                themes.append(theme)

        return self._unique(themes)

    ############################################################

    def _recommended_uses(
        self,
        analysis,
        scene,
        incident,
        themes
    ):

        uses = []

        if scene == "training" or "training" in themes:
            uses.append("training")

        if "public_education" in themes or scene == "public_education":
            uses.append("public_education")

        if "community" in themes or scene == "community":
            uses.append("community_outreach")

        if "recruitment" in themes or scene == "recruitment":
            uses.append("recruitment")

        if self._to_int(analysis.get("community_score")) >= 70:
            uses.append("social_media")

        if self._to_int(analysis.get("education_score")) >= 70:
            uses.append("safety_message")

        if incident not in ("unknown", "training", "public_education", "community"):
            uses.append("incident_archive")

        return self._unique(uses or ["archive"])

    ############################################################

    def _people_tags(self, people_count):

        count = self._to_int(people_count)

        if count <= 0:
            return ["unknown_people"]

        if count <= 2:
            return ["people", "small_group"]

        if count <= 6:
            return ["people", "crew"]

        return ["people", "large_group"]

    ############################################################

    def _score(self, analysis, tags):

        base = self._to_int(analysis.get("overall_score"))

        if base <= 0:
            scores = [
                self._to_int(analysis.get("community_score")),
                self._to_int(analysis.get("recruitment_score")),
                self._to_int(analysis.get("education_score")),
                self._to_int(analysis.get("technical_score"))
            ]
            base = int(sum(scores) / len(scores)) if scores else 0

        return min(100, base + min(10, len(tags)))

    ############################################################

    def _analysis_text(self, analysis):

        parts = [
            analysis.get("description", ""),
            analysis.get("scene_type", ""),
            analysis.get("activity", ""),
            self._list_text(analysis.get("apparatus")),
            self._list_text(analysis.get("equipment")),
            self._list_text(analysis.get("keywords"))
        ]

        return " ".join(str(part).lower() for part in parts if part)

    ############################################################

    def _collect_terms(self, existing, text, rules):

        terms = [
            self._slug(item)
            for item in (existing or [])
            if self._slug(item)
        ]

        for tag, matches in rules.items():

            if any(match in text for match in matches):
                terms.append(tag)

        return self._unique(terms)

    ############################################################

    def _first_match(self, text, rules, default):

        for value, terms in rules:

            if any(term in text for term in terms):
                return value

        return default

    ############################################################

    def _word_set(self, text):

        return set(re.findall(r"[a-z0-9]+", text))

    ############################################################

    def _clean_text(self, value):

        return " ".join(str(value).strip().split())

    ############################################################

    def _list_text(self, values):

        return " ".join(str(value) for value in (values or []))

    ############################################################

    def _slug(self, value):

        value = self._clean_text(value).lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)

        return value.strip("_")

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

    def _effective_people_count(self, analysis, text):

        count = self._to_int(analysis.get("people_count"))

        if count > 0:
            return count

        if re.search(r"\b(firefighter|firefighters|person|people|crew member)\b", text):
            return 1

        return count

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
