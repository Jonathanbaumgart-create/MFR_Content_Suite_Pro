import time

from core.app_context import context
from services.decision_explainability_service import DecisionExplainabilityService
from services.human_feedback_service import HumanFeedbackService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationPackageService:

    PACKAGE_TYPES = (
        "Facebook",
        "Instagram",
        "LinkedIn",
        "Website article",
        "News Release",
        "Newsletter"
    )
    ASSET_LIMIT = 20

    PLATFORM_GUIDANCE = {
        "Facebook": {
            "purpose": "Turn the recommendation into a community-facing story.",
            "tone": "Warm, conversational, and community focused.",
            "length": "Medium length with room for context.",
            "call_to_action": "Invite comments, sharing, safety action, or recruitment follow-up.",
            "visual": "Lead with the strongest people or action photo, then use a small supporting gallery.",
            "notes": "Use longer storytelling and community engagement."
        },
        "Instagram": {
            "purpose": "Create a visual-first post supported by a short caption.",
            "tone": "Direct, positive, and approachable.",
            "length": "Short to medium caption.",
            "call_to_action": "Encourage saves, shares, follows, or a simple safety action.",
            "visual": "Prioritize the best photo or short video and keep supporting media tight.",
            "notes": "Use visual-first framing and fewer words than Facebook."
        },
        "LinkedIn": {
            "purpose": "Frame the story as public service, leadership, training, or partnership.",
            "tone": "Professional and trust building.",
            "length": "Short professional update.",
            "call_to_action": "Point readers toward service, partnership, or recruitment value.",
            "visual": "Use a professional image that supports readiness or community service.",
            "notes": "Keep emojis and casual phrasing minimal."
        },
        "Website article": {
            "purpose": "Prepare a long-form evergreen story for the department website.",
            "tone": "Clear, factual, and public-service oriented.",
            "length": "Long-form article outline.",
            "call_to_action": "Direct readers to a related program, safety page, or contact point.",
            "visual": "Use one primary image and a concise supporting gallery.",
            "notes": "Keep it SEO friendly and useful beyond the day it is posted."
        },
        "News Release": {
            "purpose": "Prepare a factual public information release.",
            "tone": "Journalistic and restrained.",
            "length": "Concise release structure.",
            "call_to_action": "Use a public safety or information-focused closing.",
            "visual": "Use only media that clearly supports the public information angle.",
            "notes": "Avoid claims not supported by stored intelligence."
        },
        "Newsletter": {
            "purpose": "Summarize the story for internal or community newsletter readers.",
            "tone": "Informative and accessible.",
            "length": "Short summary with one clear takeaway.",
            "call_to_action": "Encourage awareness, participation, or follow-up reading.",
            "visual": "Use one strong image and optional supporting photos.",
            "notes": "Connect the story to department activity and community value."
        }
    }

    def __init__(self, database=None):

        self.db = database or context.database
        self.explainability = DecisionExplainabilityService(
            database=self.db
        )
        self.feedback = HumanFeedbackService(
            database=self.db
        )
        self.last_metrics = {}

    ############################################################

    def generate_package(
        self,
        recommendation,
        package_type="Facebook",
        include_mock=False
    ):

        started = time.perf_counter()
        package_type = self._package_type(package_type)
        assets = self._assets_for_recommendation(
            recommendation,
            include_mock=include_mock
        )
        media_package = self._media_package(
            recommendation,
            assets
        )
        scoring = self._package_scoring(
            recommendation,
            media_package,
            assets
        )
        guidance = self.PLATFORM_GUIDANCE[package_type]
        writing_strategy = self._writing_strategy(
            recommendation,
            package_type,
            guidance,
            media_package
        )
        package = {
            "package_type": package_type,
            "headline": recommendation.get("headline") or recommendation.get("title", ""),
            "primary_story": recommendation.get("summary") or recommendation.get("description", ""),
            "editorial_angle": (
                recommendation.get("editorial_angle")
                or recommendation.get("caption_theme")
                or recommendation.get("opportunity_type", "")
            ),
            "audience": self._audience(recommendation),
            "why_today_matters": recommendation.get("why_today_matters", ""),
            "supporting_evidence": self._supporting_evidence(
                recommendation,
                assets
            ),
            "best_photo": media_package["primary_photo"],
            "supporting_photos": media_package["gallery_photos"],
            "best_video": media_package["primary_video"],
            "supporting_videos": media_package["gallery_videos"],
            "recommended_platforms": self._platforms(recommendation, package_type),
            "publishing_priority": recommendation.get("priority") or self._priority_label(
                recommendation.get("priority_score", 0)
            ),
            "confidence": self._to_int(
                recommendation.get("confidence")
                or recommendation.get("confidence_score")
            ),
            "trust_label": recommendation.get("trust_label") or self._trust_label(assets),
            "trust_level": recommendation.get("trust_level") or self._trust_level(assets),
            "positive_factors": list(recommendation.get("positive_factors") or [])[:8],
            "negative_factors": list(recommendation.get("negative_factors") or [])[:8],
            "confidence_limitations": list(recommendation.get("confidence_limitations") or [])[:8],
            "suggested_hashtags": self._hashtags(
                recommendation,
                assets,
                package_type
            ),
            "suggested_cta": self._cta(recommendation, package_type),
            "suggested_posting_time": (
                recommendation.get("recommended_posting_window")
                or recommendation.get("best_posting_time")
                or "Next appropriate posting window"
            ),
            "writing_strategy": writing_strategy,
            "publishing_strategy": self._publishing_strategy(
                package_type,
                scoring,
                recommendation
            ),
            "media_package": media_package,
            "package_scoring": scoring,
            "generated_at": TimeService.utc_now_iso(),
            "source": "stored_recommendation_intelligence"
        }

        package["decision_audit"] = self.explainability.audit_package(
            package,
            recommendation=recommendation,
            persist=False
        )

        self.last_metrics = {
            "total_seconds": round(time.perf_counter() - started, 3),
            "asset_count": len(assets),
            "package_type": package_type,
            "include_mock": include_mock
        }
        logger.info(
            "Communication package generated type=%s title=%s assets=%s elapsed=%s",
            package_type,
            package.get("headline", ""),
            len(assets),
            self.last_metrics["total_seconds"]
        )

        return package

    ############################################################

    def generate_packages(self, recommendation, package_types=None, include_mock=False):

        return [
            self.generate_package(
                recommendation,
                package_type=package_type,
                include_mock=include_mock
            )
            for package_type in (package_types or self.PACKAGE_TYPES)
        ]

    ############################################################

    def _assets_for_recommendation(self, recommendation, include_mock=False):

        ids = self._asset_ids(recommendation)

        if ids:
            assets = self.db.communications_officer_assets(
                ids,
                limit=self.ASSET_LIMIT
            )
        else:
            assets = list(recommendation.get("recommended_media") or [])

        filtered = []

        for asset in assets:
            if self._is_rejected_or_failed(asset):
                continue

            if not include_mock and asset.get("provider") == "mock":
                continue

            filtered.append(
                self._effective_asset(asset)
            )

        reviewed = [
            asset
            for asset in filtered
            if self._is_reviewed(asset)
        ]

        return reviewed or filtered

    ############################################################

    def _effective_asset(self, asset):

        media_id = asset.get("media_id")

        if not media_id:
            return asset

        try:
            effective = self.feedback.effective_media_intelligence_row(
                media_id
            )
        except Exception:
            return asset

        effective.update({
            "media_id": media_id,
            "filename": asset.get("filename", ""),
            "path": asset.get("path", ""),
            "media_type": asset.get("media_type", ""),
            "provider": asset.get("provider", ""),
            "model": asset.get("model", ""),
            "failure_reason": asset.get("failure_reason", "")
        })

        return effective

    ############################################################

    def _asset_ids(self, recommendation):

        ids = []

        for key in ("best_asset_ids", "supporting_asset_ids"):
            ids.extend(recommendation.get(key) or [])

        for item in recommendation.get("recommended_media") or []:
            ids.append(item.get("media_id"))

        package = recommendation.get("media_package") or {}

        for key in (
            "best_photo",
            "best_video",
            "primary_photo",
            "primary_video"
        ):
            ids.append((package.get(key) or {}).get("media_id"))

        for key in (
            "supporting_photos",
            "supporting_videos",
            "gallery_photos",
            "gallery_videos"
        ):
            for item in package.get(key) or []:
                ids.append(item.get("media_id"))

        return self._unique(
            self._to_int(value)
            for value in ids
            if self._to_int(value)
        )[:self.ASSET_LIMIT]

    ############################################################

    def _media_package(self, recommendation, assets):

        photos = [
            asset
            for asset in assets
            if asset.get("media_type") == "image"
        ]
        videos = [
            asset
            for asset in assets
            if asset.get("media_type") == "video"
        ]
        photos.sort(key=self._asset_score, reverse=True)
        videos.sort(key=self._asset_score, reverse=True)
        scores = [
            self._to_int(asset.get("communications_score"))
            for asset in assets
        ]

        return {
            "primary_photo": self._asset_summary(photos[0]) if photos else {},
            "gallery_photos": [
                self._asset_summary(asset)
                for asset in photos[1:6]
            ],
            "primary_video": self._asset_summary(videos[0]) if videos else {},
            "gallery_videos": [
                self._asset_summary(asset)
                for asset in videos[1:4]
            ],
            "story_strength": recommendation.get("story_strength", {}),
            "communications_score": (
                round(sum(scores) / len(scores), 1)
                if scores
                else 0
            ),
            "editorial_angle": (
                recommendation.get("editorial_angle")
                or recommendation.get("caption_theme")
                or ""
            )
        }

    def _asset_summary(self, asset):

        return {
            "media_id": asset.get("media_id"),
            "filename": asset.get("filename", ""),
            "path": asset.get("path", ""),
            "media_type": asset.get("media_type", ""),
            "communications_score": asset.get("communications_score", 0),
            "intelligence_score": asset.get("intelligence_score", 0),
            "trust_state": asset.get("trust_state", ""),
            "review_status": asset.get("review_status", ""),
            "provider": asset.get("provider", ""),
            "content_tags": list(asset.get("content_tags") or [])[:6],
            "recommended_uses": list(asset.get("recommended_uses") or [])[:5]
        }

    ############################################################

    def _writing_strategy(self, recommendation, package_type, guidance, media_package):

        return {
            "purpose": guidance["purpose"],
            "tone": guidance["tone"],
            "length": guidance["length"],
            "audience": self._audience(recommendation),
            "call_to_action_strategy": guidance["call_to_action"],
            "visual_strategy": guidance["visual"],
            "platform_notes": guidance["notes"],
            "story_approach": (
                f"Lead with {recommendation.get('title', 'the strongest story')} "
                f"and support it with the selected {media_package.get('editorial_angle', 'editorial')} angle."
            )
        }

    def _publishing_strategy(self, package_type, scoring, recommendation):

        return {
            "package_type": package_type,
            "priority": recommendation.get("priority") or self._priority_label(
                recommendation.get("priority_score", 0)
            ),
            "recommended_time": (
                recommendation.get("recommended_posting_window")
                or recommendation.get("best_posting_time")
                or "Next appropriate posting window"
            ),
            "platform_fit": scoring["platform_fit"],
            "decision_note": (
                f"Use this as a {package_type} package if the trust level and media evidence are acceptable."
            )
        }

    def _package_scoring(self, recommendation, media_package, assets):

        story = recommendation.get("story_strength") or {}
        story_score = self._to_int(story.get("overall"))
        media_score = self._to_int(media_package.get("communications_score"))
        confidence = self._to_int(
            recommendation.get("confidence")
            or recommendation.get("confidence_score")
        )
        review_score = self._review_score(assets)
        platform_fit = self._platform_fit(recommendation)
        values = [
            value
            for value in (
                story_score,
                media_score,
                confidence,
                review_score,
                platform_fit
            )
            if value
        ]

        return {
            "overall_score": round(sum(values) / len(values), 1) if values else 0,
            "story_score": story_score,
            "media_score": media_score,
            "confidence": confidence,
            "platform_fit": platform_fit,
            "review_score": review_score
        }

    ############################################################

    def _supporting_evidence(self, recommendation, assets):

        evidence = list(recommendation.get("source_signals") or [])[:4]

        for asset in assets[:4]:
            name = asset.get("filename", "")
            score = asset.get("communications_score", 0)
            trust = asset.get("trust_state") or asset.get("review_status") or "unreviewed"

            if name:
                evidence.append(
                    f"{name}: communications score {score}, trust {trust}"
                )

            description = (
                asset.get("effective_description") or
                asset.get("description", "")
            )

            if description:
                evidence.append(
                    "Effective description: " + description[:220]
                )

        return evidence[:8]

    def _hashtags(self, recommendation, assets, package_type):

        terms = []
        terms.extend(recommendation.get("supporting_topics") or [])
        terms.extend(recommendation.get("supporting_programs") or [])
        terms.extend(recommendation.get("positive_factors") or [])
        terms.append(recommendation.get("editorial_angle", ""))

        for asset in assets[:5]:
            terms.extend(asset.get("content_tags") or [])
            terms.extend(asset.get("recommended_uses") or [])

        defaults = {
            "Facebook": ["#MordenFireRescue", "#CommunitySafety"],
            "Instagram": ["#MordenFireRescue", "#Morden", "#FireService"],
            "LinkedIn": ["#PublicSafety", "#Leadership", "#CommunityService"],
            "Website article": ["#MordenFireRescue", "#FireSafety"],
            "News Release": ["#PublicSafety", "#Morden"],
            "Newsletter": ["#MordenFireRescue", "#Community"]
        }
        tags = []

        for term in terms:
            tag = self._hashtag(term)

            if tag and tag not in tags:
                tags.append(tag)

        for tag in defaults.get(package_type, []):
            if tag not in tags:
                tags.append(tag)

        return tags[:5]

    def _cta(self, recommendation, package_type):

        existing = recommendation.get("call_to_action")

        if existing:
            return existing

        if "Recruit" in str(recommendation.get("title", "")):
            return "Learn how you can serve your community with Morden Fire & Rescue."

        if package_type == "News Release":
            return "For more information, follow official Morden Fire & Rescue updates."

        return "Stay connected with Morden Fire & Rescue for local safety updates."

    def _audience(self, recommendation):

        return (
            recommendation.get("recommended_audiences")
            or recommendation.get("estimated_audience")
            or ["Morden residents"]
        )

    def _platforms(self, recommendation, package_type):

        platforms = list(recommendation.get("recommended_platforms") or [])

        if package_type not in platforms:
            platforms.insert(0, package_type)

        return self._unique(platforms)[:6]

    ############################################################

    def _trust_level(self, assets):

        if any(self._is_reviewed(asset) for asset in assets):
            return "reviewed"

        if assets:
            return "fallback_unreviewed"

        return "unknown"

    def _trust_label(self, assets):

        level = self._trust_level(assets)

        if level == "reviewed":
            return "Reviewed evidence"

        if level == "fallback_unreviewed":
            return "Fallback: unreviewed evidence"

        return "Trust state unknown"

    def _review_score(self, assets):

        if not assets:
            return 0

        reviewed = sum(1 for asset in assets if self._is_reviewed(asset))

        return round((reviewed / len(assets)) * 100)

    def _platform_fit(self, recommendation):

        platforms = recommendation.get("recommended_platforms") or []

        if not platforms:
            return 50

        if len(platforms) >= 3:
            return 85

        return 70

    def _priority_label(self, score):

        score = self._to_int(score)

        if score >= 75:
            return "High"

        if score >= 45:
            return "Medium"

        return "Low"

    def _asset_score(self, asset):

        return (
            self._to_int(asset.get("communications_score")),
            self._to_int(asset.get("storytelling_score")),
            self._to_int(asset.get("intelligence_score")),
            1 if self._is_reviewed(asset) else 0,
            asset.get("filename", "")
        )

    def _is_reviewed(self, asset):

        return (
            asset.get("trust_state") in ("approved_real", "corrected_real")
            or asset.get("review_status") in ("approved", "corrected")
        )

    def _is_rejected_or_failed(self, asset):

        return (
            bool(asset.get("failure_reason"))
            or asset.get("trust_state") in ("rejected_real", "failed")
            or asset.get("review_status") == "rejected"
        )

    def _package_type(self, value):

        for package_type in self.PACKAGE_TYPES:
            if str(value or "").lower() == package_type.lower():
                return package_type

        return "Facebook"

    def _hashtag(self, value):

        text = str(value or "").strip()

        if not text:
            return ""

        text = text.split("(")[0].strip()
        words = [
            word
            for word in text.replace("_", " ").replace("-", " ").split()
            if word.isalnum()
        ]

        if not words:
            return ""

        return "#" + "".join(word[:24].title() for word in words)[:40]

    def _to_int(self, value):

        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:
            if value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
