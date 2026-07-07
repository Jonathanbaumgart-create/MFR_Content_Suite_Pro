from pathlib import Path
from tempfile import TemporaryDirectory
import os
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db_manager import DatabaseManager


def add_media(db, index, filename):

    db.add_media(
        {
            "filename": filename,
            "path": str(Path("library") / filename),
            "extension": ".jpg",
            "type": "image",
            "size": 100 + index,
            "sha256": f"hash-{index}"
        }
    )


def save_intelligence(db, media_id, incident, equipment, use, activity, score):

    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": "emergency_response",
            "incident_type": incident,
            "primary_activity": activity,
            "apparatus_tags": ["engine"],
            "equipment_tags": equipment,
            "ppe_tags": ["turnout_gear"],
            "people_tags": ["crew"],
            "content_tags": [
                incident,
                activity
            ] + equipment,
            "content_themes": ["recruitment"],
            "recommended_uses": use,
            "search_text": " ".join(
                [incident, activity] + equipment + use
            ),
            "intelligence_score": score,
            "source_model": "mock"
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            from services.intelligence_explorer_service import (
                IntelligenceExplorerService
            )
            service = IntelligenceExplorerService(db)

            add_media(db, 1, "alpha.jpg")
            save_intelligence(
                db,
                1,
                "structure_fire",
                ["scba", "hose"],
                ["recruitment"],
                "interior_attack",
                90
            )

            add_media(db, 2, "bravo.jpg")
            save_intelligence(
                db,
                2,
                "grass_fire",
                ["hose"],
                ["public_education"],
                "wildland_attack",
                70
            )

            add_media(db, 3, "charlie.jpg")
            save_intelligence(
                db,
                3,
                "structure_fire",
                ["scba"],
                ["training"],
                "interior_attack",
                80
            )

            counts = service.filter_counts()
            assert ("structure_fire", 2) in counts["incident_type"], counts
            assert ("scba", 2) in counts["equipment_tags"], counts
            assert ("recruitment", 1) in counts["recommended_uses"], counts

            filters = {
                "incident_type": ["structure_fire"],
                "equipment_tags": ["scba"]
            }

            assert service.media_count(filters) == 2

            page = service.media_page(
                filters=filters,
                sort_by="intelligence_score",
                limit=1,
                offset=0
            )

            assert len(page) == 1, page
            assert page[0][1] == "alpha.jpg", page

            page = service.media_page(
                filters={
                    "incident_type": ["structure_fire"],
                    "recommended_uses": ["recruitment"],
                    "primary_activity": ["interior_attack"]
                },
                sort_by="filename",
                limit=10,
                offset=0
            )

            assert len(page) == 1, page
            assert page[0][1] == "alpha.jpg", page

        finally:
            os.chdir(original)

    print("intelligence_explorer smoke passed")


if __name__ == "__main__":
    main()
