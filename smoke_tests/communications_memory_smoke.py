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
            "sha256": f"communications-memory-hash-{index}"
        }
    )


def save_intelligence(db, media_id):

    db.save_media_intelligence(
        media_id,
        {
            "normalized_scene": "training",
            "incident_type": "training",
            "primary_activity": "recruitment_training",
            "apparatus_tags": ["engine"],
            "equipment_tags": ["hose"],
            "ppe_tags": ["helmet"],
            "people_tags": ["crew"],
            "content_tags": ["recruitment", "community", "training"],
            "content_themes": ["recruitment"],
            "recommended_uses": ["recruitment", "social_media"],
            "search_text": "recruitment community training",
            "intelligence_score": 93,
            "source_model": "mock"
        }
    )


def deterministic_writing_service():

    from services.writing_service import WritingService

    return WritingService(
        config={
            "default_provider": "deterministic",
            "fallback_provider": "deterministic",
            "providers": {
                "deterministic": {
                    "model": "deterministic-template"
                }
            }
        }
    )


def main():

    original = Path.cwd()

    with TemporaryDirectory() as folder:

        os.chdir(folder)

        try:
            db = DatabaseManager()
            add_media(db, 1, "training.jpg")
            save_intelligence(db, 1)

            from services.communications_memory_service import (
                CommunicationsMemoryService
            )
            from services.social_import_service import SocialImportService

            memory = CommunicationsMemoryService(db)
            importer = SocialImportService(memory)

            payload = {
                "posts": [
                    {
                        "platform": "facebook",
                        "created_at": "2026-06-01T09:30:00",
                        "caption": (
                            "Join our crew for training night! "
                            "Serve your community with Morden Fire & Rescue. "
                            "Learn more today. \U0001fa96 \U0001f91d "
                            "#MordenFireRescue #Recruitment #Training"
                        ),
                        "media_ids": [1],
                        "campaign": "Recruitment",
                        "writing_style": "recruitment",
                        "opportunity_type": "recruitment",
                        "season": "summer"
                    },
                    {
                        "platform": "instagram",
                        "created_at": "2026-06-02T18:15:00",
                        "caption": (
                            "Smoke alarms save lives. Check yours tonight! "
                            "\u2705 \U0001f3e0 #FireSafety #SmokeAlarms"
                        ),
                        "campaign": "Fire Prevention",
                        "writing_style": "educational",
                        "opportunity_type": "smoke_alarm_reminder"
                    },
                    {
                        "platform": "facebook",
                        "created_at": "2026-06-01T09:30:00",
                        "caption": (
                            "Join our crew for training night! "
                            "Serve your community with Morden Fire & Rescue. "
                            "Learn more today. \U0001fa96 \U0001f91d "
                            "#MordenFireRescue #Recruitment #Training"
                        ),
                        "media_ids": [1],
                        "campaign": "Recruitment"
                    }
                ]
            }

            summary = importer.import_payload(
                payload,
                platform="facebook",
                source="smoke"
            )

            assert summary["posts_seen"] == 3, summary
            assert summary["posts_imported"] == 2, summary
            assert summary["duplicate_posts"] == 1, summary
            assert summary["media_linked"] == 1, summary
            assert "Recruitment" in summary["campaigns_discovered"], summary
            assert "#Recruitment" in summary["hashtags_discovered"], summary
            assert "recruitment" in summary["writing_styles_discovered"], summary

            stats = memory.statistics()
            assert stats["total_posts"] == 2, stats
            assert stats["campaigns"] == 2, stats
            assert stats["platforms"] >= 1, stats
            assert stats["writing_statistics"]["average_caption_length"] > 0, stats
            assert stats["writing_statistics"]["average_hashtags"] > 0, stats
            assert stats["writing_statistics"]["average_emojis"] > 0, stats
            assert stats["writing_statistics"]["recruitment_rate"] > 0, stats
            assert stats["top_hashtags"], stats

            media_memory = memory.media_memory(1)
            assert media_memory["posted_before"] is True, media_memory
            assert media_memory["post_count"] == 1, media_memory
            assert "Recruitment" in media_memory["campaigns"], media_memory

            results = memory.search("Smoke", limit=10)
            assert len(results) == 1, results
            assert results[0]["campaign"] == "Fire Prevention", results

            from services.communications_director import CommunicationsDirector
            from services.communications_reasoning_service import (
                CommunicationsReasoningService
            )
            from services.content_generation_service import (
                ContentGenerationService
            )
            from services.knowledge_service import KnowledgeService

            director = CommunicationsDirector(db)
            knowledge = KnowledgeService(db)
            reasoning = CommunicationsReasoningService(
                db,
                director=director,
                knowledge_service=knowledge,
                memory_service=memory
            )
            recommendations = reasoning.generate_recommendations(
                prompt="need a recruitment post",
                limit=1
            )

            assert recommendations, "expected recommendation"
            top_media = recommendations[0]["recommended_media"][0]
            assert top_media["posted_before"] is True, top_media
            assert "posted" in " ".join(recommendations[0]["reasoning"]).lower()

            generator = ContentGenerationService(
                db,
                knowledge_service=knowledge,
                writing_service=deterministic_writing_service(),
                memory_service=memory
            )
            package = generator.generate_package(
                recommendations[0]
            )

            assert package["facebook_caption"], package
            assert any(
                "Communications Memory" in line
                for line in package["reasoning"]
            ), package
            assert not hasattr(memory, "vision")
            assert not hasattr(importer, "vision")
            assert not hasattr(generator, "vision")

        finally:
            os.chdir(original)

    print("communications_memory smoke passed")


if __name__ == "__main__":
    main()
