from core.app_context import context
from services.context_engine import ContextEngine
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class CommunicationsDirector:

    OPPORTUNITIES = {
        "heat_warning": {
            "title": "Heat Warning",
            "keywords": (
                "heat",
                "summer",
                "hydration",
                "safety",
                "public_education",
                "safety_message",
                "community"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Heat safety reminder",
            "hashtags": ("#HeatSafety", "#FireSafety", "#CommunitySafety"),
            "call_to_action": "Stay hydrated, check on neighbours, and call 911 for emergencies.",
            "best_posting_time": "Late morning or early evening",
            "value_scores": ("community_score", "education_score")
        },
        "storm_safety": {
            "title": "Storm Safety",
            "keywords": (
                "storm",
                "wind",
                "weather",
                "preparedness",
                "public_education",
                "safety",
                "safety_message"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Storm safety preparation",
            "hashtags": ("#StormSafety", "#Preparedness", "#CommunitySafety"),
            "call_to_action": "Secure loose items, avoid downed lines, and prepare for outages.",
            "best_posting_time": "Before forecasted severe weather",
            "value_scores": ("community_score", "education_score")
        },
        "smoke_alarm_reminder": {
            "title": "Smoke Alarm Reminder",
            "keywords": (
                "smoke_alarm",
                "smoke",
                "alarm",
                "detector",
                "installation",
                "prevention",
                "public_education",
                "safety_message"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Smoke alarm testing reminder",
            "hashtags": ("#SmokeAlarms", "#FirePrevention", "#FireSafety"),
            "call_to_action": "Test every smoke alarm and replace expired units.",
            "best_posting_time": "Sunday evening",
            "value_scores": ("education_score", "community_score")
        },
        "recruitment": {
            "title": "Recruitment",
            "keywords": (
                "recruitment",
                "recruit",
                "volunteer",
                "join",
                "training",
                "crew",
                "community"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Recruitment invitation",
            "hashtags": ("#JoinMFR", "#FirefighterRecruitment", "#ServeYourCommunity"),
            "call_to_action": "Learn how to serve your community with Morden Fire & Rescue.",
            "best_posting_time": "Weekday evening",
            "value_scores": ("recruitment_score", "community_score")
        },
        "fire_prevention_week": {
            "title": "Fire Prevention Week",
            "keywords": (
                "fire_prevention",
                "prevention",
                "public_education",
                "education",
                "safety",
                "safety_message"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Fire prevention education",
            "hashtags": ("#FirePreventionWeek", "#FireSafety", "#CommunitySafety"),
            "call_to_action": "Make fire safety part of your home routine.",
            "best_posting_time": "Morning or early evening",
            "value_scores": ("education_score", "community_score")
        },
        "holiday_safety": {
            "title": "Holiday Safety",
            "keywords": (
                "holiday",
                "winter",
                "safety",
                "prevention",
                "public_education",
                "community"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Holiday fire safety",
            "hashtags": ("#HolidaySafety", "#FireSafety", "#CommunitySafety"),
            "call_to_action": "Keep exits clear and use candles, cords, and heaters safely.",
            "best_posting_time": "Early evening",
            "value_scores": ("education_score", "community_score")
        },
        "water_safety": {
            "title": "Water Safety",
            "keywords": (
                "water",
                "water_rescue",
                "rescue",
                "summer",
                "safety",
                "public_education"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Water safety reminder",
            "hashtags": ("#WaterSafety", "#SummerSafety", "#CommunitySafety"),
            "call_to_action": "Use lifejackets, supervise children, and call 911 in emergencies.",
            "best_posting_time": "Friday afternoon",
            "value_scores": ("education_score", "community_score")
        },
        "community_appreciation": {
            "title": "Community Appreciation",
            "keywords": (
                "community",
                "community_outreach",
                "open_house",
                "parade",
                "event",
                "social_media"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Community appreciation",
            "hashtags": ("#Community", "#Morden", "#MordenFireRescue"),
            "call_to_action": "Thank you for supporting local emergency services.",
            "best_posting_time": "Weekend morning",
            "value_scores": ("community_score",)
        },
        "volunteer_recognition": {
            "title": "Volunteer Recognition",
            "keywords": (
                "volunteer",
                "crew",
                "firefighter",
                "training",
                "community",
                "recruitment"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Volunteer recognition",
            "hashtags": ("#VolunteerFirefighter", "#TeamMFR", "#CommunityService"),
            "call_to_action": "Help us recognize the people who serve our community.",
            "best_posting_time": "Weekday evening",
            "value_scores": ("community_score", "recruitment_score")
        },
        "training_highlight": {
            "title": "Training Highlight",
            "keywords": (
                "training",
                "drill",
                "exercise",
                "technical_training",
                "hose",
                "scba",
                "crew"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Training highlight",
            "hashtags": ("#FireTraining", "#Preparedness", "#Teamwork"),
            "call_to_action": "Follow for more behind-the-scenes training updates.",
            "best_posting_time": "Weekday evening",
            "value_scores": ("technical_score", "recruitment_score")
        },
        "apparatus_showcase": {
            "title": "Apparatus Showcase",
            "keywords": (
                "apparatus",
                "engine",
                "ladder",
                "rescue",
                "tanker",
                "brush",
                "station"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Apparatus showcase",
            "hashtags": ("#FireApparatus", "#MordenFireRescue", "#EmergencyServices"),
            "call_to_action": "Give emergency vehicles room to work when crews respond.",
            "best_posting_time": "Saturday morning",
            "value_scores": ("technical_score", "community_score")
        },
        "behind_the_scenes": {
            "title": "Behind the Scenes",
            "keywords": (
                "training",
                "station",
                "crew",
                "equipment",
                "apparatus",
                "community"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Behind-the-scenes fire service work",
            "hashtags": ("#BehindTheScenes", "#FireService", "#MordenFireRescue"),
            "call_to_action": "Follow for a closer look at how crews prepare.",
            "best_posting_time": "Midday",
            "value_scores": ("community_score", "technical_score")
        },
        "on_this_day": {
            "title": "On This Day",
            "keywords": (
                "incident_archive",
                "archive",
                "community",
                "training",
                "apparatus"
            ),
            "platforms": ("Facebook",),
            "caption_theme": "On this day from the archive",
            "hashtags": ("#OnThisDay", "#MordenFireRescue", "#FireService"),
            "call_to_action": "Stay connected for more moments from the archive.",
            "best_posting_time": "Morning",
            "value_scores": ("community_score",)
        },
        "throwback_thursday": {
            "title": "Throwback Thursday",
            "keywords": (
                "archive",
                "incident_archive",
                "community",
                "apparatus",
                "training"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Throwback Thursday archive post",
            "hashtags": ("#ThrowbackThursday", "#MordenFireRescue", "#FireService"),
            "call_to_action": "Share your memories and follow for more department history.",
            "best_posting_time": "Thursday morning",
            "value_scores": ("community_score",)
        },
        "general_engagement": {
            "title": "General Engagement",
            "keywords": (
                "community",
                "social_media",
                "training",
                "public_education",
                "crew"
            ),
            "platforms": ("Facebook", "Instagram"),
            "caption_theme": "Community update",
            "hashtags": ("#MordenFireRescue", "#CommunitySafety", "#FireService"),
            "call_to_action": "Follow Morden Fire & Rescue for updates and safety reminders.",
            "best_posting_time": "Early evening",
            "value_scores": ("community_score", "overall_score")
        }
    }

    PROMPT_RULES = (
        ("heat_warning", ("heat", "hot", "summer", "hydration")),
        ("storm_safety", ("storm", "wind", "thunderstorm", "power outage")),
        ("smoke_alarm_reminder", ("smoke alarm", "smoke detector", "alarm")),
        ("recruitment", ("recruit", "recruitment", "volunteer", "join")),
        ("fire_prevention_week", ("fire prevention", "prevention week", "fire safety")),
        ("holiday_safety", ("holiday", "christmas", "new year", "halloween")),
        ("water_safety", ("water", "lake", "swim", "drowning")),
        ("community_appreciation", ("thank", "appreciation", "community")),
        ("volunteer_recognition", ("recognize", "recognition", "volunteer")),
        ("training_highlight", ("training", "drill", "exercise")),
        ("apparatus_showcase", ("apparatus", "engine", "ladder", "truck")),
        ("behind_the_scenes", ("behind the scenes", "station", "crew")),
        ("on_this_day", ("on this day", "anniversary", "archive")),
        ("throwback_thursday", ("throwback", "thursday", "tbt"))
    )

    GAP_TARGETS = (
        ("Water Rescue", ("water_rescue", "water", "rescue")),
        ("Night Training", ("night", "night_drill", "training")),
        ("Recruitment", ("recruitment", "recruit", "volunteer")),
        ("Smoke Alarm Installation", ("smoke_alarm", "installation", "detector")),
        ("Public Education", ("public_education", "education", "safety_message")),
        ("Holiday Safety", ("holiday", "winter", "prevention")),
        ("Water Safety", ("water", "summer", "safety"))
    )

    def __init__(self, database=None, job_manager=None, context_engine=None):

        self.db = database or context.database
        self.jobs = job_manager or context.job_manager
        self.context_engine = context_engine or ContextEngine()

    ############################################################

    def interpret_prompt(self, prompt):

        text = self._normalize(prompt)
        opportunities = []

        for key, terms in self.PROMPT_RULES:

            if any(term in text for term in terms):
                opportunities.append(key)

        return self._unique(opportunities or ["general_engagement"])

    ############################################################

    def generate_opportunities(self, prompt="", limit=5):

        snapshot = self.context_engine.snapshot()
        opportunity_types = self.interpret_prompt(prompt)

        if not prompt.strip() or opportunity_types == ["general_engagement"]:
            opportunity_types = self._context_opportunity_keys(snapshot)

        return [
            self.generate_opportunity(
                opportunity_type,
                snapshot=snapshot
            )
            for opportunity_type in opportunity_types[:limit]
        ]

    ############################################################

    def generate_opportunity(
        self,
        opportunity_type,
        media_limit=3,
        snapshot=None
    ):

        snapshot = snapshot or self.context_engine.snapshot()
        profile = self.OPPORTUNITIES.get(
            opportunity_type,
            self.OPPORTUNITIES["general_engagement"]
        )
        candidates = self.db.content_director_candidates(limit=750)
        scored = [
            self._score_media(candidate, profile)
            for candidate in candidates
        ]
        scored = [
            item
            for item in scored
            if item["score"] > 0
        ]
        scored.sort(
            key=lambda item: item["score"],
            reverse=True
        )
        recommended_media = [
            self._media_summary(item)
            for item in scored[:media_limit]
        ]
        reasoning = self._opportunity_reasoning(
            profile,
            recommended_media,
            snapshot
        )
        confidence = self._confidence(recommended_media)
        priority = self._priority(
            confidence,
            opportunity_type,
            snapshot
        )

        opportunity = {
            "opportunity_type": opportunity_type,
            "title": profile["title"],
            "description": self._description(profile, recommended_media),
            "reasoning": reasoning,
            "recommended_media": recommended_media,
            "recommended_platforms": list(profile["platforms"]),
            "best_posting_time": profile["best_posting_time"],
            "priority": priority,
            "confidence": confidence,
            "caption_theme": profile["caption_theme"],
            "hashtags": list(profile["hashtags"]),
            "call_to_action": profile["call_to_action"],
            "estimated_engagement": self._estimated_engagement(recommended_media)
        }

        logger.info(
            "Generated communication opportunity type=%s media=%s confidence=%s",
            opportunity_type,
            len(recommended_media),
            confidence
        )

        return opportunity

    ############################################################

    def todays_brief(self):

        snapshot = self.context_engine.snapshot()
        top_opportunities = self._context_opportunity_keys(snapshot)
        opportunities = [
            self.generate_opportunity(
                key,
                snapshot=snapshot
            )
            for key in top_opportunities[:5]
        ]
        insights = self.library_insights()
        gaps = self.content_gaps()
        processing_status = self.processing_status()

        brief = {
            "top_opportunities": opportunities[:3],
            "recommendations": opportunities,
            "library_health": {
                "total_media": insights["total_media"],
                "analyzed_media": insights["analyzed_media"],
                "media_with_intelligence": insights["media_with_intelligence"],
                "community_content_percentage": insights["community_content_percentage"],
                "training_percentage": insights["training_percentage"],
                "recruitment_percentage": insights["recruitment_percentage"]
            },
            "processing_status": processing_status,
            "upcoming_seasonal_opportunities": [
                self.OPPORTUNITIES[key]["title"]
                for key in self._upcoming_seasonal_keys(snapshot)
            ],
            "context_snapshot": snapshot.to_dict(),
            "content_gaps": gaps
        }

        logger.info(
            "Generated Today's Brief opportunities=%s gaps=%s",
            len(brief["recommendations"]),
            len(gaps)
        )

        return brief

    ############################################################

    def library_insights(self):

        counts = self.db.intelligence_filter_counts({})
        total_media = self.db.media_count()
        analyzed = self.db.analyzed_media_count()
        intelligence_count = self.db.media_intelligence_count()
        candidates = self.db.content_director_candidates(limit=750)

        insights = {
            "total_media": total_media,
            "analyzed_media": analyzed,
            "media_with_intelligence": intelligence_count,
            "most_common_incident": self._top_count(counts.get("incident_type")),
            "least_photographed_apparatus": self._bottom_count(counts.get("apparatus_tags")),
            "most_photographed_activity": self._top_count(counts.get("primary_activity")),
            "community_content_percentage": self._percentage_for_terms(
                candidates,
                ("community", "community_outreach")
            ),
            "training_percentage": self._percentage_for_terms(
                candidates,
                ("training", "technical_training")
            ),
            "recruitment_percentage": self._percentage_for_terms(
                candidates,
                ("recruitment",)
            ),
            "media_requiring_analysis": self.db.media_needing_analysis_count(),
            "media_requiring_intelligence": self.db.media_needing_intelligence_count(),
            "unused_high_value_media": [
                self._media_summary(
                    {
                        "candidate": candidate,
                        "score": candidate.get("intelligence_score", 0),
                        "reasons": ["high intelligence score"]
                    }
                )
                for candidate in candidates
                if candidate.get("intelligence_score", 0) >= 85
            ][:5]
        }

        logger.info(
            "Generated library insights total=%s intelligence=%s",
            total_media,
            intelligence_count
        )

        return insights

    ############################################################

    def content_gaps(self):

        snapshot = self.context_engine.snapshot()
        candidates = self.db.content_director_candidates(limit=1000)
        total = max(1, len(candidates))
        gaps = []

        for label, terms in self.GAP_TARGETS:

            count = self._count_matching_candidates(
                candidates,
                terms
            )
            percentage = int((count / total) * 100)

            if count < 3 or percentage < 5:
                gaps.append(
                    {
                        "name": label,
                        "count": count,
                        "percentage": percentage,
                        "reason": (
                            f"Only {count} matching media items found in "
                            "the sampled intelligence set."
                        )
                    }
                )

        context_gap_map = {
            "water_safety_season": ("Water Safety", ("water", "summer", "safety")),
            "summer_heat_safety": ("Heat Safety", ("heat", "summer", "hydration")),
            "fire_prevention_week": ("Fire Prevention", ("fire_prevention", "prevention")),
            "carbon_monoxide_safety_season": ("Carbon Monoxide Safety", ("carbon_monoxide", "co_alarm")),
            "winter_safety_season": ("Winter Safety", ("winter", "ice", "snow")),
            "recruitment_friendly_period": ("Recruitment", ("recruitment", "volunteer"))
        }

        for theme in snapshot.active_themes:

            if theme not in context_gap_map:
                continue

            label, terms = context_gap_map[theme]

            if any(gap["name"] == label for gap in gaps):
                continue

            count = self._count_matching_candidates(
                candidates,
                terms
            )

            if count < 3:
                gaps.append(
                    {
                        "name": label,
                        "count": count,
                        "percentage": int((count / total) * 100),
                        "reason": (
                            "Current context makes this theme important, "
                            f"but only {count} matching media items were found."
                        )
                    }
                )

        logger.info(
            "Generated content gaps gaps=%s",
            len(gaps)
        )

        return gaps

    ############################################################

    def processing_status(self):

        progress = self.jobs.progress() if self.jobs else {}

        return {
            "queued_jobs": progress.get("queued", 0),
            "running_jobs": progress.get("running", 0),
            "completed_jobs": progress.get("completed", 0),
            "failed_jobs": progress.get("failed", 0),
            "media_requiring_analysis": self.db.media_needing_analysis_count(),
            "media_requiring_intelligence": self.db.media_needing_intelligence_count()
        }

    ############################################################

    def _score_media(self, candidate, profile):

        communications_score = int(candidate.get("communications_score") or 0)
        intelligence_score = int(candidate.get("intelligence_score") or 0)
        score = (
            communications_score * 0.55
            if communications_score
            else intelligence_score * 0.45
        )
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
            score += min(35, len(matches) * 8)
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

        if candidate.get("recommended_uses"):
            score += 6
            reasons.append("has recommended content uses")

        if candidate.get("content_themes"):
            score += 6
            reasons.append("has clear content themes")

        return {
            "candidate": candidate,
            "score": round(score, 1),
            "reasons": self._unique(reasons)
        }

    ############################################################

    def _media_summary(self, scored):

        candidate = scored["candidate"]

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
            "community_score": candidate.get("community_score", 0),
            "recruitment_score": candidate.get("recruitment_score", 0),
            "education_score": candidate.get("education_score", 0),
            "technical_score": candidate.get("technical_score", 0)
        }

    ############################################################

    def _opportunity_reasoning(self, profile, recommended_media, snapshot):

        reasoning = [
            f"Aligns with {profile['caption_theme'].lower()} messaging.",
            "Uses stored Media Intelligence rather than image inspection.",
            "Uses local calendar context without external API calls."
        ]

        active_text = [
            self._format_label(theme)
            for theme in snapshot.active_themes[:3]
        ]

        if active_text:
            reasoning.append(
                "Current context supports this: " + ", ".join(active_text) + "."
            )

        if recommended_media:
            top = recommended_media[0]

            if top.get("communications_score"):
                reasoning.append(
                    f"Top media has a communications score of {top['communications_score']}."
                )

            reasoning.append(
                f"Top media has an intelligence score of {top['intelligence_score']}."
            )

            for item in top.get("communications_reasoning", [])[:2]:
                reasoning.append(item)

            if top.get("community_score", 0) >= 70:
                reasoning.append("Strong community engagement value.")

            if top.get("recruitment_score", 0) >= 70:
                reasoning.append("Recruitment value is high.")

            if top.get("education_score", 0) >= 70:
                reasoning.append("Education value supports public safety messaging.")

            if top.get("technical_score", 0) >= 70:
                reasoning.append("Technical value supports operational storytelling.")

            reasoning.append(
                top.get("reason", "Recommended media has strong intelligence signals.")
            )
        else:
            reasoning.append(
                "No strong matching media was found in stored intelligence."
            )

        return self._unique(reasoning)

    ############################################################

    def _description(self, profile, recommended_media):

        if recommended_media:
            return (
                f"Recommended communications package for {profile['title']} "
                f"using {len(recommended_media)} stored media item(s)."
            )

        return (
            f"No strong media match is available yet for {profile['title']}; "
            "this should be treated as a content gap."
        )

    ############################################################

    def _estimated_engagement(self, media):

        if not media:
            return "Low"

        average = sum(item.get("score", 0) for item in media) / len(media)

        if average >= 90:
            return "High"

        if average >= 65:
            return "Moderate"

        return "Low"

    ############################################################

    def _confidence(self, media):

        if not media:
            return 0

        average = sum(item.get("score", 0) for item in media) / len(media)

        return min(100, int(average))

    ############################################################

    def _priority(self, confidence, opportunity_type, snapshot=None):

        urgent = {
            "heat_warning",
            "storm_safety",
            "smoke_alarm_reminder",
            "fire_prevention_week"
        }

        if snapshot:
            if opportunity_type in snapshot.suggested_opportunities[:3]:
                return "High"

        if opportunity_type in urgent and confidence >= 50:
            return "High"

        if confidence >= 75:
            return "High"

        if confidence >= 45:
            return "Medium"

        return "Low"

    ############################################################

    def _context_opportunity_keys(self, snapshot=None):

        snapshot = snapshot or self.context_engine.snapshot()
        keys = list(snapshot.suggested_opportunities)

        keys.extend(
            (
                "recruitment",
                "community_appreciation",
                "training_highlight",
                "general_engagement"
            )
        )

        return self._unique(keys)

    ############################################################

    def _upcoming_seasonal_keys(self, snapshot=None):

        snapshot = snapshot or self.context_engine.snapshot()
        upcoming = []
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
            "holiday_fireplace_candle_safety": "holiday_safety",
            "new_year_safety": "general_engagement",
            "emergency_preparedness_week": "storm_safety",
            "recruitment_friendly_period": "recruitment"
        }

        for theme in snapshot.upcoming_themes:
            opportunity = mapping.get(theme)

            if opportunity:
                upcoming.append(opportunity)

        upcoming.extend(
            (
                "recruitment",
                "training_highlight",
                "community_appreciation"
            )
        )

        return self._unique(upcoming)[:5]

    ############################################################

    def _top_count(self, rows):

        if not rows:
            return {
                "name": "None",
                "count": 0
            }

        value, count = rows[0]

        return {
            "name": value or "Unknown",
            "count": count or 0
        }

    ############################################################

    def _bottom_count(self, rows):

        rows = [
            row
            for row in (rows or [])
            if row[0]
        ]

        if not rows:
            return {
                "name": "None",
                "count": 0
            }

        value, count = rows[-1]

        return {
            "name": value,
            "count": count or 0
        }

    ############################################################

    def _percentage_for_terms(self, candidates, terms):

        if not candidates:
            return 0

        count = self._count_matching_candidates(
            candidates,
            terms
        )

        return int((count / len(candidates)) * 100)

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

        return {
            self._token(value)
            for value in values
            if value
        }

    ############################################################

    def _normalize(self, value):

        return str(value or "").strip().lower()

    ############################################################

    def _token(self, value):

        return self._normalize(value).replace(
            " ",
            "_"
        )

    ############################################################

    def _format_label(self, value):

        return str(value).replace(
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
