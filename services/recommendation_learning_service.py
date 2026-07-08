from datetime import datetime
import hashlib

from core.app_context import context
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class RecommendationLearningService:

    POSITIVE_TYPES = {
        "accepted": 4.0,
        "saved": 3.0,
        "opened": 2.0,
        "useful": 4.0,
        "viewed": 0.5,
        "generated": 0.25
    }

    NEGATIVE_TYPES = {
        "dismissed": -3.0,
        "not_useful": -3.0,
        "regenerated": -1.0
    }

    OPPORTUNITY_HINTS = {
        "heat_warning": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Morning",
            "tone": "Public Safety"
        },
        "storm_safety": {
            "platforms": ("Facebook",),
            "posting_time": "Morning",
            "tone": "Public Safety"
        },
        "smoke_alarm_reminder": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Morning",
            "tone": "Educational"
        },
        "recruitment": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Evening",
            "tone": "Recruitment"
        },
        "training_highlight": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Evening",
            "tone": "Behind The Scenes"
        },
        "community_appreciation": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Afternoon",
            "tone": "Community"
        },
        "fire_prevention_week": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Morning",
            "tone": "Educational"
        },
        "apparatus_showcase": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Afternoon",
            "tone": "Technical"
        },
        "holiday_safety": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Morning",
            "tone": "Public Safety"
        },
        "water_safety": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Morning",
            "tone": "Public Safety"
        },
        "volunteer_recognition": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Evening",
            "tone": "Recognition"
        },
        "behind_the_scenes": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Evening",
            "tone": "Behind The Scenes"
        },
        "throwback_thursday": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Morning",
            "tone": "Community"
        },
        "general_engagement": {
            "platforms": ("Facebook", "Instagram"),
            "posting_time": "Afternoon",
            "tone": "Community"
        }
    }

    def __init__(self, database=None):

        self.db = database or context.database
        self._preference_cache = None

    ############################################################

    def record_generated(self, recommendation, prompt=""):

        media = self._top_media(recommendation)
        notes = ""

        if prompt:
            notes = f"prompt:{prompt}"

        return self.record_feedback(
            recommendation,
            "generated",
            media=media,
            notes=notes
        )

    ############################################################

    def record_viewed(self, recommendation):

        return self.record_feedback(
            recommendation,
            "viewed"
        )

    ############################################################

    def record_feedback(self, recommendation, feedback_type, media=None, notes=""):

        feedback_type = self._feedback_type(feedback_type)
        media = media or self._top_media(recommendation)
        recommendation_id = self._recommendation_id(
            recommendation,
            media
        )

        row = {
            "recommendation_id": recommendation_id,
            "media_id": (media or {}).get("media_id"),
            "feedback_type": feedback_type,
            "accepted": 1 if feedback_type in ("accepted", "useful", "saved") else 0,
            "dismissed": 1 if feedback_type in ("dismissed", "not_useful") else 0,
            "opened": 1 if feedback_type == "opened" else 0,
            "regenerated": 1 if feedback_type == "regenerated" else 0,
            "notes": notes,
            "confidence": recommendation.get("confidence", 0),
            "opportunity_type": recommendation.get("opportunity_type", "")
        }

        feedback_id = self.db.save_recommendation_feedback(row)
        self._preference_cache = None

        logger.info(
            "Recommendation feedback recorded id=%s type=%s media_id=%s opportunity=%s",
            feedback_id,
            feedback_type,
            row["media_id"],
            row["opportunity_type"]
        )

        return feedback_id

    ############################################################

    def preferences(self):

        scores = self.preference_scores()

        preferences = {
            "content_themes": self._top_labels(scores["content_themes"]),
            "incident_types": self._top_labels(scores["incident_types"]),
            "activities": self._top_labels(scores["activities"]),
            "apparatus": self._top_labels(scores["apparatus"]),
            "recommendation_types": self._top_labels(scores["recommendation_types"]),
            "caption_tones": self._top_labels(scores["caption_tones"]),
            "platforms": self._top_labels(scores["platforms"]),
            "posting_times": self._top_labels(scores["posting_times"])
        }
        preferences["summary"] = self.preference_summary(preferences)

        logger.info(
            "Recommendation preferences calculated summary=%s",
            preferences["summary"]
        )

        return preferences

    ############################################################

    def preference_scores(self):

        if self._preference_cache is not None:
            return self._preference_cache

        rows = self.db.recommendation_feedback_rows(limit=2500)
        scores = {
            "content_themes": {},
            "incident_types": {},
            "activities": {},
            "apparatus": {},
            "recommendation_types": {},
            "caption_tones": {},
            "platforms": {},
            "posting_times": {},
            "media": {}
        }
        intelligence_cache = {}

        for row in rows:
            weight = self._row_weight(row)

            if weight == 0:
                continue

            media_id = row.get("media_id")
            opportunity = row.get("opportunity_type", "")

            if media_id:
                scores["media"][media_id] = scores["media"].get(media_id, 0) + weight

            if opportunity:
                self._add_score(
                    scores["recommendation_types"],
                    opportunity,
                    weight
                )
                self._add_opportunity_hints(
                    scores,
                    opportunity,
                    weight
                )

            intelligence = None

            if media_id:
                if media_id not in intelligence_cache:
                    intelligence_cache[media_id] = self.db.get_media_intelligence(
                        media_id
                    )

                intelligence = intelligence_cache[media_id]

            if intelligence:
                self._add_score(
                    scores["incident_types"],
                    intelligence.get("incident_type"),
                    weight
                )
                self._add_score(
                    scores["activities"],
                    intelligence.get("primary_activity"),
                    weight
                )

                for theme in intelligence.get("content_themes") or []:
                    self._add_score(scores["content_themes"], theme, weight)

                for tag in intelligence.get("apparatus_tags") or []:
                    self._add_score(scores["apparatus"], tag, weight)

        self._preference_cache = scores

        return scores

    ############################################################

    def preference_summary(self, preferences=None):

        preferences = preferences or self.preferences()
        labels = []

        for key in (
            "content_themes",
            "recommendation_types",
            "incident_types",
            "activities",
            "apparatus",
            "platforms",
            "posting_times"
        ):
            labels.extend(preferences.get(key, [])[:2])

        return self._unique(labels)[:8]

    ############################################################

    def analytics(self):

        rows = self.db.recommendation_feedback_rows(limit=5000)
        accepted = [
            row
            for row in rows
            if row.get("accepted")
        ]
        dismissed = [
            row
            for row in rows
            if row.get("dismissed")
        ]
        actionable = len(accepted) + len(dismissed)
        confidences = [
            float(row.get("confidence") or 0)
            for row in rows
            if row.get("confidence") is not None
        ]

        analytics = {
            "total_feedback": len(rows),
            "acceptance_rate": self._rate(len(accepted), actionable),
            "dismissal_rate": self._rate(len(dismissed), actionable),
            "average_confidence": round(
                sum(confidences) / max(1, len(confidences)),
                1
            ),
            "most_accepted_opportunity_type": self._most_common(
                row.get("opportunity_type")
                for row in accepted
            ),
            "most_rejected_opportunity_type": self._most_common(
                row.get("opportunity_type")
                for row in dismissed
            ),
            "most_requested_prompts": self._prompt_counts(rows)[:5]
        }

        logger.info(
            "Recommendation analytics calculated total=%s acceptance=%s dismissal=%s",
            analytics["total_feedback"],
            analytics["acceptance_rate"],
            analytics["dismissal_rate"]
        )

        return analytics

    ############################################################

    def score_adjustment(self, candidate, opportunity_type, profile=None):

        scores = self.preference_scores()
        adjustment = 0.0
        reasons = []

        opportunity_score = scores["recommendation_types"].get(
            self._token(opportunity_type),
            0
        )

        if opportunity_score:
            value = self._bounded(opportunity_score * 0.8, -5, 5)
            adjustment += value
            reasons.append(
                f"learned preference for {self._format_label(opportunity_type)}"
            )

        for key, bucket, limit in (
            ("incident_type", "incident_types", 4),
            ("primary_activity", "activities", 4)
        ):
            value = scores[bucket].get(
                self._token(candidate.get(key)),
                0
            )

            if value:
                adjustment += self._bounded(value * 0.5, -limit, limit)
                reasons.append(
                    f"matches preferred {key.replace('_', ' ')}"
                )

        for key, bucket, limit in (
            ("content_themes", "content_themes", 5),
            ("apparatus_tags", "apparatus", 3)
        ):
            matched = self._list_score(
                candidate.get(key) or [],
                scores[bucket]
            )

            if matched:
                adjustment += self._bounded(matched * 0.4, -limit, limit)
                reasons.append(
                    f"matches learned {key.replace('_', ' ')}"
                )

        media_id = candidate.get("media_id")
        media_score = scores["media"].get(media_id, 0)

        if media_score > 0:
            penalty = min(8, media_score * 0.6)
            adjustment -= penalty
            reasons.append("diversity learning reduced repeat exposure")

        adjustment = self._bounded(adjustment, -12, 12)

        if abs(adjustment) >= 0.1:
            logger.info(
                "Recommendation learning adjustment media_id=%s opportunity=%s adjustment=%s reasons=%s",
                media_id,
                opportunity_type,
                round(adjustment, 1),
                reasons
            )

        return round(adjustment, 1), self._unique(reasons)

    ############################################################

    def _top_media(self, recommendation):

        media = recommendation.get("recommended_media") or []

        if media:
            return media[0]

        return None

    ############################################################

    def _recommendation_id(self, recommendation, media):

        if recommendation.get("recommendation_id"):
            return recommendation["recommendation_id"]

        source = "|".join(
            [
                str(recommendation.get("opportunity_type", "")),
                str((media or {}).get("media_id", "")),
                str(recommendation.get("title", "")),
                datetime.now().isoformat(timespec="seconds")
            ]
        )
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
        recommendation["recommendation_id"] = digest

        return digest

    ############################################################

    def _row_weight(self, row):

        feedback_type = row.get("feedback_type", "")

        if row.get("accepted"):
            return 4.0

        if row.get("dismissed"):
            return -3.0

        if row.get("opened"):
            return 2.0

        if row.get("regenerated"):
            return -1.0

        return (
            self.POSITIVE_TYPES.get(feedback_type) or
            self.NEGATIVE_TYPES.get(feedback_type) or
            0
        )

    ############################################################

    def _add_opportunity_hints(self, scores, opportunity, weight):

        hints = self.OPPORTUNITY_HINTS.get(opportunity, {})

        for platform in hints.get("platforms", ()):
            self._add_score(scores["platforms"], platform, weight)

        self._add_score(
            scores["posting_times"],
            hints.get("posting_time"),
            weight
        )
        self._add_score(
            scores["caption_tones"],
            hints.get("tone"),
            weight
        )

    ############################################################

    def _add_score(self, scores, value, weight):

        token = self._token(value)

        if not token:
            return

        scores[token] = scores.get(token, 0) + weight

    ############################################################

    def _top_labels(self, scores, limit=5):

        ranked = sorted(
            (
                (value, score)
                for value, score in scores.items()
                if score > 0
            ),
            key=lambda item: item[1],
            reverse=True
        )

        return [
            self._format_label(value)
            for value, _score in ranked[:limit]
        ]

    ############################################################

    def _prompt_counts(self, rows):

        counts = {}

        for row in rows:
            notes = row.get("notes", "")

            if not notes.startswith("prompt:"):
                continue

            prompt = notes.split("prompt:", 1)[1].strip()

            if not prompt:
                continue

            counts[prompt] = counts.get(prompt, 0) + 1

        return sorted(
            counts.items(),
            key=lambda item: item[1],
            reverse=True
        )

    ############################################################

    def _most_common(self, values):

        counts = {}

        for value in values:
            token = self._token(value)

            if not token:
                continue

            counts[token] = counts.get(token, 0) + 1

        if not counts:
            return ""

        return self._format_label(
            max(
                counts.items(),
                key=lambda item: item[1]
            )[0]
        )

    ############################################################

    def _list_score(self, values, scores):

        total = 0

        for value in values:
            total += scores.get(
                self._token(value),
                0
            )

        return total

    ############################################################

    def _feedback_type(self, value):

        mapping = {
            "useful": "accepted",
            "not_useful": "dismissed",
            "save_for_later": "saved"
        }

        return mapping.get(value, value)

    ############################################################

    def _rate(self, value, total):

        if total <= 0:
            return 0

        return round((value / total) * 100, 1)

    ############################################################

    def _bounded(self, value, minimum, maximum):

        return max(minimum, min(maximum, value))

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(" ", "_")

    ############################################################

    def _format_label(self, value):

        return str(value or "").replace("_", " ").title()

    ############################################################

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
