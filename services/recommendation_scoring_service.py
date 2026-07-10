from datetime import datetime


class RecommendationScoringService:

    SCORING_VERSION = "1.1"

    WEIGHTS = {
        "base": 35.0,
        "strong_photos": 1.2,
        "strong_videos": 2.0,
        "media_quality": 0.16,
        "editorial_value": 0.18,
        "communications_gap": 18.0,
        "stale_gap": 10.0,
        "seasonal_alignment": 12.0,
        "knowledge_alignment": 7.0,
        "topic_evidence": 16.0,
        "story_strength": 14.0,
        "topic_agreement": 8.0,
        "unused_media": 10.0,
        "human_correction": 4.0,
        "recent_repetition": -16.0,
        "campaign_fatigue": -10.0,
        "low_confidence": -12.0,
        "mock_source": -18.0,
        "recent_media_use": -14.0,
        "unresolved_conflict": -10.0
    }

    CONFIDENCE_WEIGHTS = {
        "intelligence": 0.32,
        "communications": 0.28,
        "fire_service": 0.16,
        "support": 0.12,
        "corrections": 0.06,
        "memory": 0.06
    }

    def score_candidate(self, candidate):

        profile = candidate["profile"]
        assets = candidate["assets"]
        snapshot = candidate["snapshot"]
        memory = candidate["memory_profile"]
        factors = [
            self._factor(
                "base",
                "Baseline editorial planning value",
                self.WEIGHTS["base"] if not candidate.get("is_topic_candidate") else 22.0,
                "positive"
            )
        ]
        photo_count = self._media_count(assets, "image")
        video_count = self._media_count(assets, "video")
        average_quality = self._average_quality(assets)
        editorial_value = self._average_editorial_value(
            assets,
            profile
        )
        story = self.story_strength(candidate)
        topic_count = len(candidate.get("supporting_topics") or [])
        topic_agreement = self._topic_agreement(candidate)

        if photo_count:
            factors.append(
                self._factor(
                    "strong_photo_availability",
                    f"{photo_count} supporting photo(s)",
                    min(18, photo_count * self.WEIGHTS["strong_photos"]),
                    "positive"
                )
            )

        if video_count:
            factors.append(
                self._factor(
                    "strong_video_availability",
                    f"{video_count} supporting video(s)",
                    min(12, video_count * self.WEIGHTS["strong_videos"]),
                    "positive"
                )
            )

        factors.append(
            self._factor(
                "media_quality",
                f"Average stored media quality {round(average_quality, 1)}",
                average_quality * self.WEIGHTS["media_quality"],
                "positive"
            )
        )
        factors.append(
            self._factor(
                "editorial_value",
                f"Average editorial value {round(editorial_value, 1)}",
                editorial_value * self.WEIGHTS["editorial_value"],
                "positive"
            )
        )

        if candidate.get("is_topic_candidate"):
            factors.append(
                self._factor(
                    "topic_evidence",
                    (
                        "Evidence supports " +
                        ", ".join(candidate.get("supporting_topics") or [profile["category"]])
                    ),
                    min(
                        self.WEIGHTS["topic_evidence"],
                        max(6, topic_count * 8)
                    ),
                    "positive"
                )
            )

        if story["overall"] >= 55:
            factors.append(
                self._factor(
                    "story_strength",
                    f"Story strength {story['overall']}",
                    min(
                        self.WEIGHTS["story_strength"],
                        story["overall"] * 0.14
                    ),
                    "positive"
                )
            )

        if topic_agreement >= 2:
            factors.append(
                self._factor(
                    "topic_agreement",
                    f"{topic_agreement} best asset(s) agree on the topic",
                    min(
                        self.WEIGHTS["topic_agreement"],
                        topic_agreement * 2
                    ),
                    "positive"
                )
            )

        if not memory["memory_available"]:
            factors.append(
                self._factor(
                    "communications_memory_unavailable",
                    "Communications Memory has no historical posts yet",
                    -4.0,
                    "negative"
                )
            )
        elif memory["matching_posts"] == 0:
            factors.append(
                self._factor(
                    "communication_gap",
                    f"No stored posts found for {profile['category']}",
                    self.WEIGHTS["communications_gap"],
                    "positive"
                )
            )
        else:
            days = self._days_since(memory.get("last_posted"))

            if days is not None and days <= 14:
                factors.append(
                    self._factor(
                        "recent_repetition",
                        f"Similar content posted {days} day(s) ago",
                        self.WEIGHTS["recent_repetition"],
                        "negative"
                    )
                )
            elif days is not None and days >= 60:
                factors.append(
                    self._factor(
                        "communications_gap",
                        f"No similar content in {days} day(s)",
                        self.WEIGHTS["stale_gap"],
                        "positive"
                    )
                )

            if memory["matching_posts"] >= 4:
                factors.append(
                    self._factor(
                        "campaign_fatigue",
                        f"{memory['matching_posts']} similar historical post(s)",
                        self.WEIGHTS["campaign_fatigue"],
                        "negative"
                    )
                )

        if self._seasonal_match(profile, snapshot):
            factors.append(
                self._factor(
                    "seasonal_alignment",
                    "Matches current local seasonal context",
                    self.WEIGHTS["seasonal_alignment"],
                    "positive"
                )
            )

        if candidate.get("knowledge_signals"):
            factors.append(
                self._factor(
                    "department_knowledge_alignment",
                    (
                        "Matches stored department knowledge: " +
                        ", ".join(candidate["knowledge_signals"][:3])
                    ),
                    self.WEIGHTS["knowledge_alignment"],
                    "positive"
                )
            )

        unused = [
            asset
            for asset in assets
            if asset.get("media_id") not in candidate["recent_social"]
            and asset.get("media_id") not in candidate["recent_recommended"]
        ]

        if unused:
            factors.append(
                self._factor(
                    "unused_underused_media",
                    f"{len(unused)} unused or underused supporting asset(s)",
                    self.WEIGHTS["unused_media"],
                    "positive"
                )
            )

        if any(asset.get("is_human_corrected") for asset in assets):
            factors.append(
                self._factor(
                    "human_correction",
                    "Uses human-corrected Effective Intelligence",
                    self.WEIGHTS["human_correction"],
                    "positive"
                )
            )

        recently_used = [
            asset
            for asset in assets[:5]
            if asset.get("media_id") in candidate["recent_social"]
            or asset.get("media_id") in candidate["recent_recommended"]
        ]

        if recently_used:
            factors.append(
                self._factor(
                    "recent_media_use",
                    f"{len(recently_used)} best asset(s) used or recommended recently",
                    self.WEIGHTS["recent_media_use"],
                    "negative"
                )
            )

        if self._low_confidence(assets):
            factors.append(
                self._factor(
                    "low_confidence_intelligence",
                    "Some supporting intelligence is low-confidence",
                    self.WEIGHTS["low_confidence"],
                    "negative"
                )
            )

        if self._mock_source(assets):
            factors.append(
                self._factor(
                    "mock_source",
                    "Some supporting assets are mock/test analysis",
                    self.WEIGHTS["mock_source"],
                    "negative"
                )
            )

        if self._unresolved_conflicts(assets):
            factors.append(
                self._factor(
                    "unresolved_conflict",
                    "Some media has unresolved or low-confidence correction signals",
                    self.WEIGHTS["unresolved_conflict"],
                    "negative"
                )
            )

        raw_score = round(
            sum(item["score"] for item in factors),
            1
        )
        priority = self._clamp(raw_score)
        confidence = self.confidence_score(
            candidate,
            factors
        )

        return {
            "priority_score": priority,
            "confidence_score": confidence,
            "raw_score": raw_score,
            "reasoning_factors": factors,
            "communications_gap": self._communications_gap(memory),
            "repetition_risk": self._repetition_risk(memory),
            "primary_reason": self._primary_reason(factors),
            "story_strength": story,
            "confidence_limitations": self._confidence_limitations(
                candidate,
                memory,
                story
            ),
            "topic_agreement": topic_agreement
        }

    ############################################################

    def confidence_score(self, candidate, factors=None):

        assets = candidate["assets"]
        memory = candidate["memory_profile"]
        intelligence = self._average(
            asset.get("intelligence_score", 0)
            for asset in assets
        )
        communications = self._average(
            asset.get("communications_score", 0) or
            asset.get("intelligence_score", 0)
            for asset in assets
        )
        fire = self._average(
            (asset.get("fire_service_intelligence") or {}).get(
                "operational_confidence",
                0
            )
            for asset in assets
        )
        support = min(100, len(assets) * 12)
        corrections = 75 if any(asset.get("is_human_corrected") for asset in assets) else 55
        memory_score = 50

        if not memory["memory_available"]:
            memory_score = 22
        elif memory.get("matching_posts"):
            memory_score = 78
        elif memory.get("history_post_count"):
            memory_score = 58

        story = self.story_strength(candidate)["overall"]
        topic_agreement = min(100, self._topic_agreement(candidate) * 20)

        score = (
            intelligence * self.CONFIDENCE_WEIGHTS["intelligence"] +
            communications * self.CONFIDENCE_WEIGHTS["communications"] +
            fire * self.CONFIDENCE_WEIGHTS["fire_service"] +
            support * self.CONFIDENCE_WEIGHTS["support"] +
            corrections * self.CONFIDENCE_WEIGHTS["corrections"] +
            memory_score * self.CONFIDENCE_WEIGHTS["memory"]
        )
        score = (
            score * 0.78 +
            story * 0.12 +
            topic_agreement * 0.10
        )

        if self._mock_source(assets):
            score -= 24

        if self._low_confidence(assets):
            score -= 14

        if not memory["memory_available"]:
            score -= 8

        if candidate.get("is_topic_candidate") and self._topic_agreement(candidate) < 2:
            score -= 6

        return self._clamp(score)

    ############################################################

    def story_strength(self, candidate):

        assets = candidate["assets"]
        profile = candidate["profile"]

        dimensions = {
            "educational": self._average(
                asset.get("educational_value_score", 0)
                or asset.get("public_education_value_score", 0)
                for asset in assets
            ),
            "emotional": self._average(
                asset.get("emotional_impact_score", 0)
                for asset in assets
            ),
            "operational": self._average(
                (asset.get("fire_service_intelligence") or {}).get(
                    "operational_confidence",
                    0
                )
                for asset in assets
            ),
            "community": self._average(
                asset.get("community_engagement_score", 0)
                or asset.get("trust_building_score", 0)
                for asset in assets
            ),
            "recruitment": self._average(
                asset.get("recruitment_value_score", 0)
                for asset in assets
            ),
            "leadership": self._field_bonus(assets, ("officer", "leadership", "command")),
            "preparedness": self._field_bonus(assets, ("preparedness", "safety", "prevention")),
            "historical": self._average(
                asset.get("historical_importance_score", 0)
                for asset in assets
            ),
            "human_interest": self._field_bonus(assets, ("firefighter", "children", "families", "crew", "people"))
        }
        fields = profile.get("score_fields") or ()
        focus = self._average(
            max(
                float(asset.get(field) or 0)
                for field in fields
            )
            if fields else 0
            for asset in assets
        )
        best_dimensions = sorted(
            dimensions.items(),
            key=lambda item: item[1],
            reverse=True
        )[:3]
        overall = self._clamp(
            (
                self._average(value for _key, value in best_dimensions) * 0.7
                + focus * 0.3
            )
        )

        return {
            "overall": overall,
            "dimensions": {
                key: self._clamp(value)
                for key, value in dimensions.items()
            },
            "strongest": [
                key
                for key, value in best_dimensions
                if value > 0
            ]
        }

    ############################################################

    def _factor(self, factor, label, score, direction):

        return {
            "factor": factor,
            "label": label,
            "score": round(float(score), 1),
            "direction": direction
        }

    def _topic_agreement(self, candidate):

        topic = candidate["profile"].get("topic", "")

        return sum(
            1
            for asset in candidate["assets"][:5]
            if any(
                item.get("topic") == topic
                for item in asset.get("topics", [])
            )
        )

    def _confidence_limitations(self, candidate, memory, story):

        limitations = []
        assets = candidate["assets"]

        if not memory["memory_available"]:
            limitations.append(
                "Communications Memory has no historical posts to compare."
            )
        elif not memory.get("matching_posts"):
            limitations.append(
                "Communications Memory exists, but no matching post history was found for this topic."
            )

        if len(assets) < 3:
            limitations.append(
                "Fewer than three supporting media assets were found."
            )

        if self._mock_source(assets):
            limitations.append(
                "Some supporting media came from mock/test analysis."
            )

        if self._low_confidence(assets):
            limitations.append(
                "Some supporting media has low intelligence confidence."
            )

        if story.get("overall", 0) < 55:
            limitations.append(
                "Story strength is limited by weak stored evidence."
            )

        return limitations

    def _media_count(self, assets, media_type):

        return sum(
            1
            for asset in assets
            if str(asset.get("media_type", "")).lower() == media_type
        )

    def _average_quality(self, assets):

        return self._average(
            asset.get("communications_score", 0) or
            asset.get("overall_score", 0) or
            asset.get("intelligence_score", 0)
            for asset in assets
        )

    def _average_editorial_value(self, assets, profile):

        fields = profile.get("score_fields") or ()
        values = []

        for asset in assets:
            field_values = [
                float(asset.get(field) or 0)
                for field in fields
            ]

            if field_values:
                values.append(max(field_values))

        return self._average(values)

    def _seasonal_match(self, profile, snapshot):

        terms = {
            self._token(value)
            for value in profile.get("terms", ())
        }
        context_terms = {
            self._token(value)
            for value in (
                list(getattr(snapshot, "active_themes", [])) +
                list(getattr(snapshot, "suggested_opportunities", []))
            )
        }

        return bool(terms & context_terms)

    def _communications_gap(self, memory):

        if not memory["memory_available"]:
            return "Communications Memory unavailable"

        if memory["matching_posts"] == 0:
            return "No matching historical posts"

        days = self._days_since(memory.get("last_posted"))

        if days is None:
            return "Historical timing unknown"

        return f"Last similar post {days} day(s) ago"

    def _repetition_risk(self, memory):

        if not memory["memory_available"]:
            return "Unknown"

        days = self._days_since(memory.get("last_posted"))

        if days is not None and days <= 14:
            return "High"

        if memory["matching_posts"] >= 4:
            return "Medium"

        return "Low"

    def _primary_reason(self, factors):

        preferred = {
            "topic_evidence",
            "story_strength",
            "topic_agreement",
            "seasonal_alignment",
            "communication_gap",
            "department_knowledge_alignment",
            "human_correction",
            "strong_video_availability",
            "strong_photo_availability"
        }
        positives = [
            factor
            for factor in factors
            if (
                factor["direction"] == "positive" and
                factor["factor"] in preferred
            )
        ]

        if not positives:
            positives = [
                factor
                for factor in factors
                if (
                    factor["direction"] == "positive" and
                    factor["factor"] != "base"
                )
            ]

        if not positives:
            return "Limited supporting evidence."

        best = max(
            positives,
            key=lambda item: item["score"]
        )

        return best["label"]

    def _low_confidence(self, assets):

        return any(
            int(asset.get("intelligence_score") or 0) < 50
            for asset in assets
        )

    def _mock_source(self, assets):

        return any(
            str(asset.get("source_model", "")).startswith("mock")
            or str(asset.get("provider", "")) == "mock"
            or str(asset.get("model", "")).startswith("mock")
            for asset in assets
        )

    def _unresolved_conflicts(self, assets):

        return any(
            int(asset.get("correction_count") or 0) >= 3
            and int(asset.get("intelligence_score") or 0) < 60
            for asset in assets
        )

    def _field_bonus(self, assets, terms):

        target = {
            self._token(term)
            for term in terms
        }
        scores = []

        for asset in assets:
            asset_terms = {
                self._token(term)
                for term in asset.get("all_terms", [])
            }

            if asset_terms & target:
                scores.append(
                    asset.get("communications_score", 0)
                    or asset.get("intelligence_score", 0)
                    or 55
                )

        return self._average(scores)

    def _days_since(self, value):

        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(str(value)[:10])
        except Exception:
            return None

        return max(0, (datetime.now() - parsed).days)

    def _average(self, values):

        values = [
            float(value or 0)
            for value in values
        ]

        if not values:
            return 0

        return sum(values) / len(values)

    def _token(self, value):

        return str(value or "").strip().lower().replace(" ", "_")

    def _clamp(self, value):

        try:
            value = int(round(float(value)))
        except Exception:
            value = 0

        return max(0, min(100, value))
