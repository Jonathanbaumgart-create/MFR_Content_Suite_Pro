import hashlib
import re
from collections import Counter
from datetime import datetime

from core.app_context import context
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationsMemoryService:

    RE_HASHTAG = re.compile(r"#[A-Za-z0-9_]+")
    RE_EMOJI = re.compile(
        "["
        "\U0001f300-\U0001f6ff"
        "\U0001f700-\U0001f77f"
        "\U0001f780-\U0001f7ff"
        "\U0001f800-\U0001f8ff"
        "\U0001f900-\U0001f9ff"
        "\U0001fa00-\U0001faff"
        "\u2600-\u27bf"
        "]+",
        flags=re.UNICODE
    )

    def __init__(self, database=None):

        self.db = database or context.database

    ############################################################

    def remember_post(self, post):

        normalized = self.normalize_post(
            post
        )
        existing = self.db.social_post_exists(
            normalized["caption_hash"]
        )

        if existing:
            return {
                "post_id": existing,
                "status": "duplicate_post",
                "post": normalized
            }

        duplicate_caption = self.db.social_caption_exists(
            normalized["caption"]
        )

        post_id = self.db.save_social_post(
            normalized
        )

        if not post_id:
            return {
                "post_id": existing,
                "status": "duplicate_post",
                "post": normalized
            }

        self.db.save_platform(
            normalized["platform"]
        )

        if normalized.get("campaign"):
            self.db.save_campaign(
                {
                    "name": normalized["campaign"],
                    "description": "Discovered from communications memory.",
                    "season": normalized.get("season", "")
                }
            )

        for media_id in normalized.get("media_ids", []):
            self.db.save_media_usage(
                {
                    "media_id": media_id,
                    "post_id": post_id,
                    "platform": normalized["platform"],
                    "used_at": normalized["post_date"],
                    "campaign": normalized.get("campaign", "")
                }
            )

        pattern = self.analyze_post(
            normalized
        )
        pattern["post_id"] = post_id
        self.db.save_writing_pattern(
            pattern
        )

        for tag in normalized["hashtags"]:
            self.db.save_hashtag_use(
                tag,
                normalized["post_date"]
            )

        logger.info(
            "Saved communications memory post_id=%s platform=%s campaign=%s",
            post_id,
            normalized["platform"],
            normalized.get("campaign", "")
        )

        return {
            "post_id": post_id,
            "status": "duplicate_caption" if duplicate_caption else "imported",
            "post": normalized,
            "pattern": pattern
        }

    ############################################################

    def remember_strategy_package(self, package, strategy, recommendation):

        if not package or not strategy:
            return {
                "post_id": None,
                "status": "no_strategy_package"
            }

        post = {
            "platform": "draft",
            "post_date": TimeService.local_date(TimeService.utc_now_iso()),
            "headline": package.get("headline", ""),
            "caption": package.get("facebook_caption", ""),
            "cta": package.get("call_to_action", ""),
            "hashtags": package.get("facebook_hashtags") or package.get("hashtags") or [],
            "emojis": package.get("emoji_suggestions") or [],
            "media_ids": [],
            "campaign": strategy.get("title", ""),
            "writing_style": package.get("writing_style", ""),
            "opportunity_type": strategy.get("strategy_type", ""),
            "season": "",
            "context": recommendation.get("title", ""),
            "source": "accepted_editorial_strategy",
            "imported": False,
            "generated": True,
            "manually_created": False
        }

        result = self.remember_post(post)

        logger.info(
            "Remembered accepted editorial strategy draft post_id=%s strategy=%s",
            result.get("post_id"),
            strategy.get("strategy_type", "")
        )

        return result

    ############################################################

    def normalize_post(self, post):

        caption = self._clean(
            post.get("caption", "")
        )
        hashtags = self._unique(
            post.get("hashtags") or self.extract_hashtags(caption)
        )
        emojis = self._unique(
            post.get("emojis") or self.extract_emojis(caption)
        )
        media_ids = [
            self._to_int(value)
            for value in post.get("media_ids", [])
            if self._to_int(value)
        ]
        platform = self._clean(
            post.get("platform", "")
        ).lower()

        if not platform:
            platform = "unknown"

        post_date, post_time = self._date_time_parts(
            post.get("date") or
            post.get("created_at") or
            post.get("timestamp") or
            post.get("post_date") or
            ""
        )

        normalized = {
            "platform": platform,
            "post_date": post.get("post_date") or post_date,
            "post_time": post.get("post_time") or post_time,
            "headline": self._clean(post.get("headline", "")),
            "caption": caption,
            "cta": self._clean(post.get("cta", "")),
            "hashtags": hashtags,
            "emojis": emojis,
            "media_ids": media_ids,
            "campaign": self._clean(post.get("campaign", "")),
            "writing_style": self._clean(post.get("writing_style", "")),
            "opportunity_type": self._clean(post.get("opportunity_type", "")),
            "season": self._clean(post.get("season", "")),
            "context": self._clean(post.get("context", "")),
            "source": self._clean(post.get("source", "import")),
            "imported": 1 if post.get("imported", True) else 0,
            "generated": 1 if post.get("generated", False) else 0,
            "manually_created": 1 if post.get("manually_created", False) else 0
        }
        normalized["caption_hash"] = self.caption_hash(
            normalized
        )

        if not normalized["writing_style"]:
            normalized["writing_style"] = self.detect_tone(caption)

        if not normalized["cta"]:
            normalized["cta"] = self.detect_cta(caption)

        return normalized

    ############################################################

    def analyze_post(self, post):

        caption = post.get("caption", "")
        lower = caption.lower()
        hashtags = post.get("hashtags") or self.extract_hashtags(caption)
        emojis = post.get("emojis") or self.extract_emojis(caption)

        return {
            "opening_hook": self.opening_hook(caption),
            "caption_length": len(caption),
            "emoji_count": len(emojis),
            "hashtag_count": len(hashtags),
            "writing_tone": post.get("writing_style") or self.detect_tone(caption),
            "cta": post.get("cta") or self.detect_cta(caption),
            "question_asked": 1 if "?" in caption else 0,
            "storytelling": self._contains_any(
                lower,
                ("today", "yesterday", "this week", "our crews", "behind")
            ),
            "educational": self._contains_any(
                lower,
                ("remember", "tip", "safety", "check", "test", "prevent")
            ),
            "recognition": self._contains_any(
                lower,
                ("thank", "congrat", "recognize", "appreciation", "proud")
            ),
            "recruitment": self._contains_any(
                lower,
                ("join", "recruit", "volunteer", "apply", "serve")
            ),
            "incident_recap": self._contains_any(
                lower,
                ("responded", "incident", "call", "scene", "crews attended")
            ),
            "community_engagement": self._contains_any(
                lower,
                ("community", "morden", "families", "neighbours", "open house")
            ),
            "safety_message": self._contains_any(
                lower,
                ("safety", "alarm", "escape", "prevention", "emergency")
            )
        }

    ############################################################

    def statistics(self):

        summary = self.db.communication_memory_summary()
        patterns = self.db.writing_pattern_statistics()

        return {
            **summary,
            "writing_statistics": patterns,
            "posting_frequency": self.posting_frequency(),
            "platform_preferences": summary["platform_counts"]
        }

    ############################################################

    def writing_memory(self):

        stats = self.statistics()

        return {
            "average_caption_length": round(
                stats["writing_statistics"]["average_caption_length"],
                1
            ),
            "average_hashtags": round(
                stats["writing_statistics"]["average_hashtags"],
                1
            ),
            "average_emojis": round(
                stats["writing_statistics"]["average_emojis"],
                1
            ),
            "common_openings": [
                item[0]
                for item in stats["writing_statistics"]["common_openings"]
            ],
            "common_ctas": [
                item[0]
                for item in stats["writing_statistics"]["common_ctas"]
            ],
            "top_hashtags": [
                item[0]
                for item in stats["top_hashtags"]
            ],
            "campaigns": self.db.campaign_names(limit=10)
        }

    ############################################################

    def media_memory(self, media_id):

        usage = self.db.media_usage_summary(
            media_id
        )

        return {
            "posted_before": bool(usage),
            "post_count": len(usage),
            "last_posted": usage[0]["used_at"] if usage else "",
            "campaigns": self._unique(
                item["campaign"]
                for item in usage
                if item.get("campaign")
            ),
            "usage": usage
        }

    ############################################################

    def search(self, query, limit=50):

        return self.db.social_posts(
            limit=limit,
            search_text=query
        )

    ############################################################

    def recent_social_media_ids(self, days=90):

        return self.db.recently_used_social_media_ids(
            days=days
        )

    ############################################################

    def posting_frequency(self):

        posts = self.db.social_posts(limit=1000)
        counts = Counter(
            post.get("post_date", "")[:7]
            for post in posts
            if post.get("post_date")
        )

        return sorted(
            counts.items(),
            reverse=True
        )[:12]

    ############################################################

    def caption_hash(self, post):

        source = "|".join(
            [
                post.get("platform", ""),
                post.get("post_date", ""),
                post.get("caption", "")
            ]
        ).lower()

        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    ############################################################

    def extract_hashtags(self, caption):

        return self._unique(
            self.RE_HASHTAG.findall(caption or "")
        )

    ############################################################

    def extract_emojis(self, caption):

        return self._unique(
            match.group(0)
            for match in self.RE_EMOJI.finditer(caption or "")
        )

    ############################################################

    def opening_hook(self, caption):

        text = self._clean(
            caption
        )

        if not text:
            return ""

        first = re.split(
            r"(?<=[.!?])\s+",
            text
        )[0]

        return first[:140]

    ############################################################

    def detect_cta(self, caption):

        lines = [
            line.strip()
            for line in str(caption or "").splitlines()
            if line.strip()
        ]

        for line in reversed(lines):
            lower = line.lower()

            if self._contains_any(
                lower,
                ("learn", "visit", "join", "apply", "call", "check", "test")
            ):
                return line[:180]

        return ""

    ############################################################

    def detect_tone(self, caption):

        lower = str(caption or "").lower()

        if self._contains_any(lower, ("join", "recruit", "volunteer", "apply")):
            return "recruitment"

        if self._contains_any(lower, ("thank", "proud", "recognize")):
            return "recognition"

        if self._contains_any(lower, ("tip", "remember", "check", "prevent")):
            return "educational"

        if self._contains_any(lower, ("responded", "incident", "scene")):
            return "incident_recap"

        if self._contains_any(lower, ("training", "drill", "practice")):
            return "training"

        if self._contains_any(lower, ("community", "open house", "families")):
            return "community"

        return "general"

    ############################################################

    def _date_time_parts(self, value):

        if not value:
            return "", ""

        text = str(value).replace("Z", "+00:00")

        try:
            parsed = datetime.fromisoformat(text)
            return (
                parsed.date().isoformat(),
                parsed.time().isoformat(timespec="minutes")
            )
        except Exception:
            pass

        if " " in text:
            date_part, time_part = text.split(" ", 1)
            return date_part[:10], time_part[:5]

        return text[:10], ""

    ############################################################

    def _contains_any(self, value, terms):

        return 1 if any(term in value for term in terms) else 0

    ############################################################

    def _clean(self, value):

        return "\n".join(
            line.strip()
            for line in str(value or "").splitlines()
            if line.strip()
        )

    ############################################################

    def _to_int(self, value):

        try:
            return int(value)
        except Exception:
            return 0

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
