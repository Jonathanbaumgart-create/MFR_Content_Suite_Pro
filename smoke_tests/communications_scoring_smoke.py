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
            "sha256": f"communications-scoring-hash-{index}"
        }
    )


def save_intelligence(db, media_id, values):

    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": values.get("normalized_scene", "community"),
            "incident_type": values.get("incident_type", "community_event"),
            "primary_activity": values.get("primary_activity", "community_outreach"),
            "apparatus_tags": values.get("apparatus_tags", []),
            "equipment_tags": values.get("equipment_tags", []),
            "ppe_tags": values.get("ppe_tags", []),
            "people_tags": values.get("people_tags", ["crew"]),
            "content_tags": values.get("content_tags", []),
            "content_themes": values.get("content_themes", []),
            "recommended_uses": values.get("recommended_uses", []),
            "search_text": values.get("search_text", ""),
            "intelligence_score": values.get("intelligence_score", 80),
            "source_model": "mock"
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()

            add_media(db, 1, "community_school_visit.jpg")
            save_intelligence(
                db,
                1,
                {
                    "normalized_scene": "public_education",
                    "incident_type": "public_education",
                    "primary_activity": "school_visit",
                    "apparatus_tags": ["engine"],
                    "equipment_tags": ["smoke_alarm"],
                    "ppe_tags": ["turnout_gear", "helmet"],
                    "people_tags": ["crew", "children"],
                    "content_tags": [
                        "community",
                        "children",
                        "public_education",
                        "fire_prevention",
                        "safety"
                    ],
                    "content_themes": ["community", "public_education"],
                    "recommended_uses": [
                        "community",
                        "public_education",
                        "facebook"
                    ],
                    "search_text": (
                        "community children school public education fire "
                        "prevention safety firefighters"
                    ),
                    "intelligence_score": 92
                }
            )

            add_media(db, 2, "equipment_closeup.jpg")
            save_intelligence(
                db,
                2,
                {
                    "normalized_scene": "station",
                    "incident_type": "equipment",
                    "primary_activity": "equipment_check",
                    "apparatus_tags": [],
                    "equipment_tags": ["hose"],
                    "ppe_tags": [],
                    "people_tags": [],
                    "content_tags": ["equipment"],
                    "content_themes": ["technical"],
                    "recommended_uses": ["website"],
                    "search_text": "hose equipment station",
                    "intelligence_score": 70
                }
            )

            from services.communications_memory_service import (
                CommunicationsMemoryService
            )
            from services.communications_reasoning_service import (
                CommunicationsReasoningService
            )
            from services.communications_scoring_service import (
                CommunicationsScoringService
            )

            service = CommunicationsScoringService(
                database=db,
                memory_service=CommunicationsMemoryService(database=db)
            )
            rebuilt = service.rebuild_missing()

            assert rebuilt["total"] == 2, rebuilt
            assert rebuilt["completed"] == 2, rebuilt

            scored = db.get_media_intelligence(1)

            assert scored["communications_score"] > 0, scored
            assert scored["community_engagement_score"] > 60, scored
            assert scored["public_education_value_score"] > 60, scored
            assert scored["trust_building_score"] > 50, scored
            assert isinstance(scored["platform_suitability"], dict), scored
            assert scored["suggested_campaigns"], scored
            assert scored["suggested_audience"], scored
            assert scored["suggested_platform"], scored
            assert scored["communications_reasoning"], scored

            page = db.get_intelligence_media_page(
                sort_by="communications_score",
                limit=2
            )
            assert page[0][1] == "community_school_visit.jpg", page

            reasoning = CommunicationsReasoningService(
                database=db
            )
            recommendation = reasoning.generate_recommendations(
                prompt="fire prevention week",
                limit=1
            )[0]
            media = recommendation["recommended_media"][0]

            assert media["media_id"] == 1, recommendation
            assert media["communications_score"] == scored["communications_score"], media
            assert any(
                "communications score" in item.lower()
                for item in recommendation["reasoning"]
            ), recommendation
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")

            from gui.photo_viewer import PhotoViewer

            viewer = object.__new__(PhotoViewer)
            viewer.intelligence = scored
            lines = PhotoViewer.communications_intelligence_lines(viewer)
            assert any("Overall Score:" in line for line in lines), lines
            assert any("Suggested Campaigns:" in line for line in lines), lines

        finally:
            os.chdir(original)

    print("communications_scoring smoke passed")


if __name__ == "__main__":
    main()
