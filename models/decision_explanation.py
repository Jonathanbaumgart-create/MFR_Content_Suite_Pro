from dataclasses import asdict, dataclass, field


@dataclass
class DecisionExplanation:

    decision_id: str
    decision_type: str
    subject_type: str
    subject_id: str
    headline: str
    summary: str
    decision_score: float = 0
    confidence_score: float = 0
    trust_label: str = ""
    evidence_count: int = 0
    positive_factors: list = field(default_factory=list)
    negative_factors: list = field(default_factory=list)
    limiting_factors: list = field(default_factory=list)
    source_signals: list = field(default_factory=list)
    supporting_assets: list = field(default_factory=list)
    supporting_communications: list = field(default_factory=list)
    supporting_campaigns: list = field(default_factory=list)
    supporting_programs: list = field(default_factory=list)
    historical_evidence: list = field(default_factory=list)
    seasonal_evidence: list = field(default_factory=list)
    trust_state_breakdown: dict = field(default_factory=dict)
    comparison_candidates: list = field(default_factory=list)
    why_selected: list = field(default_factory=list)
    why_not_selected: list = field(default_factory=list)
    score_reconciliation: dict = field(default_factory=dict)
    package_audit: dict = field(default_factory=dict)
    generated_content_audit: dict = field(default_factory=dict)
    changed_since_previous: dict = field(default_factory=dict)
    generated_at: str = ""
    explanation_version: str = ""

    def to_dict(self):

        return asdict(self)
