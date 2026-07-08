import csv
import hashlib
import re
import zipfile
from html import unescape
from pathlib import Path
from xml.etree import ElementTree

from core.app_context import context
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class KnowledgeIngestionService:

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".docx",
        ".txt",
        ".md",
        ".markdown",
        ".rtf",
        ".csv"
    }

    SECTION_TABLES = {
        "program": "programs",
        "programs": "programs",
        "public education program": "programs",
        "public education programs": "programs",
        "apparatus": "apparatus",
        "truck": "apparatus",
        "engine": "apparatus",
        "station": "locations",
        "stations": "locations",
        "location": "locations",
        "locations": "locations",
        "response area": "response_area",
        "response areas": "response_area",
        "mutual aid partner": "community_partners",
        "mutual aid partners": "community_partners",
        "community partner": "community_partners",
        "community partners": "community_partners",
        "school": "community_partners",
        "schools": "community_partners",
        "annual event": "annual_events",
        "annual events": "annual_events",
        "event": "annual_events",
        "events": "annual_events",
        "safety campaign": "annual_events",
        "safety campaigns": "annual_events"
    }

    PROFILE_KEYS = {
        "mission": "mission_statement",
        "mission statement": "mission_statement",
        "core values": "core_values",
        "values": "core_values",
        "preferred writing style": "preferred_writing_style",
        "writing style": "preferred_writing_style",
        "department terminology": "department_terminology",
        "terminology": "department_terminology",
        "standard abbreviations": "standard_abbreviations",
        "abbreviations": "standard_abbreviations",
        "common hashtags": "common_hashtags",
        "hashtags": "common_hashtags",
        "recruitment information": "recruitment_information",
        "emergency response capabilities": "emergency_response_capabilities",
        "capabilities": "emergency_response_capabilities"
    }

    def __init__(self, database=None, knowledge_service=None):

        self.db = database or context.database
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )

    ############################################################

    def import_documents(self, paths):

        candidates = []
        documents = []
        skipped = []

        for path in paths:
            path = Path(path)
            extension = path.suffix.lower()

            if extension not in self.SUPPORTED_EXTENSIONS:
                skipped.append(
                    {
                        "path": str(path),
                        "reason": "unsupported file type"
                    }
                )
                continue

            try:
                text = self.extract_text(path)
                sha256 = self.file_hash(path)
                document = {
                    "path": str(path),
                    "filename": path.name,
                    "sha256": sha256,
                    "duplicate_document": self.db.knowledge_document_exists(sha256)
                }
                documents.append(document)
                candidates.extend(
                    self.extract_candidates(
                        text,
                        source=path.name
                    )
                )

            except Exception as ex:
                skipped.append(
                    {
                        "path": str(path),
                        "reason": str(ex)
                    }
                )
                logger.error(
                    "Knowledge document import failed path=%s",
                    path,
                    exc_info=(
                        type(ex),
                        ex,
                        ex.__traceback__
                    )
                )

        reviewed = self.review_candidates(candidates)
        summary = self.import_summary(
            reviewed,
            documents,
            skipped
        )

        logger.info(
            "Knowledge import reviewed documents=%s candidates=%s imported=%s duplicates=%s conflicts=%s",
            len(documents),
            len(reviewed),
            summary["imported"],
            summary["duplicates"],
            summary["conflicts"]
        )

        return {
            "documents": documents,
            "records": reviewed,
            "summary": summary,
            "skipped_files": skipped
        }

    ############################################################

    def apply_import(self, import_result):

        applied = 0
        skipped = 0

        for record in import_result.get("records", []):

            if record["status"] != "new":
                skipped += 1
                continue

            item = record["item"]

            if record["table"] == "department_profile":
                self.db.save_department_profile_value(
                    item["key"],
                    item["value"]
                )
            else:
                self.db.save_knowledge_item(
                    record["table"],
                    item
                )

            applied += 1

        for document in import_result.get("documents", []):
            self.db.save_knowledge_document(
                {
                    "path": document["path"],
                    "filename": document["filename"],
                    "sha256": document["sha256"],
                    "summary": import_result.get("summary", {})
                }
            )

        logger.info(
            "Knowledge import applied applied=%s skipped=%s",
            applied,
            skipped
        )

        return {
            "applied": applied,
            "skipped": skipped
        }

    ############################################################

    def extract_text(self, path):

        extension = path.suffix.lower()

        if extension in (".txt", ".md", ".markdown"):
            return path.read_text(encoding="utf-8", errors="ignore")

        if extension == ".rtf":
            return self.extract_rtf(path)

        if extension == ".csv":
            return self.extract_csv_text(path)

        if extension == ".docx":
            return self.extract_docx(path)

        if extension == ".pdf":
            return self.extract_pdf(path)

        raise ValueError("Unsupported file type")

    ############################################################

    def extract_docx(self, path):

        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")

        root = ElementTree.fromstring(xml)
        namespace = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        }
        paragraphs = []

        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(
                node.text or ""
                for node in paragraph.findall(".//w:t", namespace)
            )

            if text.strip():
                paragraphs.append(text.strip())

        return "\n".join(paragraphs)

    ############################################################

    def extract_pdf(self, path):

        data = path.read_bytes()
        text = data.decode("latin-1", errors="ignore")
        chunks = []

        for match in re.findall(r"\((.*?)\)", text, flags=re.S):
            value = match.replace("\\(", "(").replace("\\)", ")")

            if any(character.isalpha() for character in value):
                chunks.append(value)

        if chunks:
            return "\n".join(chunks)

        return re.sub(
            r"[^A-Za-z0-9#:\-_,.\n ]+",
            " ",
            text
        )

    ############################################################

    def extract_rtf(self, path):

        text = path.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
        text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
        text = text.replace("{", " ").replace("}", " ")

        return re.sub(r"\s+", " ", text)

    ############################################################

    def extract_csv_text(self, path):

        lines = []

        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.DictReader(handle)

            if reader.fieldnames:
                for row in reader:
                    kind = row.get("type") or row.get("table") or row.get("category")
                    name = row.get("name") or row.get("title")
                    description = row.get("description") or row.get("notes") or ""
                    tags = row.get("tags") or ""

                    if kind and name:
                        lines.append(
                            f"{kind}: {name} - {description} Tags: {tags}"
                        )

        if lines:
            return "\n".join(lines)

        return path.read_text(encoding="utf-8", errors="ignore")

    ############################################################

    def extract_candidates(self, text, source=""):

        candidates = []
        normalized = text.replace("\r", "\n")

        for raw_line in normalized.split("\n"):
            line = raw_line.strip(" -\t")

            if not line:
                continue

            candidates.extend(
                self.extract_line_candidates(
                    line,
                    source
                )
            )

        candidates.extend(
            self.extract_known_names(
                normalized,
                source
            )
        )

        return self.unique_candidates(candidates)

    ############################################################

    def extract_line_candidates(self, line, source):

        candidates = []
        match = re.match(r"^([^:]{3,80}):\s*(.+)$", line)

        if not match:
            return candidates

        label = self.clean_label(match.group(1))
        value = match.group(2).strip()
        profile_key = self.PROFILE_KEYS.get(label)

        if profile_key:
            candidates.append(
                {
                    "table": "department_profile",
                    "item": {
                        "key": profile_key,
                        "value": value
                    },
                    "source": source
                }
            )
            return candidates

        table = self.SECTION_TABLES.get(label)

        if not table:
            table = self.infer_table(label + " " + value)

        if not table:
            return candidates

        for part in re.split(r";|\|", value):
            item = self.parse_item(
                part,
                label
            )

            if item["name"]:
                candidates.append(
                    {
                        "table": table,
                        "item": item,
                        "source": source
                    }
                )

        return candidates

    ############################################################

    def extract_known_names(self, text, source):

        known = (
            ("programs", "Hydrant Heroes", "community public_education school"),
            ("programs", "Travelling Sparky", "public_education fire_prevention school"),
            ("annual_events", "Fire Prevention Week", "fire_prevention public_education october")
        )
        candidates = []
        lower = text.lower()

        for table, name, tags in known:

            if name.lower() not in lower:
                continue

            candidates.append(
                {
                    "table": table,
                    "item": {
                        "name": name,
                        "category": tags.split()[0],
                        "description": f"Imported mention of {name}.",
                        "tags": tags.split(),
                        "active": True
                    },
                    "source": source
                }
            )

        return candidates

    ############################################################

    def parse_item(self, text, label):

        text = text.strip(" -")
        tags = []
        tag_match = re.search(r"\bTags?:\s*(.+)$", text, flags=re.I)

        if tag_match:
            tags = [
                self.token(item)
                for item in re.split(r",|\s", tag_match.group(1))
                if item.strip()
            ]
            text = text[:tag_match.start()].strip()

        if " - " in text:
            name, description = text.split(" - ", 1)
        elif " -- " in text:
            name, description = text.split(" -- ", 1)
        else:
            name, description = text, ""

        category = self.clean_label(label)

        if not tags:
            tags = self.tags_for_text(
                f"{category} {name} {description}"
            )

        return {
            "name": name.strip(),
            "category": category,
            "description": description.strip(),
            "tags": tags,
            "active": True
        }

    ############################################################

    def review_candidates(self, candidates):

        reviewed = []

        for candidate in candidates:
            status, existing = self.classify_candidate(candidate)
            reviewed.append(
                {
                    "table": candidate["table"],
                    "item": candidate["item"],
                    "source": candidate.get("source", ""),
                    "status": status,
                    "existing": existing
                }
            )

            if status in ("duplicate", "conflicting"):
                logger.info(
                    "Knowledge import %s table=%s name=%s source=%s",
                    status,
                    candidate["table"],
                    self.item_name(candidate),
                    candidate.get("source", "")
                )

        return reviewed

    ############################################################

    def classify_candidate(self, candidate):

        if candidate["table"] == "department_profile":
            profile = self.db.department_profile()
            key = candidate["item"]["key"]
            value = candidate["item"]["value"]

            if key not in profile:
                return "new", None

            if self.same_text(profile[key], value):
                return "duplicate", {
                    "key": key,
                    "value": profile[key]
                }

            return "conflicting", {
                "key": key,
                "value": profile[key]
            }

        existing_items = self.db.knowledge_items(candidate["table"])
        item = candidate["item"]

        for existing in existing_items:

            if self.token(existing["name"]) != self.token(item["name"]):
                continue

            if self.same_item(existing, item):
                return "duplicate", existing

            if self.token(existing.get("category")) == self.token(item.get("category")):
                return "updated", existing

            return "conflicting", existing

        return "new", None

    ############################################################

    def import_summary(self, records, documents, skipped):

        summary = {
            "imported": sum(1 for item in records if item["status"] == "new"),
            "skipped": len(skipped) + sum(1 for item in records if item["status"] != "new"),
            "duplicates": sum(1 for item in records if item["status"] == "duplicate"),
            "conflicts": sum(1 for item in records if item["status"] == "conflicting"),
            "updated": sum(1 for item in records if item["status"] == "updated"),
            "new_programs": self.count_new(records, "programs"),
            "new_apparatus": self.count_new(records, "apparatus"),
            "new_events": self.count_new(records, "annual_events"),
            "new_partners": self.count_new(records, "community_partners"),
            "new_locations": self.count_new(records, "locations"),
            "documents": len(documents),
            "duplicate_documents": sum(
                1
                for document in documents
                if document.get("duplicate_document")
            )
        }

        return summary

    ############################################################

    def count_new(self, records, table):

        return sum(
            1
            for item in records
            if item["table"] == table and item["status"] == "new"
        )

    ############################################################

    def file_hash(self, path):

        digest = hashlib.sha256()

        with path.open("rb") as handle:

            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()

    ############################################################

    def infer_table(self, text):

        text = text.lower()

        if any(term in text for term in ("apparatus", "engine", "rescue", "tanker", "ladder")):
            return "apparatus"

        if any(term in text for term in ("program", "sparky", "hydrant heroes", "education")):
            return "programs"

        if any(term in text for term in ("event", "week", "campaign")):
            return "annual_events"

        if any(term in text for term in ("station", "hall", "location")):
            return "locations"

        if any(term in text for term in ("response area", "district")):
            return "response_area"

        if any(term in text for term in ("partner", "school", "mutual aid")):
            return "community_partners"

        return None

    ############################################################

    def tags_for_text(self, text):

        text = text.lower()
        tags = []

        for term in (
            "community",
            "public_education",
            "fire_prevention",
            "recruitment",
            "training",
            "apparatus",
            "engine",
            "school",
            "safety",
            "response_area",
            "mutual_aid"
        ):

            if term.replace("_", " ") in text or term in text:
                tags.append(term)

        return tags

    ############################################################

    def unique_candidates(self, candidates):

        unique = []
        seen = set()

        for candidate in candidates:
            key = (
                candidate["table"],
                self.item_name(candidate).lower()
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(candidate)

        return unique

    ############################################################

    def same_item(self, existing, imported):

        return (
            self.same_text(existing.get("category"), imported.get("category")) and
            self.same_text(existing.get("description"), imported.get("description")) and
            set(existing.get("tags") or []) == set(imported.get("tags") or [])
        )

    ############################################################

    def item_name(self, candidate):

        item = candidate["item"]

        return item.get("name") or item.get("key") or ""

    ############################################################

    def same_text(self, first, second):

        return self.token(first) == self.token(second)

    ############################################################

    def clean_label(self, value):

        return unescape(str(value or "")).strip().lower().replace(
            "_",
            " "
        )

    ############################################################

    def token(self, value):

        return re.sub(
            r"\s+",
            " ",
            str(value or "").strip().lower()
        )
