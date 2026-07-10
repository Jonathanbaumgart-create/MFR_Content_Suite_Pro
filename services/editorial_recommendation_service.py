import hashlib
import threading
import time

from core.app_context import context
from models.editorial_recommendation import EditorialRecommendation
from services.logging_service import LoggingService
from services.recommendation_candidate_service import RecommendationCandidateService
from services.recommendation_scoring_service import RecommendationScoringService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class EditorialRecommendationService:

    DEFAULT_LIMIT = 5

    def __init__(
        self,
        database=None,
        candidate_service=None,
        scoring_service=None
    ):

        self.db = database or context.database
        self.candidates = candidate_service or RecommendationCandidateService(
            database=self.db
        )
        self.scoring = scoring_service or RecommendationScoringService()
        self.last_metrics = {}

    ############################################################

    def generate_recommendations(self, limit=DEFAULT_LIMIT, as_of=None):

        started = time.perf_counter()
        limit = max(0, min(int(limit or self.DEFAULT_LIMIT), 10))
        ran_on_main_thread = threading.current_thread() is threading.main_thread()

        logger.info(
            (
                "Editorial recommendation generation started limit=%s "
                "scoring_version=%s main_thread=%s"
            ),
            limit,
            self.scoring.SCORING_VERSION,
            ran_on_main_thread
        )

        if limit <= 0:
            self.last_metrics = {
                "total_seconds": 0,
                "candidate_seconds": 0,
                "scoring_seconds": 0,
                "candidate_count": 0,
                "returned_count": 0,
                "ran_on_main_thread": ran_on_main_thread,
                "scoring_version": self.scoring.SCORING_VERSION
            }
            return []

        try:
            candidate_started = time.perf_counter()
            candidates = self.candidates.build_candidates(
                as_of=as_of
            )
            candidate_seconds = round(
                time.perf_counter() - candidate_started,
                3
            )
        except Exception as ex:
            logger.error(
                "Editorial recommendation candidate generation failed",
                exc_info=(type(ex), ex, ex.__traceback__)
            )
            self.last_metrics = {
                "total_seconds": round(time.perf_counter() - started, 3),
                "candidate_seconds": 0,
                "scoring_seconds": 0,
                "candidate_count": 0,
                "returned_count": 0,
                "ran_on_main_thread": ran_on_main_thread,
                "scoring_version": self.scoring.SCORING_VERSION,
                "error": str(ex)
            }
            return []

        recommendations = []
        filtered_count = 0
        scoring_started = time.perf_counter()

        for candidate in candidates:
            scored = self.scoring.score_candidate(candidate)

            if not candidate["assets"]:
                filtered_count += 1
                continue

            if scored["priority_score"] <= 0:
                filtered_count += 1
                continue

            recommendations.append(
                self._recommendation(
                    candidate,
                    scored
                )
            )

        scoring_seconds = round(time.perf_counter() - scoring_started, 3)
        for recommendation in recommendations:
            self._attach_ordering_inputs(recommendation)

        recommendations.sort(
            key=lambda item: (
                item.final_order_score,
                item.title
            ),
            reverse=True
        )
        recommendations, diversity_pruned = self._diverse_recommendations(
            recommendations,
            limit
        )
        elapsed = round(time.perf_counter() - started, 3)
        confidence_values = [
            item.confidence_score
            for item in recommendations
        ]
        self.last_metrics = {
            "total_seconds": elapsed,
            "candidate_seconds": candidate_seconds,
            "candidate_breakdown": getattr(
                self.candidates,
                "last_metrics",
                {}
            ),
            "scoring_seconds": scoring_seconds,
            "candidate_count": len(candidates),
            "returned_count": len(recommendations),
            "filtered_count": filtered_count,
            "diversity_pruned_count": diversity_pruned,
            "confidence_min": min(confidence_values) if confidence_values else 0,
            "confidence_max": max(confidence_values) if confidence_values else 0,
            "ran_on_main_thread": ran_on_main_thread,
            "scoring_version": self.scoring.SCORING_VERSION
        }

        logger.info(
            (
                "Editorial recommendation generation completed "
                "candidates=%s filtered=%s diversity_pruned=%s returned=%s elapsed=%s "
                "candidate_seconds=%s scoring_seconds=%s "
                "confidence_range=%s-%s main_thread=%s scoring_version=%s"
            ),
            len(candidates),
            filtered_count,
            diversity_pruned,
            len(recommendations),
            elapsed,
            candidate_seconds,
            scoring_seconds,
            self.last_metrics["confidence_min"],
            self.last_metrics["confidence_max"],
            ran_on_main_thread,
            self.scoring.SCORING_VERSION
        )

        return [
            recommendation.to_dict()
            for recommendation in recommendations
        ]

    ############################################################

    def _recommendation(self, candidate, scored):

        profile = candidate["profile"]
        assets = candidate["assets"]
        best_assets = sorted(
            assets,
            key=self._asset_rank_key,
            reverse=True
        )[:self.candidates.MAX_BEST_IDS]
        supporting_ids = [
            asset.get("media_id")
            for asset in assets[:self.candidates.MAX_SUPPORTING_IDS]
        ]
        best_ids = [
            asset.get("media_id")
            for asset in best_assets
        ]
        photo_count = self._media_count(assets, "image")
        video_count = self._media_count(assets, "video")
        title = profile["title"]
        recommendation_id = self._recommendation_id(
            profile,
            best_ids
        )
        source_signals = self._source_signals(
            candidate,
            scored,
            best_assets
        )

        return EditorialRecommendation(
            recommendation_id=recommendation_id,
            title=title,
            topic=profile["topic"],
            category=profile["category"],
            priority_score=scored["priority_score"],
            confidence_score=scored["confidence_score"],
            summary=self._summary(
                profile,
                photo_count,
                video_count,
                scored,
                candidate
            ),
            primary_reason=scored["primary_reason"],
            headline=title,
            reasoning_factors=scored["reasoning_factors"],
            supporting_topics=self._supporting_topics(candidate),
            supporting_programs=candidate.get("supporting_programs", []),
            story_strength=scored.get("story_strength", {}),
            confidence_limitations=scored.get("confidence_limitations", []),
            editorial_angle=(profile.get("editorial_angles") or ("",))[0],
            topic_agreement_score=scored.get("topic_agreement", 0),
            supporting_photo_count=photo_count,
            supporting_video_count=video_count,
            supporting_asset_ids=supporting_ids,
            best_asset_ids=best_ids,
            editorial_angles=list(profile["editorial_angles"])[:5],
            recommended_platforms=self._platforms(
                profile,
                best_assets
            ),
            recommended_audiences=list(profile["audiences"])[:4],
            recommended_content_formats=self._formats(
                profile,
                video_count
            ),
            recommended_posting_window=profile["posting_window"],
            communications_gap=scored["communications_gap"],
            repetition_risk=scored["repetition_risk"],
            source_signals=source_signals,
            generated_at=TimeService.utc_now_iso(),
            scoring_version=self.scoring.SCORING_VERSION
        )

    ############################################################

    def _summary(self, profile, photos, videos, scored, candidate):

        topics = self._supporting_topics(candidate)
        topic_text = ", ".join(topics[:3]) if topics else profile["category"]

        return (
            f"{topic_text} ranks at {scored['priority_score']} priority "
            f"with {photos} photo(s) and {videos} video(s) supporting it. "
            f"{scored['primary_reason']}."
        )

    def _source_signals(self, candidate, scored, assets):

        signals = [
            f"Scoring version {self.scoring.SCORING_VERSION}",
            f"Raw scoring factor total {scored['raw_score']}",
            "Uses Effective Intelligence with active human corrections applied.",
            "Uses stored Media Intelligence, Fire Service Intelligence, Communications Memory, Department Knowledge, Knowledge Graph, and local Context Engine data.",
            "No Vision AI, LLM, cloud service, external API, image decoding, or video processing was used."
        ]
        memory = candidate["memory_profile"]

        if memory["memory_available"]:
            signals.append(
                (
                    "Communications Memory matching posts: "
                    f"{memory['matching_posts']} of "
                    f"{memory.get('history_post_count', 0)} stored post(s)"
                )
            )
        else:
            signals.append(
                "Communications Memory has no imported or generated posts yet."
            )

        if candidate.get("knowledge_signals"):
            signals.append(
                "Department Knowledge matches: " +
                ", ".join(candidate["knowledge_signals"][:5])
            )

        for asset in assets[:3]:
            signals.append(
                (
                    f"Asset {asset.get('media_id')} "
                    f"{asset.get('filename', '')}: "
                    f"communications {asset.get('communications_score', 0)}, "
                    f"intelligence {asset.get('intelligence_score', 0)}, "
                    f"matches {', '.join(asset.get('matched_terms', [])[:5])}"
                )
            )

        return signals

    def _supporting_topics(self, candidate):

        topics = list(candidate.get("supporting_topics") or [])

        if not topics:
            for asset in candidate.get("assets", [])[:5]:
                for topic in asset.get("topics", [])[:2]:
                    topics.append(topic.get("label", ""))

        return [
            value
            for value in self._unique(topics)
            if value
        ][:6]

    def _platforms(self, profile, assets):

        platform_scores = {}

        for asset in assets:
            suitability = asset.get("platform_suitability") or {}

            if isinstance(suitability, dict):
                for platform, score in suitability.items():
                    platform_scores[platform] = max(
                        platform_scores.get(platform, 0),
                        int(score or 0)
                    )

        profile_platforms = list(profile["platforms"])

        if not platform_scores:
            return profile_platforms[:3]

        ranked = [
            platform
            for platform, _score in sorted(
                platform_scores.items(),
                key=lambda item: item[1],
                reverse=True
            )
        ]

        combined = []

        for platform in profile_platforms + ranked:
            label = str(platform).replace("_", " ").title()

            if label not in combined:
                combined.append(label)

        return combined[:4]

    def _formats(self, profile, video_count):

        formats = list(profile["formats"])

        if video_count and "short-form video" not in formats:
            formats.insert(0, "short-form video")

        return formats[:4]

    def _recommendation_id(self, profile, asset_ids):

        source = "|".join(
            [
                self.scoring.SCORING_VERSION,
                profile["topic"],
                ",".join(str(value) for value in asset_ids)
            ]
        )

        return hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]

    def _diverse_recommendations(self, recommendations, limit):

        selected = []
        deferred = []
        seen = set()

        for recommendation in recommendations:
            key = (
                recommendation.topic,
                recommendation.editorial_angle,
                tuple(recommendation.recommended_audiences[:1])
            )

            if key in seen:
                deferred.append(recommendation)
                continue

            seen.add(key)
            selected.append(recommendation)

            if len(selected) >= limit:
                break

        if len(selected) < limit:
            for recommendation in deferred:
                if recommendation in selected:
                    continue

                selected.append(recommendation)

                if len(selected) >= limit:
                    break

        return selected[:limit], max(0, len(recommendations) - len(selected))

    def _attach_ordering_inputs(self, recommendation):

        recommendation.specificity_score = self._specificity_score(
            recommendation
        )
        recommendation.media_support_score = min(
            10,
            recommendation.supporting_photo_count +
            recommendation.supporting_video_count * 2
        )
        recommendation.communications_gap_score = self._gap_score(
            recommendation.communications_gap
        )
        recommendation.repetition_penalty = self._repetition_penalty(
            recommendation.repetition_risk
        )
        recommendation.diversity_adjustment = 0
        recommendation.final_order_score = round(
            (
                recommendation.priority_score * 1.0 +
                recommendation.confidence_score * 0.35 +
                recommendation.story_strength.get("overall", 0) * 0.25 +
                recommendation.specificity_score * 4.0 +
                recommendation.media_support_score * 1.5 +
                recommendation.topic_agreement_score * 2.0 +
                recommendation.communications_gap_score +
                recommendation.repetition_penalty +
                self._generic_penalty(recommendation)
            ),
            2
        )
        recommendation.ordering_tuple = (
            recommendation.final_order_score,
            recommendation.priority_score,
            recommendation.confidence_score,
            recommendation.story_strength.get("overall", 0),
            recommendation.specificity_score,
            recommendation.media_support_score,
            recommendation.topic_agreement_score,
            recommendation.title
        )

    def _specificity_score(self, recommendation):

        score = 0

        if recommendation.supporting_topics:
            score += 2

        if not recommendation.title.endswith("Opportunity"):
            score += 3

        if recommendation.editorial_angle:
            score += 1

        return score

    def _gap_score(self, gap):

        text = str(gap or "").lower()

        if "no matching" in text:
            return 8

        if "no similar content" in text:
            return 6

        if "last similar post" in text:
            return 2

        return 0

    def _repetition_penalty(self, risk):

        text = str(risk or "").lower()

        if text == "high":
            return -20

        if text == "medium":
            return -8

        return 0

    def _generic_penalty(self, recommendation):

        if recommendation.title.endswith("Opportunity"):
            return -10

        return 0

    def _asset_rank_key(self, asset):

        return (
            int(asset.get("communications_score") or 0),
            int(asset.get("storytelling_score") or 0),
            int(asset.get("intelligence_score") or 0),
            int((asset.get("fire_service_intelligence") or {}).get("operational_confidence") or 0),
            1 if asset.get("is_human_corrected") else 0,
            1 if asset.get("media_type") == "video" else 0,
            asset.get("filename", "")
        )

    def _media_count(self, assets, media_type):

        return sum(
            1
            for asset in assets
            if str(asset.get("media_type", "")).lower() == media_type
        )

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:
            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
