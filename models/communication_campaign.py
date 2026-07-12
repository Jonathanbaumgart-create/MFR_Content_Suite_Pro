from dataclasses import dataclass, field


@dataclass
class CommunicationCampaign:

    campaign_id: int = 0
    name: str = ""
    description: str = ""
    active_years: list = field(default_factory=list)
    recurring_months: list = field(default_factory=list)
    goals: list = field(default_factory=list)
    audiences: list = field(default_factory=list)
    associated_program_ids: list = field(default_factory=list)
    editorial_angles: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    partner_organizations: list = field(default_factory=list)
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self):

        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "description": self.description,
            "active_years": self.active_years,
            "recurring_months": self.recurring_months,
            "goals": self.goals,
            "audiences": self.audiences,
            "associated_program_ids": self.associated_program_ids,
            "editorial_angles": self.editorial_angles,
            "topics": self.topics,
            "partner_organizations": self.partner_organizations,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
