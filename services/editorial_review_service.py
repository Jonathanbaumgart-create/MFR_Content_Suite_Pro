import re

from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class EditorialReviewService:

    COMPONENTS = (
        "Hook",
        "Readability",
        "Community Value",
        "Educational Value",
        "Engagement Potential",
        "CTA",
        "Hashtags",
        "Emoji Balance",
        "Authenticity",
        "Department Voice"
    )

    GENERIC_PHRASES = (
        "selected media",
        "this image shows",
        "a practical reminder",
        "as an ai",
        "metadata",
        "database",
        "provider"
    )

    def review_package(self, package):

        captions = [
            package.get("facebook_caption", ""),
            package.get("instagram_caption", ""),
            package.get("linkedin_caption", "")
        ]
        combined = "\n".join(captions)
        hashtags = self._hashtags(package)
        emoji_count = self._emoji_count(combined)
        scores = {
            "Hook": self._hook_score(captions),
            "Readability": self._readability_score(combined),
            "Community Value": self._keyword_score(
                combined,
                ("community", "morden", "neighbour", "family", "resident")
            ),
            "Educational Value": self._keyword_score(
                combined,
                ("safety", "learn", "tip", "prepare", "check", "practice")
            ),
            "Engagement Potential": self._engagement_score(combined),
            "CTA": self._cta_score(package),
            "Hashtags": self._hashtag_score(hashtags),
            "Emoji Balance": self._emoji_score(emoji_count),
            "Authenticity": self._authenticity_score(combined),
            "Department Voice": self._department_voice_score(combined, package)
        }
        overall = round(
            sum(scores.values()) / len(scores)
        )
        strengths = self._strengths(scores)
        suggestions = self._suggestions(scores, combined, hashtags, emoji_count)

        review = {
            "overall_score": overall,
            "scores": scores,
            "strengths": strengths,
            "suggestions": suggestions
        }

        logger.info(
            "Editorial review completed score=%s",
            overall
        )

        return review

    def _hook_score(self, captions):

        first = next(
            (caption.strip() for caption in captions if caption.strip()),
            ""
        )

        if not first:
            return 20

        first_sentence = re.split(r"[.!?\n]", first)[0]

        if 20 <= len(first_sentence) <= 120:
            return 90

        if len(first_sentence) < 20:
            return 70

        return 55

    def _readability_score(self, text):

        words = re.findall(r"\w+", text)

        if not words:
            return 20

        average = sum(len(word) for word in words) / len(words)
        paragraphs = [
            item
            for item in text.split("\n\n")
            if item.strip()
        ]

        score = 85

        if average > 7:
            score -= 15

        if any(len(paragraph) > 650 for paragraph in paragraphs):
            score -= 20

        return max(35, score)

    def _keyword_score(self, text, keywords):

        lower = text.lower()
        matches = sum(
            1
            for keyword in keywords
            if keyword in lower
        )

        return min(95, 45 + matches * 15)

    def _engagement_score(self, text):

        lower = text.lower()
        score = 55

        if "?" in text:
            score += 12

        if any(word in lower for word in ("share", "join", "follow", "learn")):
            score += 13

        if any(word in lower for word in ("thank", "proud", "together")):
            score += 10

        return min(95, score)

    def _cta_score(self, package):

        cta = package.get("call_to_action", "")

        if len(cta.strip()) >= 12:
            return 90

        combined = (
            package.get("facebook_caption", "") + " " +
            package.get("instagram_caption", "")
        ).lower()

        if any(word in combined for word in ("learn", "join", "share", "check")):
            return 75

        return 35

    def _hashtag_score(self, hashtags):

        count = len(hashtags)

        if 1 <= count <= 5:
            return 90

        if count == 0:
            return 55

        return 45

    def _emoji_score(self, count):

        if 2 <= count <= 10:
            return 88

        if count == 0:
            return 60

        return 50

    def _authenticity_score(self, text):

        lower = text.lower()
        score = 92

        for phrase in self.GENERIC_PHRASES:
            if phrase in lower:
                score -= 18

        if lower.count("morden fire & rescue") > 3:
            score -= 12

        return max(25, score)

    def _department_voice_score(self, text, package):

        lower = text.lower()
        score = 50

        if "morden" in lower:
            score += 15

        if "fire" in lower or "rescue" in lower:
            score += 10

        if any(
            term.lower() in lower
            for term in self._terms(package)
        ):
            score += 15

        if any(word in lower for word in ("community", "safety", "service")):
            score += 10

        return min(95, score)

    def _terms(self, package):

        terms = []

        for media in package.get("suggested_media", []) or []:
            for key in (
                "content_tags",
                "content_themes",
                "recommended_uses",
                "equipment_tags",
                "apparatus_tags"
            ):
                values = media.get(key, []) if isinstance(media, dict) else []

                if isinstance(values, str):
                    terms.append(values)
                else:
                    terms.extend(values)

        return terms

    def _hashtags(self, package):

        values = []

        for key in (
            "facebook_hashtags",
            "instagram_hashtags",
            "hashtags"
        ):
            values.extend(
                package.get(key, []) or []
            )

        unique = []
        seen = set()

        for value in values:
            key = str(value).lower()

            if not value or key in seen:
                continue

            seen.add(key)
            unique.append(value)

        return unique

    def _emoji_count(self, text):

        return sum(
            1
            for character in text
            if ord(character) > 10000
        )

    def _strengths(self, scores):

        strengths = []

        for name, score in scores.items():
            if score >= 80:
                strengths.append(
                    f"{name} is strong."
                )

        return strengths[:5] or [
            "The draft has a usable local communication structure."
        ]

    def _suggestions(self, scores, text, hashtags, emoji_count):

        suggestions = []

        if any(phrase in text.lower() for phrase in self.GENERIC_PHRASES):
            suggestions.append(
                "Replace generic or internal-sounding wording with plain local language."
            )

        for name, score in scores.items():
            if score < 70:
                suggestions.append(
                    f"Improve {name.lower()} before publishing."
                )

        if len(hashtags) > 5:
            suggestions.append(
                "Reduce hashtags to the strongest five or fewer."
            )

        if emoji_count > 10:
            suggestions.append(
                "Use fewer emojis for a more polished department voice."
            )

        return suggestions[:6] or [
            "Review final details for accuracy before publishing."
        ]
