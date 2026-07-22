import hashlib
import json
from datetime import timedelta

from core.app_context import context
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class RecommendationFreshnessService:
    """Centralized recommendation identity, exposure, and rotation policy."""

    EXACT_COOLDOWN_DAYS = 3
    EVENT_ANGLE_COOLDOWN_DAYS = 5
    MEDIA_COOLDOWN_DAYS = 2

    def __init__(self, database=None):

        self.db = database or context.database

    ############################################################

    def fingerprint(self, package, source_opportunity_id=""):

        package = package or {}
        media_ids = self.media_ids(package)
        angle = self._angle(package)
        payload = {
            "event_id": self.event_id(package),
            "media_ids": media_ids,
            "objective": self._objective(package),
            "narrative_angle": angle,
            "teaching_point": self._teaching_point(package),
            "platform_package_type": self._platform_package_type(package),
            "campaign": self._campaign(package),
            "program": self._program(package),
            "source_opportunity_id": (
                source_opportunity_id
                or str(package.get("source_opportunity_id") or "")
                or str(package.get("option_id") or "")
                or str(package.get("recommendation_id") or "")
            )
        }
        identity = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]

    ############################################################

    def apply_to_packages(
        self,
        packages,
        page,
        limit=None,
        record=True,
        now=None,
        preserve_order=False
    ):

        packages = [dict(item or {}) for item in packages or []]
        if not packages:
            return []

        now = now or TimeService.utc_now()
        fingerprints = [
            self.fingerprint(package)
            for package in packages
        ]
        media_ids = sorted({
            media_id
            for package in packages
            for media_id in self.media_ids(package)
        })
        event_ids = sorted({
            event_id
            for event_id in (self.event_id(package) for package in packages)
            if event_id
        })
        exposures = self._exposure_index(
            self.db.recommendation_exposures(
                fingerprints=fingerprints,
                media_ids=media_ids,
                event_ids=event_ids,
                days=45,
                limit=1000
            )
        )

        scored = []
        for index, package in enumerate(packages):
            fingerprint = self.fingerprint(package)
            package["recommendation_fingerprint"] = fingerprint
            package["_freshness_source_order"] = index
            package["package_state"] = self.package_state(package)
            diagnostics = self.freshness_diagnostics(
                package,
                exposures,
                page=page,
                now=now
            )
            package["freshness"] = diagnostics
            package["freshness_penalty"] = diagnostics["total_penalty"]
            package["exposure_count"] = diagnostics["prior_exposure_count"]
            package["score_components"] = self.score_components(package)
            score = self.final_score(package, diagnostics)
            package["final_ranking_score"] = score
            scored.append((score, package))

        if preserve_order:
            scored.sort(
                key=lambda item: (
                    int(item[1].get("freshness_penalty") or 0),
                    -self._state_weight(item[1].get("package_state")),
                    int(item[1].get("_freshness_source_order") or 0)
                )
            )
        else:
            scored.sort(
                key=lambda item: (
                    item[0],
                    -int(item[1].get("freshness_penalty") or 0),
                    -int(item[1].get("exposure_count") or 0),
                    self._state_weight(item[1].get("package_state")),
                    int(item[1].get("confidence") or 0)
                ),
                reverse=True
            )
        ranked = self._diverse([item[1] for item in scored], limit)
        for package in ranked:
            package.pop("_freshness_source_order", None)

        if record:
            for package in ranked:
                self.record_exposure(package, page=page, now=now)

        logger.info(
            "Recommendation freshness applied page=%s candidates=%s returned=%s",
            page,
            len(packages),
            len(ranked)
        )
        return ranked

    ############################################################

    def record_exposure(self, package, page, now=None, status=None):

        package = package or {}
        self.db.record_recommendation_exposure({
            "fingerprint": package.get("recommendation_fingerprint") or self.fingerprint(package),
            "event_id": self.event_id(package),
            "media_ids": self.media_ids(package),
            "communication_objective": self._objective(package),
            "narrative_angle": self._angle(package),
            "teaching_point": self._teaching_point(package),
            "platform_package_type": self._platform_package_type(package),
            "campaign": self._campaign(package),
            "program": self._program(package),
            "source_opportunity_id": (
                package.get("source_opportunity_id")
                or package.get("option_id")
                or package.get("recommendation_id")
                or ""
            ),
            "page": page,
            "status": status or package.get("package_state") or "Shown",
            "shown_at": (now or TimeService.utc_now()).isoformat(timespec="seconds"),
            "metadata": {
                "title": package.get("title") or package.get("option_title") or "",
                "confidence": package.get("confidence", 0),
                "score": package.get("final_ranking_score", 0),
                "freshness_penalty": package.get("freshness_penalty", 0)
            }
        })

    ############################################################

    def update_status(self, fingerprint, status, page="", timestamp_field=""):

        if not fingerprint:
            return False
        return self.db.update_recommendation_exposure_status(
            fingerprint=fingerprint,
            status=status,
            page=page,
            timestamp_field=timestamp_field
        )

    ############################################################

    def package_state(self, package):

        quality = package.get("quality_gate") or {}
        media = package.get("media_package") or {}
        if package.get("package_status", "").startswith("blocked"):
            return "Blocked"
        if not self.media_ids(package):
            return "Needs Media"
        if not quality.get("passed", True):
            return "Needs Review"
        if package.get("caption_quality", {}).get("passed") is False:
            return "Needs Context"
        if media.get("needs_media_review") or package.get("needs_media_review"):
            return "Needs Review"
        return "Publish Ready"

    ############################################################

    def freshness_diagnostics(self, package, exposures, page="", now=None):

        now = now or TimeService.utc_now()
        fingerprint = package.get("recommendation_fingerprint") or self.fingerprint(package)
        event_id = self.event_id(package)
        angle = self._angle(package)
        media_ids = set(self.media_ids(package))
        exact = exposures["by_fingerprint"].get(fingerprint, [])
        event_angle = [
            item for item in exposures["rows"]
            if event_id
            and item.get("event_id") == event_id
            and item.get("narrative_angle") == angle
            and item.get("fingerprint") != fingerprint
        ]
        media_overlap = [
            item for item in exposures["rows"]
            if media_ids & set(item.get("media_ids") or [])
        ]

        penalty = 0
        factors = []
        dismissed = any(item.get("status") == "Dismissed" for item in exact)
        if exact:
            recent_exact = self._recent_count(
                exact,
                now,
                self.EXACT_COOLDOWN_DAYS
            )
            penalty += min(70, recent_exact * 45)
            factors.append(f"Exact package shown {sum(item.get('shown_count', 0) for item in exact)} time(s).")
            if dismissed:
                penalty += 80
                factors.append("Package was dismissed.")
        if event_angle:
            recent_angle = self._recent_count(
                event_angle,
                now,
                self.EVENT_ANGLE_COOLDOWN_DAYS
            )
            penalty += min(45, recent_angle * 25)
            factors.append("Same event and narrative angle was recently shown.")
        if media_overlap:
            recent_media = self._recent_count(
                media_overlap,
                now,
                self.MEDIA_COOLDOWN_DAYS
            )
            penalty += min(40, recent_media * 8)
            factors.append("Some selected media was used in recent recommendations.")

        return {
            "total_penalty": min(100, penalty),
            "prior_exposure_count": sum(item.get("shown_count", 0) for item in exact),
            "same_event_angle_count": len(event_angle),
            "media_reuse_count": len(media_overlap),
            "dismissed": dismissed,
            "page": page,
            "factors": factors or ["No recent exposure found."],
            "policy": {
                "exact_cooldown_days": self.EXACT_COOLDOWN_DAYS,
                "event_angle_cooldown_days": self.EVENT_ANGLE_COOLDOWN_DAYS,
                "media_cooldown_days": self.MEDIA_COOLDOWN_DAYS
            }
        }

    ############################################################

    def score_components(self, package):

        quality = package.get("quality_gate") or {}
        media = package.get("media_package") or {}
        media_score = (
            media.get("story_strength")
            or media.get("communications_score")
            or package.get("communications_score")
            or 0
        )
        return {
            "confidence": int(package.get("confidence") or 0),
            "media_relevance": int(media_score or 0),
            "editorial_specificity": int(
                (package.get("caption_quality") or {}).get("specificity_score")
                or (package.get("scroll_stop_score") or {}).get("total_score")
                or 0
            ),
            "quality_gate": 100 if quality.get("passed", True) else 0,
            "freshness_penalty": int(package.get("freshness_penalty") or 0)
        }

    def final_score(self, package, freshness):

        components = self.score_components(package)
        base = (
            components["confidence"] * 0.35
            + components["media_relevance"] * 0.25
            + components["editorial_specificity"] * 0.25
            + components["quality_gate"] * 0.15
        )
        return round(max(0, base - freshness.get("total_penalty", 0)), 2)

    ############################################################

    def media_ids(self, package):

        ids = []
        media_package = package.get("media_package") or {}
        for key in (
            "verified_media_ids",
            "selected_media_ids"
        ):
            ids.extend(self._ids(media_package.get(key)))
        for key in (
            "primary_media",
            "primary_photo",
            "primary_video"
        ):
            ids.extend(self._ids(package.get(key)))
            ids.extend(self._ids(media_package.get(key)))
        for key in (
            "alternative_media",
            "gallery_photos",
            "gallery_videos",
            "carousel_order",
            "reel_options",
            "supporting_media",
            "alternates"
        ):
            ids.extend(self._ids(package.get(key)))
            ids.extend(self._ids(media_package.get(key)))
        return sorted({int(item) for item in ids if str(item).isdigit()})

    def event_id(self, package):

        event = package.get("event_collection") or {}
        media_package = package.get("media_package") or {}
        return str(
            package.get("event_id")
            or package.get("verified_event_id")
            or event.get("event_id")
            or media_package.get("event_id")
            or ""
        )

    ############################################################

    def _exposure_index(self, rows):

        index = {
            "rows": rows or [],
            "by_fingerprint": {}
        }
        for row in rows or []:
            index["by_fingerprint"].setdefault(row.get("fingerprint", ""), []).append(row)
        return index

    def _recent_count(self, rows, now, days):

        threshold = TimeService.normalize_stored_timestamp(now) - timedelta(days=days)
        count = 0
        for row in rows:
            shown = TimeService.normalize_stored_timestamp(
                row.get("last_shown_at") or row.get("first_shown_at")
            )
            if shown and shown >= threshold:
                count += 1
        return count

    def _diverse(self, packages, limit):

        if not limit:
            return packages
        selected = []
        used_events = set()
        used_objectives = set()
        for package in packages:
            event = self.event_id(package)
            objective = self._objective(package)
            if (
                len(selected) < limit
                and (not event or event not in used_events)
                and (not objective or objective not in used_objectives)
            ):
                selected.append(package)
                used_events.add(event)
                used_objectives.add(objective)
        for package in packages:
            if len(selected) >= limit:
                break
            if package not in selected:
                selected.append(package)
        return selected[:limit]

    def _state_weight(self, state):

        return {
            "Publish Ready": 5,
            "Needs Review": 3,
            "Needs Context": 2,
            "Needs Media": 1,
            "Blocked": 0
        }.get(state, 1)

    def _objective(self, package):

        return str(
            package.get("communication_objective")
            or package.get("opportunity_type")
            or package.get("content_family")
            or package.get("strategy")
            or ""
        )

    def _angle(self, package):

        angle = package.get("narrative_angle") or {}
        if isinstance(angle, dict):
            return str(angle.get("angle_name") or angle.get("title") or "")
        return str(angle or package.get("content_angle") or package.get("strategy") or "")

    def _teaching_point(self, package):

        return str(
            package.get("narrative_focus")
            or package.get("selected_teaching_point")
            or package.get("teaching_point")
            or package.get("content_angle")
            or ""
        )

    def _platform_package_type(self, package):

        platforms = package.get("recommended_platforms") or []
        if isinstance(platforms, str):
            platforms = [platforms]
        return "|".join(str(item) for item in platforms) + "|" + str(package.get("recommended_format") or "")

    def _campaign(self, package):

        media_package = package.get("media_package") or {}
        return str(
            package.get("campaign")
            or media_package.get("campaign")
            or ""
        )

    def _program(self, package):

        media_package = package.get("media_package") or {}
        return str(
            package.get("program")
            or media_package.get("program")
            or ""
        )

    def _ids(self, value):

        if not value:
            return []
        if isinstance(value, dict):
            value = [value]
        result = []
        if isinstance(value, (list, tuple, set)):
            for item in value:
                if isinstance(item, dict):
                    result.append(item.get("media_id") or item.get("id"))
                else:
                    result.append(item)
        else:
            result.append(value)
        return result
