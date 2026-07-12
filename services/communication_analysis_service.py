import re

from services.campaign_detection_service import CampaignDetectionService
from services.logging_service import LoggingService
from services.program_detection_service import ProgramDetectionService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationAnalysisService:

    ANALYSIS_VERSION = "communication_intelligence_v1"

    TOPIC_DEFINITIONS = (
        ("heat_safety", "Heat Safety", ("heat warning", "heat", "hot weather", "hydrate")),
        ("winter_safety", "Winter Safety", ("winter", "ice", "snow", "cold", "hydrant")),
        ("smoke_alarm", "Smoke Alarms", ("smoke alarm", "smoke alarms", "test your alarm")),
        ("fire_prevention", "Fire Prevention", ("fire prevention", "escape plan", "cooking safety")),
        ("recruitment", "Recruitment", ("recruit", "volunteer", "join our crew", "join our team")),
        ("scba_training", "SCBA Training", ("scba", "breathing apparatus", "air pack")),
        ("training", "Training", ("training", "drill", "evolution", "academy")),
        ("community_event", "Community Event", ("open house", "community event", "parade", "visit")),
        ("recognition", "Recognition", ("thank", "congratulations", "recognize", "appreciation")),
        ("emergency_response", "Emergency Response", ("responded", "incident", "scene", "crews attended")),
        ("preparedness", "Preparedness", ("prepared", "preparedness", "emergency kit", "storm")),
        ("water_safety", "Water Safety", ("water safety", "swim", "lake", "river")),
        ("apparatus", "Apparatus", ("engine", "pumper", "ladder truck", "rescue truck"))
    )

    CATEGORY_TERMS = {
        "public_education": ("safety", "remember", "check", "prevent", "alarm", "escape"),
        "recruitment": ("recruit", "volunteer", "join", "apply", "serve"),
        "community": ("community", "morden", "neighbour", "family", "open house"),
        "operations": ("responded", "incident", "scene", "training", "drill"),
        "recognition": ("thank", "congrat", "proud", "recognize")
    }

    def __init__(self, campaign_detector=None, program_detector=None):

        self.campaign_detector = campaign_detector or CampaignDetectionService()
        self.program_detector = program_detector or ProgramDetectionService()

    ############################################################

    def analyze(self, record, delivery=None):

        delivery = delivery or {}
        text = self._combined_text(record, delivery)
        lower = text.lower()
        explicit_campaign = record.get("campaign") or delivery.get("campaign")
        explicit_program = record.get("program") or delivery.get("program")
        campaigns = self.campaign_detector.detect(
            text,
            explicit=explicit_campaign
        )
        programs = self.program_detector.detect(
            text,
            explicit=explicit_program
        )
        topics = self.extract_topics(text)

        for topic in record.get("topics") or delivery.get("topics") or []:
            token = self._token(topic)

            if not any(item["topic"] == token for item in topics):
                topics.append(
                    {
                        "topic": token,
                        "label": str(topic).replace("_", " ").title(),
                        "matches": ["explicit import field"],
                        "confidence": 90
                    }
                )
        category = self._category(lower)
        values = self._value_scores(lower, topics, campaigns, programs)

        intelligence = {
            "communication_id": record.get("communication_id", 0),
            "primary_story": self._primary_story(record, text),
            "editorial_angle": self._editorial_angle(category, topics),
            "communication_purpose": self._purpose(category, topics),
            "category": category,
            "intended_audiences": self._audiences(lower, campaigns, programs),
            "topics": [
                item["topic"]
                for item in topics
            ],
            "programs": [
                item["name"]
                for item in programs
            ],
            "campaigns": [
                item["name"]
                for item in campaigns
            ],
            "seasonal_relevance": self._seasonal_relevance(lower, topics),
            "educational_value": values["educational_value"],
            "recruitment_value": values["recruitment_value"],
            "preparedness_value": values["preparedness_value"],
            "operational_value": values["operational_value"],
            "community_trust_value": values["community_trust_value"],
            "historical_value": values["historical_value"],
            "human_interest_value": values["human_interest_value"],
            "evergreen_value": values["evergreen_value"],
            "confidence_score": self._confidence(text, topics, campaigns, programs),
            "source_signals": self._source_signals(topics, campaigns, programs),
            "analysis_version": self.ANALYSIS_VERSION,
            "generated_at": TimeService.utc_now_iso(),
            "campaign_objects": campaigns,
            "program_objects": programs,
            "topic_objects": topics,
            "outcome": self._outcome(values, topics)
        }

        logger.info(
            "Generated communication intelligence topics=%s campaigns=%s programs=%s",
            len(topics),
            len(campaigns),
            len(programs)
        )

        return intelligence

    ############################################################

    def extract_topics(self, text):

        lower = self._clean(text).lower()
        topics = []

        for topic, label, terms in self.TOPIC_DEFINITIONS:
            matches = [
                term
                for term in terms
                if self._contains_phrase(lower, term)
            ]

            if not matches:
                continue

            topics.append(
                {
                    "topic": topic,
                    "label": label,
                    "matches": matches,
                    "confidence": min(95, 55 + len(matches) * 15)
                }
            )

        return topics

    ############################################################

    def _combined_text(self, record, delivery):

        return " ".join(
            value
            for value in (
                record.get("title", ""),
                record.get("original_text", ""),
                record.get("summary", ""),
                delivery.get("delivery_text", "")
            )
            if value
        )

    def _primary_story(self, record, text):

        summary = self._clean(record.get("summary", ""))

        if summary:
            return summary[:240]

        sentences = re.split(r"(?<=[.!?])\s+", self._clean(text))

        return (sentences[0] if sentences else "")[:240]

    def _category(self, lower):

        best = ("general", 0)

        for category, terms in self.CATEGORY_TERMS.items():
            score = sum(1 for term in terms if self._contains_phrase(lower, term))

            if score > best[1]:
                best = (category, score)

        return best[0]

    def _editorial_angle(self, category, topics):

        if topics:
            return topics[0]["label"]

        return category.replace("_", " ").title()

    def _purpose(self, category, topics):

        if category == "recruitment":
            return "Encourage future members to consider serving."

        if category == "public_education":
            return "Share a practical public safety message."

        if category == "community":
            return "Build community connection and trust."

        if topics:
            return f"Communicate about {topics[0]['label'].lower()}."

        return "Record a department communication for future planning."

    def _audiences(self, lower, campaigns, programs):

        audiences = []

        for item in campaigns:
            audiences.extend(item.get("audiences") or [])

        for item in programs:
            audiences.extend(item.get("typical_audiences") or [])

        if self._contains_phrase(lower, "children") or self._contains_phrase(lower, "students"):
            audiences.append("families")

        if self._contains_phrase(lower, "volunteer") or self._contains_phrase(lower, "recruit"):
            audiences.append("prospective firefighters")

        if not audiences:
            audiences.append("community")

        return self._unique(audiences)

    def _seasonal_relevance(self, lower, topics):

        values = []
        topic_names = {item["topic"] for item in topics}

        if "winter_safety" in topic_names:
            values.append("winter")

        if "heat_safety" in topic_names or "water_safety" in topic_names:
            values.append("summer")

        if "fire_prevention" in topic_names:
            values.append("fall")

        if "canada day" in lower:
            values.append("july")

        return self._unique(values)

    def _value_scores(self, lower, topics, campaigns, programs):

        topic_names = {item["topic"] for item in topics}

        return {
            "educational_value": self._score(
                lower,
                ("safety", "remember", "check", "prevent", "education", "alarm"),
                topic_names & {"smoke_alarm", "fire_prevention", "preparedness"}
            ),
            "recruitment_value": self._score(
                lower,
                ("join", "recruit", "volunteer", "apply"),
                topic_names & {"recruitment"}
            ),
            "preparedness_value": self._score(
                lower,
                ("prepared", "storm", "emergency kit", "warning"),
                topic_names & {"preparedness", "heat_safety", "winter_safety"}
            ),
            "operational_value": self._score(
                lower,
                ("training", "responded", "incident", "scene", "drill"),
                topic_names & {"training", "emergency_response"}
            ),
            "community_trust_value": self._score(
                lower,
                ("community", "morden", "neighbour", "thank", "open house"),
                topic_names & {"community_event", "recognition"}
            ),
            "historical_value": self._score(
                lower,
                ("throwback", "history", "anniversary", "on this day"),
                set()
            ),
            "human_interest_value": self._score(
                lower,
                ("firefighter", "family", "children", "volunteer", "thank"),
                topic_names & {"recognition", "recruitment"}
            ),
            "evergreen_value": 70 if topic_names & {
                "smoke_alarm",
                "fire_prevention",
                "preparedness",
                "recruitment"
            } else 45
        }

    def _score(self, lower, terms, matched_topics):

        score = sum(
            18
            for term in terms
            if self._contains_phrase(lower, term)
        ) + len(matched_topics) * 20

        return max(0, min(100, score))

    def _confidence(self, text, topics, campaigns, programs):

        score = 25

        if len(text) > 30:
            score += 25

        score += min(25, len(topics) * 8)
        score += min(20, len(campaigns) * 10 + len(programs) * 10)

        return max(0, min(95, score))

    def _source_signals(self, topics, campaigns, programs):

        signals = []

        for topic in topics:
            signals.append(
                f"topic:{topic['topic']} via {', '.join(topic['matches'][:3])}"
            )

        for campaign in campaigns:
            signals.append(
                f"campaign:{campaign['name']}"
            )

        for program in programs:
            signals.append(
                f"program:{program['name']}"
            )

        return signals

    def _outcome(self, values, topics):

        should_repeat = values["evergreen_value"] >= 65

        return {
            "engagement_assessment": "insufficient imported outcomes",
            "educational_strength": values["educational_value"],
            "recruitment_strength": values["recruitment_value"],
            "community_trust_strength": values["community_trust_value"],
            "preparedness_strength": values["preparedness_value"],
            "historical_value": values["historical_value"],
            "evergreen_status": "evergreen" if should_repeat else "contextual",
            "recommended_repeat_interval_days": 90 if should_repeat else 0,
            "should_repeat": 1 if should_repeat else 0,
            "editorial_success_notes": "Outcome data is local/imported only.",
            "confidence_score": min(85, 35 + len(topics) * 10),
            "source": self.ANALYSIS_VERSION
        }

    def _contains_phrase(self, text, phrase):

        return re.search(
            r"(?<![a-z0-9])" + re.escape(str(phrase).lower()) + r"(?![a-z0-9])",
            text
        ) is not None

    def _clean(self, value):

        return " ".join(str(value or "").split())

    def _unique(self, values):

        result = []
        seen = set()

        for value in values:
            value = str(value or "").strip()

            if not value or value.lower() in seen:
                continue

            seen.add(value.lower())
            result.append(value)

        return result

    def _token(self, value):

        return str(value or "").strip().lower().replace(" ", "_")
