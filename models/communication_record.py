from dataclasses import dataclass, field


@dataclass
class CommunicationRecord:

    communication_id: int = 0
    title: str = ""
    original_text: str = ""
    summary: str = ""
    original_date: str = ""
    source_type: str = ""
    source_identifier: str = ""
    imported_from: str = ""
    imported_at: str = ""
    content_hash: str = ""
    notes: str = ""
    created_at: str = ""

    def to_dict(self):

        return {
            "communication_id": self.communication_id,
            "title": self.title,
            "original_text": self.original_text,
            "summary": self.summary,
            "original_date": self.original_date,
            "source_type": self.source_type,
            "source_identifier": self.source_identifier,
            "imported_from": self.imported_from,
            "imported_at": self.imported_at,
            "content_hash": self.content_hash,
            "notes": self.notes,
            "created_at": self.created_at
        }


@dataclass
class CommunicationImportSummary:

    records_processed: int = 0
    records_inserted: int = 0
    deliveries_inserted: int = 0
    duplicates_skipped: int = 0
    records_failed: int = 0
    campaigns_detected: set = field(default_factory=set)
    programs_detected: set = field(default_factory=set)
    topics_extracted: set = field(default_factory=set)
    warnings: list = field(default_factory=list)
    import_duration: float = 0.0

    def to_dict(self):

        return {
            "records_processed": self.records_processed,
            "records_inserted": self.records_inserted,
            "deliveries_inserted": self.deliveries_inserted,
            "duplicates_skipped": self.duplicates_skipped,
            "records_failed": self.records_failed,
            "campaigns_detected": sorted(self.campaigns_detected),
            "programs_detected": sorted(self.programs_detected),
            "topics_extracted": sorted(self.topics_extracted),
            "warnings": list(self.warnings),
            "import_duration": round(self.import_duration, 3)
        }
