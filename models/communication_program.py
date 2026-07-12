from dataclasses import dataclass, field


@dataclass
class CommunicationProgram:

    program_id: int = 0
    name: str = ""
    description: str = ""
    typical_audiences: list = field(default_factory=list)
    typical_topics: list = field(default_factory=list)
    associated_campaign_ids: list = field(default_factory=list)
    associated_partner_ids: list = field(default_factory=list)
    seasonal_pattern: str = ""
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self):

        return {
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "typical_audiences": self.typical_audiences,
            "typical_topics": self.typical_topics,
            "associated_campaign_ids": self.associated_campaign_ids,
            "associated_partner_ids": self.associated_partner_ids,
            "seasonal_pattern": self.seasonal_pattern,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
