import json
import re

from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class AIService:

    STATUS_VALID = "valid_structured_response"
    STATUS_REPAIRED = "repaired_structured_response"
    STATUS_PARTIAL = "partial_response"
    STATUS_INVALID = "invalid_response"
    STATUS_EMPTY = "empty_response"

    ############################################################

    def parse_analysis(self, text, model="unknown"):

        raw_response = "" if text is None else str(text)
        warnings = []
        parse_status = self.STATUS_VALID

        if not raw_response.strip():
            data = {}
            parse_status = self.STATUS_EMPTY
            warnings.append("Provider returned empty output")
        else:
            data, parse_status, warnings = self._parse_json(raw_response)

        analysis = self._normalize_analysis(
            data,
            model,
            raw_response,
            parse_status,
            warnings
        )

        return analysis

    ############################################################

    def analyze_image(self, image_path, vision_service):

        text = vision_service.analyze(image_path)

        return self.parse_analysis(
            text,
            vision_service.model_name()
        )

    ############################################################

    def _parse_json(self, raw_response):

        text = self._strip_fence(raw_response.strip())
        warnings = []

        try:
            return json.loads(text), self.STATUS_VALID, warnings
        except Exception:
            pass

        extracted = self._extract_json_object(text)

        if extracted and extracted != text:
            warnings.append("Extracted JSON object from surrounding text")

            try:
                return json.loads(extracted), self.STATUS_REPAIRED, warnings
            except Exception:
                text = extracted

        repaired = self._repair_truncated_json(text)

        if repaired and repaired != text:
            warnings.append("Repaired truncated JSON braces")

            try:
                return json.loads(repaired), self.STATUS_PARTIAL, warnings
            except Exception:
                pass

        logger.warning("AI response was not valid structured JSON")
        warnings.append("Could not parse provider output as JSON")

        return {}, self.STATUS_INVALID, warnings

    ############################################################

    def _normalize_analysis(
        self,
        data,
        model,
        raw_response,
        parse_status,
        warnings
    ):

        if not isinstance(data, dict):
            data = {}
            warnings.append("JSON root was not an object")
            parse_status = self.STATUS_INVALID

        description = self._text(data.get("description"))
        people = self._list(data.get("people"))
        apparatus = self._list(data.get("apparatus"))
        equipment = self._list(data.get("equipment"))
        activities = self._list(data.get("activities") or data.get("activity"))
        keywords = self._list(data.get("keywords"))
        safety_concerns = self._list(data.get("safety_concerns"))
        public_use_risks = self._list(data.get("public_use_risks"))
        setting = self._text(data.get("setting"))
        indoor_outdoor = self._choice(
            data.get("indoor_outdoor"),
            {"indoor", "outdoor", "mixed", "unknown"},
            "unknown"
        )
        confidence = self._confidence(data.get("confidence"), warnings)
        people_count = self._people_count(
            data.get("people_count"),
            description,
            people,
            warnings
        )
        visual_facts = self._visual_fact_count(
            description,
            people_count,
            people,
            apparatus,
            equipment,
            activities,
            setting
        )

        if parse_status == self.STATUS_VALID and visual_facts < 2:
            parse_status = self.STATUS_PARTIAL
            warnings.append("Structured response contained little visual detail")

        if parse_status == self.STATUS_EMPTY:
            confidence = 0.0
        elif parse_status == self.STATUS_INVALID:
            confidence = min(confidence, 0.05)
        elif parse_status == self.STATUS_PARTIAL:
            confidence = min(confidence, 0.35)
        elif parse_status == self.STATUS_REPAIRED:
            confidence = min(confidence, 0.7)

        scene_type = self._scene_type(
            data,
            setting,
            indoor_outdoor,
            activities
        )
        activity = ", ".join(activities)
        keyword_set = self._unique(
            keywords +
            people +
            activities +
            safety_concerns +
            public_use_risks +
            [setting, indoor_outdoor]
        )
        overall_score = int(round(confidence * 100))

        return {
            "description": description,
            "scene_type": scene_type,
            "activity": activity,
            "people_count": people_count,
            "people": people,
            "apparatus": apparatus,
            "equipment": equipment,
            "activities": activities,
            "setting": setting,
            "indoor_outdoor": indoor_outdoor,
            "training": self._bool(data.get("training")),
            "incident_scene": self._bool(data.get("incident_scene")),
            "public_education": self._bool(data.get("public_education")),
            "community_event": self._bool(data.get("community_event")),
            "safety_concerns": safety_concerns,
            "public_use_risks": public_use_risks,
            "keywords": keyword_set,
            "community_score": overall_score if self._bool(data.get("community_event")) else 0,
            "recruitment_score": 0,
            "education_score": overall_score if self._bool(data.get("public_education")) else 0,
            "technical_score": overall_score if equipment or apparatus else 0,
            "overall_score": overall_score,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": self._text(data.get("model")) or model,
            "confidence": confidence,
            "raw_response": raw_response,
            "parse_status": parse_status,
            "parse_warnings": warnings,
            "structured_field_completeness": self._completeness({
                "description": description,
                "people_count": people_count,
                "people": people,
                "apparatus": apparatus,
                "equipment": equipment,
                "activities": activities,
                "setting": setting,
                "indoor_outdoor": indoor_outdoor,
                "confidence": confidence
            })
        }

    ############################################################

    def _strip_fence(self, text):

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
            text = re.sub(r"\s*```$", "", text)

        return text.strip()

    ############################################################

    def _extract_json_object(self, text):

        start = text.find("{")
        end = text.rfind("}")

        if start < 0 or end < start:
            return ""

        return text[start:end + 1].strip()

    ############################################################

    def _repair_truncated_json(self, text):

        start = text.find("{")

        if start < 0:
            return ""

        candidate = text[start:].strip().rstrip(",")
        open_braces = candidate.count("{")
        close_braces = candidate.count("}")
        open_brackets = candidate.count("[")
        close_brackets = candidate.count("]")

        if open_braces <= close_braces and open_brackets <= close_brackets:
            return candidate

        candidate += "]" * max(0, open_brackets - close_brackets)
        candidate += "}" * max(0, open_braces - close_braces)

        return candidate

    ############################################################

    def _list(self, value):

        if value is None:
            return []

        if isinstance(value, list):
            return [
                self._text(item)
                for item in value
                if self._text(item)
            ]

        if isinstance(value, str):
            if not value.strip():
                return []
            return [
                item.strip()
                for item in re.split(r"[,;\n]+", value)
                if item.strip()
            ]

        return [self._text(value)] if self._text(value) else []

    ############################################################

    def _text(self, value):

        if value is None:
            return ""

        return str(value).strip()

    ############################################################

    def _int(self, value):

        if isinstance(value, str):
            match = re.search(r"-?\d+", value)
            if match:
                value = match.group(0)

        try:
            return int(value)
        except Exception:
            return 0

    ############################################################

    def _confidence(self, value, warnings):

        try:
            confidence = float(value)
        except Exception:
            warnings.append("Missing or invalid confidence")
            return 0.0

        if confidence > 1:
            warnings.append("Confidence was outside 0-1 range")
            confidence = confidence / 100 if confidence <= 100 else 1

        return max(0.0, min(1.0, confidence))

    ############################################################

    def _people_count(self, value, description, people, warnings):

        count = self._int(value)

        if count < 0:
            warnings.append("Negative people_count changed to zero")
            return 0

        if count == 0 and people:
            count = len(people)

        description_text = description.lower()

        if count == 0 and re.search(
            r"\b(no|without)\s+(people|person|firefighters|firefighter|crew)\b",
            description_text
        ):
            return 0

        if count == 0 and re.search(
            r"\b(person|people|firefighter|firefighters|crew|child|children)\b",
            description_text
        ):
            count = 1
            warnings.append("Inferred people_count from description text")

        return count

    ############################################################

    def _choice(self, value, allowed, default):

        text = self._text(value).lower()
        return text if text in allowed else default

    ############################################################

    def _bool(self, value):

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "1"}

        return bool(value)

    ############################################################

    def _scene_type(self, data, setting, indoor_outdoor, activities):

        scene = self._text(data.get("scene_type"))

        if scene:
            return scene

        if setting:
            return setting

        if activities:
            return activities[0]

        return indoor_outdoor if indoor_outdoor != "unknown" else ""

    ############################################################

    def _visual_fact_count(
        self,
        description,
        people_count,
        people,
        apparatus,
        equipment,
        activities,
        setting
    ):

        return sum(
            1
            for value in (
                description,
                people_count,
                people,
                apparatus,
                equipment,
                activities,
                setting
            )
            if value
        )

    ############################################################

    def _completeness(self, fields):

        total = len(fields)
        present = 0

        for key, value in fields.items():
            if key == "people_count":
                present += 1
            elif key == "indoor_outdoor":
                present += 1 if value != "unknown" else 0
            elif value:
                present += 1

        return round(present / total, 3) if total else 0

    ############################################################

    def _unique(self, values):

        seen = set()
        results = []

        for value in values:
            text = self._text(value)
            key = text.lower()

            if not text or key in seen:
                continue

            seen.add(key)
            results.append(text)

        return results
