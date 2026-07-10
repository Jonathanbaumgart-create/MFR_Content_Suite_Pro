from datetime import datetime

from core.app_context import context
from services.communications_director import CommunicationsDirector
from services.communications_memory_service import CommunicationsMemoryService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.recommendation_learning_service import RecommendationLearningService


logger = LoggingService.get_logger("content")


class CommunicationsReasoningService:

    OPPORTUNITY_ALIASES = {
        "apparatus_feature": "apparatus_showcase",
        "firefighter_feature": "volunteer_recognition",
        "fire_prevention": "fire_prevention_week",
        "smoke_alarm": "smoke_alarm_reminder"
    }

    GAP_TARGETS = (
        (
            "Missing Recruitment Content",
            ("recruitment", "volunteer", "join"),
            "Recruitment coverage is weak for future hiring campaigns."
        ),
        (
            "Weak Public Education Coverage",
            ("public_education", "education", "safety_message"),
            "Public education media is limited for safety messaging."
        ),
        (
            "Weak Apparatus Coverage",
            ("apparatus", "engine", "ladder", "rescue", "tanker"),
            "Apparatus content is thin for equipment features."
        ),
        (
            "Weak Training Coverage",
            ("training", "drill", "technical_training", "exercise"),
            "Training content is limited for behind-the-scenes storytelling."
        )
    )

    CONTEXT_GAP_MAP = {
        "summer_heat_safety": (
            "Missing Seasonal Heat Safety Content",
            ("heat", "summer", "hydration", "safety")
        ),
        "water_safety_season": (
            "Missing Seasonal Water Safety Content",
            ("water", "water_rescue", "summer", "safety")
        ),
        "fire_prevention_week": (
            "Missing Fire Prevention Content",
            ("fire_prevention", "prevention", "smoke_alarm")
        ),
        "carbon_monoxide_safety_season": (
            "Missing Carbon Monoxide Content",
            ("carbon_monoxide", "co_alarm", "smoke_alarm")
        ),
        "winter_safety_season": (
            "Missing Winter Safety Content",
            ("winter", "ice", "snow", "safety")
        )
    }

    def __init__(
        self,
        database=None,
        director=None,
        knowledge_service=None,
        learning_service=None,
        memory_service=None
    ):

        self.db = database or context.database
        self.director = director or CommunicationsDirector(
            database=self.db
        )
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.learning = learning_service or RecommendationLearningService(
            database=self.db
        )
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.graph = None

    ############################################################

    def todays_communications_brief(self):

        snapshot = self.director.context_engine.snapshot()
        insights = self.director.library_insights()
        processing_status = self.director.processing_status()
        content_gaps = self.content_gaps(
            snapshot=snapshot,
            insights=insights
        )
        opportunity_keys = self._ranked_opportunity_keys(
            snapshot,
            content_gaps
        )
        recommendations = self.generate_recommendations(
            opportunity_keys=opportunity_keys,
            snapshot=snapshot,
            limit=5,
            persist_history=True
        )

        top = recommendations[0] if recommendations else None
        additional = recommendations[1:]

        brief = {
            "title": "Today's Communications Brief",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "top_recommendation": top,
            "additional_opportunities": additional,
            "recommendations": recommendations,
            "top_opportunities": recommendations[:3],
            "library_health": self._library_health(insights),
            "processing_status": processing_status,
            "content_gaps": content_gaps,
            "upcoming_opportunities": self._upcoming_opportunities(snapshot),
            "upcoming_seasonal_opportunities": [
                item["title"]
                for item in self._upcoming_opportunities(snapshot)
            ],
            "seasonal_context": snapshot.to_dict(),
            "context_snapshot": snapshot.to_dict(),
            "department_knowledge": self.knowledge.snapshot(),
            "communication_preferences": self.learning.preferences(),
            "learning_analytics": self.learning.analytics()
        }

        logger.info(
            "Generated Today's Communications Brief top=%s recommendations=%s gaps=%s",
            top.get("opportunity_type") if top else "",
            len(recommendations),
            len(content_gaps)
        )

        return brief

    ############################################################

    def generate_recommendations(
        self,
        prompt="",
        opportunity_keys=None,
        snapshot=None,
        limit=5,
        persist_history=False
    ):

        snapshot = snapshot or self.director.context_engine.snapshot()
        explicit_program = self.knowledge.explicit_program_from_prompt(
            prompt
        )

        if opportunity_keys is None:
            opportunity_keys = self.director.interpret_prompt(prompt)

            if explicit_program:
                opportunity_keys = (
                    self.knowledge.opportunity_keys_for_knowledge_item(
                        explicit_program
                    ) +
                    list(opportunity_keys)
                )

        opportunity_keys = [
            self._canonical_opportunity(key)
            for key in opportunity_keys
        ]
        opportunity_keys = self._unique(
            key
            for key in opportunity_keys
            if key in self.director.OPPORTUNITIES
        )

        if not opportunity_keys:
            opportunity_keys = ["general_engagement"]

        candidates = self.db.content_director_candidates(limit=1000)
        recent_media_ids = self.db.recent_recommended_media_ids(days=30)
        recent_social_media_ids = self.memory.recent_social_media_ids(days=90)
        recommendations = []

        for opportunity in opportunity_keys:
            recommendation = self._build_recommendation(
                opportunity,
                candidates,
                recent_media_ids,
                recent_social_media_ids,
                snapshot,
                explicit_program=explicit_program
            )

            if recommendation:
                recommendations.append(recommendation)

        recommendations.sort(
            key=lambda item: (
                self._priority_rank(item["priority"]),
                item["confidence"]
            ),
            reverse=True
        )
        recommendations = recommendations[:limit]

        for recommendation in recommendations:
            self.learning.record_generated(
                recommendation,
                prompt=prompt
            )

        if persist_history:
            self._record_history(recommendations)

        logger.info(
            "Generated reasoning recommendations opportunities=%s results=%s",
            opportunity_keys,
            len(recommendations)
        )

        return recommendations

    ############################################################

    def content_gaps(self, snapshot=None, insights=None):

        snapshot = snapshot or self.director.context_engine.snapshot()
        insights = insights or self.director.library_insights()
        candidates = self.db.content_director_candidates(limit=1000)
        total = max(1, len(candidates))
        gaps = []

        for name, terms, reason in self.GAP_TARGETS:
            count = self._count_matching_candidates(
                candidates,
                terms
            )

            if count < 3 or int((count / total) * 100) < 8:
                gaps.append(
                    {
                        "name": name,
                        "count": count,
                        "severity": self._gap_severity(count, total),
                        "reason": reason
                    }
                )

        for theme in snapshot.active_themes:

            if theme not in self.CONTEXT_GAP_MAP:
                continue

            name, terms = self.CONTEXT_GAP_MAP[theme]
            count = self._count_matching_candidates(
                candidates,
                terms
            )

            if count < 3:
                gaps.append(
                    {
                        "name": name,
                        "count": count,
                        "severity": "High",
                        "reason": (
                            "Current seasonal context makes this important, "
                            "but matching media coverage is weak."
                        )
                    }
                )

        overused = self._overused_content()
        gaps.extend(overused)

        unused = insights.get(
            "unused_high_value_media",
            []
        )

        if unused:
            gaps.append(
                {
                    "name": "Unused High-Value Media",
                    "count": len(unused),
                    "severity": "Medium",
                    "reason": (
                        "High-value media exists that has not been surfaced "
                        "recently by the recommendation history."
                    )
                }
            )

        logger.info(
            "Generated reasoning content gaps gaps=%s",
            len(gaps)
        )

        return gaps

    ############################################################

    def _build_recommendation(
        self,
        opportunity,
        candidates,
        recent_media_ids,
        recent_social_media_ids,
        snapshot,
        explicit_program=None
    ):

        profile = self.director.OPPORTUNITIES[opportunity]
        today = getattr(
            snapshot,
            "date",
            None
        )
        title = self.knowledge.label_for_opportunity(
            opportunity,
            profile["title"],
            today=today,
            explicit_program=explicit_program
        )
        caption_strategy = self.knowledge.caption_strategy(
            opportunity,
            profile["caption_theme"],
            today=today,
            explicit_program=explicit_program
        )
        call_to_action = self.knowledge.call_to_action(
            opportunity,
            profile["call_to_action"],
            today=today,
            explicit_program=explicit_program
        )
        timing_context = self.knowledge.program_timing_context(
            opportunity,
            today=today,
            explicit_program=explicit_program
        )
        scored = []

        for candidate in candidates:
            candidate = self._effective_candidate(candidate)
            item = self._score_candidate(
                candidate,
                profile,
                opportunity,
                recent_media_ids,
                recent_social_media_ids,
                snapshot
            )

            if item["score"] > 0:
                scored.append(item)

        scored.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        recommended_media = [
            self._media_summary(item)
            for item in scored[:3]
        ]

        confidence = self._confidence(scored[:3])
        priority = self._priority(
            opportunity,
            confidence,
            snapshot
        )
        reasoning = self._reasoning(
            opportunity,
            profile,
            recommended_media,
            snapshot,
            timing_context=timing_context
        )

        recommendation = {
            "opportunity_type": opportunity,
            "title": title,
            "summary": self._summary(title, recommended_media),
            "description": self._summary(title, recommended_media),
            "reasoning": reasoning,
            "priority": priority,
            "confidence": confidence,
            "recommended_media": recommended_media,
            "recommended_platforms": list(profile["platforms"]),
            "best_posting_time": profile["best_posting_time"],
            "caption_strategy": caption_strategy,
            "caption_theme": caption_strategy,
            "engagement_prediction": self._engagement_prediction(confidence),
            "estimated_engagement": self._engagement_prediction(confidence),
            "call_to_action": call_to_action,
            "hashtags": list(profile["hashtags"]),
            "program_timing": timing_context
        }

        logger.info(
            "Reasoned recommendation opportunity=%s priority=%s confidence=%s media=%s reasoning=%s",
            opportunity,
            priority,
            confidence,
            len(recommended_media),
            reasoning
        )

        return recommendation

    ############################################################

    def _score_candidate(
        self,
        candidate,
        profile,
        opportunity,
        recent_media_ids,
        recent_social_media_ids,
        snapshot
    ):

        communications_score = int(candidate.get("communications_score") or 0)
        intelligence_score = int(candidate.get("intelligence_score") or 0)
        base = (
            communications_score * 0.55
            if communications_score
            else intelligence_score * 0.45
        )
        score = base
        reasons = []

        if communications_score:
            reasons.append(
                f"communications score {communications_score}"
            )
        terms = self._candidate_terms(candidate)
        profile_terms = {
            self._token(term)
            for term in profile["keywords"]
        }
        matches = terms & profile_terms

        if matches:
            score += min(35, len(matches) * 7)
            reasons.append(
                "matches " + ", ".join(sorted(matches)[:5])
            )

        for field in profile.get("value_scores", ()):
            value = int(candidate.get(field) or 0)

            if value >= 70:
                score += 12
                reasons.append(
                    f"{field.replace('_', ' ')} is high"
                )

        if opportunity in snapshot.suggested_opportunities[:4]:
            score += 15
            reasons.append("aligns with today's seasonal messaging")

        if candidate.get("recommended_uses"):
            score += 6
            reasons.append("has recommended content uses")

        if candidate.get("content_themes"):
            score += 6
            reasons.append("has clear content themes")

        if candidate.get("media_id") in recent_media_ids:
            score -= 45
            reasons.append("was recently recommended, so diversity penalty applied")
        else:
            score += 10
            reasons.append("has not recently been recommended")

        if candidate.get("media_id") in recent_social_media_ids:
            score -= 35
            reasons.append("has already appeared in recent social posting")
        else:
            score += 6
            reasons.append("has not appeared in recent social posting")

        learning_adjustment, learning_reasons = self.learning.score_adjustment(
            candidate,
            opportunity,
            profile
        )

        if learning_adjustment:
            score += learning_adjustment
            reasons.append(
                f"learning adjustment {learning_adjustment:+.1f}"
            )
            reasons.extend(learning_reasons)

        return {
            "candidate": candidate,
            "score": round(score, 1),
            "reasons": self._unique(reasons)
        }

    ############################################################

    def _effective_candidate(self, candidate):

        try:
            from services.human_feedback_service import HumanFeedbackService

            effective = HumanFeedbackService(
                database=self.db
            ).effective_media_intelligence_row(
                candidate.get("media_id")
            )
            effective.update(
                {
                    "filename": candidate.get("filename"),
                    "path": candidate.get("path"),
                    "media_type": candidate.get("media_type"),
                    "community_score": candidate.get("community_score", 0),
                    "recruitment_score": candidate.get("recruitment_score", 0),
                    "education_score": candidate.get("education_score", 0),
                    "technical_score": candidate.get("technical_score", 0),
                    "overall_score": candidate.get("overall_score", 0)
                }
            )
            return effective

        except Exception:
            return candidate

    ############################################################

    def _media_summary(self, scored):

        candidate = scored["candidate"]
        memory = self.memory.media_memory(
            candidate.get("media_id")
        )
        fire_service = candidate.get("fire_service_intelligence") or (
            self._fire_service_intelligence(
                candidate.get("media_id")
            ) or {}
        )

        return {
            "media_id": candidate.get("media_id"),
            "filename": candidate.get("filename"),
            "path": candidate.get("path"),
            "media_type": candidate.get("media_type"),
            "score": scored["score"],
            "reason": "; ".join(scored.get("reasons") or ["strong stored intelligence"]),
            "intelligence_score": candidate.get("intelligence_score", 0),
            "communications_score": candidate.get("communications_score", 0),
            "storytelling_score": candidate.get("storytelling_score", 0),
            "community_engagement_score": candidate.get("community_engagement_score", 0),
            "educational_value_score": candidate.get("educational_value_score", 0),
            "recruitment_value_score": candidate.get("recruitment_value_score", 0),
            "trust_building_score": candidate.get("trust_building_score", 0),
            "suggested_campaigns": candidate.get("suggested_campaigns", []),
            "suggested_platform": candidate.get("suggested_platform", ""),
            "suggested_time_of_year": candidate.get("suggested_time_of_year", ""),
            "communications_reasoning": candidate.get("communications_reasoning", []),
            "operational_context": fire_service.get("operational_context", ""),
            "operational_skills": fire_service.get("operational_skills", []),
            "communications_intent": fire_service.get("communications_intent", []),
            "operational_confidence": fire_service.get("operational_confidence", 0),
            "operational_reasoning": fire_service.get("operational_reasoning", []),
            "community_score": candidate.get("community_score", 0),
            "recruitment_score": candidate.get("recruitment_score", 0),
            "education_score": candidate.get("education_score", 0),
            "technical_score": candidate.get("technical_score", 0),
            "posted_before": memory["posted_before"],
            "post_count": memory["post_count"],
            "last_posted": memory["last_posted"],
            "posted_campaigns": memory["campaigns"]
        }

    ############################################################

    def _reasoning(
        self,
        opportunity,
        profile,
        media,
        snapshot,
        timing_context=None
    ):

        reasoning = [
            f"Best fit for {profile['caption_theme'].lower()} today.",
            "Uses Context Engine, stored Media Intelligence, library insights, and recommendation history.",
            "No image analysis or external API calls are used.",
            self.knowledge.reasoning_context(
                opportunity,
                today=getattr(
                    snapshot,
                    "date",
                    None
                ),
                explicit_program=(
                    timing_context or {}
                ).get("explicit_program")
            )
        ]

        timing_context = timing_context or {}

        active_program = timing_context.get("active_program")

        if active_program:
            reasoning.append(
                active_program["status"]["reason"]
            )

            if (
                timing_context.get("explicit_program") and
                not active_program["status"]["active"]
            ):
                reasoning.append(
                    "It is included because the prompt explicitly requested that program."
                )

        for entry in timing_context.get("out_of_season", [])[:2]:
            reasoning.append(
                entry["status"]["reason"]
            )

        for entry in timing_context.get("upcoming", [])[:2]:
            reasoning.append(
                entry["program"]["name"] +
                " may be useful as upcoming content preparation, not as today's main post."
            )

        active = [
            self._format_label(theme)
            for theme in snapshot.active_themes[:4]
        ]

        if active:
            reasoning.append(
                "Seasonal context supports this: " + ", ".join(active) + "."
            )

        if opportunity in snapshot.suggested_opportunities[:4]:
            reasoning.append("It aligns with today's proactive communication window.")

        if media:
            top = media[0]

            if top.get("communications_score"):
                reasoning.append(
                    f"Top media has a communications score of {top['communications_score']}."
                )

            reasoning.append(
                f"Top media has an intelligence score of {top['intelligence_score']}."
            )
            reasoning.append(top.get("reason", "Recommended media has strong intelligence signals."))

            for item in top.get("communications_reasoning", [])[:2]:
                reasoning.append(item)

            if top.get("operational_context"):
                reasoning.append(
                    (
                        "Operational reasoning: " +
                        self._format_label(top["operational_context"]) +
                        f" confidence {top.get('operational_confidence', 0)}."
                    )
                )

            for item in top.get("operational_reasoning", [])[:2]:
                reasoning.append(item)

            if top.get("communications_intent"):
                reasoning.append(
                    (
                        "Communications intent: " +
                        ", ".join(
                            self._format_label(value)
                            for value in top["communications_intent"][:4]
                        ) +
                        "."
                    )
                )

            if top.get("community_score", 0) >= 70:
                reasoning.append("Community interaction value is strong.")

            if top.get("recruitment_score", 0) >= 70:
                reasoning.append("Recruitment score is high.")

            if top.get("education_score", 0) >= 70:
                reasoning.append("Education value supports public safety messaging.")

            if "has not recently been recommended" in top.get("reason", ""):
                reasoning.append("It has not recently been recommended.")

            if top.get("posted_before"):
                reasoning.append(
                    (
                        "Communications Memory shows this media was posted "
                        f"{top['post_count']} time(s), most recently "
                        f"{top['last_posted']}."
                    )
                )
            else:
                reasoning.append(
                    "Communications Memory shows this media has not been posted before."
                )
        else:
            reasoning.append("No strong matching media was found; this is also a content gap.")

        return self._unique(reasoning)

    ############################################################

    def _ranked_opportunity_keys(self, snapshot, gaps):

        keys = list(snapshot.suggested_opportunities)

        gap_text = " ".join(
            gap["name"].lower()
            for gap in gaps
        )

        if "recruitment" in gap_text:
            keys.append("recruitment")

        if "public education" in gap_text:
            keys.append("smoke_alarm_reminder")

        if "apparatus" in gap_text:
            keys.append("apparatus_showcase")

        if "training" in gap_text:
            keys.append("training_highlight")

        keys.extend(
            (
                "community_appreciation",
                "volunteer_recognition",
                "behind_the_scenes",
                "general_engagement"
            )
        )

        return self._unique(
            self._canonical_opportunity(key)
            for key in keys
        )

    ############################################################

    def _record_history(self, recommendations):

        for recommendation in recommendations:
            platform = ", ".join(
                recommendation.get(
                    "recommended_platforms",
                    []
                )
            )

            for media in recommendation.get("recommended_media", [])[:1]:
                self.db.save_recommendation_history(
                    {
                        "media_id": media.get("media_id"),
                        "reason": media.get("reason", ""),
                        "opportunity": recommendation.get("opportunity_type", ""),
                        "score": media.get("score", 0),
                        "platform": platform
                    }
                )

    ############################################################

    def _library_health(self, insights):

        return {
            "total_media": insights["total_media"],
            "analyzed_media": insights["analyzed_media"],
            "media_with_intelligence": insights["media_with_intelligence"],
            "community_content_percentage": insights["community_content_percentage"],
            "training_percentage": insights["training_percentage"],
            "recruitment_percentage": insights["recruitment_percentage"]
        }

    ############################################################

    def _upcoming_opportunities(self, snapshot):

        opportunities = []
        mapping = {
            "summer_heat_safety": "heat_warning",
            "water_safety_season": "water_safety",
            "winter_safety_season": "holiday_safety",
            "ice_safety_season": "storm_safety",
            "spring_melt_flood_awareness": "storm_safety",
            "wildfire_grass_fire_season": "fire_prevention_week",
            "back_to_school_safety": "community_appreciation",
            "fire_prevention_week": "fire_prevention_week",
            "halloween_safety": "holiday_safety",
            "carbon_monoxide_safety_season": "smoke_alarm_reminder",
            "recruitment_friendly_period": "recruitment"
        }

        for theme in snapshot.upcoming_themes:
            key = mapping.get(theme)

            if key and key in self.director.OPPORTUNITIES:
                opportunities.append(
                    {
                        "opportunity_type": key,
                        "title": self.director.OPPORTUNITIES[key]["title"],
                        "reason": f"Upcoming context: {self._format_label(theme)}"
                    }
                )

        return opportunities[:5]

    ############################################################

    def _overused_content(self):

        gaps = []

        for opportunity, count in self.db.recommendation_counts(days=90):

            if count >= 5:
                gaps.append(
                    {
                        "name": f"Overused Content: {self._format_label(opportunity)}",
                        "count": count,
                        "severity": "Medium",
                        "reason": (
                            "This opportunity has been recommended often "
                            "recently, so diversify the next plan."
                        )
                    }
                )

        return gaps

    ############################################################

    def _summary(self, title, media):

        if media:
            return (
                f"Recommended communications package for {title} "
                f"using {len(media)} stored media item(s)."
            )

        return (
            f"No strong media match is available yet for {title}; "
            "treat this as a content gap."
        )

    ############################################################

    def _confidence(self, scored):

        if not scored:
            return 0

        average = sum(item.get("score", 0) for item in scored) / len(scored)

        return min(100, max(0, int(average)))

    ############################################################

    def _priority(self, opportunity, confidence, snapshot):

        if opportunity in snapshot.suggested_opportunities[:3] and confidence >= 45:
            return "High"

        if confidence >= 80:
            return "High"

        if confidence >= 45:
            return "Medium"

        return "Low"

    ############################################################

    def _engagement_prediction(self, confidence):

        if confidence >= 85:
            return "Excellent"

        if confidence >= 65:
            return "Strong"

        if confidence >= 40:
            return "Moderate"

        return "Limited"

    ############################################################

    def _priority_rank(self, value):

        return {
            "High": 3,
            "Medium": 2,
            "Low": 1
        }.get(value, 0)

    ############################################################

    def _gap_severity(self, count, total):

        if count == 0:
            return "High"

        if int((count / max(1, total)) * 100) < 5:
            return "Medium"

        return "Low"

    ############################################################

    def _count_matching_candidates(self, candidates, terms):

        term_set = {
            self._token(term)
            for term in terms
        }
        count = 0

        for candidate in candidates:

            if self._candidate_terms(candidate) & term_set:
                count += 1

        return count

    ############################################################

    def _candidate_terms(self, candidate):

        values = []

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "search_text"
        ):
            values.append(candidate.get(key, ""))

        for key in (
            "apparatus_tags",
            "equipment_tags",
            "ppe_tags",
            "people_tags",
            "content_tags",
            "content_themes",
            "recommended_uses"
        ):
            values.extend(candidate.get(key) or [])

        fire_service = self._fire_service_intelligence(
            candidate.get("media_id")
        )

        if fire_service:
            for key in (
                "incident_classification",
                "operational_activity",
                "operational_context",
                "group_size"
            ):
                values.append(fire_service.get(key, ""))

            for key in (
                "ppe",
                "equipment",
                "apparatus",
                "communications_uses",
                "operational_skills",
                "communications_intent",
                "operational_reasoning"
            ):
                values.extend(fire_service.get(key) or [])

        terms = {
            self._token(value)
            for value in values
            if value
        }
        terms |= self._graph_terms(terms)

        return terms

    ############################################################

    def _fire_service_intelligence(self, media_id):

        if not media_id or not self.db:
            return None

        try:
            return self.db.get_fire_service_intelligence(media_id)

        except Exception:
            return None

    ############################################################

    def _graph_terms(self, terms):

        if not terms:
            return set()

        try:
            if self.graph is None:
                from services.knowledge_graph_service import KnowledgeGraphService

                self.graph = KnowledgeGraphService(
                    database=self.db,
                    knowledge_service=self.knowledge
                )

            context = self.graph.reasoning_context(list(terms))
            values = set()

            for key in (
                "operational_skills",
                "communications_intent",
                "campaigns"
            ):
                values.update(
                    self._token(value)
                    for value in context.get(key, [])
                )

            for rows in context.get("expanded_terms", {}).values():
                values.update(
                    self._token(row.get("name", ""))
                    for row in rows
                )

            return {
                value
                for value in values
                if value
            }

        except Exception:
            return set()

    ############################################################

    def _canonical_opportunity(self, value):

        return self.OPPORTUNITY_ALIASES.get(
            value,
            value
        )

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )

    ############################################################

    def _format_label(self, value):

        return str(value or "").replace(
            "_",
            " "
        ).title()

    ############################################################

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
