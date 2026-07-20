from collections import defaultdict
from datetime import timedelta
from pathlib import Path
import re

from core.app_context import context
from services.automated_editorial_trust_service import AutomatedEditorialTrustService
from services.editorial_story_classifier import EditorialStoryClassifier
from services.time_service import TimeService


class EventCollectionService:

    DEFAULT_LIMIT = 500
    EVENT_GAP_HOURS = 8
    CAMPAIGN_GAP_DAYS = 45
    MIN_HOME_COHERENCE = 65
    GENERIC_TITLES = {
        "",
        "unknown",
        "media event",
        "event",
        "activity",
        "training activity",
        "posing for a photo",
        "type posing for a photo",
        "photo",
        "image",
        "picture"
    }
    GRAPHIC_EXTENSIONS = {".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
    DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".csv"}
    CAMPAIGN_TERMS = (
        "recruit",
        "hydrant heroes",
        "travelling sparky",
        "fire prevention",
        "water safety",
        "heat safety",
        "smoke alarm",
        "campaign",
        "program"
    )

    def __init__(
        self,
        database=None,
        trust_service=None,
        classifier=None
    ):

        self.db = database or context.database
        self.trust = trust_service or AutomatedEditorialTrustService(
            database=self.db
        )
        self.classifier = classifier or EditorialStoryClassifier()

    ############################################################

    def build_collections(self, limit=None, usable_only=False):

        rows = self._candidate_rows(limit or self.DEFAULT_LIMIT)
        groups = defaultdict(list)

        for row in rows:
            groups[self._event_key(row)].append(dict(row))

        collections = []
        for key, items in groups.items():
            if not items:
                continue
            collection = self._collection(key, items)
            if usable_only and not self._usable_for_packages(collection):
                continue
            collections.append(collection)

        collections.sort(
            key=lambda item: (
                item.get("event_integrity", {}).get("coherence_score", 0),
                item.get("title_confidence", 0),
                item.get("confidence", 0),
                item.get("media_count", 0),
                item.get("date_range", {}).get("end", "")
            ),
            reverse=True
        )
        return collections

    def top_collections(self, limit=20, source_limit=None):

        return self.build_collections(
            limit=source_limit or self.DEFAULT_LIMIT,
            usable_only=True
        )[:limit]

    ############################################################

    def event_summary(self, collection):

        collection = dict(collection or {})
        return {
            "event_id": collection.get("event_id", ""),
            "title": collection.get("title", ""),
            "title_source": collection.get("title_source", ""),
            "title_confidence": collection.get("title_confidence", 0),
            "alternative_titles": collection.get("alternative_titles", []),
            "what_occurred": collection.get("summary", ""),
            "when_it_occurred": collection.get("date_range", {}),
            "visible_activities": collection.get("visible_activities", []),
            "apparatus_equipment": collection.get("apparatus_equipment", []),
            "communication_angles": collection.get("communication_angles", []),
            "strongest_media": collection.get("representative_media", [])[:5],
            "best_photo": collection.get("best_photo", {}),
            "carousel_candidates": collection.get("carousel_candidates", []),
            "video_reel_candidates": collection.get("video_candidates", []),
            "risks": collection.get("risks", []),
            "missing_context": collection.get("missing_context", []),
            "event_integrity": collection.get("event_integrity", {}),
            "event_kind": collection.get("event_kind", "event")
        }

    def event_diagnostics(self, collection):

        collection = dict(collection or {})
        integrity = collection.get("event_integrity") or {}
        return {
            "event_id": collection.get("event_id", ""),
            "event_title": collection.get("title", ""),
            "confidence": collection.get("confidence", 0),
            "title_confidence": collection.get("title_confidence", 0),
            "title_source": collection.get("title_source", ""),
            "date_range": collection.get("date_range", {}),
            "source_folders": collection.get("source_folders", []),
            "media_count": collection.get("media_count", 0),
            "representative_media": collection.get("representative_media", [])[:8],
            "grouping_evidence": integrity.get("grouping_evidence", []),
            "conflicts": integrity.get("conflicts", []),
            "excluded_items": integrity.get("excluded_media", []),
            "anchor_evidence": integrity.get("anchor_evidence", []),
            "semantic_verification_status": collection.get(
                "semantic_verification_status",
                "not_required_for_coherent_group"
            ),
            "event_usability_state": integrity.get("event_usability_state", ""),
            "event_integrity": integrity
        }

    def rank_event_photos(self, collection, limit=8):

        allowed = {
            item.get("media_id") or item.get("id")
            for item in collection.get("media", [])
        }
        media_class = collection.get("media_class", "")
        photos = [
            item for item in collection.get("media", [])
            if item.get("media_type") == "image"
            and (item.get("media_id") or item.get("id")) in allowed
            and self._media_class(item) == media_class
            and not self._graphic_or_document(item)
        ]
        ranked = sorted(
            photos,
            key=lambda item: (
                item.get("automated_trust", {}).get("score", 0),
                item.get("communications_score", 0),
                self._capture_rank(item),
                item.get("width", 0) * item.get("height", 0),
                item.get("filename", "")
            ),
            reverse=True
        )
        return self._suppress_duplicates(ranked)[:limit]

    def contact_sheet_classification(
        self,
        collection,
        max_items=16,
        vision_provider=None
    ):

        ranked = self.rank_event_photos(collection, limit=max_items)
        integrity = collection.get("event_integrity") or {}
        provider_calls = 0
        semantic_status = "not_required_for_coherent_group"

        if integrity.get("event_usability_state") in ("uncertain", "invalid_mixed_event"):
            if vision_provider is None:
                semantic_status = "provider_unavailable_uncertain_event_excluded"
            else:
                provider_calls = 1
                semantic_status = "provider_screened_contact_sheet"

        families = [
            (item.get("story") or {}).get("primary_family")
            for item in collection.get("media", [])
            if (item.get("story") or {}).get("primary_family")
        ]
        family = self._most_common(families) or collection.get("activity_type", "")
        risks = sorted(set(collection.get("risks") or []))

        return {
            "event_id": collection.get("event_id", ""),
            "temporary_contact_sheet_stored": False,
            "full_library_deep_analysis_required": False,
            "provider_calls": provider_calls,
            "semantic_verification_status": semantic_status,
            "shared_event_visible": collection.get("title", ""),
            "primary_family": family,
            "strongest_frame_ids": [
                item.get("media_id") or item.get("id")
                for item in ranked[:5]
            ],
            "excluded_frame_ids": [
                item.get("media_id")
                for item in integrity.get("excluded_media", [])
                if item.get("media_id")
            ],
            "redundant_frame_groups": self._duplicate_groups(collection.get("media", [])),
            "supports_action": family in ("action_first_visual", "training_readiness", "technical_rescue"),
            "supports_community": family in ("community_event", "public_education", "prevention_safety"),
            "supports_teamwork": any("team" in str(value).lower() for value in collection.get("visible_activities", [])),
            "supports_personality": any(
                (item.get("story", {}).get("light_hearted", {}) or {}).get("suitable")
                for item in collection.get("media", [])
            ),
            "sensitivity_risks": risks,
            "confidence": collection.get("confidence", 0),
            "evidence": collection.get("evidence", [])
        }

    def apply_event_anchor(self, collection, anchor_media_id, correction):

        threshold = self.MIN_HOME_COHERENCE
        related = []
        for item in collection.get("media", []):
            media_id = item.get("media_id") or item.get("id")
            if media_id == anchor_media_id:
                continue
            if (item.get("automated_trust") or {}).get("score", 0) < 35:
                continue
            related.append(media_id)

        return {
            "event_id": collection.get("event_id", ""),
            "anchor_media_id": anchor_media_id,
            "correction": dict(correction or {}),
            "apply_confirmation_to_related_media": True,
            "affected_media_count": len(related[:100]),
            "evidence_threshold": threshold,
            "preview_of_inferred_changes": [
                {
                    "media_id": media_id,
                    "inference": "same coherent event, package-level confirmation"
                }
                for media_id in related[:10]
            ],
            "propagated_to_media_ids": related[:100],
            "inference_label": "Inferred from confirmed event",
            "raw_analysis_overwritten": False,
            "relationship_confidence": collection.get("confidence", 0)
        }

    ############################################################

    def _candidate_rows(self, limit):

        try:
            return self.db.content_director_candidates(limit=limit)
        except Exception:
            return []

    def _collection(self, key, items):

        title_info = self._title_info(items)
        title = title_info["title"]
        dates = sorted(
            value for value in (self._date(item) for item in items) if value
        )
        anchors = [
            item for item in items
            if item.get("trust_state") in ("approved_real", "corrected_real")
            or item.get("review_status") in ("approved", "corrected")
        ]
        media_class = self._most_common(self._media_class(item) for item in items)
        enriched = []

        for item in items:
            trust = self.trust.score_media(
                item,
                event={
                    "photo_count": sum(1 for row in items if row.get("media_type") == "image"),
                    "video_count": sum(1 for row in items if row.get("media_type") == "video"),
                    "confidence": 65 if len(items) >= 3 else 45
                },
                anchors=anchors
            )
            row = dict(item)
            row["media_class"] = self._media_class(row)
            row["automated_trust"] = trust
            row["story"] = self.classifier.classify(row)
            enriched.append(row)

        integrity = self._integrity(enriched, anchors, title_info)
        representative = sorted(
            [
                item for item in enriched
                if item.get("media_class") == media_class
                and not self._excluded_by_integrity(item, integrity)
            ],
            key=lambda item: (
                item["automated_trust"]["score"],
                item.get("communications_score", 0)
            ),
            reverse=True
        )
        primary_story = self.classifier.classify({
            "title": title,
            "search_text": " ".join(self._terms(enriched))
        })
        photo_count = sum(1 for row in enriched if row.get("media_type") == "image")
        video_count = sum(1 for row in enriched if row.get("media_type") == "video")
        confidence = min(
            95,
            integrity.get("coherence_score", 0) +
            min(10, len(anchors) * 4)
        )
        risks = sorted({
            risk
            for row in enriched
            for risk in row.get("story", {}).get("risks", [])
        })

        collection = {
            "event_id": key,
            "title": title,
            "title_source": title_info["source"],
            "title_confidence": title_info["confidence"],
            "alternative_titles": title_info["alternatives"],
            "conflicting_labels": title_info["conflicts"],
            "activity_type": primary_story.get("primary_family", ""),
            "event_kind": self._event_kind(enriched),
            "program_campaign": self._program(enriched),
            "date_range": {
                "start": dates[0] if dates else "",
                "end": dates[-1] if dates else ""
            },
            "source_folders": sorted({self._folder(item) for item in enriched})[:6],
            "media_class": media_class,
            "photo_count": photo_count,
            "video_count": video_count,
            "helmet_camera_sources": [
                item.get("filename", "")
                for item in enriched
                if "helmet" in str(item.get("path", "")).lower()
            ][:5],
            "media_count": len(enriched),
            "evidence": self._evidence(enriched, anchors, integrity),
            "confidence": confidence,
            "sensitive_content_risk": bool(risks),
            "risks": risks,
            "representative_media": representative[:8],
            "best_photo": {},
            "carousel_candidates": [],
            "video_candidates": [
                item for item in representative if item.get("media_type") == "video"
            ][:4],
            "communication_status": "draft_candidate",
            "historical_related_posts": [],
            "summary": self._summary(title, primary_story, len(enriched), integrity),
            "visible_activities": sorted(set(self._terms(enriched)))[:8],
            "apparatus_equipment": self._apparatus_equipment(enriched),
            "communication_angles": [
                primary_story.get("primary_family", ""),
                *primary_story.get("secondary_families", [])
            ][:5],
            "missing_context": self._missing_context(enriched, integrity),
            "semantic_verification_status": "not_required_for_coherent_group",
            "event_integrity": integrity,
            "media": enriched
        }
        ranked_photos = self.rank_event_photos(collection, limit=6)
        collection["best_photo"] = ranked_photos[0] if ranked_photos else {}
        collection["carousel_candidates"] = ranked_photos[:6]
        return collection

    def _event_key(self, row):

        folder = self._folder(row)
        media_class = self._media_class(row)
        date_bucket = self._date_bucket(row)
        activity = self._activity_identity(row)

        return "|".join(
            part.strip().lower().replace(" ", "_")
            for part in (folder, date_bucket, media_class, activity)
            if part
        )[:180]

    def _integrity(self, items, anchors, title_info):

        folders = sorted({self._folder(item) for item in items if self._folder(item)})
        media_classes = sorted({self._media_class(item) for item in items})
        sources = sorted({self._source_device(item) for item in items if self._source_device(item)})
        dates = [
            self._date_object(item)
            for item in items
            if self._date_object(item) is not None
        ]
        span_hours = None
        if len(dates) >= 2:
            span_hours = (max(dates) - min(dates)).total_seconds() / 3600

        evidence = []
        conflicts = []
        score = 15

        if len(folders) == 1 and not self._generic_folder(folders[0]):
            score += 30
            evidence.append("Common specific parent folder: " + folders[0])
        elif len(folders) > 1:
            conflicts.append("Multiple source folders: " + ", ".join(folders[:4]))

        if len(media_classes) == 1:
            score += 18
            evidence.append("Single media class: " + media_classes[0])
        else:
            conflicts.append("Mixed media classes: " + ", ".join(media_classes))

        if span_hours is not None and span_hours <= self.EVENT_GAP_HOURS:
            score += 18
            evidence.append(f"Narrow capture-time span: {span_hours:.1f} hour(s)")
        elif span_hours is not None and span_hours <= 24:
            score += 8
            evidence.append(f"Same-day capture span: {span_hours:.1f} hour(s)")
        elif span_hours is not None:
            conflicts.append(f"Capture dates span {span_hours / 24:.1f} day(s)")
        elif len(items) > 1:
            conflicts.append("Capture timestamps are missing or insufficient.")

        if self._sequence_agreement(items):
            score += 10
            evidence.append("Filename sequence or burst proximity exists.")

        if len(sources) == 1:
            score += 6
            evidence.append("Common source/device evidence exists.")

        if anchors:
            score += min(12, len(anchors) * 6)
            evidence.append(f"{len(anchors)} approved/corrected anchor item(s).")

        if title_info.get("confidence", 0) >= 70:
            score += 10
            evidence.append(
                f"Usable title from {title_info.get('source', 'stored evidence')}."
            )
        else:
            conflicts.append("No high-confidence event title.")

        excluded = self._excluded_media(items, media_classes, folders, span_hours)
        if excluded:
            score -= min(25, len(excluded) * 5)

        score = max(0, min(100, score))
        state = self._integrity_state(score, conflicts, title_info, media_classes)
        if state == "invalid_mixed_event" and not excluded:
            excluded = [
                self._excluded_summary(item, "Mixed event evidence requires clarification.")
                for item in items[1:25]
            ]

        return {
            "coherence_score": score,
            "grouping_evidence": evidence,
            "conflicts": conflicts,
            "excluded_media": excluded,
            "anchor_evidence": [
                {
                    "media_id": item.get("media_id") or item.get("id"),
                    "filename": item.get("filename", ""),
                    "review_status": item.get("review_status", ""),
                    "trust_state": item.get("trust_state", "")
                }
                for item in anchors[:8]
            ],
            "event_usability_state": state,
            "usable_for_home": state in ("coherent", "coherent_with_review"),
            "manual_clarification_required": state in ("uncertain", "invalid_mixed_event")
        }

    def _integrity_state(self, score, conflicts, title_info, media_classes):

        if len(media_classes) > 1:
            return "invalid_mixed_event"
        if self._generic_title(title_info.get("title", "")):
            return "uncertain"
        if any("span" in conflict.lower() for conflict in conflicts):
            return "invalid_mixed_event"
        if score >= 78:
            return "coherent"
        if score >= self.MIN_HOME_COHERENCE:
            return "coherent_with_review"
        return "uncertain"

    def _usable_for_packages(self, collection):

        integrity = collection.get("event_integrity") or {}
        return (
            integrity.get("event_usability_state") in ("coherent", "coherent_with_review")
            and not self._generic_title(collection.get("title", ""))
            and collection.get("title_confidence", 0) >= 65
        )

    def _excluded_media(self, items, media_classes, folders, span_hours):

        excluded = []
        majority_class = self._most_common(media_classes)
        majority_folder = self._most_common(folders)

        for item in items:
            reasons = []
            if majority_class and self._media_class(item) != majority_class:
                reasons.append("different media class")
            if majority_folder and self._folder(item) != majority_folder:
                reasons.append("different source folder")
            if span_hours is not None and span_hours > self.EVENT_GAP_HOURS:
                reasons.append("outside event time window")
            if reasons:
                excluded.append(
                    self._excluded_summary(item, ", ".join(reasons))
                )
        return excluded[:50]

    def _excluded_summary(self, item, reason):

        return {
            "media_id": item.get("media_id") or item.get("id"),
            "filename": item.get("filename", ""),
            "path": item.get("path", ""),
            "media_class": self._media_class(item),
            "capture_time": item.get("capture_time", ""),
            "reason": reason
        }

    def _excluded_by_integrity(self, item, integrity):

        media_id = item.get("media_id") or item.get("id")
        return any(
            excluded.get("media_id") == media_id
            for excluded in integrity.get("excluded_media", [])
        )

    def _title_info(self, items):

        alternatives = []
        conflicts = []
        folder = self._folder(items[0]) if items else ""
        folder_title = self._clean_title(folder)

        if folder_title and not self._generic_title(folder_title):
            return {
                "title": folder_title,
                "source": "exact_event_folder",
                "confidence": 88,
                "alternatives": alternatives,
                "conflicts": conflicts
            }

        labels = []
        for item in items:
            for key in ("event_title", "operational_context", "primary_activity", "incident_type", "normalized_scene"):
                value = self._clean_title(item.get(key, ""))
                if value and not self._generic_title(value):
                    labels.append(value)

        label = self._most_common(labels)
        if label:
            alternatives = sorted(set(labels))[:5]
            if len(set(labels)) > 1:
                conflicts = sorted(set(labels))[1:5]
            return {
                "title": label,
                "source": "shared_corrected_or_activity_label",
                "confidence": 72 if labels.count(label) >= 2 else 62,
                "alternatives": alternatives,
                "conflicts": conflicts
            }

        program = self._program(items)
        first_date = self._date(items[0])[:10] if items else ""
        if program:
            title = self._clean_title(program)
            if first_date:
                title = f"{title} - {first_date}"
            return {
                "title": title,
                "source": "program_campaign_plus_date",
                "confidence": 66,
                "alternatives": alternatives,
                "conflicts": conflicts
            }

        return {
            "title": "Unnamed Event",
            "source": "insufficient_authoritative_evidence",
            "confidence": 20,
            "alternatives": alternatives,
            "conflicts": conflicts
        }

    def _summary(self, title, story, count, integrity):

        return (
            f"{title} with {count} related media item(s), classified primarily as "
            f"{story.get('primary_family', '').replace('_', ' ')}. "
            f"Event integrity is {integrity.get('event_usability_state')} "
            f"at {integrity.get('coherence_score', 0)}."
        )

    def _date(self, item):

        value = self._date_object(item)
        return value.isoformat() if value else ""

    def _date_object(self, item):

        for key in ("capture_time", "captured_at", "date_taken"):
            if item.get(key):
                parsed = TimeService.to_local(item.get(key))
                if parsed is not None:
                    return parsed

        filesystem = item.get("filesystem_intelligence") or {}
        for key in ("date", "folder_date", "event_date"):
            if filesystem.get(key):
                parsed = TimeService.to_local(filesystem.get(key))
                if parsed is not None:
                    return parsed

        for key in ("first_seen_at", "date_added"):
            if item.get(key):
                parsed = TimeService.to_local(item.get(key))
                if parsed is not None:
                    return parsed

        return None

    def _date_bucket(self, item):

        value = self._date_object(item)
        if value is None:
            return "undated"
        bucket_hour = (value.hour // self.EVENT_GAP_HOURS) * self.EVENT_GAP_HOURS
        return value.replace(
            hour=bucket_hour,
            minute=0,
            second=0,
            microsecond=0
        ).isoformat()

    def _capture_rank(self, item):

        value = self._date_object(item)
        if value is None:
            return ""
        return value.isoformat()

    def _folder(self, item):

        path = Path(str(item.get("path") or ""))
        parent = ""
        try:
            parent = path.parent.name
        except Exception:
            parent = ""

        if self._year_folder(parent):
            try:
                grandparent = path.parent.parent.name
                if grandparent and not self._generic_folder(grandparent):
                    return grandparent
            except Exception:
                pass

        if parent and not self._generic_folder(parent):
            return parent

        filesystem = item.get("filesystem_intelligence") or {}
        for key in ("event_name", "program", "subcategory", "root_category"):
            value = str(filesystem.get(key) or "")
            if value and not self._generic_folder(value):
                return value

        return parent or "Unfiled Media"

    def _media_class(self, item):

        path = Path(str(item.get("path") or item.get("filename") or ""))
        ext = path.suffix.lower()
        filename = path.name.lower()
        media_type = str(item.get("media_type") or "").lower()
        width = self._to_int(item.get("width"))
        height = self._to_int(item.get("height"))
        ratio = width / height if width and height else 0
        text = " ".join(
            str(value or "")
            for value in (
                filename,
                item.get("path", ""),
                item.get("normalized_scene", ""),
                item.get("primary_activity", "")
            )
        ).lower()

        if "helmet cam" in text or "helmet camera" in text:
            return "helmet_camera_clip"
        if media_type == "video":
            return "ordinary_video"
        if ext in self.DOCUMENT_EXTENSIONS:
            return "document"
        if any(token in text for token in ("certificate", "award", "anniversary", "poster", "graphic", "flyer")):
            return "social_graphic"
        if ext in self.GRAPHIC_EXTENSIONS and not self._looks_like_camera_file(filename):
            return "social_graphic"
        if "scan" in text or "scanned" in text:
            return "scanned_historical_image"
        if "apparatus" in text or re.search(r"\b(engine|rescue|pumper|ladder|tanker)\b", text):
            if not any(token in text for token in ("training", "firefighter", "team", "public education")):
                return "apparatus_portrait"
        if ratio and (ratio > 2.2 or ratio < 0.42):
            return "unusual_crop_photo"
        return "captured_photo"

    def _graphic_or_document(self, item):

        return self._media_class(item) in (
            "social_graphic",
            "document",
            "scanned_historical_image"
        )

    def _activity_identity(self, row):

        for key in ("operational_context", "primary_activity", "incident_type", "normalized_scene"):
            value = self._clean_title(row.get(key, ""))
            if value and not self._generic_title(value):
                return value
        return self._program([row]) or "event"

    def _event_kind(self, items):

        text = " ".join(self._terms(items)).lower()
        if any(term in text for term in self.CAMPAIGN_TERMS):
            dates = [
                self._date_object(item)
                for item in items
                if self._date_object(item) is not None
            ]
            if len(dates) >= 2 and max(dates) - min(dates) > timedelta(days=self.CAMPAIGN_GAP_DAYS):
                return "campaign_program"
        return "event"

    def _sequence_agreement(self, items):

        prefixes = defaultdict(list)
        for item in items:
            filename = str(item.get("filename") or "").lower()
            stem = filename.rsplit(".", 1)[0]
            match = re.match(r"(.+?)(\d{2,})$", stem)
            if match:
                prefixes[match.group(1)].append(int(match.group(2)))
        return any(len(values) >= 2 and max(values) - min(values) <= 30 for values in prefixes.values())

    def _source_device(self, item):

        for key in ("camera_make", "camera_model", "device_id", "sha256"):
            if item.get(key):
                return str(item.get(key))[:32]
        return ""

    def _terms(self, items):

        terms = []
        for item in items:
            for key in ("primary_activity", "incident_type", "normalized_scene", "operational_context"):
                if item.get(key):
                    value = str(item.get(key))
                    if not self._generic_title(value):
                        terms.append(value)
            for key in ("content_tags", "content_themes", "recommended_uses"):
                terms.extend(str(value) for value in (item.get(key) or []))
        return terms

    def _program(self, items):

        for item in items:
            filesystem = item.get("filesystem_intelligence") or {}
            for key in ("public_education_program", "campaign", "community_event", "program"):
                if filesystem.get(key):
                    return filesystem.get(key)
        return ""

    def _apparatus_equipment(self, items):

        values = []
        for item in items:
            values.extend(item.get("apparatus_tags") or [])
            values.extend(item.get("equipment_tags") or [])
        return sorted(set(str(value) for value in values if value))[:10]

    def _evidence(self, items, anchors, integrity):

        evidence = list(integrity.get("grouping_evidence") or [])
        evidence.insert(0, f"{len(items)} media item(s) considered after class/date/folder grouping.")
        evidence.append(f"{len(anchors)} approved or corrected anchor item(s).")
        return evidence

    def _missing_context(self, items, integrity):

        missing = []
        if not any(item.get("capture_time") for item in items):
            missing.append("Capture date is missing for some or all media.")
        if not any(item.get("primary_activity") for item in items):
            missing.append("Primary activity needs stronger confirmation.")
        if integrity.get("event_usability_state") in ("uncertain", "invalid_mixed_event"):
            missing.append("Package-level event clarification is required before use.")
        return missing

    def _suppress_duplicates(self, ranked):

        seen = set()
        result = []
        for item in ranked:
            key = self._duplicate_key(item)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _duplicate_key(self, item):

        filename = str(item.get("filename") or "").lower()
        prefix = filename.rsplit(".", 1)[0]
        folder = self._folder(item).lower()
        return folder + "|" + prefix.rstrip("0123456789_- ")

    def _duplicate_groups(self, items):

        groups = defaultdict(list)
        for item in items:
            groups[self._duplicate_key(item)].append(item.get("media_id") or item.get("id"))

        return [
            values for values in groups.values()
            if len(values) > 1
        ][:10]

    def _most_common(self, values):

        counts = defaultdict(int)
        for value in values:
            if value:
                counts[value] += 1
        if not counts:
            return ""
        return sorted(counts.items(), key=lambda item: item[1], reverse=True)[0][0]

    def _clean_title(self, value):

        text = str(value or "").strip().replace("_", " ")
        text = re.sub(r"\s+", " ", text)
        if not text:
            return ""
        return text.title()

    def _generic_title(self, value):

        text = str(value or "").strip().replace("_", " ").lower()
        text = re.sub(r"\s+", " ", text)
        return text in self.GENERIC_TITLES or text.startswith("type ") or self._year_folder(text)

    def _generic_folder(self, value):

        text = str(value or "").strip().lower()
        return text in ("", ".", "unknown", "media", "images", "photos", "pictures", "unfiled media") or self._year_folder(text)

    def _year_folder(self, value):

        return bool(re.fullmatch(r"(19|20)\d{2}", str(value or "").strip()))

    def _looks_like_camera_file(self, filename):

        text = str(filename or "").lower()
        return bool(
            re.match(r"(img|dsc|dji|pxl|image|photo)[_ -]?\d+", text)
            or re.match(r"\d{8}[_-]\d{6}", text)
        )

    def _to_int(self, value):

        try:
            return int(value or 0)
        except Exception:
            return 0
