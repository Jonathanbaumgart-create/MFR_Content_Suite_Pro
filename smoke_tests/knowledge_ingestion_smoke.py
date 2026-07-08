from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager


def create_docx(path, lines):

    text_nodes = "".join(
        (
            "<w:p><w:r><w:t>" +
            line.replace("&", "&amp;") +
            "</w:t></w:r></w:p>"
        )
        for line in lines
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{text_nodes}</w:body></w:document>"
    )

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>'
        )
        archive.writestr(
            "word/document.xml",
            document
        )


def create_pdf(path, lines):

    text = "\n".join(lines)
    content = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        "4 0 obj << /Length 120 >> stream\n"
        f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET\n"
        "endstream endobj\n"
        "xref\n0 5\n0000000000 65535 f \n"
        "trailer << /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
    )
    path.write_bytes(content.encode("latin-1"))


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        root = Path(folder)
        os.chdir(root)

        try:
            db = DatabaseManager()

            from services.knowledge_ingestion_service import (
                KnowledgeIngestionService
            )
            from services.knowledge_service import KnowledgeService

            knowledge = KnowledgeService(db)
            ingestion = KnowledgeIngestionService(
                db,
                knowledge_service=knowledge
            )

            knowledge.save_profile(
                {
                    "mission_statement": "Protect the community."
                }
            )
            knowledge.save_item(
                "programs",
                {
                    "name": "Duplicate Program",
                    "category": "programs",
                    "description": "Existing duplicate.",
                    "tags": ["community"],
                    "active": True
                }
            )
            knowledge.save_item(
                "apparatus",
                {
                    "name": "Conflict Unit",
                    "category": "engine",
                    "description": "Existing engine.",
                    "tags": ["engine"],
                    "active": True
                }
            )

            txt = root / "knowledge.txt"
            txt.write_text(
                "\n".join(
                    [
                        "Programs: Smoke School - Public education for smoke alarm safety Tags: public_education, smoke_alarm",
                        "Community Partners: Morden Schools - Partner for classroom safety visits Tags: school, public_education",
                        "Mission Statement: Serve with courage and care."
                    ]
                ),
                encoding="utf-8"
            )

            docx = root / "apparatus.docx"
            create_docx(
                docx,
                [
                    "Apparatus: Rescue 2 - Emergency response rescue unit Tags: apparatus, rescue",
                    "Annual Events: Open House - Community fire hall event Tags: community, event"
                ]
            )

            pdf = root / "response.pdf"
            create_pdf(
                pdf,
                [
                    "Response Area: Rural Morden - Rural response area Tags: response_area",
                    "Stations: Training Grounds - Training location Tags: training, station"
                ]
            )

            duplicate = root / "duplicate.txt"
            duplicate.write_text(
                "Programs: Duplicate Program - Existing duplicate. Tags: community",
                encoding="utf-8"
            )

            conflict = root / "conflict.txt"
            conflict.write_text(
                "Apparatus: Conflict Unit - Listed as tanker in a new document Tags: tanker",
                encoding="utf-8"
            )

            csv_file = root / "partners.csv"
            csv_file.write_text(
                "\n".join(
                    [
                        "type,name,description,tags",
                        "Community Partners,Western School Division,School partner for public education,school public_education"
                    ]
                ),
                encoding="utf-8"
            )

            result = ingestion.import_documents(
                [
                    txt,
                    docx,
                    pdf,
                    duplicate,
                    conflict,
                    csv_file
                ]
            )
            summary = result["summary"]

            assert summary["documents"] == 6, summary
            assert summary["imported"] >= 5, summary
            assert summary["duplicates"] >= 1, summary
            assert summary["conflicts"] >= 2, summary
            assert summary["new_programs"] >= 1, summary
            assert summary["new_apparatus"] >= 1, summary
            assert summary["new_events"] >= 1, summary
            assert summary["new_partners"] >= 1, summary
            assert summary["new_locations"] >= 1, summary

            applied = ingestion.apply_import(result)
            assert applied["applied"] == summary["imported"], applied
            assert applied["skipped"] >= summary["duplicates"], applied

            stats = knowledge.statistics()
            assert stats["documents_imported"] == 6, stats
            assert stats["programs"] >= 3, stats
            assert stats["apparatus"] >= 2, stats
            assert stats["events"] >= 2, stats
            assert stats["partners"] >= 2, stats
            assert stats["locations"] >= 3, stats
            assert stats["knowledge_completeness_score"] == 100, stats

            duplicate_result = ingestion.import_documents([txt])
            assert duplicate_result["summary"]["duplicate_documents"] == 1

            names = [
                item["name"]
                for item in knowledge.items("programs")
            ]
            assert "Smoke School" in names, names

        finally:
            os.chdir(original)

    print("knowledge_ingestion smoke passed")


if __name__ == "__main__":
    main()
