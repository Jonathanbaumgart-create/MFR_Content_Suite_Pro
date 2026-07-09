import re
import json

from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class AIService:

    def parse_analysis(self, text, model="unknown"):

        try:
            data = json.loads(self._clean_json(text))
        except Exception:
            logger.exception("AI response was not valid JSON")

            data = {
                "description": text,
                "scene_type": "",
                "activity": "",
                "people_count": 0,
                "apparatus": [],
                "equipment": [],
                "keywords": [],
                "community_score": 50,
                "recruitment_score": 50,
                "education_score": 50,
                "technical_score": 50,
                "overall_score": 50,
                "facebook_caption": "",
                "instagram_caption": "",
                "model": model
            }

        defaults = {
            "description": "",
            "scene_type": "",
            "activity": "",
            "people_count": 0,
            "apparatus": [],
            "equipment": [],
            "keywords": [],
            "community_score": 0,
            "recruitment_score": 0,
            "education_score": 0,
            "technical_score": 0,
            "overall_score": 0,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": model
        }

        for k, v in defaults.items():
            data.setdefault(k, v)

        data["description"] = self._ensure_text(data.get("description"))
        data["scene_type"] = self._ensure_text(data.get("scene_type"))
        data["activity"] = self._ensure_text(data.get("activity"))
        data["apparatus"] = self._ensure_list(data.get("apparatus"))
        data["equipment"] = self._ensure_list(data.get("equipment"))
        data["keywords"] = self._ensure_list(data.get("keywords"))
        data["people_count"] = self._ensure_people_count(
            data.get("people_count"),
            data
        )

        for key in (
            "community_score",
            "recruitment_score",
            "education_score",
            "technical_score",
            "overall_score"
        ):
            data[key] = self._ensure_int(data.get(key))

        return data

    ############################################################

    def analyze_image(self, image_path, vision_service):

        text = vision_service.analyze(image_path)

        return self.parse_analysis(
            text,
            vision_service.model_name()
        )

    ############################################################

    def _clean_json(self, text):

        text = text.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text)
            text = re.sub(r"```$", "", text)

        return text.strip()

    ############################################################

    def _ensure_list(self, value):

        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            if not value.strip():
                return []
            return [
                item.strip()
                for item in re.split(r"[,;\n]+", value)
                if item.strip()
            ]

        return [str(value)]

    ############################################################

    def _ensure_int(self, value):

        if isinstance(value, str):
            match = re.search(r"-?\d+", value)

            if match:
                value = match.group(0)

        try:
            return int(value)
        except Exception:
            return 0

    ############################################################

    def _ensure_people_count(self, value, data):

        count = self._ensure_int(value)

        if count > 0:
            return count

        text = self._analysis_text(data)

        if re.search(r"\b(one|single|a)\s+(firefighter|person|worker)\b", text):
            return 1

        if re.search(r"\b(firefighter|firefighters|person|people|crew member)\b", text):
            return 1

        return 0

    ############################################################

    def _analysis_text(self, data):

        parts = [
            data.get("description", ""),
            data.get("scene_type", ""),
            data.get("activity", ""),
            " ".join(self._ensure_list(data.get("apparatus"))),
            " ".join(self._ensure_list(data.get("equipment"))),
            " ".join(self._ensure_list(data.get("keywords")))
        ]

        return " ".join(str(part).lower() for part in parts if part)

    ############################################################

    def _ensure_text(self, value):

        if value is None:
            return ""

        return str(value).strip()
