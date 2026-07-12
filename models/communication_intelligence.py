from dataclasses import dataclass, field


@dataclass
class CommunicationIntelligence:

    communication_id: int = 0
    primary_story: str = ""
    editorial_angle: str = ""
    communication_purpose: str = ""
    category: str = ""
    intended_audiences: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    programs: list = field(default_factory=list)
    campaigns: list = field(default_factory=list)
    seasonal_relevance: list = field(default_factory=list)
    educational_value: int = 0
    recruitment_value: int = 0
    preparedness_value: int = 0
    operational_value: int = 0
    community_trust_value: int = 0
    historical_value: int = 0
    human_interest_value: int = 0
    evergreen_value: int = 0
    confidence_score: int = 0
    source_signals: list = field(default_factory=list)
    analysis_version: str = "communication_intelligence_v1"
    generated_at: str = ""

    def to_dict(self):

        return {
            "communication_id": self.communication_id,
            "primary_story": self.primary_story,
            "editorial_angle": self.editorial_angle,
            "communication_purpose": self.communication_purpose,
            "category": self.category,
            "intended_audiences": self.intended_audiences,
            "topics": self.topics,
            "programs": self.programs,
            "campaigns": self.campaigns,
            "seasonal_relevance": self.seasonal_relevance,
            "educational_value": self.educational_value,
            "recruitment_value": self.recruitment_value,
            "preparedness_value": self.preparedness_value,
            "operational_value": self.operational_value,
            "community_trust_value": self.community_trust_value,
            "historical_value": self.historical_value,
            "human_interest_value": self.human_interest_value,
            "evergreen_value": self.evergreen_value,
            "confidence_score": self.confidence_score,
            "source_signals": self.source_signals,
            "analysis_version": self.analysis_version,
            "generated_at": self.generated_at
        }
