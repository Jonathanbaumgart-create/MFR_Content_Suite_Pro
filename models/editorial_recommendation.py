from dataclasses import asdict, dataclass, field


@dataclass
class EditorialRecommendation:

    recommendation_id: str
    title: str
    topic: str
    category: str
    priority_score: int
    confidence_score: int
    summary: str
    primary_reason: str
    reasoning_factors: list = field(default_factory=list)
    supporting_photo_count: int = 0
    supporting_video_count: int = 0
    supporting_asset_ids: list = field(default_factory=list)
    best_asset_ids: list = field(default_factory=list)
    editorial_angles: list = field(default_factory=list)
    recommended_platforms: list = field(default_factory=list)
    recommended_audiences: list = field(default_factory=list)
    recommended_content_formats: list = field(default_factory=list)
    recommended_posting_window: str = ""
    communications_gap: str = ""
    repetition_risk: str = ""
    source_signals: list = field(default_factory=list)
    generated_at: str = ""
    scoring_version: str = ""

    def to_dict(self):

        return asdict(self)
