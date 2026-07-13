import csv
import hashlib
import json
import re
import time
from datetime import datetime, time as dt_time, timezone
from pathlib import Path

from core.app_context import context
from services.communication_analysis_service import CommunicationAnalysisService
from services.communications_intelligence_service import CommunicationsIntelligenceService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationImportService:

    BATCH_SIZE = 100
    PREVIEW_LIMIT = 25

    FIELD_ALIASES = {
        "title": ("title", "headline", "name", "subject", "post_title"),
        "text": ("text", "caption", "body", "message", "description", "content", "post_text", "message_text"),
        "published_date": ("published_date", "published_at", "date", "created_at", "timestamp", "post_date", "creation_timestamp", "taken_at"),
        "platform": ("platform", "channel", "network", "service"),
        "source_identifier": ("source_identifier", "source_id", "id", "post_id", "platform_post_id", "fbid", "pk"),
        "platform_post_id": ("platform_post_id", "post_id", "id", "fbid", "pk"),
        "permalink": ("permalink", "url", "link", "post_url", "href"),
        "reactions": ("reactions", "likes", "like_count", "reaction_count"),
        "comments": ("comments", "comment_count", "comments_count"),
        "shares": ("shares", "share_count", "shares_count"),
        "views": ("views", "view_count", "play_count"),
        "photo_count": ("photo_count", "photos", "image_count"),
        "video_count": ("video_count", "videos", "video_count"),
        "media_count": ("media_count", "attachments", "attachment_count"),
        "hashtags": ("hashtags", "hash_tags"),
        "campaign": ("campaign", "campaign_name"),
        "program": ("program", "program_name"),
        "topics": ("topics", "tags", "labels"),
        "cta": ("cta", "call_to_action"),
        "engagement_metrics": ("engagement_metrics", "metrics", "engagement"),
        "attachment_filenames": ("attachment_filenames", "attachments", "media", "photos", "videos", "files")
    }

    DATE_FORMATS = {
        "canadian_date": "%d/%m/%Y",
        "canadian_datetime": "%d/%m/%Y %H:%M",
        "us_date": "%m/%d/%Y",
        "us_datetime": "%m/%d/%Y %H:%M",
        "iso_date": "%Y-%m-%d",
        "iso_datetime_space": "%Y-%m-%d %H:%M:%S",
        "long_month": "%B %d, %Y",
        "short_month": "%b %d, %Y"
    }

    def __init__(self, database=None, analysis_service=None):

        self.db = database or context.database
        self.analysis = analysis_service or CommunicationAnalysisService()
        self.last_metrics = {}

    ############################################################

    def inspect_source(self, path, sample_size=5):

        path = Path(path)
        started = time.perf_counter()
        warnings = []
        source_type = "unsupported"
        fields = []
        records = []

        try:
            if path.suffix.lower() == ".csv":
                source_type, fields, records = self._inspect_csv(path, sample_size)
            elif path.suffix.lower() == ".json":
                source_type, fields, records = self._inspect_json(path, sample_size)
            else:
                warnings.append(f"Unsupported file extension: {path.suffix}")
        except Exception as ex:
            warnings.append(str(ex))

        mapping = self._auto_mapping(fields)
        date_findings = self._date_findings(records, mapping)
        platform_findings = self._platform_findings(records, mapping)
        attachments = self._attachment_findings(records, mapping)
        confidence = self._source_confidence(source_type, mapping, warnings)

        return {
            "detected_source_type": source_type,
            "source_type": source_type,
            "detected_fields": fields,
            "sample_records": records[:sample_size],
            "record_count_estimate": self._record_count(path, source_type),
            "date_format_findings": date_findings,
            "platform_findings": platform_findings,
            "attachment_media_references": attachments,
            "mapped_fields": mapping,
            "warnings": warnings + date_findings.get("warnings", []),
            "confidence": confidence,
            "inspection_seconds": round(time.perf_counter() - started, 3)
        }

    ############################################################

    def import_file(
        self,
        path,
        source_type=None,
        dry_run=False,
        cancel_check=None,
        progress_callback=None,
        mapping=None,
        date_format=None,
        max_inserted_records=None
    ):

        path = Path(path)
        detected = self.inspect_source(path)
        source_type = source_type or detected["source_type"]

        if source_type == "unsupported":
            raise ValueError("Unsupported communication import structure.")

        summary = self._summary(source_type, path)
        started = time.perf_counter()
        parse_seconds = 0
        duplicate_seconds = 0
        persistence_seconds = 0
        enrichment_seconds = 0
        import_run_id = 0

        if not dry_run:
            import_run_id = self.db.create_communication_import_run(summary)
            summary["import_run_id"] = import_run_id

        rows = self._iter_records(path, source_type)

        for raw in rows:
            if (
                max_inserted_records and
                summary["records_inserted"] >= max_inserted_records
            ):
                summary["status"] = "bounded_sample"
                break

            if cancel_check and cancel_check():
                summary["status"] = "cancelled"
                break

            row_started = time.perf_counter()
            normalized = self._normalize_row(
                raw,
                str(path),
                source_type,
                mapping=mapping,
                date_format=date_format,
                import_run_id=import_run_id
            )
            parse_seconds += time.perf_counter() - row_started
            summary["records_processed"] += 1
            summary["warnings"].extend(normalized["warnings"])

            if not normalized["record"]["original_text"]:
                summary["invalid_records"] += 1
                summary["records_failed"] += 1
                summary["warnings"].append("Skipped row with no text.")
                continue

            if not normalized["record"]["original_date"]:
                summary["invalid_records"] += 1
                summary["records_failed"] += 1
                summary["warnings"].append("Skipped row with missing or ambiguous date.")
                continue

            duplicate_started = time.perf_counter()
            duplicate = self._duplicate_candidate(normalized)
            duplicate_seconds += time.perf_counter() - duplicate_started

            if duplicate.get("duplicate_type") == "normalized_text_date":
                existing_id = duplicate.get("communication_id", 0)
                already_has_platform = self.db.communication_has_delivery_platform(
                    existing_id,
                    normalized["delivery"].get("platform", "")
                )

                if not already_has_platform and not dry_run:
                    delivery = {
                        **normalized["delivery"],
                        "communication_id": existing_id
                    }
                    delivery_result = self.db.save_communication_delivery(delivery)
                    delivery_id = delivery_result.get("delivery_id") or 0
                    self._save_media_references(
                        import_run_id,
                        existing_id,
                        delivery_id,
                        normalized
                    )
                    summary["linked_as_delivery"] += 1
                    summary["deliveries_inserted"] += 1 if delivery_result["inserted"] else 0
                    self._record_import_item(
                        import_run_id,
                        "linked_delivery",
                        duplicate.get("reason", ""),
                        normalized,
                        {
                            "communication_id": existing_id,
                            "delivery_id": delivery_id
                        }
                    )
                    self._notify_progress(progress_callback, summary)
                    continue

            if duplicate.get("confidence", 0) >= 98:
                summary["exact_duplicates_skipped"] += 1
                summary["duplicates_skipped"] += 1
                self._record_import_item(
                    import_run_id,
                    "duplicate_skipped",
                    duplicate.get("reason", ""),
                    normalized,
                    duplicate
                )
                continue

            if duplicate.get("confidence", 0) >= 75:
                summary["probable_duplicates_review"] += 1
                self._save_duplicate_review(
                    import_run_id,
                    normalized,
                    duplicate
                )

            if dry_run:
                continue

            persistence_started = time.perf_counter()
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
            delivery_id = delivery_result.get("delivery_id") or 0

            if delivery_result["inserted"]:
                summary["deliveries_inserted"] += 1
            else:
                summary["linked_as_delivery"] += 1

            self._save_media_references(
                import_run_id,
                communication_id,
                delivery_id,
                normalized
            )
            persistence_seconds += time.perf_counter() - persistence_started

            enrichment_started = time.perf_counter()
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
            enrichment_seconds += time.perf_counter() - enrichment_started

            self._record_import_item(
                import_run_id,
                "inserted" if record_result["inserted"] else "linked_delivery",
                "",
                normalized,
                {
                    "communication_id": communication_id,
                    "delivery_id": delivery_id
                }
            )
            self._notify_progress(progress_callback, summary)

        summary["parsing_seconds"] = round(parse_seconds, 3)
        summary["duplicate_check_seconds"] = round(duplicate_seconds, 3)
        summary["persistence_seconds"] = round(persistence_seconds, 3)
        summary["enrichment_seconds"] = round(enrichment_seconds, 3)
        summary["completed_at"] = TimeService.utc_now_iso()
        summary["duration_seconds"] = round(time.perf_counter() - started, 3)
        summary["records_per_second"] = round(
            summary["records_processed"] / max(0.001, summary["duration_seconds"]),
            1
        )

        if summary["status"] == "running":
            summary["status"] = "preview" if dry_run else "completed"

        if not dry_run:
            profile_started = time.perf_counter()
            CommunicationsIntelligenceService(database=self.db).profile(force=True)
            summary["profile_rebuild_seconds"] = round(
                time.perf_counter() - profile_started,
                3
            )
            self.db.update_communication_import_run(
                import_run_id,
                self._public_summary(summary)
            )

        logger.info(
            (
                "Historical communication import completed run=%s processed=%s "
                "inserted=%s duplicates=%s failed=%s duration=%s"
            ),
            summary.get("import_run_id", 0),
            summary["records_processed"],
            summary["records_inserted"],
            summary["duplicates_skipped"],
            summary["records_failed"],
            summary["duration_seconds"]
        )

        return self._public_summary(summary)

    ############################################################

    def preview_file(
        self,
        path,
        source_type=None,
        sample_size=5,
        mapping=None,
        date_format=None
    ):

        path = Path(path)
        inspection = self.inspect_source(path, sample_size=sample_size)
        source_type = source_type or inspection["source_type"]
        mapping = self._normalize_mapping(
            mapping or inspection.get("mapped_fields", {})
        )
        rows = []
        warnings = list(inspection.get("warnings", []))
        invalid = 0
        duplicate_count = 0
        probable_duplicates = 0

        for index, item in enumerate(self._iter_records(path, source_type)):
            normalized = self._normalize_row(
                item,
                str(path),
                source_type,
                mapping=mapping,
                date_format=date_format
            )
            duplicate = self._duplicate_candidate(normalized)

            if not normalized["record"]["original_text"] or not normalized["record"]["original_date"]:
                invalid += 1

            if duplicate.get("confidence", 0) >= 98:
                duplicate_count += 1
            elif duplicate.get("confidence", 0) >= 75:
                probable_duplicates += 1

            warnings.extend(normalized["warnings"])

            if len(rows) < sample_size:
                analysis = self.analysis.analyze(
                    {
                        **normalized["record"],
                        "communication_id": 0
                    },
                    normalized["delivery"]
                )
                rows.append(
                    {
                        "sample_title": normalized["record"]["title"],
                        "sample_text": normalized["record"]["original_text"],
                        "sample_date": normalized["record"]["original_date"],
                        "original_date_text": normalized["record"]["original_date_text"],
                        "sample_platform": normalized["delivery"]["platform"],
                        "campaign": analysis.get("campaigns", []),
                        "program": analysis.get("programs", []),
                        "topics": analysis.get("topics", []),
                        "engagement_fields": sorted(
                            normalized["delivery"].get("engagement_metrics", {}).keys()
                        ),
                        "media_references": normalized.get("attachment_references", []),
                        "duplicate": duplicate,
                        "warnings": normalized["warnings"]
                    }
                )

            if index + 1 >= self.PREVIEW_LIMIT:
                break

        return {
            **inspection,
            "mapped_fields": mapping,
            "sample_normalized_records": rows,
            "potential_duplicate_count": duplicate_count,
            "probable_duplicate_count": probable_duplicates,
            "invalid_record_count": invalid,
            "warning_count": len(warnings),
            "warnings": warnings[:50],
            "manual_mapping_supported": True,
            "required_fields": ["text", "published_date"],
            "optional_fields": sorted(self.FIELD_ALIASES.keys())
        }

    ############################################################

    def rollback_import_run(self, import_run_id):

        return self.db.rollback_communication_import_run(import_run_id)

    ############################################################

    def review_intelligence(
        self,
        communication_id,
        updates,
        reviewer="Jonathan",
        notes=""
    ):

        effective = self.db.effective_communication_intelligence(
            communication_id
        )

        for field, value in (updates or {}).items():
            self.db.save_communication_correction(
                {
                    "communication_id": communication_id,
                    "field_name": field,
                    "original_value": effective.get(field),
                    "corrected_value": value,
                    "correction_source": reviewer,
                    "notes": notes
                }
            )

        self.db.update_communication_intelligence_review(
            communication_id,
            {
                "review_status": "approved" if updates else "rejected",
                "reviewer_notes": notes,
                "reviewed_at": TimeService.utc_now_iso()
            }
        )

        return self.db.effective_communication_intelligence(
            communication_id
        )

    ############################################################

    def _inspect_csv(self, path, sample_size):

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = list(reader.fieldnames or [])
            records = []

            for row in reader:
                records.append(dict(row))

                if len(records) >= sample_size:
                    break

        return "generic_csv", fields, records

    def _inspect_json(self, path, sample_size):

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        source_type, records = self._json_records(payload)
        fields = sorted(
            {
                key
                for row in records[:sample_size]
                for key in row.keys()
            }
        )

        return source_type, fields, records[:sample_size]

    def _json_records(self, payload):

        if isinstance(payload, list):
            records = [
                item
                for item in payload
                if isinstance(item, dict)
            ]

            if self._looks_facebook(records):
                return "facebook_export", self._facebook_records(records)

            if self._looks_instagram(records):
                return "instagram_export", records

            return "generic_json_list", records

        if not isinstance(payload, dict):
            return "unsupported", []

        if "media" in payload and "profile" in payload:
            return "instagram_export", self._instagram_records(payload)

        if "posts" in payload and any(
            key in payload for key in ("page", "timestamp", "facebook_posts")
        ):
            return "facebook_export", self._facebook_records(payload.get("posts"))

        for key in (
            "communications",
            "posts",
            "videos_v2",
            "items",
            "records",
            "data"
        ):
            if isinstance(payload.get(key), list):
                guessed = "generic_json_object"

                if key in ("posts", "videos_v2") and self._looks_facebook(payload.get(key)):
                    guessed = "facebook_export"
                    return guessed, self._facebook_records(payload.get(key))
                elif self._looks_instagram(payload.get(key)):
                    guessed = "instagram_export"

                return guessed, self._record_list(payload.get(key))

        return "unsupported", []

    def _iter_records(self, path, source_type):

        path = Path(path)

        if source_type == "generic_csv" or source_type == "csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)

                for row in reader:
                    yield dict(row)

            return

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        detected, records = self._json_records(payload)

        if source_type and source_type not in ("json", detected):
            records = self._record_list(
                payload.get("posts") if isinstance(payload, dict) else payload
            )

        for record in records:
            yield record

    ############################################################

    def _normalize_row(
        self,
        row,
        source_name,
        source_type,
        mapping=None,
        date_format=None,
        import_run_id=0
    ):

        row = row or {}
        mapping = self._normalize_mapping(
            mapping or self._auto_mapping(row.keys())
        )
        mapped = {
            field: self._mapped_value(row, field, mapping)
            for field in self.FIELD_ALIASES
        }
        text = self._clean(mapped["text"])
        title = self._clean(mapped["title"]) or self._title_from_text(text)
        published_at, date_warnings, original_date_text = self._safe_date(
            mapped["published_date"],
            date_format=date_format
        )
        platform = self._clean(mapped["platform"]).lower() or self._platform_from_source(source_type)
        source_identifier = self._clean(mapped["source_identifier"])
        platform_post_id = self._clean(mapped["platform_post_id"]) or source_identifier
        imported_at = TimeService.utc_now_iso()
        attachments = self._attachment_list(mapped["attachment_filenames"])
        engagement = self._engagement(mapped)
        content_hash = self.content_hash(
            text,
            published_at,
            source_identifier
        )
        delivery_hash = self.delivery_hash(
            platform,
            published_at,
            platform_post_id,
            text
        )
        photo_count = self._to_int(mapped["photo_count"])
        video_count = self._to_int(mapped["video_count"])
        media_count = (
            self._to_int(mapped["media_count"]) or
            photo_count + video_count or
            len(attachments)
        )

        return {
            "record": {
                "title": title,
                "original_text": text,
                "summary": self._summary_text(text),
                "original_date": published_at,
                "original_date_text": original_date_text,
                "normalized_date_utc": published_at,
                "source_type": "imported_historical_" + source_type,
                "source_identifier": source_identifier,
                "imported_from": Path(source_name).name,
                "source_file": str(source_name),
                "import_run_id": import_run_id,
                "raw_record": row,
                "raw_engagement": engagement,
                "attachment_references": attachments,
                "original_platform": platform,
                "import_status": "active",
                "imported_at": imported_at,
                "content_hash": content_hash,
                "notes": "Imported historical communication.",
                "campaign": self._clean(mapped["campaign"]),
                "program": self._clean(mapped["program"]),
                "topics": self._as_list(mapped["topics"])
            },
            "delivery": {
                "platform": platform,
                "published_at": published_at,
                "platform_post_id": platform_post_id,
                "permalink": self._clean(mapped["permalink"]),
                "delivery_text": text,
                "media_count": media_count,
                "photo_count": photo_count,
                "video_count": video_count,
                "engagement_metrics": engagement,
                "source_file": str(source_name),
                "import_run_id": import_run_id,
                "attachment_references": attachments,
                "media_matches": [],
                "match_confidence": 0,
                "original_platform": platform,
                "imported_at": imported_at,
                "delivery_hash": delivery_hash,
                "campaign": self._clean(mapped["campaign"]),
                "program": self._clean(mapped["program"]),
                "topics": self._as_list(mapped["topics"])
            },
            "campaign": self._clean(mapped["campaign"]),
            "program": self._clean(mapped["program"]),
            "topics": self._as_list(mapped["topics"]),
            "attachment_references": attachments,
            "warnings": date_warnings,
            "raw_keys": list(row.keys())
        }

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

    def _save_media_references(self, import_run_id, communication_id, delivery_id, normalized):

        for reference in normalized.get("attachment_references", []):
            self.db.save_communication_media_reference(
                {
                    "import_run_id": import_run_id,
                    "communication_id": communication_id,
                    "delivery_id": delivery_id,
                    "reference_text": reference,
                    "source_relative_path": reference,
                    "matched_media_id": 0,
                    "match_confidence": 0,
                    "match_reason": "Stored for later manual media linking.",
                    "status": "unmatched"
                }
            )

    def _record_import_item(self, import_run_id, action, reason, normalized, details=None):

        if not import_run_id:
            return

        self.db.save_communication_import_item(
            {
                "import_run_id": import_run_id,
                "communication_id": (details or {}).get("communication_id", 0),
                "delivery_id": (details or {}).get("delivery_id", 0),
                "action": action,
                "reason": reason,
                "details": {
                    "title": normalized["record"].get("title", ""),
                    "date": normalized["record"].get("original_date", ""),
                    "platform": normalized["delivery"].get("platform", ""),
                    **(details or {})
                }
            }
        )

    def _save_duplicate_review(self, import_run_id, normalized, duplicate):

        if not import_run_id:
            return

        self.db.save_communication_duplicate_review(
            {
                "import_run_id": import_run_id,
                "candidate_hash": normalized["record"].get("content_hash", ""),
                "incoming_summary": normalized["record"].get("summary", ""),
                "existing_communication_id": duplicate.get("communication_id", 0),
                "duplicate_type": duplicate.get("duplicate_type", ""),
                "confidence": duplicate.get("confidence", 0),
                "reason": duplicate.get("reason", ""),
                "status": "needs_review"
            }
        )

    ############################################################

    def _duplicate_candidate(self, normalized):

        return self.db.communication_duplicate_candidate(
            self._normalized_text(normalized["record"].get("original_text", "")),
            normalized["record"].get("original_date", "")[:10],
            normalized["record"].get("source_identifier", ""),
            normalized["delivery"].get("platform_post_id", "")
        )

    def _summary(self, source_type, path):

        return {
            "source_type": source_type,
            "source_name": Path(path).name,
            "started_at": TimeService.utc_now_iso(),
            "completed_at": "",
            "records_processed": 0,
            "records_inserted": 0,
            "deliveries_inserted": 0,
            "linked_as_delivery": 0,
            "duplicates_skipped": 0,
            "exact_duplicates_skipped": 0,
            "probable_duplicates_review": 0,
            "invalid_records": 0,
            "records_failed": 0,
            "campaigns_detected": set(),
            "programs_detected": set(),
            "topics_extracted": set(),
            "warnings": [],
            "status": "running",
            "duration_seconds": 0,
            "records_per_second": 0,
            "parsing_seconds": 0,
            "duplicate_check_seconds": 0,
            "persistence_seconds": 0,
            "enrichment_seconds": 0,
            "profile_rebuild_seconds": 0
        }

    def _public_summary(self, summary):

        return {
            **summary,
            "campaigns_detected": sorted(summary.get("campaigns_detected") or []),
            "programs_detected": sorted(summary.get("programs_detected") or []),
            "topics_extracted": sorted(summary.get("topics_extracted") or []),
            "warnings": list(summary.get("warnings") or [])[:100]
        }

    ############################################################

    def content_hash(self, text, published_at="", source_identifier=""):

        source = "|".join(
            (
                self._clean(source_identifier).lower(),
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

    def _auto_mapping(self, columns):

        return {
            field: column
            for field in self.FIELD_ALIASES
            for column in columns
            if self._field_for_column(column) == field
        }

    def _normalize_mapping(self, mapping):

        mapping = mapping or {}
        normalized = {}

        for key, value in mapping.items():
            if key in self.FIELD_ALIASES:
                normalized[key] = value
            else:
                field = self._field_for_column(key)

                if field:
                    normalized[field] = value

        return normalized

    def _field_for_column(self, column):

        normalized = str(column or "").strip().lower()

        for field, aliases in self.FIELD_ALIASES.items():
            if normalized in aliases:
                return field

        return ""

    def _mapped_value(self, row, field, mapping):

        key = mapping.get(field)

        if key and key in row:
            return row.get(key)

        lower_map = {
            str(raw_key).strip().lower(): value
            for raw_key, value in row.items()
        }

        for alias in self.FIELD_ALIASES[field]:
            if alias in lower_map and lower_map[alias] not in (None, ""):
                return lower_map[alias]

        return ""

    ############################################################

    def _safe_date(self, value, date_format=None):

        original = self._clean(value)

        if not original:
            return "", ["Missing publication date."], original

        if date_format:
            parsed = self._parse_with_format(original, date_format)

            if parsed:
                return parsed, [], original

            normalized = TimeService.normalize_stored_timestamp(original)

            if normalized and ("T" in original or "-" in original):
                return normalized.isoformat(timespec="seconds"), [], original

            return "", [f"Date did not match selected format {date_format}: {original}"], original

        if self._unix_timestamp(original):
            seconds = int(original[:10])
            return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec="seconds"), [], original

        normalized = TimeService.normalize_stored_timestamp(original)

        if normalized and ("T" in original or "-" in original):
            return normalized.isoformat(timespec="seconds"), [], original

        if "/" in original:
            parts = re.split(r"\D+", original)

            if len(parts) >= 3:
                first = self._to_int(parts[0])
                second = self._to_int(parts[1])

                if first <= 12 and second <= 12:
                    return "", [f"Ambiguous date requires selected format: {original}"], original

            for option in ("canadian_datetime", "canadian_date", "us_datetime", "us_date"):
                parsed = self._parse_with_format(original, option)

                if parsed:
                    return parsed, [], original

        for option in (
            "iso_datetime_space",
            "iso_date",
            "long_month",
            "short_month"
        ):
            parsed = self._parse_with_format(original, option)

            if parsed:
                return parsed, [], original

        return "", [f"Unrecognized date format: {original}"], original

    def _parse_with_format(self, value, date_format):

        fmt = self.DATE_FORMATS.get(date_format, date_format)

        try:
            parsed = datetime.strptime(value, fmt)
        except Exception:
            return ""

        if parsed.year < 1990 or parsed.year > 2100:
            return ""

        if "%H" not in fmt:
            parsed = datetime.combine(parsed.date(), dt_time(12, 0))

        parsed = parsed.replace(
            tzinfo=TimeService.local_timezone()
        )

        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")

    def _date_findings(self, records, mapping):

        warnings = []
        samples = []
        key = mapping.get("published_date", "")

        for record in records[:10]:
            value = record.get(key, "") if key else ""
            normalized, row_warnings, original = self._safe_date(value)
            samples.append(
                {
                    "original": original,
                    "normalized": normalized,
                    "warnings": row_warnings
                }
            )
            warnings.extend(row_warnings)

        return {
            "samples": samples,
            "warnings": warnings,
            "requires_manual_format": any("Ambiguous date" in warning for warning in warnings)
        }

    ############################################################

    def _engagement(self, mapped):

        if isinstance(mapped.get("engagement_metrics"), dict):
            return mapped["engagement_metrics"]

        if mapped.get("engagement_metrics"):
            try:
                parsed = json.loads(mapped["engagement_metrics"])
            except Exception:
                parsed = {
                    "raw": str(mapped["engagement_metrics"])
                }

            if isinstance(parsed, dict):
                return parsed

            return {
                "raw": parsed
            }

        metrics = {}

        for field in (
            "reactions",
            "comments",
            "shares",
            "views"
        ):
            value = self._to_int(mapped.get(field))

            if value:
                metrics[field] = value

        return metrics

    def _attachment_list(self, value):

        if isinstance(value, list):
            raw = value
        elif isinstance(value, dict):
            raw = value.get("data") or value.get("items") or list(value.values())
        else:
            raw = str(value or "").replace(";", ",").split(",")

        result = []

        for item in raw:
            if isinstance(item, dict):
                candidate = (
                    item.get("uri") or
                    item.get("path") or
                    item.get("filename") or
                    item.get("title") or
                    item.get("media")
                )
            else:
                candidate = item

            candidate = str(candidate or "").strip()

            if candidate:
                result.append(candidate)

        return result

    def _platform_findings(self, records, mapping):

        key = mapping.get("platform", "")
        values = sorted(
            {
                self._clean(record.get(key)).lower()
                for record in records
                if key and record.get(key)
            }
        )

        return values

    def _attachment_findings(self, records, mapping):

        key = mapping.get("attachment_filenames", "")
        values = []

        for record in records[:10]:
            values.extend(self._attachment_list(record.get(key, "")) if key else [])

        return values[:25]

    ############################################################

    def _record_count(self, path, source_type):

        try:
            return sum(1 for _item in self._iter_records(path, source_type))
        except Exception:
            return 0

    def _source_confidence(self, source_type, mapping, warnings):

        if source_type == "unsupported":
            return 0

        score = 40

        if mapping.get("text"):
            score += 20

        if mapping.get("published_date"):
            score += 20

        if mapping.get("platform"):
            score += 10

        if not warnings:
            score += 10

        return min(100, score)

    def _platform_from_source(self, source_type):

        if "facebook" in source_type:
            return "facebook"

        if "instagram" in source_type:
            return "instagram"

        return "unknown"

    def _looks_facebook(self, rows):

        keys = {
            key.lower()
            for row in self._record_list(rows)[:5]
            for key in row.keys()
        }

        return bool(keys & {"timestamp", "data", "attachments", "post", "title"})

    def _looks_instagram(self, rows):

        records = self._record_list(rows)[:5]
        keys = {
            key.lower()
            for row in records
            for key in row.keys()
        }
        platforms = {
            str(row.get("platform", "")).strip().lower()
            for row in records
            if row.get("platform")
        }

        if "instagram" in platforms:
            return True

        return bool(keys & {"media_type", "taken_at", "permalink"})

    def _record_list(self, value):

        return [
            item
            for item in (value or [])
            if isinstance(item, dict)
        ]

    def _instagram_records(self, payload):

        media = payload.get("media") or []

        return self._record_list(media)

    def _facebook_records(self, rows):

        records = []

        for item in self._record_list(rows):
            flattened = dict(item)
            data = item.get("data")

            if isinstance(data, list):
                text_parts = []

                for part in data:
                    if not isinstance(part, dict):
                        continue

                    text_parts.append(
                        part.get("post") or
                        part.get("text") or
                        part.get("message") or
                        ""
                    )

                if text_parts and not flattened.get("text"):
                    flattened["text"] = " ".join(
                        value
                        for value in text_parts
                        if value
                    )

            if item.get("timestamp") and not flattened.get("published_date"):
                flattened["published_date"] = item.get("timestamp")

            if item.get("creation_timestamp") and not flattened.get("published_date"):
                flattened["published_date"] = item.get("creation_timestamp")

            attachments = item.get("attachments")
            media_references = []

            if attachments and not flattened.get("attachment_filenames"):
                media_references.extend(
                    self._facebook_attachment_references(attachments)
                )

            if item.get("uri"):
                media_references.append(item.get("uri"))

            if media_references and not flattened.get("attachment_filenames"):
                flattened["attachment_filenames"] = media_references

            if attachments and not flattened.get("text"):
                attachment_text = self._facebook_attachment_text(attachments)

                if attachment_text:
                    flattened["text"] = attachment_text

            if item.get("uri") and not flattened.get("video_count"):
                flattened["video_count"] = 1 if str(item.get("uri")).lower().endswith(".mp4") else 0

            if media_references and not flattened.get("media_count"):
                flattened["media_count"] = len(media_references)

            flattened.setdefault("platform", "facebook")
            records.append(flattened)

        return records

    def _facebook_attachment_text(self, attachments):

        parts = []

        for attachment in self._record_list(attachments):
            for data in self._record_list(attachment.get("data")):
                media = data.get("media") if isinstance(data, dict) else None

                if isinstance(media, dict):
                    parts.append(media.get("description") or "")
                    parts.append(media.get("title") or "")

                external = data.get("external_context") if isinstance(data, dict) else None

                if isinstance(external, dict):
                    parts.append(external.get("name") or "")
                    parts.append(external.get("description") or "")

        return " ".join(value for value in parts if value)

    def _facebook_attachment_references(self, attachments):

        references = []

        for attachment in self._record_list(attachments):
            for data in self._record_list(attachment.get("data")):
                media = data.get("media") if isinstance(data, dict) else None

                if isinstance(media, dict) and media.get("uri"):
                    references.append(media.get("uri"))

                external = data.get("external_context") if isinstance(data, dict) else None

                if isinstance(external, dict) and external.get("url"):
                    references.append(external.get("url"))

        return references

    def _unix_timestamp(self, value):

        value = str(value or "").strip()

        return value.isdigit() and len(value) in (10, 13)

    def _summary_text(self, text):

        return self._clean(text)[:240]

    def _title_from_text(self, text):

        cleaned = self._clean(text)

        if not cleaned:
            return "Untitled Communication"

        return cleaned[:80]

    def _normalized_text(self, text):

        return re_space(self._clean(text).lower())

    def _clean(self, value):

        return " ".join(self._decode_meta_text(str(value or "")).split())

    def _decode_meta_text(self, value):

        try:
            decoded = value.encode("latin-1").decode("utf-8")
        except Exception:
            return value

        if any(marker in value for marker in ("Ã", "â", "ð")):
            return decoded

        return value

    def _as_list(self, value):

        if isinstance(value, list):
            return [
                self._clean(
                    item.get("name") or
                    item.get("topic") or
                    item.get("label") or
                    ""
                ) if isinstance(item, dict) else str(item).strip()
                for item in value
                if (
                    self._clean(
                        item.get("name") or
                        item.get("topic") or
                        item.get("label") or
                        ""
                    ) if isinstance(item, dict) else str(item).strip()
                )
            ]

        return [
            item.strip()
            for item in str(value or "").replace(";", ",").split(",")
            if item.strip()
        ]

    def _to_int(self, value):

        try:
            return int(float(value))
        except Exception:
            return 0


def re_space(value):

    return " ".join(str(value or "").split())
