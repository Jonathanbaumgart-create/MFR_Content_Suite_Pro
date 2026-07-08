import json
from pathlib import Path

from services.communications_memory_service import CommunicationsMemoryService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class SocialImportService:

    def __init__(self, memory_service=None):

        self.memory = memory_service or CommunicationsMemoryService()

    ############################################################

    def import_file(self, path, platform=None):

        path = Path(path)

        with path.open(
            "r",
            encoding="utf-8"
        ) as handle:
            payload = json.load(handle)

        return self.import_payload(
            payload,
            platform=platform or self._platform_from_name(path.name),
            source=str(path)
        )

    ############################################################

    def import_payload(self, payload, platform="facebook", source="import"):

        posts = self._posts_from_payload(
            payload,
            platform=platform,
            source=source
        )
        summary = {
            "posts_imported": 0,
            "media_linked": 0,
            "unknown_media": 0,
            "duplicate_posts": 0,
            "duplicate_captions": 0,
            "campaigns_discovered": set(),
            "hashtags_discovered": set(),
            "writing_styles_discovered": set(),
            "posts_seen": len(posts)
        }

        for post in posts:
            result = self.memory.remember_post(
                post
            )
            status = result["status"]

            if status == "duplicate_post":
                summary["duplicate_posts"] += 1
                continue

            if status == "duplicate_caption":
                summary["duplicate_captions"] += 1

            saved = result["post"]
            summary["posts_imported"] += 1
            summary["media_linked"] += len(saved.get("media_ids", []))

            if post.get("unknown_media"):
                summary["unknown_media"] += len(post["unknown_media"])

            if saved.get("campaign"):
                summary["campaigns_discovered"].add(saved["campaign"])

            summary["hashtags_discovered"].update(
                saved.get("hashtags", [])
            )
            summary["writing_styles_discovered"].add(
                saved.get("writing_style", "")
            )

        result = {
            "posts_imported": summary["posts_imported"],
            "media_linked": summary["media_linked"],
            "unknown_media": summary["unknown_media"],
            "duplicate_posts": summary["duplicate_posts"],
            "duplicate_captions": summary["duplicate_captions"],
            "campaigns_discovered": sorted(summary["campaigns_discovered"]),
            "hashtags_discovered": sorted(summary["hashtags_discovered"]),
            "writing_styles_discovered": sorted(
                value
                for value in summary["writing_styles_discovered"]
                if value
            ),
            "posts_seen": summary["posts_seen"]
        }

        logger.info(
            "Social import completed platform=%s imported=%s duplicates=%s",
            platform,
            result["posts_imported"],
            result["duplicate_posts"]
        )

        return result

    ############################################################

    def _posts_from_payload(self, payload, platform, source):

        if isinstance(payload, list):
            raw_posts = payload
        elif isinstance(payload, dict):
            raw_posts = (
                payload.get("posts") or
                payload.get("media") or
                payload.get("items") or
                payload.get("messages") or
                []
            )
        else:
            raw_posts = []

        posts = []

        for item in raw_posts:
            post = self._normalize_export_item(
                item,
                platform=platform,
                source=source
            )

            if post["caption"]:
                posts.append(post)

        return posts

    ############################################################

    def _normalize_export_item(self, item, platform, source):

        if not isinstance(item, dict):
            item = {}

        data = item.get("data") or [{}]

        if not data:
            data = [{}]

        caption = (
            item.get("caption") or
            item.get("title") or
            item.get("description") or
            item.get("text") or
            data[0].get("post", "")
        )

        timestamp = (
            item.get("timestamp") or
            item.get("creation_timestamp") or
            item.get("created_at") or
            item.get("date") or
            ""
        )

        if isinstance(timestamp, (int, float)):
            from datetime import datetime

            timestamp = datetime.fromtimestamp(timestamp).isoformat()

        media_ids = (
            item.get("media_ids") or
            item.get("media") or
            []
        )
        known_media_ids = []
        unknown_media = []

        for media in media_ids:
            if isinstance(media, dict):
                value = media.get("media_id") or media.get("id")
            else:
                value = media

            try:
                known_media_ids.append(int(value))
            except Exception:
                unknown_media.append(value)

        return {
            "platform": item.get("platform", platform),
            "date": timestamp,
            "headline": item.get("headline", ""),
            "caption": caption,
            "cta": item.get("cta", ""),
            "media_ids": known_media_ids,
            "unknown_media": unknown_media,
            "campaign": item.get("campaign", ""),
            "writing_style": item.get("writing_style", ""),
            "opportunity_type": item.get("opportunity_type", ""),
            "season": item.get("season", ""),
            "context": item.get("context", ""),
            "source": source,
            "imported": True
        }

    ############################################################

    def _platform_from_name(self, name):

        lower = name.lower()

        if "instagram" in lower:
            return "instagram"

        if "facebook" in lower:
            return "facebook"

        return "unknown"
