from dataclasses import asdict, dataclass, field


@dataclass
class MediaPackageAsset:

    media_id: int = 0
    filename: str = ""
    media_type: str = ""
    path: str = ""
    thumbnail_path: str = ""
    trust_state: str = ""
    analysis_state: str = ""
    capture_time: str = ""
    added_at: str = ""
    orientation: str = ""
    width: int = 0
    height: int = 0
    duration_seconds: float = 0
    communications_score: float = 0
    media_score: float = 0
    editorial_score: float = 0
    topic_relevance_score: float = 0
    campaign_relevance_score: float = 0
    platform_fit_score: float = 0
    recent_use_risk: float = 0
    duplicate_scene_risk: float = 0
    selected_as: str = ""
    why_selected: str = ""
    why_not_primary: str = ""
    platform_suitability: dict = field(default_factory=dict)
    selection_factors: list = field(default_factory=list)
    confidence_limitations: list = field(default_factory=list)

    def to_dict(self):

        return asdict(self)


@dataclass
class MediaPackage:

    package_id: str = ""
    recommendation_id: str = ""
    story_title: str = ""
    primary_photo: dict = field(default_factory=dict)
    supporting_photos: list = field(default_factory=list)
    gallery_photos: list = field(default_factory=list)
    primary_video: dict = field(default_factory=dict)
    supporting_videos: list = field(default_factory=list)
    gallery_videos: list = field(default_factory=list)
    media_count: int = 0
    trust_counts: dict = field(default_factory=dict)
    story_relevance: float = 0
    platform_fit: float = 0
    media_score: float = 0
    diversity_score: float = 0
    recent_use_risk: float = 0
    duplicate_scene_risk: float = 0
    communications_score: float = 0
    story_strength: dict = field(default_factory=dict)
    editorial_angle: str = ""
    recommended_platforms: list = field(default_factory=list)
    platform_media_guidance: dict = field(default_factory=dict)
    confidence: float = 0
    confidence_limitations: list = field(default_factory=list)
    reasons: list = field(default_factory=list)
    diversity_reasoning: list = field(default_factory=list)
    excluded_asset_ids: list = field(default_factory=list)
    replacement_history: list = field(default_factory=list)
    automatic_selection: dict = field(default_factory=dict)
    version: str = "media-package-v1"
    generated_at: str = ""

    def to_dict(self):

        data = asdict(self)
        data["best_photo"] = data["primary_photo"]
        data["best_video"] = data["primary_video"]
        return data
