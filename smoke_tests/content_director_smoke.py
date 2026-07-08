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
            "sha256": f"content-director-hash-{index}"
        }
    )


def save_intelligence(db, media_id, values):

    intelligence = {
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

    db.save_media_intelligence(
        media_id,
        intelligence
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:

            db = DatabaseManager()

            add_media(db, 1, "recruitment_training.jpg")
            save_intelligence(
                db,
                1,
                {
                    "normalized_scene": "training",
                    "incident_type": "training",
                    "primary_activity": "training",
                    "apparatus_tags": ["engine"],
                    "equipment_tags": ["hose", "scba"],
                    "ppe_tags": ["turnout_gear", "helmet"],
                    "content_tags": ["training", "recruitment", "crew"],
                    "content_themes": ["recruitment", "technical_training"],
                    "recommended_uses": ["recruitment", "training", "social_media"],
                    "search_text": "training recruitment crew engine hose scba",
                    "intelligence_score": 92
                }
            )

            add_media(db, 2, "community_event.jpg")
            save_intelligence(
                db,
                2,
                {
                    "normalized_scene": "community",
                    "incident_type": "community_event",
                    "primary_activity": "community_outreach",
                    "content_tags": ["community", "public_education"],
                    "content_themes": ["community", "public_education"],
                    "recommended_uses": ["community_outreach", "social_media"],
                    "search_text": "community public education open house",
                    "intelligence_score": 88
                }
            )

            from services.content_director_service import ContentDirectorService

            service = ContentDirectorService(db)

            assert "heat_warning" in service.interpret_prompt("heat warning")
            assert "recruitment" in service.interpret_prompt(
                "need a recruitment post"
            )
            assert "fire_prevention" in service.interpret_prompt(
                "fire prevention week"
            )
            assert "storm_safety" in service.interpret_prompt(
                "storm coming tonight"
            )
            assert "smoke_alarm" in service.interpret_prompt(
                "show something about smoke alarms"
            )

            result = service.recommend(
                "need a recruitment post",
                limit=3
            )

            assert result["opportunity_types"] == ["recruitment"], result
            assert result["recommendations"], result

            top = result["recommendations"][0]

            assert top["media_id"] == 1, top
            assert top["path"].endswith("recruitment_training.jpg"), top
            assert top["reason"], top
            assert "captions" in top, top
            assert top["captions"]["facebook_caption"], top
            assert top["captions"]["instagram_caption"], top
            assert top["captions"]["hashtags"], top
            assert not hasattr(service, "vision")
            assert not hasattr(service, "ai")

            candidates = db.content_director_candidates(limit=10)
            assert candidates[0]["filename"] == "recruitment_training.jpg"
            assert isinstance(candidates[0]["content_tags"], list), candidates

        finally:
            os.chdir(original)

    print("content_director smoke passed")


if __name__ == "__main__":
    main()
