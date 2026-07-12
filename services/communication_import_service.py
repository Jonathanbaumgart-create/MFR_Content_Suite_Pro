import csv
import hashlib
import json
import time
from pathlib import Path

from core.app_context import context
from services.communication_analysis_service import CommunicationAnalysisService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationImportService:

    BATCH_SIZE = 100

    FIELD_ALIASES = {
        "title": ("title", "headline", "name", "subject"),
        "text": ("text", "caption", "body", "message", "description", "content"),
        "published_date": ("published_date", "published_at", "date", "created_at", "timestamp", "post_date"),
        "platform": ("platform", "channel"),
        "source_identifier": ("source_identifier", "source_id", "id", "post_id", "platform_post_id"),
        "permalink": ("permalink", "url", "link"),
        "photo_count": ("photo_count", "photos", "image_count"),
        "video_count": ("video_count", "videos", "video_count"),
        "media_count": ("media_count", "attachments", "attachment_count"),
        "campaign": ("campaign", "campaign_name"),
        "program": ("program", "program_name"),
        "topics": ("topics", "tags"),
        "cta": ("cta", "call_to_action"),
        "engagement_metrics": ("engagement_metrics", "metrics", "engagement")
    }

    def __init__(self, database=None, analysis_service=None):

        self.db = database or context.database
        self.analysis = analysis_service or CommunicationAnalysisService()

    ############################################################

    def import_file(
        self,
        path,
        source_type=None,
        dry_run=False,
        cancel_check=None,
        progress_callback=None
    ):

        path = Path(path)
        source_type = (source_type or path.suffix.lstrip(".") or "unknown").lower()

        if source_type == "csv":
            return self.import_csv(
                path,
                dry_run=dry_run,
                cancel_check=cancel_check,
                progress_callback=progress_callback
            )

        if source_type == "json":
            return self.import_json(
                path,
                dry_run=dry_run,
                cancel_check=cancel_check,
                progress_callback=progress_callback
            )

        raise ValueError(f"Unsupported communication import type: {source_type}")

    ############################################################

    def preview_file(self, path, source_type=None, sample_size=5):

        path = Path(path)
        source_type = (source_type or path.suffix.lstrip(".") or "unknown").lower()

        if source_type == "csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = []

                for row in reader:
                    rows.append(self._normalize_row(row, str(path), "csv"))

                    if len(rows) >= sample_size:
                        break

                columns = list(reader.fieldnames or [])

        elif source_type == "json":
            rows = []

            for item in self._iter_json(path):
                rows.append(self._normalize_row(item, str(path), "json"))

                if len(rows) >= sample_size:
                    break

            columns = sorted(
                {
                    key
                    for row in rows
                    for key in row.get("raw_keys", [])
                }
            )
        else:
            raise ValueError(f"Unsupported communication import type: {source_type}")

        warnings = [
            warning
            for row in rows
            for warning in row.get("warnings", [])
        ]

        return {
            "source_type": source_type,
            "detected_columns": columns,
            "mapped_fields": self._mapping_for_columns(columns),
            "sample_normalized_records": rows,
            "missing_required_fields": [
                "text"
            ] if not any(self._field_for_column(column) == "text" for column in columns) else [],
            "warning_count": len(warnings),
            "warnings": warnings[:10]
        }

    ############################################################

    def import_csv(
        self,
        path,
        dry_run=False,
        cancel_check=None,
        progress_callback=None
    ):

        path = Path(path)
        started = time.perf_counter()
        summary = self._summary("csv", path)
        logger.info(
            "Communication import started type=csv"
        )

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)

            for row in reader:
                if cancel_check and cancel_check():
                    summary["status"] = "cancelled"
                    break

                self._process_row(
                    row,
                    str(path),
                    "csv",
                    summary,
                    dry_run=dry_run
                )
                self._notify_progress(progress_callback, summary)

        return self._finish_summary(summary, started, dry_run)

    ############################################################

    def import_json(
        self,
        path,
        dry_run=False,
        cancel_check=None,
        progress_callback=None
    ):

        path = Path(path)
        started = time.perf_counter()
        summary = self._summary("json", path)
        logger.info(
            "Communication import started type=json"
        )

        for item in self._iter_json(path):
            if cancel_check and cancel_check():
                summary["status"] = "cancelled"
                break

            self._process_row(
                item,
                str(path),
                "json",
                summary,
                dry_run=dry_run
            )
            self._notify_progress(progress_callback, summary)

        return self._finish_summary(summary, started, dry_run)

    ############################################################

    def _iter_json(self, path):

        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = (
                payload.get("communications") or
                payload.get("posts") or
                payload.get("items") or
                payload.get("records") or
                []
            )
        else:
            rows = []

        for item in rows:
            if isinstance(item, dict):
                yield item

    ############################################################

    def _process_row(self, row, source_name, source_type, summary, dry_run=False):

        summary["records_processed"] += 1

        try:
            normalized = self._normalize_row(
                row,
                source_name,
                source_type
            )

            summary["warnings"].extend(normalized["warnings"])

            if not normalized["record"]["original_text"]:
                summary["records_failed"] += 1
                summary["warnings"].append("Skipped row with no text.")
                return

            if dry_run:
                return

            record_result = self.db.save_communication_record(
                normalized["record"]
            )
            communication_id = record_result["communication_id"]
            record = {
                **normalized["record"],
                "communication_id": communication_id
            }

            if record_result["inserted"]:
                summary["records_inserted"] += 1
            else:
                summary["duplicates_skipped"] += 1

            delivery = {
                **normalized["delivery"],
                "communication_id": communication_id
            }
            delivery_result = self.db.save_communication_delivery(delivery)

            if delivery_result["inserted"]:
                summary["deliveries_inserted"] += 1

            intelligence = self.analysis.analyze(
                record,
                delivery
            )
            self.db.save_communication_intelligence(intelligence)
            self._save_detected_objects(
                communication_id,
                intelligence,
                summary
            )
            outcome = {
                **intelligence["outcome"],
                "communication_id": communication_id
            }
            self.db.save_communication_outcome(outcome)

        except Exception as ex:
            summary["records_failed"] += 1
            summary["warnings"].append(str(ex))

    ############################################################

    def _save_detected_objects(self, communication_id, intelligence, summary):

        for campaign in intelligence.get("campaign_objects", []):
            campaign_id = self.db.save_communication_campaign(campaign)
            self.db.link_communication_campaign(
                communication_id,
                campaign_id,
                evidence=", ".join(campaign.get("evidence") or []),
                confidence=campaign.get("confidence", 0)
            )
            summary["campaigns_detected"].add(campaign["name"])

        for program in intelligence.get("program_objects", []):
            program_id = self.db.save_communication_program(program)
            self.db.link_communication_program(
                communication_id,
                program_id,
                evidence=", ".join(program.get("evidence") or []),
                confidence=program.get("confidence", 0)
            )
            summary["programs_detected"].add(program["name"])

        for topic in intelligence.get("topic_objects", []):
            self.db.link_communication_topic(
                communication_id,
                topic["topic"],
                evidence=", ".join(topic.get("matches") or []),
                confidence=topic.get("confidence", 0)
            )
            summary["topics_extracted"].add(topic["topic"])

    ############################################################

    def _normalize_row(self, row, source_name, source_type):

        row = row or {}
        mapped = {
            field: self._value_for(row, field)
            for field in self.FIELD_ALIASES
        }
        text = self._clean(mapped["text"])
        title = self._clean(mapped["title"]) or self._title_from_text(text)
        published_at, warnings = self._safe_date(mapped["published_date"])
        platform = self._clean(mapped["platform"]).lower() or "unknown"
        source_identifier = self._clean(mapped["source_identifier"])
        imported_at = TimeService.utc_now_iso()
        content_hash = self.content_hash(
            text,
            published_at
        )
        delivery_hash = self.delivery_hash(
            platform,
            published_at,
            source_identifier,
            text
        )
        photo_count = self._to_int(mapped["photo_count"])
        video_count = self._to_int(mapped["video_count"])
        media_count = (
            self._to_int(mapped["media_count"]) or
            photo_count + video_count
        )

        return {
            "record": {
                "title": title,
                "original_text": text,
                "summary": self._summary_text(text),
                "original_date": published_at,
                "source_type": source_type,
                "source_identifier": source_identifier,
                "imported_from": source_name,
                "imported_at": imported_at,
                "content_hash": content_hash,
                "notes": "",
                "campaign": self._clean(mapped["campaign"]),
                "program": self._clean(mapped["program"]),
                "topics": self._as_list(mapped["topics"])
            },
            "delivery": {
                "platform": platform,
                "published_at": published_at,
                "platform_post_id": source_identifier,
                "permalink": self._clean(mapped["permalink"]),
                "delivery_text": text,
                "media_count": media_count,
                "photo_count": photo_count,
                "video_count": video_count,
                "engagement_metrics": self._engagement(mapped["engagement_metrics"]),
                "imported_at": imported_at,
                "delivery_hash": delivery_hash,
                "campaign": self._clean(mapped["campaign"]),
                "program": self._clean(mapped["program"]),
                "topics": self._as_list(mapped["topics"])
            },
            "campaign": self._clean(mapped["campaign"]),
            "program": self._clean(mapped["program"]),
            "topics": self._as_list(mapped["topics"]),
            "warnings": warnings,
            "raw_keys": list(row.keys())
        }

    ############################################################

    def _finish_summary(self, summary, started, dry_run):

        summary["completed_at"] = TimeService.utc_now_iso()
        summary["duration_seconds"] = round(time.perf_counter() - started, 3)

        if summary["status"] == "running":
            summary["status"] = "preview" if dry_run else "completed"

        public = {
            **summary,
            "campaigns_detected": sorted(summary["campaigns_detected"]),
            "programs_detected": sorted(summary["programs_detected"]),
            "topics_extracted": sorted(summary["topics_extracted"]),
            "warnings": summary["warnings"][:50]
        }

        if not dry_run:
            self.db.save_communication_import_run(public)

        logger.info(
            (
                "Communication import completed type=%s processed=%s "
                "inserted=%s duplicates=%s failed=%s duration=%s"
            ),
            public["source_type"],
            public["records_processed"],
            public["records_inserted"],
            public["duplicates_skipped"],
            public["records_failed"],
            public["duration_seconds"]
        )

        return public

    def _summary(self, source_type, path):

        return {
            "source_type": source_type,
            "source_name": Path(path).name,
            "started_at": TimeService.utc_now_iso(),
            "completed_at": "",
            "records_processed": 0,
            "records_inserted": 0,
            "deliveries_inserted": 0,
            "duplicates_skipped": 0,
            "records_failed": 0,
            "campaigns_detected": set(),
            "programs_detected": set(),
            "topics_extracted": set(),
            "warnings": [],
            "status": "running",
            "duration_seconds": 0
        }

    ############################################################

    def content_hash(self, text, published_at="", source_identifier=""):

        source = "|".join(
            (
                self._clean(published_at)[:10],
                self._normalized_text(text)
            )
        )

        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    def delivery_hash(self, platform, published_at, source_identifier, text):

        source = "|".join(
            (
                self._clean(platform).lower(),
                self._clean(source_identifier).lower(),
                self._clean(published_at),
                self._normalized_text(text)
            )
        )

        return hashlib.sha256(source.encode("utf-8")).hexdigest()

    ############################################################

    def _value_for(self, row, field):

        for alias in self.FIELD_ALIASES[field]:
            if alias in row and row[alias] not in (None, ""):
                return row[alias]

        lower_map = {
            str(key).strip().lower(): value
            for key, value in row.items()
        }

        for alias in self.FIELD_ALIASES[field]:
            value = lower_map.get(alias)

            if value not in (None, ""):
                return value

        return ""

    def _notify_progress(self, progress_callback, summary):

        if not progress_callback:
            return

        if (
            summary["records_processed"] > 10 and
            summary["records_processed"] % self.BATCH_SIZE != 0
        ):
            return

        progress_callback(
            {
                "records_processed": summary["records_processed"],
                "records_inserted": summary["records_inserted"],
                "deliveries_inserted": summary["deliveries_inserted"],
                "duplicates_skipped": summary["duplicates_skipped"],
                "records_failed": summary["records_failed"],
                "status": summary["status"]
            }
        )

    def _mapping_for_columns(self, columns):

        return {
            column: self._field_for_column(column)
            for column in columns
            if self._field_for_column(column)
        }

    def _field_for_column(self, column):

        normalized = str(column or "").strip().lower()

        for field, aliases in self.FIELD_ALIASES.items():
            if normalized in aliases:
                return field

        return ""

    def _safe_date(self, value):

        text = self._clean(value)

        if not text:
            return "", []

        if "/" in text:
            return "", [
                f"Ambiguous date was not imported automatically: {text}"
            ]

        normalized = TimeService.normalize_stored_timestamp(text)

        if normalized:
            return normalized.isoformat(timespec="seconds"), []

        return "", [
            f"Unrecognized date format: {text}"
        ]

    def _engagement(self, value):

        if isinstance(value, dict):
            return value

        if not value:
            return {}

        try:
            parsed = json.loads(value)
        except Exception:
            return {
                "raw": str(value)
            }

        return parsed if isinstance(parsed, dict) else {"raw": parsed}

    def _summary_text(self, text):

        cleaned = self._clean(text)

        return cleaned[:240]

    def _title_from_text(self, text):

        cleaned = self._clean(text)

        if not cleaned:
            return "Untitled Communication"

        return cleaned[:80]

    def _normalized_text(self, text):

        return re_space(self._clean(text).lower())

    def _clean(self, value):

        return " ".join(str(value or "").split())

    def _as_list(self, value):

        if isinstance(value, list):
            return [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

        return [
            item.strip()
            for item in str(value or "").replace(";", ",").split(",")
            if item.strip()
        ]

    def _to_int(self, value):

        try:
            return int(value)
        except Exception:
            return 0


def re_space(value):

    return " ".join(str(value or "").split())
