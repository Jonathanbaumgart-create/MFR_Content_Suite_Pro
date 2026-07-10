from core.app_context import context
from services.editorial_strategy_service import EditorialStrategyService
from services.logging_service import LoggingService
from services.recommendation_learning_service import RecommendationLearningService


logger = LoggingService.get_logger("content")


class EditorialComparisonService:

    WEIGHTS = {
        "strategic_fit": 0.18,
        "context_relevance": 0.12,
        "department_priority": 0.12,
        "audience_value": 0.12,
        "communications_score": 0.16,
        "originality": 0.09,
        "posting_history_risk": 0.08,
        "seasonal_relevance": 0.05,
        "authenticity": 0.04,
        "content_gap_value": 0.02,
        "learning_alignment": 0.02
    }

    def __init__(
        self,
        database=None,
        strategy_service=None,
        learning_service=None
    ):

        self.db = database or context.database
        self.strategy_service = strategy_service or EditorialStrategyService(
            database=self.db
        )
        self.learning = learning_service or RecommendationLearningService(
            database=self.db
        )

    ############################################################

    def compare(self, media_id, strategies=None, persist=True):

        strategies = strategies or self.strategy_service.strategies_for_media(
            media_id,
            generate_if_missing=True,
            limit=6
        )

        scored = [
            {
                **strategy,
                "comparison_score": self._comparison_score(strategy)
            }
            for strategy in strategies
        ]
        scored.sort(
            key=lambda item: item["comparison_score"],
            reverse=True
        )

        recommended = scored[0] if scored else None
        runner_up = scored[1] if len(scored) > 1 else None

        comparison = {
            "media_id": media_id,
            "recommended_strategy": recommended,
            "runner_up": runner_up,
            "alternative_strategies": scored[1:3],
            "comparison_summary": self._summary(
                recommended,
                runner_up
            ),
            "tradeoffs": self._tradeoffs(scored),
            "why_not_others": self._why_not_others(scored),
            "debate_summary": self._debate(scored),
            "confidence": self._confidence(recommended, runner_up)
        }

        if persist and self.db and recommended:
            self.db.save_editorial_comparison(
                media_id,
                comparison
            )

        logger.info(
            "Compared editorial strategies media_id=%s recommended=%s confidence=%s",
            media_id,
            recommended.get("strategy_type") if recommended else "",
            comparison["confidence"]
        )

        return comparison

    ############################################################

    def latest_or_compare(self, media_id):

        latest = self.latest(media_id)

        if latest:
            return latest

        return self.compare(
            media_id,
            strategies=None,
            persist=True
        )

    ############################################################

    def latest(self, media_id):

        comparison = self.db.latest_editorial_comparison(media_id)
        strategies = self.db.editorial_strategies_for_media(
            media_id,
            limit=6
        )

        if comparison and strategies:
            by_id = {
                strategy["strategy_id"]: strategy
                for strategy in strategies
            }
            recommended = by_id.get(
                comparison.get("recommended_strategy_id")
            )
            runner_up = by_id.get(
                comparison.get("runner_up_strategy_id")
            )

            if recommended:
                return {
                    "media_id": media_id,
                    "recommended_strategy": recommended,
                    "runner_up": runner_up,
                    "alternative_strategies": [
                        strategy
                        for strategy in strategies
                        if strategy.get("strategy_id") != recommended.get("strategy_id")
                    ][:2],
                    "comparison_summary": comparison.get("comparison_summary", ""),
                    "tradeoffs": comparison.get("tradeoffs", []),
                    "why_not_others": comparison.get("why_not_others", []),
                    "debate_summary": comparison.get("debate_summary", ""),
                    "confidence": comparison.get("confidence", 0)
                }

        return None

    ############################################################

    def record_viewed(self, media_id, strategy):

        return self._record_feedback(
            media_id,
            strategy,
            "strategy_viewed"
        )

    ############################################################

    def select_strategy(self, media_id, strategy):

        strategy_id = strategy.get("strategy_id", "")
        self.db.mark_editorial_strategy(
            media_id,
            strategy_id,
            selected=True,
            dismissed=False
        )
        return self._record_feedback(
            media_id,
            strategy,
            "strategy_selected"
        )

    ############################################################

    def dismiss_strategy(self, media_id, strategy):

        strategy_id = strategy.get("strategy_id", "")
        self.db.mark_editorial_strategy(
            media_id,
            strategy_id,
            dismissed=True,
            selected=False
        )
        return self._record_feedback(
            media_id,
            strategy,
            "strategy_dismissed"
        )

    ############################################################

    def alternative_requested(self, media_id, strategy):

        return self._record_feedback(
            media_id,
            strategy,
            "strategy_alternative_requested"
        )

    ############################################################

    def _record_feedback(self, media_id, strategy, feedback_type):

        recommendation = {
            "recommendation_id": (
                f"strategy:{media_id}:{strategy.get('strategy_id', '')}"
            ),
            "opportunity_type": strategy.get("strategy_type", ""),
            "confidence": strategy.get("confidence", 0),
            "recommended_media": [
                {
                    "media_id": media_id
                }
            ]
        }
        mapped = {
            "strategy_selected": "accepted",
            "strategy_dismissed": "dismissed",
            "strategy_viewed": "viewed",
            "strategy_alternative_requested": "regenerated"
        }.get(
            feedback_type,
            "viewed"
        )

        return self.learning.record_feedback(
            recommendation,
            mapped,
            media={"media_id": media_id},
            notes=feedback_type
        )

    ############################################################

    def _comparison_score(self, strategy):

        confidence = int(strategy.get("confidence") or 0)
        communications = int(strategy.get("communications_score") or 0)
        evidence_count = len(strategy.get("supporting_evidence") or [])
        limitation_count = len(strategy.get("limitations") or [])
        risk_count = len(strategy.get("risks") or [])
        platform_count = len(strategy.get("recommended_platforms") or [])

        scores = {
            "strategic_fit": confidence,
            "context_relevance": self._evidence_score(strategy, "Current context"),
            "department_priority": self._evidence_score(strategy, "Knowledge graph"),
            "audience_value": min(100, 45 + platform_count * 12),
            "communications_score": communications,
            "originality": 85 if self._has_evidence(strategy, "no prior post") else 45,
            "posting_history_risk": max(0, 90 - risk_count * 18),
            "seasonal_relevance": self._evidence_score(strategy, "context"),
            "authenticity": max(45, 90 - limitation_count * 8),
            "content_gap_value": 55,
            "learning_alignment": 55
        }

        score = sum(
            scores[key] * weight
            for key, weight in self.WEIGHTS.items()
        )
        score += min(8, evidence_count * 1.5)

        return round(score, 1)

    ############################################################

    def _summary(self, recommended, runner_up):

        if not recommended:
            return "No editorial strategy could be recommended."

        summary = (
            f"{recommended['title']} is strongest because it has "
            f"{recommended['confidence']}% confidence and the clearest fit "
            "with the stored intelligence."
        )

        if runner_up:
            summary += (
                f" {runner_up['title']} is a credible runner-up, but its "
                "strategic fit is slightly weaker."
            )

        return summary

    ############################################################

    def _tradeoffs(self, strategies):

        tradeoffs = []

        for strategy in strategies[:3]:
            risks = strategy.get("risks") or []
            limitations = strategy.get("limitations") or []
            line = (
                f"{strategy['title']}: strong for "
                f"{strategy['target_audience']} with "
                f"{strategy['confidence']}% confidence"
            )

            if risks:
                line += "; risk: " + risks[0]
            elif limitations:
                line += "; limitation: " + limitations[0]

            tradeoffs.append(line)

        return tradeoffs

    ############################################################

    def _why_not_others(self, strategies):

        if len(strategies) <= 1:
            return []

        top = strategies[0]
        reasons = []

        for strategy in strategies[1:4]:
            gap = top["comparison_score"] - strategy["comparison_score"]
            reason = (
                f"{strategy['title']} was not selected because its comparison "
                f"score was {round(gap, 1)} points lower."
            )

            if strategy.get("risks"):
                reason += " " + strategy["risks"][0]
            elif strategy.get("limitations"):
                reason += " " + strategy["limitations"][0]

            reasons.append(reason)

        return reasons

    ############################################################

    def _debate(self, strategies):

        if not strategies:
            return "No strategy debate is available."

        top = strategies[0]
        runner = strategies[1] if len(strategies) > 1 else None
        third = strategies[2] if len(strategies) > 2 else None
        parts = [
            (
                f"{top['title']} is strongest because {self._main_reason(top)}"
            )
        ]

        if runner:
            parts.append(
                (
                    f"{runner['title']} is also viable because "
                    f"{self._main_reason(runner)}, but it is less compelling "
                    "on balance."
                )
            )

        if third:
            parts.append(
                (
                    f"{third['title']} remains useful as an alternate angle, "
                    "especially if the communications goal changes."
                )
            )

        return " ".join(parts)

    ############################################################

    def _main_reason(self, strategy):

        evidence = strategy.get("supporting_evidence") or []

        if evidence:
            return evidence[0].rstrip(".").lower()

        reasoning = strategy.get("reasoning") or []

        if reasoning:
            return reasoning[0].rstrip(".").lower()

        return "it has the best strategic fit"

    ############################################################

    def _confidence(self, recommended, runner_up):

        if not recommended:
            return 0

        value = int(recommended.get("comparison_score", 0))

        if runner_up:
            value += min(
                10,
                int(recommended["comparison_score"] - runner_up["comparison_score"])
            )

        return max(0, min(100, value))

    ############################################################

    def _evidence_score(self, strategy, text):

        if self._has_evidence(strategy, text):
            return 82

        return 45

    ############################################################

    def _has_evidence(self, strategy, text):

        text = text.lower()
        values = (
            (strategy.get("supporting_evidence") or []) +
            (strategy.get("reasoning") or [])
        )

        return any(
            text in value.lower()
            for value in values
        )
