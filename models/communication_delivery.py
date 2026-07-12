from dataclasses import dataclass


@dataclass
class CommunicationDelivery:

    delivery_id: int = 0
    communication_id: int = 0
    platform: str = ""
    published_at: str = ""
    platform_post_id: str = ""
    permalink: str = ""
    delivery_text: str = ""
    media_count: int = 0
    photo_count: int = 0
    video_count: int = 0
    engagement_metrics: dict | None = None
    imported_at: str = ""
    delivery_hash: str = ""

    def to_dict(self):

        return {
            "delivery_id": self.delivery_id,
            "communication_id": self.communication_id,
            "platform": self.platform,
            "published_at": self.published_at,
            "platform_post_id": self.platform_post_id,
            "permalink": self.permalink,
            "delivery_text": self.delivery_text,
            "media_count": self.media_count,
            "photo_count": self.photo_count,
            "video_count": self.video_count,
            "engagement_metrics": self.engagement_metrics or {},
            "imported_at": self.imported_at,
            "delivery_hash": self.delivery_hash
        }
