import re


class ProgramDetectionService:

    PROGRAMS = (
        {
            "name": "Hydrant Heroes",
            "terms": ("hydrant heroes",),
            "topics": ("hydrant", "winter_safety"),
            "audiences": ("community",),
            "seasonal_pattern": "winter"
        },
        {
            "name": "Travelling Sparky",
            "terms": ("travelling sparky", "traveling sparky"),
            "topics": ("public_education", "school_safety"),
            "audiences": ("grade 1 students", "children"),
            "seasonal_pattern": "school year"
        },
        {
            "name": "Fire Chief for a Day",
            "terms": ("fire chief for a day",),
            "topics": ("public_education", "recognition"),
            "audiences": ("students",),
            "seasonal_pattern": ""
        },
        {
            "name": "Recruit Academy",
            "terms": ("recruit academy",),
            "topics": ("recruitment", "training"),
            "audiences": ("recruits",),
            "seasonal_pattern": ""
        },
        {
            "name": "SCBA Training",
            "terms": ("scba", "breathing apparatus", "air pack"),
            "topics": ("scba_training", "training"),
            "audiences": ("firefighters",),
            "seasonal_pattern": ""
        },
        {
            "name": "Public Education",
            "terms": ("public education",),
            "topics": ("public_education",),
            "audiences": ("community",),
            "seasonal_pattern": ""
        },
        {
            "name": "Community Events",
            "terms": ("community event", "community events", "open house"),
            "topics": ("community_event",),
            "audiences": ("community",),
            "seasonal_pattern": ""
        },
        {
            "name": "Fire Prevention",
            "terms": ("fire prevention",),
            "topics": ("fire_prevention", "public_education"),
            "audiences": ("community",),
            "seasonal_pattern": "fall"
        }
    )

    def detect(self, text, explicit=None):

        explicit = self._clean(explicit)
        lower = self._clean(text).lower()
        results = []

        if explicit:
            results.append(
                self._program(
                    explicit,
                    ["explicit import field"],
                    95
                )
            )

        for program in self.PROGRAMS:
            evidence = [
                term
                for term in program["terms"]
                if self._contains_phrase(lower, term)
            ]

            if not evidence:
                continue

            results.append(
                {
                    "name": program["name"],
                    "description": "Detected from imported communication evidence.",
                    "typical_audiences": list(program["audiences"]),
                    "typical_topics": list(program["topics"]),
                    "seasonal_pattern": program["seasonal_pattern"],
                    "evidence": evidence,
                    "confidence": 90
                }
            )

        return self._unique_by_name(results)

    def _program(self, name, evidence, confidence):

        return {
            "name": name,
            "description": "Provided by import data.",
            "typical_audiences": [],
            "typical_topics": [],
            "seasonal_pattern": "",
            "evidence": evidence,
            "confidence": confidence
        }

    def _contains_phrase(self, text, phrase):

        return re.search(
            r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])",
            text
        ) is not None

    def _unique_by_name(self, programs):

        result = []
        seen = set()

        for program in programs:
            key = program["name"].strip().lower()

            if not key or key in seen:
                continue

            seen.add(key)
            result.append(program)

        return result

    def _clean(self, value):

        return " ".join(str(value or "").split())
