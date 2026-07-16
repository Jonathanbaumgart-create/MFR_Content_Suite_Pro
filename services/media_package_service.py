import hashlib
from pathlib import Path

from core.app_context import context
from models.media_package import MediaPackage, MediaPackageAsset
from services.cache_invalidation_service import CacheInvalidationService
from services.communications_memory_service import CommunicationsMemoryService
from services.human_feedback_service import HumanFeedbackService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class MediaPackageService:

    PACKAGE_VERSION = "media-package-v1"
    ASSET_LIMIT = 36
    ALTERNATIVE_LIMIT = 25
    SUPPORTING_PHOTO_LIMIT = 5
    SUPPORTING_VIDEO_LIMIT = 3

    PLATFORM_KEYS = (
        "Facebook",
        "Instagram",
        "LinkedIn",
        "Website",
        "News Release",
        "Newsletter"
    )

    def __init__(
        self,
        database=None,
        memory_service=None,
        feedback_service=None
    ):

        self.db = database or context.database
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.feedback = feedback_service or HumanFeedbackService(
            database=self.db
        )
        self.last_metrics = {}

    ############################################################

    def build_package(
        self,
        recommendation,
        platforms=None,
        include_mock=False,
        candidate_limit=160,
        persist=True
    ):

        started = TimeService.utc_now_iso()
        recommendation = recommendation or {}
        platforms = self._platforms(recommendation, platforms)
        assets = self._eligible_assets(
            recommendation,
            include_mock=include_mock,
            candidate_limit=candidate_limit
        )
        ranked = self._rank_assets(
            assets,
            recommendation,
            platforms
        )
        package = self._assemble_package(
            recommendation,
            ranked,
            platforms,
            started
        )
        package = self._apply_saved_actions(package)

        if persist and self._has_media(package):
            try:
                self.db.save_communication_package_history(package)
            except Exception:
                logger.warning(
                    "Communication package history could not be saved",
                    exc_info=True
                )

        self.last_metrics = {
            "candidate_count": len(assets),
            "ranked_count": len(ranked),
            "media_count": package.get("media_count", 0),
            "version": self.PACKAGE_VERSION
        }
        logger.info(
            "Media package built title=%s media=%s candidates=%s",
            recommendation.get("title", ""),
            package.get("media_count", 0),
            len(assets)
        )

        return package

    ############################################################

    def _apply_saved_actions(self, package):

        package = dict(package or {})
        package_id = package.get("package_id", "")

        if not package_id:
            return package

        try:
            actions = self.db.communication_package_asset_actions(
                package_id,
                limit=100
            )
        except Exception:
            return package

        if not actions:
            return package

        for action in reversed(actions):
            media_id = self._to_int(action.get("media_id"))

            if not media_id:
                continue

            if action.get("action") == "exclude":
                package = self.exclude_asset(
                    package,
                    media_id,
                    reason=action.get("reason", ""),
                    persist=False
                )
            elif action.get("action") == "replace":
                replacement = self._asset_for_media_id(media_id)
                if not replacement:
                    continue

                package = self.replace_asset(
                    package,
                    replacement,
                    action.get("new_role") or "primary_photo",
                    reason=action.get("reason", ""),
                    persist=False
                )

        return package

    def _asset_for_media_id(self, media_id):

        rows = self.db.communications_officer_assets(
            [media_id],
            limit=1
        )

        if not rows:
            return {}

        asset = self._effective_asset(rows[0])
        enriched = self._enrich_base_media([asset])

        return enriched[0] if enriched else asset

    ############################################################

    def alternatives(
        self,
        recommendation,
        media_type=None,
        exclude_ids=None,
        limit=ALTERNATIVE_LIMIT
    ):

        recommendation = recommendation or {}
        exclude_ids = {
            self._to_int(media_id)
            for media_id in (exclude_ids or [])
            if self._to_int(media_id)
        }
        assets = self._eligible_assets(
            recommendation,
            include_mock=False,
            candidate_limit=max(limit * 4, self.ALTERNATIVE_LIMIT)
        )
        ranked = self._rank_assets(
            assets,
            recommendation,
            self._platforms(recommendation, None)
        )
        results = []

        for asset in ranked:
            if media_type and asset.get("media_type") != media_type:
                continue

            if asset.get("media_id") in exclude_ids:
                continue

            results.append(asset)

            if len(results) >= limit:
                break

        return results

    ############################################################

    def replace_asset(
        self,
        package,
        replacement_asset,
        role,
        reason="Manual replacement",
        persist=True
    ):

        package = dict(package or {})
        replacement = dict(replacement_asset or {})
        media = dict(package)
        role = role or "primary_photo"
        previous = dict(media.get(role) or {})
        replacement["selected_as"] = role
        replacement["why_selected"] = (
            reason or "Selected by Jonathan as a package-specific replacement."
        )

        if role in ("primary_photo", "primary_video"):
            media[role] = replacement
        else:
            media.setdefault(role, []).append(replacement)

        action = {
            "package_id": package.get("package_id", ""),
            "media_id": replacement.get("media_id"),
            "action": "replace",
            "reason": reason,
            "previous_role": role if previous else "",
            "new_role": role,
            "previous_media_id": previous.get("media_id"),
            "created_at": TimeService.utc_now_iso()
        }
        media.setdefault("replacement_history", []).append(action)

        if persist:
            try:
                self.db.save_communication_package_asset_action(action)
            except Exception:
                logger.warning(
                    "Package replacement action could not be saved",
                    exc_info=True
                )

            CacheInvalidationService.invalidate(
                replacement.get("media_id"),
                reason="communication package media replacement",
                scopes=["communication_package", "communications_officer"]
            )
        return media

    ############################################################

    def exclude_asset(self, package, media_id, reason="Package-specific exclusion", persist=True):

        package = dict(package or {})
        media_id = self._to_int(media_id)

        if not media_id:
            return package

        package.setdefault("excluded_asset_ids", [])
        if media_id not in package["excluded_asset_ids"]:
            package["excluded_asset_ids"].append(media_id)

        for key in ("primary_photo", "primary_video"):
            if (package.get(key) or {}).get("media_id") == media_id:
                package[key] = {}

        for key in ("supporting_photos", "gallery_photos", "supporting_videos", "gallery_videos"):
            package[key] = [
                item
                for item in package.get(key, [])
                if item.get("media_id") != media_id
            ]

        action = {
            "package_id": package.get("package_id", ""),
            "media_id": media_id,
            "action": "exclude",
            "reason": reason,
            "previous_role": "",
            "new_role": "",
            "created_at": TimeService.utc_now_iso()
        }
        package.setdefault("replacement_history", []).append(action)

        if persist:
            try:
                self.db.save_communication_package_asset_action(action)
            except Exception:
                logger.warning(
                    "Package exclusion action could not be saved",
                    exc_info=True
                )

            CacheInvalidationService.invalidate(
                media_id,
                reason="communication package media exclusion",
                scopes=["communication_package", "communications_officer"]
            )
        return package

    ############################################################

    def preview_asset(self, asset):

        asset = dict(asset or {})
        return {
            "media_id": asset.get("media_id"),
            "filename": asset.get("filename", ""),
            "path": asset.get("path", ""),
            "media_type": asset.get("media_type", ""),
            "trust_state": asset.get("trust_state", ""),
            "communications_score": asset.get("communications_score", 0),
            "media_score": asset.get("media_score", 0),
            "story_relevance": asset.get("topic_relevance_score", 0),
            "platform_fit": asset.get("platform_fit_score", 0),
            "why_selected": asset.get("why_selected", ""),
            "selection_factors": list(asset.get("selection_factors") or []),
            "confidence_limitations": list(asset.get("confidence_limitations") or [])
        }

    ############################################################

    def _eligible_assets(
        self,
        recommendation,
        include_mock=False,
        candidate_limit=160
    ):

        ids = self._asset_ids(recommendation)
        assets = []

        if ids:
            assets.extend(
                self.db.communications_officer_assets(
                    ids,
                    limit=self.ASSET_LIMIT
                )
            )
            found_ids = {
                self._to_int(asset.get("media_id"))
                for asset in assets
            }
            missing_ids = [
                media_id
                for media_id in ids
                if media_id and media_id not in found_ids
            ]
            if missing_ids:
                assets.extend(
                    self.db.media_package_asset_rows(
                        missing_ids,
                        limit=len(missing_ids)
                    )
                )

        if len(assets) < 6:
            assets.extend(
                self.db.content_director_candidates(
                    limit=min(max(candidate_limit, 24), 500)
                )
            )

        effective = []
        seen = set()

        for asset in assets:
            media_id = self._to_int(asset.get("media_id"))

            if not media_id or media_id in seen:
                continue

            seen.add(media_id)

            if self._excluded(asset, include_mock=include_mock):
                continue

            effective.append(
                self._effective_asset(asset)
            )

        effective = self._enrich_base_media(effective)
        reviewed = [
            asset
            for asset in effective
            if self._reviewed(asset)
        ]

        return reviewed or effective

    ############################################################

    def _effective_asset(self, asset):

        asset = dict(asset or {})
        media_id = self._to_int(asset.get("media_id"))

        if not media_id:
            return asset

        try:
            effective = self.feedback.effective_media_intelligence_row(media_id)
        except Exception:
            effective = {}

        merged = dict(asset)
        if effective:
            merged.update(effective)
            merged.update({
                "media_id": media_id,
                "filename": asset.get("filename", ""),
                "path": asset.get("path", ""),
                "media_type": asset.get("media_type", ""),
                "provider": asset.get("provider", ""),
                "model": asset.get("model", ""),
                "failure_reason": asset.get("failure_reason", ""),
                "trust_state": effective.get("trust_state") or asset.get("trust_state", ""),
                "review_status": effective.get("review_status") or asset.get("review_status", "")
            })

        return merged

    ############################################################

    def _enrich_base_media(self, assets):

        ids = [
            asset.get("media_id")
            for asset in assets
            if asset.get("media_id")
        ]

        if not ids:
            return assets

        try:
            rows = self.db.media_package_asset_rows(
                ids,
                limit=len(ids)
            )
        except Exception:
            return assets

        by_id = {
            row.get("media_id"): row
            for row in rows
        }
        enriched = []

        for asset in assets:
            base = by_id.get(asset.get("media_id"), {})
            merged = dict(asset)
            merged.update({
                key: base.get(key, merged.get(key))
                for key in (
                    "filename",
                    "path",
                    "media_type",
                    "capture_time",
                    "first_seen_at",
                    "date_added",
                    "orientation",
                    "width",
                    "height",
                    "duration_seconds",
                    "sha256",
                    "reel_potential",
                    "story_potential",
                    "clip_recommendations",
                    "cover_recommendation",
                    "video_story_category",
                    "video_communications_themes"
                )
            })
            enriched.append(merged)

        return enriched

    ############################################################

    def _rank_assets(self, assets, recommendation, platforms):

        ranked = []
        recommendation_terms = self._recommendation_terms(recommendation)
        recent_recommended = set()
        recent_used = set()

        try:
            recent_recommended = self.db.recent_recommended_media_ids(
                days=60,
                limit=500
            )
        except Exception:
            pass

        try:
            recent_used = self.memory.recent_social_media_ids(days=120)
        except Exception:
            pass

        for asset in assets:
            scored = self._score_asset(
                asset,
                recommendation,
                recommendation_terms,
                platforms,
                recent_recommended,
                recent_used
            )
            ranked.append(scored)

        ranked.sort(
            key=lambda item: (
                item.get("media_score", 0),
                item.get("communications_score", 0),
                item.get("filename", "")
            ),
            reverse=True
        )
        return ranked

    def _score_asset(
        self,
        asset,
        recommendation,
        recommendation_terms,
        platforms,
        recent_recommended,
        recent_used
    ):

        asset = dict(asset or {})
        asset_terms = self._asset_terms(asset)
        matches = sorted(asset_terms & recommendation_terms)
        topic_score = min(100, len(matches) * 18)
        if not matches and asset.get("communications_score"):
            topic_score = min(45, int(asset.get("communications_score") or 0) // 2)

        platform_score = self._platform_score(asset, platforms)
        trust_score = self._trust_score(asset)
        quality_score = self._quality_score(asset)
        communications_score = self._to_int(asset.get("communications_score"))
        recent_risk = self._recent_use_risk(
            asset,
            recent_recommended,
            recent_used
        )
        duplicate_risk = self._duplicate_scene_risk(asset)
        filesystem = asset.get("filesystem_intelligence") or {}
        filesystem_conflict = filesystem.get("conflict_state") == "conflict"
        media_score = round(
            communications_score * 0.34 +
            topic_score * 0.24 +
            platform_score * 0.16 +
            trust_score * 0.14 +
            quality_score * 0.08 -
            recent_risk * 0.08 -
            duplicate_risk * 0.04,
            1
        )
        reel_potential = self._to_int(asset.get("reel_potential"))

        if asset.get("media_type") == "video" and reel_potential:
            media_score = round(
                media_score * 0.78 + reel_potential * 0.22,
                1
            )

        media_score = max(0, min(100, media_score))
        factors = [
            f"story relevance {topic_score}",
            f"communications score {communications_score}",
            f"platform fit {platform_score}",
            f"trust score {trust_score}",
            f"recent-use risk {recent_risk}",
            f"duplicate-scene risk {duplicate_risk}"
        ]

        if reel_potential:
            factors.append(f"Reel potential {reel_potential}")
        limitations = []

        if filesystem.get("filesystem_confidence", 0):
            factors.append(
                "folder context " +
                str(filesystem.get("root_category") or "available")
            )

        if not self._reviewed(asset):
            limitations.append(
                "Human review is incomplete; use only if no reviewed alternative fits."
            )

        if filesystem_conflict:
            limitations.append(
                "Folder context conflicts with stored intelligence and needs review."
            )

        if not matches:
            limitations.append(
                "Story-term match is weak, so this asset should support a broader story only."
            )

        asset.update({
            "topic_relevance_score": topic_score,
            "campaign_relevance_score": topic_score,
            "platform_fit_score": platform_score,
            "trust_score": trust_score,
            "media_quality_score": quality_score,
            "media_score": media_score,
            "recent_use_risk": recent_risk,
            "duplicate_scene_risk": duplicate_risk,
            "reel_potential": reel_potential,
            "matched_terms": matches[:8],
            "selection_factors": factors,
            "confidence_limitations": limitations
        })
        return asset

    ############################################################

    def _assemble_package(self, recommendation, ranked, platforms, generated_at):

        primary_photo = self._first_of_type(ranked, "image")
        primary_video = self._first_of_type(ranked, "video")
        support_photos = self._supporting_assets(
            ranked,
            "image",
            exclude_ids={primary_photo.get("media_id")} if primary_photo else set(),
            limit=self.SUPPORTING_PHOTO_LIMIT
        )
        support_videos = self._supporting_assets(
            ranked,
            "video",
            exclude_ids={primary_video.get("media_id")} if primary_video else set(),
            limit=self.SUPPORTING_VIDEO_LIMIT
        )
        selected = []

        if primary_photo:
            selected.append(self._asset_summary(primary_photo, "primary_photo"))

        selected.extend(
            self._asset_summary(asset, "supporting_photo")
            for asset in support_photos
        )

        if primary_video:
            selected.append(self._asset_summary(primary_video, "primary_video"))

        selected.extend(
            self._asset_summary(asset, "supporting_video")
            for asset in support_videos
        )
        trust_counts = self._trust_counts(selected)
        score_values = [
            self._to_float(asset.get("media_score"))
            for asset in selected
        ]
        communications_values = [
            self._to_float(asset.get("communications_score"))
            for asset in selected
        ]
        package_id = self._package_id(recommendation, selected)
        guidance = self._platform_guidance(
            platforms,
            selected,
            recommendation
        )
        reasons = self._package_reasons(
            recommendation,
            selected
        )
        diversity = self._diversity_reasoning(selected)
        limitations = self._package_limitations(selected)

        package = MediaPackage(
            package_id=package_id,
            recommendation_id=recommendation.get("recommendation_id", ""),
            story_title=recommendation.get("title", ""),
            primary_photo=selected[0] if primary_photo else {},
            supporting_photos=[
                item
                for item in selected
                if item.get("selected_as") == "supporting_photo"
            ],
            gallery_photos=[
                item
                for item in selected
                if item.get("selected_as") == "supporting_photo"
            ],
            primary_video=(
                next(
                    (
                        item
                        for item in selected
                        if item.get("selected_as") == "primary_video"
                    ),
                    {}
                )
            ),
            supporting_videos=[
                item
                for item in selected
                if item.get("selected_as") == "supporting_video"
            ],
            gallery_videos=[
                item
                for item in selected
                if item.get("selected_as") == "supporting_video"
            ],
            media_count=len(selected),
            trust_counts=trust_counts,
            story_relevance=self._average(selected, "topic_relevance_score"),
            platform_fit=self._average(selected, "platform_fit_score"),
            media_score=round(sum(score_values) / len(score_values), 1) if score_values else 0,
            diversity_score=self._diversity_score(selected),
            recent_use_risk=self._average(selected, "recent_use_risk"),
            duplicate_scene_risk=self._average(selected, "duplicate_scene_risk"),
            communications_score=round(sum(communications_values) / len(communications_values), 1) if communications_values else 0,
            story_strength=recommendation.get("story_strength", {}),
            editorial_angle=(
                recommendation.get("editorial_angle")
                or recommendation.get("caption_theme")
                or ""
            ),
            recommended_platforms=platforms,
            platform_media_guidance=guidance,
            confidence=recommendation.get("confidence") or recommendation.get("confidence_score") or 0,
            confidence_limitations=limitations,
            reasons=reasons,
            diversity_reasoning=diversity,
            automatic_selection={
                "asset_ids": [
                    asset.get("media_id")
                    for asset in selected
                    if asset.get("media_id")
                ],
                "selection_version": self.PACKAGE_VERSION
            },
            version=self.PACKAGE_VERSION,
            generated_at=generated_at
        ).to_dict()

        return package

    ############################################################

    def _asset_summary(self, asset, selected_as):

        summary = MediaPackageAsset(
            media_id=self._to_int(asset.get("media_id")),
            filename=asset.get("filename", ""),
            media_type=asset.get("media_type", ""),
            path=asset.get("path", ""),
            thumbnail_path=asset.get("thumbnail_path", ""),
            trust_state=asset.get("trust_state", ""),
            analysis_state=asset.get("review_status", ""),
            capture_time=asset.get("capture_time", ""),
            added_at=asset.get("first_seen_at") or asset.get("date_added", ""),
            orientation=asset.get("orientation") or self._orientation(asset),
            width=self._to_int(asset.get("width")),
            height=self._to_int(asset.get("height")),
            duration_seconds=self._to_float(asset.get("duration_seconds")),
            communications_score=self._to_float(asset.get("communications_score")),
            media_score=self._to_float(asset.get("media_score")),
            editorial_score=self._to_float(asset.get("storytelling_score")),
            topic_relevance_score=self._to_float(asset.get("topic_relevance_score")),
            campaign_relevance_score=self._to_float(asset.get("campaign_relevance_score")),
            platform_fit_score=self._to_float(asset.get("platform_fit_score")),
            recent_use_risk=self._to_float(asset.get("recent_use_risk")),
            duplicate_scene_risk=self._to_float(asset.get("duplicate_scene_risk")),
            reel_potential=self._to_float(asset.get("reel_potential")),
            story_potential=self._to_float(asset.get("story_potential")),
            clip_recommendations=list(asset.get("clip_recommendations") or []),
            cover_recommendation=dict(asset.get("cover_recommendation") or {}),
            selected_as=selected_as,
            why_selected=self._why_selected(asset, selected_as),
            why_not_primary=self._why_not_primary(asset, selected_as),
            platform_suitability=dict(asset.get("platform_suitability") or {}),
            selection_factors=list(asset.get("selection_factors") or []),
            confidence_limitations=list(asset.get("confidence_limitations") or [])
        ).to_dict()
        return summary

    ############################################################

    def _first_of_type(self, ranked, media_type):

        for asset in ranked:
            if asset.get("media_type") == media_type:
                return asset

        return {}

    def _supporting_assets(self, ranked, media_type, exclude_ids, limit):

        selected = []
        scene_keys = set()
        exclude_ids = {
            self._to_int(value)
            for value in exclude_ids
            if self._to_int(value)
        }

        for asset in ranked:
            media_id = self._to_int(asset.get("media_id"))

            if asset.get("media_type") != media_type:
                continue

            if media_id in exclude_ids:
                continue

            scene = self._scene_key(asset)
            if scene in scene_keys and len(selected) >= max(1, limit // 2):
                continue

            scene_keys.add(scene)
            selected.append(asset)

            if len(selected) >= limit:
                break

        return selected

    ############################################################

    def _asset_ids(self, recommendation):

        ids = []

        for key in ("best_asset_ids", "supporting_asset_ids"):
            ids.extend(recommendation.get(key) or [])

        for item in recommendation.get("recommended_media") or []:
            ids.append(item.get("media_id"))

        package = recommendation.get("media_package") or {}
        for key in ("best_photo", "best_video", "primary_photo", "primary_video"):
            ids.append((package.get(key) or {}).get("media_id"))

        for key in ("supporting_photos", "supporting_videos", "gallery_photos", "gallery_videos"):
            for item in package.get(key) or []:
                ids.append(item.get("media_id"))

        return self._unique_ids(ids)[:self.ASSET_LIMIT]

    def _excluded(self, asset, include_mock=False):

        trust = str(asset.get("trust_state") or "").lower()
        review = str(asset.get("review_status") or "").lower()
        provider = str(asset.get("provider") or "").lower()

        if asset.get("failure_reason"):
            return True

        if trust in ("rejected_real", "failed") or review in ("rejected", "failed"):
            return True

        if provider == "mock" and not include_mock:
            return True

        return False

    def _reviewed(self, asset):

        return (
            asset.get("trust_state") in ("approved_real", "corrected_real")
            or asset.get("review_status") in ("approved", "corrected")
        )

    ############################################################

    def _recommendation_terms(self, recommendation):

        values = []

        for key in (
            "title",
            "headline",
            "summary",
            "topic",
            "category",
            "editorial_angle",
            "primary_reason",
            "communications_gap"
        ):
            values.extend(self._split(recommendation.get(key)))

        for key in (
            "supporting_topics",
            "supporting_programs",
            "editorial_angles",
            "recommended_platforms",
            "recommended_audiences",
            "source_signals"
        ):
            for value in recommendation.get(key) or []:
                values.extend(self._split(value))

        return {
            self._token(value)
            for value in values
            if self._token(value)
        }

    def _asset_terms(self, asset):

        values = []
        filesystem = asset.get("filesystem_intelligence") or {}

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "search_text",
            "description",
            "effective_description",
            "suggested_platform",
            "suggested_time_of_year",
            "video_story_category",
            "reel_explanation"
        ):
            values.extend(self._split(asset.get(key)))

        for key in (
            "apparatus_tags",
            "equipment_tags",
            "ppe_tags",
            "people_tags",
            "content_tags",
            "content_themes",
            "recommended_uses",
            "suggested_campaigns",
            "suggested_audience",
            "communications_reasoning"
        ):
            for value in asset.get(key) or []:
                values.extend(self._split(value))

        for value in asset.get("video_communications_themes") or []:
            values.extend(self._split(value))

        for key in (
            "root_category",
            "subcategory",
            "apparatus_identifier",
            "apparatus_name",
            "incident_type",
            "training_type",
            "public_education_program",
            "campaign",
            "community_event",
            "station",
            "season"
        ):
            values.extend(self._split(filesystem.get(key)))

        for key in (
            "normalized_tags",
            "folder_keywords",
            "source_folders"
        ):
            for value in filesystem.get(key) or []:
                values.extend(self._split(value))

        return {
            self._token(value)
            for value in values
            if self._token(value)
        }

    ############################################################

    def _platform_score(self, asset, platforms):

        suitability = asset.get("platform_suitability") or {}
        scores = []

        for platform in platforms:
            key = self._platform_key(platform)
            for candidate in (
                key,
                key.lower(),
                key.lower().replace(" ", "_"),
                key.lower().replace(" ", "")
            ):
                if candidate in suitability:
                    scores.append(self._to_int(suitability[candidate]))

        if scores:
            return max(scores)

        media_type = asset.get("media_type", "")
        orientation = asset.get("orientation") or self._orientation(asset)

        if media_type == "video":
            reel = self._to_int(asset.get("reel_potential"))

            if reel and any(platform in ("Instagram", "Facebook") for platform in platforms):
                return max(82, min(100, reel))

            if any(platform in ("Instagram", "Facebook") for platform in platforms):
                return 82
            return 68

        if orientation == "portrait" and "Instagram" in platforms:
            return 86

        if orientation == "landscape" and any(
            platform in platforms
            for platform in ("Facebook", "Website", "News Release", "Newsletter")
        ):
            return 84

        return 70

    def _trust_score(self, asset):

        trust = asset.get("trust_state") or ""
        review = asset.get("review_status") or ""

        if trust == "corrected_real" or review == "corrected":
            return 100

        if trust == "approved_real" or review == "approved":
            return 92

        if trust == "unreviewed_real" or review == "review_required":
            return 42

        if trust == "mock":
            return 0

        return 35

    def _quality_score(self, asset):

        width = self._to_int(asset.get("width"))
        height = self._to_int(asset.get("height"))
        media_type = asset.get("media_type", "")

        if media_type == "video" and self._to_float(asset.get("duration_seconds")) > 0:
            return 80

        if width <= 0 or height <= 0:
            return 55

        pixels = width * height

        if pixels >= 3000 * 2000:
            return 92

        if pixels >= 1600 * 1000:
            return 82

        if pixels >= 900 * 600:
            return 70

        return 48

    def _recent_use_risk(self, asset, recent_recommended, recent_used):

        media_id = self._to_int(asset.get("media_id"))
        risk = 0

        if media_id in recent_recommended:
            risk += 35

        if media_id in recent_used:
            risk += 50

        try:
            memory = self.memory.media_memory(media_id)
            if memory.get("post_count"):
                risk += min(40, int(memory.get("post_count") or 0) * 12)
        except Exception:
            pass

        return min(100, risk)

    def _duplicate_scene_risk(self, asset):

        filename = str(asset.get("filename") or "").lower()
        risk = 0

        if any(token in filename for token in ("copy", "duplicate", "edited")):
            risk += 30

        if asset.get("sha256"):
            risk += 0

        if self._to_int(asset.get("uniqueness_score")):
            risk += max(0, 65 - self._to_int(asset.get("uniqueness_score")))

        return min(100, risk)

    ############################################################

    def _platform_guidance(self, platforms, selected, recommendation):

        guidance = {}

        for platform in platforms:
            key = self._platform_key(platform)
            primary = self._best_for_platform(selected, key)
            support = [
                item
                for item in selected
                if item.get("media_id") != (primary or {}).get("media_id")
            ][:4]
            guidance[key] = {
                "primary_media_id": (primary or {}).get("media_id"),
                "primary_filename": (primary or {}).get("filename", ""),
                "supporting_media_ids": [
                    item.get("media_id")
                    for item in support
                    if item.get("media_id")
                ],
                "platform_fit": (primary or {}).get("platform_fit_score", 0),
                "reason": self._platform_reason(key, primary, recommendation)
            }

        return guidance

    def _best_for_platform(self, selected, platform):

        if not selected:
            return {}

        if platform == "Instagram":
            videos = [
                item
                for item in selected
                if item.get("media_type") == "video"
            ]
            if videos:
                return max(videos, key=lambda item: item.get("platform_fit_score", 0))

        return max(
            selected,
            key=lambda item: (
                item.get("platform_fit_score", 0),
                item.get("media_score", 0)
            )
        )

    def _platform_reason(self, platform, asset, recommendation):

        if not asset:
            return (
                f"No specific {platform} asset was selected; use the primary story media if available."
            )

        return (
            f"{asset.get('filename', 'Media')} is recommended for {platform} "
            f"because it has platform fit {asset.get('platform_fit_score', 0)} "
            f"and story relevance {asset.get('topic_relevance_score', 0)}."
        )

    ############################################################

    def _package_reasons(self, recommendation, selected):

        reasons = []

        if recommendation.get("title"):
            reasons.append(
                "Media was selected to support story: " + recommendation.get("title", "")
            )

        if selected:
            reasons.append(
                f"{len(selected)} eligible asset(s) were selected from bounded Gallery candidates."
            )

        reviewed = [
            asset
            for asset in selected
            if asset.get("trust_state") in ("approved_real", "corrected_real")
        ]

        if reviewed:
            reasons.append(
                f"{len(reviewed)} approved/corrected real asset(s) anchor the package."
            )

        reasons.append(
            "Rejected, failed, and mock analysis are excluded unless explicitly allowed."
        )
        return reasons

    def _diversity_reasoning(self, selected):

        types = sorted({asset.get("media_type", "") for asset in selected if asset.get("media_type")})
        orientations = sorted({asset.get("orientation", "") for asset in selected if asset.get("orientation")})
        return [
            "Media types included: " + ", ".join(types or ["none"]),
            "Orientations included: " + ", ".join(orientations or ["unknown"]),
            "Supporting assets avoid repeating the same strongest scene when alternatives exist."
        ]

    def _package_limitations(self, selected):

        limitations = []

        if not selected:
            limitations.append(
                "No eligible media was found; this communication package is incomplete."
            )

        if not any(asset.get("trust_state") in ("approved_real", "corrected_real") for asset in selected):
            limitations.append(
                "No approved or corrected real intelligence was available."
            )

        if not any(asset.get("selected_as") == "primary_photo" for asset in selected):
            limitations.append(
                "No primary hero photo was available."
            )

        return limitations

    ############################################################

    def _why_selected(self, asset, selected_as):

        label = selected_as.replace("_", " ")
        return (
            f"Selected as {label} with media score {asset.get('media_score', 0)}, "
            f"story relevance {asset.get('topic_relevance_score', 0)}, "
            f"communications score {asset.get('communications_score', 0)}, "
            f"and trust state {asset.get('trust_state') or asset.get('review_status') or 'unknown'}."
        )

    def _why_not_primary(self, asset, selected_as):

        if selected_as.startswith("primary"):
            return ""

        return (
            "Used as supporting media because another asset scored higher for the primary role "
            "or provided a stronger platform fit."
        )

    ############################################################

    def _trust_counts(self, selected):

        counts = {
            "approved_real": 0,
            "corrected_real": 0,
            "unreviewed_real": 0,
            "mock": 0,
            "unknown": 0
        }

        for asset in selected:
            trust = asset.get("trust_state") or "unknown"
            counts[trust if trust in counts else "unknown"] += 1

        return counts

    def _diversity_score(self, selected):

        if not selected:
            return 0

        types = len({asset.get("media_type") for asset in selected if asset.get("media_type")})
        orientations = len({asset.get("orientation") for asset in selected if asset.get("orientation")})
        scenes = len({self._scene_key(asset) for asset in selected})
        score = min(100, 35 + types * 18 + orientations * 12 + scenes * 6)
        return score

    def _scene_key(self, asset):

        return "|".join(
            [
                str(asset.get("incident_type", "")),
                str(asset.get("primary_activity", "")),
                ",".join(sorted(asset.get("content_tags") or [])[:3])
            ]
        ).lower()

    def _orientation(self, asset):

        width = self._to_int(asset.get("width"))
        height = self._to_int(asset.get("height"))

        if not width or not height:
            return "unknown"

        if width == height:
            return "square"

        return "landscape" if width > height else "portrait"

    def _package_id(self, recommendation, selected):

        source = "|".join(
            [
                self.PACKAGE_VERSION,
                recommendation.get("recommendation_id", ""),
                recommendation.get("title", ""),
                ",".join(str(asset.get("media_id")) for asset in selected)
            ]
        )
        return hashlib.sha1(source.encode("utf-8")).hexdigest()[:18]

    def _has_media(self, package):

        return bool(
            package.get("primary_photo")
            or package.get("primary_video")
            or package.get("gallery_photos")
            or package.get("gallery_videos")
        )

    ############################################################

    def _platforms(self, recommendation, platforms):

        values = list(platforms or recommendation.get("recommended_platforms") or [])

        if not values:
            values = ["Facebook", "Instagram", "LinkedIn"]

        normalized = []
        for value in values:
            key = self._platform_key(value)
            if key not in normalized:
                normalized.append(key)

        return normalized[:6]

    def _platform_key(self, value):

        text = str(value or "").replace("_", " ").strip().lower()
        mapping = {
            "facebook": "Facebook",
            "instagram": "Instagram",
            "linkedin": "LinkedIn",
            "website": "Website",
            "website article": "Website",
            "news release": "News Release",
            "newsletter": "Newsletter"
        }
        return mapping.get(text, str(value or "").strip().title() or "Facebook")

    def _unique_ids(self, values):

        ids = []
        seen = set()

        for value in values:
            media_id = self._to_int(value)

            if not media_id or media_id in seen:
                continue

            seen.add(media_id)
            ids.append(media_id)

        return ids

    def _split(self, value):

        if value is None:
            return []

        if isinstance(value, (list, tuple, set)):
            result = []
            for item in value:
                result.extend(self._split(item))
            return result

        return [
            part.strip()
            for part in str(value).replace(",", " ").replace("_", " ").replace("-", " ").split()
            if part.strip()
        ]

    def _token(self, value):

        return str(value or "").strip().lower().replace(" ", "_")

    def _average(self, rows, key):

        values = [
            self._to_float(row.get(key))
            for row in rows
            if self._to_float(row.get(key))
        ]

        return round(sum(values) / len(values), 1) if values else 0

    def _to_int(self, value):

        try:
            return int(float(value or 0))
        except Exception:
            return 0

    def _to_float(self, value):

        try:
            return float(value or 0)
        except Exception:
            return 0.0
