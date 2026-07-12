import re


class CampaignDetectionService:

    CAMPAIGNS = (
        {
            "name": "Hydrant Heroes",
            "terms": ("hydrant heroes",),
            "topics": ("hydrant", "winter_safety"),
            "audiences": ("community",)
        },
        {
            "name": "Travelling Sparky",
            "terms": ("travelling sparky", "traveling sparky"),
            "topics": ("public_education", "school_safety"),
            "audiences": ("students", "children")
        },
        {
            "name": "Fire Prevention Week",
            "terms": ("fire prevention week",),
            "topics": ("fire_prevention", "public_education"),
            "audiences": ("community",)
        },
        {
            "name": "Emergency Preparedness Week",
            "terms": ("emergency preparedness week",),
            "topics": ("preparedness", "public_education"),
            "audiences": ("community",)
        },
        {
            "name": "Volunteer Recruitment",
            "terms": ("volunteer recruitment", "join our team", "join our crew"),
            "topics": ("recruitment",),
            "audiences": ("prospective firefighters",)
        },
        {
            "name": "Canada Day",
            "terms": ("canada day", "july 1"),
            "topics": ("holiday_safety", "community_event"),
            "audiences": ("community",)
        },
        {
            "name": "Open House",
            "terms": ("open house",),
            "topics": ("community_event", "recruitment"),
            "audiences": ("community",)
        },
        {
            "name": "Smoke Alarm Campaign",
            "terms": ("smoke alarm", "smoke alarms"),
            "topics": ("smoke_alarm", "fire_prevention"),
            "audiences": ("community",)
        }
    )

    def detect(self, text, explicit=None):

        explicit = self._clean(explicit)
        lower = self._clean(text).lower()
        results = []

        if explicit:
            results.append(
                self._campaign(
                    explicit,
                    ["explicit import field"],
                    95
                )
            )

        for campaign in self.CAMPAIGNS:
            evidence = [
                term
                for term in campaign["terms"]
                if self._contains_phrase(lower, term)
            ]

            if not evidence:
                continue

            results.append(
                {
                    "name": campaign["name"],
                    "description": "Detected from imported communication evidence.",
                    "goals": list(campaign["topics"]),
                    "audiences": list(campaign["audiences"]),
                    "topics": list(campaign["topics"]),
                    "editorial_angles": list(campaign["topics"]),
                    "evidence": evidence,
                    "confidence": 90
                }
            )

        return self._unique_by_name(results)

    def _campaign(self, name, evidence, confidence):

        return {
            "name": name,
            "description": "Provided by import data.",
            "goals": [],
            "audiences": [],
            "topics": [],
            "editorial_angles": [],
            "evidence": evidence,
            "confidence": confidence
        }

    def _contains_phrase(self, text, phrase):

        return re.search(
            r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])",
            text
        ) is not None

    def _unique_by_name(self, campaigns):

        result = []
        seen = set()

        for campaign in campaigns:
            key = campaign["name"].strip().lower()

            if not key or key in seen:
                continue

            seen.add(key)
            result.append(campaign)

        return result

    def _clean(self, value):

        return " ".join(str(value or "").split())
