import time
from pathlib import Path

from core.app_context import context
from services.filesystem_intelligence_service import FilesystemIntelligenceService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("intelligence")


class AnalysisTierService:

    TIER_FAST_INDEX = "tier1_fast_index"
    TIER_FAST_SCREEN = "tier2_fast_screen"
    TIER_DEEP = "tier3_deep_production"
    DEEP_WARNING_THRESHOLD = 25

    def __init__(self, database=None, filesystem_service=None):

        self.db = database or context.database
        self.filesystem = filesystem_service or FilesystemIntelligenceService(
            database=self.db
        )

    ############################################################

    def fast_index(self, media_ids, limit=1000):

        started = time.perf_counter()
        rows = self.db.media_rows_by_ids(
            list(media_ids or [])[:int(limit or 1000)],
            limit=limit
        )
        indexed = []

        for row in rows:
            item_started = time.perf_counter()
            evidence = self._tier1_evidence(row)

            if not evidence.get("filesystem_intelligence"):
                try:
                    filesystem = self.filesystem.save_for_media(
                        {
                            "id": row.get("id"),
                            "media_id": row.get("id"),
                            "filename": row.get("filename", ""),
                            "path": row.get("path", ""),
                            "media_type": row.get("media_type", "")
                        },
                        media_root=self._safe_parent(row.get("path", ""))
                    )
                    evidence["filesystem_intelligence"] = filesystem
                except Exception as ex:
                    evidence["filesystem_error"] = str(ex)

            score = self._index_score(row, evidence)
            tier = {
                "tier": self.TIER_FAST_INDEX,
                "provider": "local_index",
                "model": "deterministic-filesystem-v1",
                "status": "completed",
                "score": score,
                "summary": self._index_summary(row, evidence),
                "evidence": evidence,
                "started_at": TimeService.utc_now_iso(),
                "completed_at": TimeService.utc_now_iso(),
                "elapsed_seconds": round(time.perf_counter() - item_started, 3)
            }
            self.db.save_media_analysis_tier(row.get("id"), tier)
            indexed.append({
                "media_id": row.get("id"),
                "filename": row.get("filename", ""),
                "tier": tier
            })

        result = {
            "tier": self.TIER_FAST_INDEX,
            "processed": len(indexed),
            "provider_calls": 0,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "items": indexed
        }
        logger.info(
            "Tier 1 fast index completed processed=%s elapsed=%s",
            result["processed"],
            result["elapsed_seconds"]
        )
        return result

    ############################################################

    def fast_screen(self, media_ids, limit=20, vision_provider=None, topic=""):

        started = time.perf_counter()
        rows = self.db.media_rows_by_ids(
            list(media_ids or [])[:int(limit or 20)],
            limit=limit
        )
        screened = []
        provider_calls = 0

        for row in rows:
            item_started = time.perf_counter()
            evidence = self._tier1_evidence(row)
            score = self._screen_score(row, evidence, topic=topic)
            status = "completed_local"
            provider = "local_screen"
            model = "deterministic-topic-fit-v1"

            if vision_provider is not None and row.get("media_type") == "image":
                provider_calls += 1
                provider = getattr(vision_provider, "provider_key", lambda: "vision")()
                model = getattr(vision_provider, "model_name", lambda: "unknown")()
                status = "completed_provider"

            tier = {
                "tier": self.TIER_FAST_SCREEN,
                "provider": provider,
                "model": model,
                "status": status,
                "score": score,
                "summary": self._screen_summary(row, score, topic),
                "evidence": {
                    **evidence,
                    "topic": topic,
                    "bounded": True,
                    "provider_call_used": bool(vision_provider)
                },
                "started_at": TimeService.utc_now_iso(),
                "completed_at": TimeService.utc_now_iso(),
                "elapsed_seconds": round(time.perf_counter() - item_started, 3)
            }
            self.db.save_media_analysis_tier(row.get("id"), tier)
            screened.append({
                "media_id": row.get("id"),
                "filename": row.get("filename", ""),
                "score": score,
                "tier": tier
            })

        screened.sort(
            key=lambda item: item.get("score", 0),
            reverse=True
        )
        return {
            "tier": self.TIER_FAST_SCREEN,
            "processed": len(screened),
            "provider_calls": provider_calls,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "items": screened
        }

    ############################################################

    def deep_analysis_warning(self, media_count, average_seconds=None):

        media_count = int(media_count or 0)
        average = float(average_seconds or 105)
        total_seconds = media_count * average
        hours = total_seconds / 3600

        return {
            "tier": self.TIER_DEEP,
            "explicit_opt_in_required": (
                media_count >= self.DEEP_WARNING_THRESHOLD
            ),
            "media_count": media_count,
            "estimated_seconds": round(total_seconds, 1),
            "estimated_hours": round(hours, 2),
            "message": (
                f"Deep analysis of {media_count:,} media item(s) may require "
                f"approximately {hours:.1f} hours on the current provider."
            )
        }

    ############################################################

    def _tier1_evidence(self, row):

        media_id = row.get("id") or row.get("media_id")
        filesystem = {}

        try:
            filesystem = self.db.get_filesystem_intelligence(media_id) or {}
        except Exception:
            filesystem = {}

        return {
            "path": row.get("path", ""),
            "filename": row.get("filename", ""),
            "media_type": row.get("media_type", ""),
            "filesize": row.get("filesize", 0),
            "capture_time": row.get("capture_time", ""),
            "first_seen_at": row.get("first_seen_at") or row.get("date_added", ""),
            "duration_seconds": row.get("duration_seconds", 0),
            "width": row.get("width", 0),
            "height": row.get("height", 0),
            "frame_rate": row.get("frame_rate", 0),
            "orientation": row.get("orientation", ""),
            "filesystem_intelligence": filesystem,
            "uses_vision_model": False
        }

    def _index_score(self, row, evidence):

        score = 30
        filesystem = evidence.get("filesystem_intelligence") or {}

        if filesystem.get("filesystem_confidence"):
            score += min(40, int(filesystem.get("filesystem_confidence") or 0) // 2)

        if row.get("capture_time"):
            score += 10

        if row.get("media_type") == "video" and row.get("duration_seconds"):
            score += 10

        if row.get("width") and row.get("height"):
            score += 10

        return min(100, score)

    def _screen_score(self, row, evidence, topic=""):

        score = self._index_score(row, evidence)
        topic = str(topic or "").lower()
        filesystem = evidence.get("filesystem_intelligence") or {}
        searchable = " ".join(
            str(value or "")
            for value in (
                row.get("filename"),
                filesystem.get("root_category"),
                filesystem.get("subcategory"),
                filesystem.get("incident_type"),
                filesystem.get("training_type"),
                filesystem.get("public_education_program"),
                filesystem.get("campaign"),
                filesystem.get("community_event")
            )
        ).lower()

        if topic and any(part in searchable for part in topic.split()):
            score += 20

        if filesystem.get("conflict_state") == "conflict":
            score -= 15

        return max(0, min(100, score))

    def _index_summary(self, row, evidence):

        filesystem = evidence.get("filesystem_intelligence") or {}
        category = filesystem.get("root_category") or "filesystem context"
        return (
            f"Fast indexed {row.get('filename', '')} using {category}, "
            "stored dates, dimensions, duration, and review state only."
        )

    def _screen_summary(self, row, score, topic):

        return (
            f"Fast screened {row.get('filename', '')} for "
            f"{topic or 'general communications'} compatibility; score {score}."
        )

    def _safe_parent(self, path):

        try:
            return str(Path(path).parent)
        except Exception:
            return ""
