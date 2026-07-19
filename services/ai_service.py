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

        raw_response = self._raw_text(text)
        warnings = []
        parse_status = self.STATUS_VALID
        failure_category = ""
        normalization_evidence = []

        if not raw_response.strip():
            data = {}
            parse_status = self.STATUS_EMPTY
            failure_category = "empty_response"
            warnings.append("Provider returned empty output")
        else:
            (
                data,
                parse_status,
                warnings,
                failure_category,
                normalization_evidence
            ) = self._parse_json(raw_response)

        analysis = self._normalize_analysis(
            data,
            model,
            raw_response,
            parse_status,
            warnings,
            failure_category,
            normalization_evidence
        )

        return analysis

    ############################################################

    def analyze_image(self, image_path, vision_service, prompt_context=""):

        try:
            text = vision_service.analyze(
                image_path,
                prompt_context=prompt_context
            )
        except TypeError:
            text = vision_service.analyze(image_path)

        return self.parse_analysis(
            text,
            vision_service.model_name()
        )

    ############################################################

    def _parse_json(self, raw_response):

        original = raw_response.strip()
        text, fence = self._strip_fence(original)
        warnings = []
        evidence = []

        if fence:
            warnings.append("Removed JSON/code fence before parsing")
            evidence.append("markdown_wrapped_json")

        try:
            return (
                json.loads(text),
                self.STATUS_REPAIRED if fence else self.STATUS_VALID,
                warnings,
                "markdown_wrapped_json" if fence else "",
                evidence
            )
        except json.JSONDecodeError as ex:
            first_error = ex
        except Exception as ex:
            first_error = ex

        extracted = self._extract_json_object(text)

        if extracted and extracted != text:
            warnings.append("Extracted JSON object from surrounding text")
            evidence.append("extra_text_around_json")

            try:
                return (
                    json.loads(extracted),
                    self.STATUS_REPAIRED,
                    warnings,
                    "extra_text_around_json",
                    evidence
                )
            except Exception as ex:
                first_error = ex
                text = extracted

        repaired = self._repair_truncated_json(text)

        if repaired and repaired != text:
            warnings.append("Repaired truncated JSON braces")
            evidence.append("truncated_response")

            try:
                return (
                    json.loads(repaired),
                    self.STATUS_PARTIAL,
                    warnings,
                    "truncated_response",
                    evidence
                )
            except Exception:
                pass

        category = "malformed_json"
        if not extracted:
            category = "malformed_json"
        if "unterminated" in str(first_error).lower():
            category = "truncated_response"

        logger.warning(
            "AI response was not valid structured JSON category=%s error=%s",
            category,
            first_error
        )
        warnings.append(
            "Could not parse provider output as JSON: " + category
        )

        return {}, self.STATUS_INVALID, warnings, category, evidence

    ############################################################

    def _normalize_analysis(
        self,
        data,
        model,
        raw_response,
        parse_status,
        warnings,
        failure_category="",
        normalization_evidence=None
    ):

        normalization_evidence = list(normalization_evidence or [])

        if not isinstance(data, dict):
            data = {}
            warnings.append("JSON root was not an object")
            parse_status = self.STATUS_INVALID
            failure_category = failure_category or "unsupported_response_shape"

        description = self._text(data.get("description"))
        people = self._list(data.get("people"))
        apparatus = self._list(data.get("apparatus"))
        equipment = self._list(data.get("equipment"))
        activities = self._list(data.get("activities") or data.get("activity"))
        keywords = self._list(data.get("keywords"))
        safety_concerns = self._list(data.get("safety_concerns"))
        public_use_risks = self._list(data.get("public_use_risks"))
        visible_text = self._list(data.get("visible_text"))
        uncertain_observations = self._list(data.get("uncertain_observations"))
        setting = self._text(data.get("setting"))
        indoor_outdoor = self._choice(
            data.get("indoor_outdoor"),
            {"indoor", "outdoor", "mixed", "unknown"},
            "unknown"
        )
        confidence_value = self._confidence_value(data)
        confidence = self._confidence(confidence_value, warnings)
        people_count = self._people_count(
            data.get("people_count"),
            description,
            people,
            warnings
        )
        validation_category = self._validation_failure_category(
            data,
            description,
            confidence,
            people_count,
            warnings
        )
        if validation_category:
            parse_status = self.STATUS_INVALID
            failure_category = validation_category
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

        parser_classification = self._parser_classification(parse_status)
        persisted_failure_category = (
            failure_category
            if parser_classification == "invalid"
            else ""
        )

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
            "visible_text": visible_text,
            "uncertain_observations": uncertain_observations,
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
            "parser_classification": parser_classification,
            "failure_category": persisted_failure_category,
            "provider_failure_category": persisted_failure_category,
            "normalization_evidence": normalization_evidence,
            "user_facing_reason": self._user_reason(persisted_failure_category),
            "technical_detail": self._technical_detail(
                persisted_failure_category,
                warnings
            ),
            "retryable": persisted_failure_category in {
                "empty_response",
                "truncated_response",
                "malformed_json",
                "markdown_wrapped_json",
                "extra_text_around_json"
            },
            "structured_field_completeness": self._completeness({
                "description": description,
                "people_count": people_count,
                "people": people,
                "apparatus": apparatus,
                "equipment": equipment,
                "activities": activities,
                "setting": setting,
                "indoor_outdoor": indoor_outdoor,
                "visible_text": visible_text,
                "confidence": confidence
            })
        }

    ############################################################

    def _raw_text(self, value):

        if value is None:
            return ""

        if isinstance(value, (dict, list)):
            try:
                return json.dumps(value)
            except Exception:
                return str(value)

        return str(value)

    ############################################################

    def _strip_fence(self, text):

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
            text = re.sub(r"\s*```$", "", text)
            return text.strip(), True

        return text.strip(), False

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

    def _confidence_value(self, data):

        for key in (
            "confidence",
            "overall_score",
            "communications_score",
            "community_score",
            "education_score",
            "technical_score"
        ):

            value = data.get(key)

            if value is not None and value != "":
                return value

        return None

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

    def _validation_failure_category(
        self,
        data,
        description,
        confidence,
        people_count,
        warnings
    ):

        if not data:
            return ""

        if not description or len(description.strip()) < 8:
            warnings.append("Missing usable description")
            return "missing_required_fields"

        raw_confidence = self._confidence_value(data)
        try:
            raw_confidence_float = float(raw_confidence)
        except Exception:
            return "invalid_field_types"

        if raw_confidence_float < 0 or raw_confidence_float > 100:
            warnings.append("Confidence was outside supported range")
            return "invalid_field_types"

        raw_people_count = data.get("people_count")
        if raw_people_count is not None:
            try:
                raw_people_int = int(raw_people_count)
            except Exception:
                return "invalid_field_types"
            if raw_people_int < 0 or raw_people_int > 1000:
                warnings.append("people_count was outside supported range")
                return "invalid_field_types"

        for key in (
            "people",
            "apparatus",
            "equipment",
            "activities",
            "visible_text",
            "safety_concerns",
            "public_use_risks",
            "uncertain_observations"
        ):
            value = data.get(key)
            if value is not None and not isinstance(value, (list, str)):
                warnings.append(f"{key} used an unsupported field type")
                return "invalid_field_types"

        return ""

    ############################################################

    def _parser_classification(self, parse_status):

        if parse_status == self.STATUS_VALID:
            return "valid"
        if parse_status == self.STATUS_REPAIRED:
            return "normalized_valid"
        if parse_status == self.STATUS_PARTIAL:
            return "partial_valid"
        return "invalid"

    ############################################################

    def _user_reason(self, category):

        return {
            "empty_response": "Ollama returned no analysis text.",
            "truncated_response": "The model response appeared incomplete.",
            "malformed_json": "The model returned malformed JSON.",
            "markdown_wrapped_json": "The model wrapped JSON in Markdown.",
            "extra_text_around_json": "The model added text around the JSON.",
            "unsupported_response_shape": "Ollama returned an unsupported response shape.",
            "missing_required_fields": "The model omitted required analysis fields.",
            "invalid_field_types": "The model returned unsupported field values."
        }.get(category or "", "")

    ############################################################

    def _technical_detail(self, category, warnings):

        if not category:
            return ""

        return "; ".join([category] + [str(item) for item in warnings[:4]])

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
