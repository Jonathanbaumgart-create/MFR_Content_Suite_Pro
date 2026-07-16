import re
import time
from pathlib import Path, PureWindowsPath

from config.filesystem_intelligence_rules import FILESYSTEM_INTELLIGENCE_RULES
from core.app_context import context
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("intelligence")


class _EmptyKnowledgeService:

    def items(self, _table):

        return []


class FilesystemIntelligenceService:

    CONFIDENCE_HIGH = 90
    CONFIDENCE_MEDIUM = 70
    CONFIDENCE_LOW = 45
    BACKFILL_BATCH_SIZE = 200

    def __init__(self, database=None, knowledge_service=None, rules=None):

        self.db = database or context.database
        if knowledge_service is not None:
            self.knowledge = knowledge_service
        elif hasattr(self.db, "knowledge_items"):
            self.knowledge = KnowledgeService(database=self.db)
        else:
            self.knowledge = _EmptyKnowledgeService()
        self.rules = rules or FILESYSTEM_INTELLIGENCE_RULES
        self.rules_version = self.rules.get(
            "version",
            "filesystem-intelligence-v1"
        )

    ############################################################

    def derive_for_media(self, media, media_root=None):

        started = time.perf_counter()
        media = self._media_with_context(media)
        path = media.get("path", "") if isinstance(media, dict) else str(media)
        root = media_root or media.get("media_root", "") if isinstance(media, dict) else media_root
        hierarchy = self._relative_hierarchy(path, root)
        normalized_folders = [
            self.normalize_token(part)
            for part in hierarchy
            if self.normalize_token(part)
        ]
        folder_text = " ".join(normalized_folders)
        tags = []
        source_folders = []
        matched_rules = []
        category = "unknown"
        subcategory = "unknown"
        parent_category = hierarchy[-2] if len(hierarchy) > 1 else ""

        apparatus = self._apparatus(folder_text, normalized_folders)
        training = self._match_group("training", folder_text)
        incidents = self._match_group("incidents", folder_text)
        programs = self._match_group("programs", folder_text)
        campaigns = self._match_group("campaigns", folder_text)
        community = self._match_group("community", folder_text)
        years = self._years(normalized_folders)
        month = self._month(normalized_folders)

        for match in (
            apparatus.get("tags", []) +
            training +
            incidents +
            programs +
            campaigns +
            community
        ):
            tags.append(match)

        if years:
            tags.extend(years)

        category, subcategory = self._category(
            apparatus,
            training,
            incidents,
            programs,
            campaigns,
            community
        )
        source_folders = self._source_folders(
            hierarchy,
            tags
        )
        matched_rules = self._unique(tags)
        conflicts = self._conflicts(media, tags, category)
        confidence = self._confidence(
            category,
            apparatus,
            training,
            incidents,
            programs,
            campaigns,
            community,
            conflicts
        )

        result = {
            "media_id": self._to_int(media.get("id") or media.get("media_id"))
            if isinstance(media, dict)
            else 0,
            "media_root": self._safe_root(root, path),
            "relative_path": self._relative_path(path, root),
            "folder_hierarchy": hierarchy,
            "root_category": category,
            "parent_category": parent_category,
            "subcategory": subcategory,
            "folder_keywords": normalized_folders,
            "normalized_tags": self._unique(tags),
            "apparatus_identifier": apparatus.get("identifier", ""),
            "apparatus_name": apparatus.get("name", ""),
            "apparatus_resolved": bool(apparatus.get("resolved")),
            "incident_category": (
                "incident"
                if category == "Incidents" and incidents
                else "unknown"
            ),
            "incident_type": (
                self._first_specific(incidents)
                if category == "Incidents"
                else "unknown"
            ),
            "training_category": (
                "training"
                if category == "Training" and training
                else "unknown"
            ),
            "training_type": (
                self._first_specific(training)
                if category == "Training"
                else "unknown"
            ),
            "drill_type": (
                "drill"
                if category == "Training" and "drill" in training
                else ""
            ),
            "live_burn_context": (
                category == "Training" and "live_burn" in training
            ),
            "public_education_program": (
                self._first_specific(programs)
                if category == "Programs"
                else "unknown"
            ),
            "campaign": (
                self._first_specific(campaigns)
                if category == "Campaigns"
                else "unknown"
            ),
            "community_event": (
                self._first_specific(community)
                if category == "Community"
                else "unknown"
            ),
            "station": self._station(folder_text),
            "recruit_class": "recruit_class" in training,
            "mutual_aid_context": "mutual aid" in folder_text,
            "year": years[0] if years else "",
            "month": month,
            "season": self._season(month),
            "location_context": "",
            "filesystem_confidence": confidence,
            "matching_rule": ", ".join(matched_rules[:8]),
            "source_folders": source_folders,
            "conflict_state": "conflict" if conflicts else "none",
            "conflict_details": conflicts,
            "enrichment_version": self.rules_version,
            "last_derived_at": TimeService.utc_now_iso(),
            "derivation_duration_ms": round(
                (time.perf_counter() - started) * 1000,
                3
            )
        }

        logger.info(
            "Derived filesystem intelligence media_id=%s category=%s confidence=%s",
            result.get("media_id"),
            category,
            confidence
        )
        return result

    ############################################################

    def save_for_media(self, media, media_root=None, force=False):

        media_id = (
            self._to_int(media.get("id") or media.get("media_id"))
            if isinstance(media, dict)
            else 0
        )

        if not media_id:
            return {}

        existing = self.db.get_filesystem_intelligence(media_id)

        if (
            existing and
            not force and
            existing.get("enrichment_version") == self.rules_version and
            existing.get("relative_path") == self._relative_path(
                media.get("path", ""),
                media_root
            )
        ):
            return existing

        intelligence = self.derive_for_media(
            media,
            media_root=media_root
        )
        self.db.save_filesystem_intelligence(
            media_id,
            intelligence
        )
        return intelligence

    ############################################################

    def preview_backfill(self, limit=500):

        rows = self.db.get_media_needing_filesystem_intelligence(
            self.rules_version,
            limit=limit
        )
        categories = {}
        conflicts = 0
        videos = 0

        for row in rows:
            media = self._row_media(row)
            derived = self.derive_for_media(media)
            category = derived.get("root_category") or derived.get("subcategory")
            categories[category or "unknown"] = categories.get(category or "unknown", 0) + 1
            if media.get("media_type") == "video":
                videos += 1
            if derived.get("conflict_state") == "conflict":
                conflicts += 1

        return {
            "eligible": len(rows),
            "preview_limit": limit,
            "already_current": max(
                0,
                self.db.media_count() - len(rows)
            ),
            "category_counts": categories,
            "video_count": videos,
            "conflict_estimate": conflicts,
            "rules_version": self.rules_version
        }

    ############################################################

    def backfill(
        self,
        limit=500,
        batch_size=BACKFILL_BATCH_SIZE,
        progress_callback=None,
        cancel_event=None
    ):

        rows = self.db.get_media_needing_filesystem_intelligence(
            self.rules_version,
            limit=limit
        )
        total = len(rows)
        processed = 0
        updated = 0
        failed = 0
        conflicts = 0

        for row in rows:
            if cancel_event is not None and cancel_event.is_set():
                break

            try:
                media = self._row_media(row)
                derived = self.save_for_media(
                    media,
                    force=True
                )
                updated += 1
                if derived.get("conflict_state") == "conflict":
                    conflicts += 1
            except Exception:
                failed += 1
                logger.warning(
                    "Filesystem intelligence backfill failed media=%s",
                    dict(row) if hasattr(row, "keys") else row,
                    exc_info=True
                )

            processed += 1

            if progress_callback and (
                processed % max(1, int(batch_size or 1)) == 0 or
                processed == total
            ):
                progress_callback(
                    {
                        "status": "filesystem intelligence",
                        "total": total,
                        "processed": processed,
                        "updated": updated,
                        "failed": failed,
                        "conflicts": conflicts
                    }
                )

        return {
            "total": total,
            "processed": processed,
            "updated": updated,
            "skipped": max(0, total - processed),
            "failed": failed,
            "conflicts": conflicts,
            "canceled": bool(cancel_event and cancel_event.is_set()),
            "rules_version": self.rules_version
        }

    ############################################################

    def folder_knowledge_map(self, limit=100):

        return self.db.filesystem_knowledge_map(limit=limit)

    ############################################################

    def prompt_context(self, media_id):

        if not hasattr(self.db, "get_filesystem_intelligence"):
            return ""

        intel = self.db.get_filesystem_intelligence(media_id) or {}

        if not intel:
            return ""

        parts = []

        for label, key in (
            ("category", "subcategory"),
            ("apparatus", "apparatus_name"),
            ("training", "training_type"),
            ("incident", "incident_type"),
            ("program", "public_education_program"),
            ("campaign", "campaign")
        ):
            value = intel.get(key)

            if value and value != "unknown":
                parts.append(f"{label}: {value}")

        if not parts:
            return ""

        return (
            "Folder context suggests " +
            "; ".join(parts[:6]) +
            ". Confirm only if visually supported. "
            "Do not treat folder context as visual proof."
        )

    ############################################################

    def normalize_token(self, value):

        text = str(value or "").lower()
        text = text.replace("\\", " ").replace("/", " ")
        text = re.sub(r"[_\-]+", " ", text)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        singulars = {
            "drills": "drill",
            "ladders": "ladder",
            "incidents": "incident",
            "trainings": "training"
        }
        return singulars.get(text, text)

    ############################################################

    def _relative_hierarchy(self, path, root=None):

        relative = self._relative_path(path, root)
        parts = [
            part
            for part in PureWindowsPath(relative).parts[:-1]
            if part and part not in ("\\", "/")
        ]
        return parts[-12:]

    def _relative_path(self, path, root=None):

        path_text = str(path or "")

        if not path_text:
            return ""

        try:
            source = Path(path_text)
            if root:
                return str(source.resolve().relative_to(Path(root).resolve()))
        except Exception:
            pass

        parts = PureWindowsPath(path_text).parts

        if parts:
            safe_parts = list(parts)

            if safe_parts[0].endswith("\\") or safe_parts[0].endswith("/"):
                safe_parts = safe_parts[1:]

            lower_parts = [
                part.lower()
                for part in safe_parts
            ]

            if "pictures" in lower_parts:
                index = len(lower_parts) - 1 - lower_parts[::-1].index("pictures")
                safe_parts = safe_parts[index + 1:]

            if len(safe_parts) > 8:
                safe_parts = safe_parts[-8:]

            if safe_parts:
                return str(PureWindowsPath(*safe_parts))

        return path_text

    def _safe_root(self, root, path):

        if root:
            return str(PureWindowsPath(str(root)).name)

        parts = PureWindowsPath(str(path or "")).parts

        if len(parts) >= 3:
            return parts[-3]

        return ""

    def _match_group(self, group, text):

        matches = []

        for key, aliases in self.rules.get(group, {}).items():
            for alias in aliases:
                needle = self.normalize_token(alias)
                if needle and self._contains_token(text, needle):
                    matches.append(key)
                    break

        return self._unique(matches)

    def _apparatus(self, text, folders):

        for key, rule in self.rules.get("apparatus", {}).items():
            aliases = rule.get("aliases", [])

            for alias in aliases:
                needle = self.normalize_token(alias)
                if needle and self._contains_token(text, needle):
                    resolved = self._resolve_apparatus(
                        rule.get("apparatus_identifier", key),
                        rule.get("apparatus_name", "")
                    )
                    return {
                        "identifier": rule.get("apparatus_identifier", key),
                        "name": resolved.get("name") or rule.get("apparatus_name", ""),
                        "resolved": resolved.get("resolved", False),
                        "tags": [
                            "apparatus",
                            "apparatus_" + rule.get("apparatus_identifier", key)
                        ]
                    }

        for folder in folders:
            if (
                re.fullmatch(r"\d{2,4}", folder or "") and
                not re.fullmatch(r"(19|20)\d{2}", folder or "")
            ):
                resolved = self._resolve_apparatus(folder, "")
                return {
                    "identifier": folder,
                    "name": resolved.get("name", ""),
                    "resolved": resolved.get("resolved", False),
                    "tags": ["apparatus", "apparatus_" + folder]
                }

        return {"tags": []}

    def _resolve_apparatus(self, identifier, fallback_name):

        identifier = str(identifier or "")
        normalized_id = self.normalize_token(identifier)

        for item in self.knowledge.items("apparatus"):
            name = str(item.get("name", ""))
            tags = " ".join(str(tag) for tag in item.get("tags", []))
            haystack = self.normalize_token(name + " " + tags)

            if normalized_id and self._contains_token(haystack, normalized_id):
                return {
                    "resolved": True,
                    "name": name or fallback_name
                }

        return {
            "resolved": False,
            "name": fallback_name
        }

    def _category(
        self,
        apparatus,
        training,
        incidents,
        programs,
        campaigns,
        community
    ):

        if apparatus.get("identifier"):
            return "Apparatus", apparatus.get("name") or apparatus.get("identifier")

        if training:
            return "Training", self._first_specific(training)

        if incidents:
            return "Incidents", self._first_specific(incidents)

        if programs:
            return "Programs", self._first_specific(programs)

        if campaigns:
            return "Campaigns", self._first_specific(campaigns)

        if community:
            return "Community", self._first_specific(community)

        return "unknown", "unknown"

    def _confidence(
        self,
        category,
        apparatus,
        training,
        incidents,
        programs,
        campaigns,
        community,
        conflicts
    ):

        if category == "unknown":
            return 0

        score = self.CONFIDENCE_LOW

        if apparatus.get("identifier") or programs or campaigns:
            score = self.CONFIDENCE_HIGH
        elif training or incidents or community:
            score = self.CONFIDENCE_MEDIUM

        if conflicts:
            score = max(25, score - 25)

        return score

    def _conflicts(self, media, tags, category="unknown"):

        text = " ".join(
            str(media.get(key, "") or "").lower()
            for key in ("normalized_scene", "incident_type", "primary_activity")
        ) if isinstance(media, dict) else ""

        if not text:
            return []

        conflicts = []
        incident_tags = set(self.rules.get("incidents", {}).keys())
        community_tags = set(self.rules.get("community", {}).keys())
        has_incident_context = bool(incident_tags.intersection(tags))
        has_community_context = bool(community_tags.intersection(tags))

        has_training_context = bool(set(self.rules.get("training", {}).keys()).intersection(tags))

        if (
            category == "Training" and
            has_training_context and
            any(term in text for term in ("community", "public_education"))
        ):
            conflicts.append(
                "Folder suggests training while existing intelligence suggests community/public education."
            )

        if category == "Incidents" and has_incident_context and "training" in text:
            conflicts.append(
                "Folder suggests incident context while existing intelligence suggests training."
            )

        if category == "Community" and has_community_context and any(
            term in text
            for term in (
                "incident_response",
                "fire_suppression",
                "structure_fire",
                "motor_vehicle_collision",
                "mvc",
                "hazmat"
            )
        ):
            conflicts.append(
                "Folder suggests community context while existing intelligence suggests incident response."
            )

        return conflicts

    def _source_folders(self, hierarchy, tags):

        sources = []

        for folder in hierarchy:
            normalized = self.normalize_token(folder)

            if any(self._contains_token(normalized, tag) for tag in tags):
                sources.append(folder)

        return sources[:8]

    def _contains_token(self, haystack, needle):

        haystack = " " + str(haystack or "") + " "
        needle = str(needle or "").strip()

        if not needle:
            return False

        return (" " + needle + " ") in haystack

    def _first_specific(self, values):

        for value in values or []:
            if value not in ("training", "drill", "incidents"):
                return value

        return values[0] if values else "unknown"

    def _years(self, folders):

        years = []

        for folder in folders:
            match = re.search(r"\b(19|20)\d{2}\b", folder)
            if match:
                years.append(match.group(0))

        return self._unique(years)

    def _month(self, folders):

        months = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12
        }

        for folder in folders:
            for name, number in months.items():
                if self._contains_token(folder, name):
                    return number

        return 0

    def _season(self, month):

        if month in (12, 1, 2):
            return "winter"

        if month in (3, 4, 5):
            return "spring"

        if month in (6, 7, 8):
            return "summer"

        if month in (9, 10, 11):
            return "fall"

        return ""

    def _station(self, text):

        if "station" in text or "fire hall" in text:
            return "fire_station"

        return ""

    def _row_media(self, row):

        if isinstance(row, dict):
            return row

        return {
            "id": row["id"],
            "media_id": row["id"],
            "filename": row["filename"],
            "path": row["path"],
            "media_type": row["media_type"]
        }

    def _media_with_context(self, media):

        if not isinstance(media, dict):
            return media

        media_id = self._to_int(media.get("id") or media.get("media_id"))

        if not media_id or not hasattr(self.db, "get_media_intelligence"):
            return media

        contextual = dict(media)

        try:
            intelligence = self.db.get_media_intelligence(media_id) or {}
        except Exception:
            intelligence = {}

        for key in ("normalized_scene", "incident_type", "primary_activity"):
            if not contextual.get(key) and intelligence.get(key):
                contextual[key] = intelligence.get(key)

        return contextual

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values or []:
            value = str(value or "").strip()

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique

    def _to_int(self, value):

        try:
            return int(value)
        except Exception:
            return 0
