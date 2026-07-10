import time

from core.app_context import context
from services.communications_memory_service import CommunicationsMemoryService
from services.context_engine import ContextEngine
from services.knowledge_graph_service import KnowledgeGraphService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class RecommendationCandidateService:

    MAX_CANDIDATES = 500
    MAX_SUPPORTING_IDS = 25
    MAX_BEST_IDS = 5

    CATEGORY_PROFILES = (
        {
            "category": "Community Education",
            "topic": "community_education",
            "title": "Community Education Opportunity",
            "terms": (
                "community_education",
                "public_education",
                "education",
                "safety",
                "children",
                "school",
                "smoke_alarm"
            ),
            "score_fields": (
                "educational_value_score",
                "public_education_value_score",
                "community_engagement_score",
                "trust_building_score"
            ),
            "editorial_angles": (
                "Community Education",
                "Public Education",
                "Seasonal Safety"
            ),
            "platforms": ("Facebook", "Instagram", "Website"),
            "audiences": ("Morden residents", "Families", "Students"),
            "formats": ("educational post", "photo carousel", "website feature"),
            "posting_window": "This morning"
        },
        {
            "category": "Seasonal Safety",
            "topic": "seasonal_safety",
            "title": "Seasonal Safety Opportunity",
            "terms": (
                "heat",
                "summer",
                "winter",
                "storm",
                "water_safety",
                "fire_prevention",
                "carbon_monoxide",
                "preparedness"
            ),
            "score_fields": (
                "seasonal_relevance_score",
                "public_education_value_score",
                "educational_value_score",
                "time_sensitive_score"
            ),
            "editorial_angles": (
                "Seasonal Safety",
                "Community Education",
                "Preparedness"
            ),
            "platforms": ("Facebook", "Instagram"),
            "audiences": ("Morden residents", "Families"),
            "formats": ("campaign post", "single photo", "photo carousel"),
            "posting_window": "Within 48 hours"
        },
        {
            "category": "Recruitment",
            "topic": "recruitment",
            "title": "Recruitment Opportunity",
            "terms": (
                "recruitment",
                "recruit",
                "volunteer",
                "firefighter",
                "crew",
                "training",
                "teamwork"
            ),
            "score_fields": (
                "recruitment_value_score",
                "storytelling_score",
                "community_engagement_score",
                "emotional_impact_score"
            ),
            "editorial_angles": (
                "Recruitment",
                "Volunteer Spotlight",
                "Training Highlight"
            ),
            "platforms": ("Facebook", "Instagram", "LinkedIn"),
            "audiences": ("Prospective firefighters", "Community-minded residents"),
            "formats": ("firefighter profile", "photo carousel", "short-form video"),
            "posting_window": "This evening"
        },
        {
            "category": "Training",
            "topic": "training",
            "title": "Training Highlight Opportunity",
            "terms": (
                "training",
                "drill",
                "exercise",
                "technical_training",
                "ladder_operations",
                "hose",
                "scba",
                "officer_development"
            ),
            "score_fields": (
                "educational_value_score",
                "recruitment_value_score",
                "storytelling_score",
                "visual_impact_score"
            ),
            "editorial_angles": (
                "Training Tuesday",
                "Technical Education",
                "Recruitment"
            ),
            "platforms": ("Facebook", "Instagram", "LinkedIn"),
            "audiences": ("Morden residents", "Prospective firefighters"),
            "formats": ("behind-the-scenes post", "photo carousel", "short-form video"),
            "posting_window": "Next appropriate weekday"
        },
        {
            "category": "Firefighter Spotlight",
            "topic": "firefighter_spotlight",
            "title": "Firefighter Spotlight Opportunity",
            "terms": (
                "firefighter",
                "crew",
                "volunteer",
                "recognition",
                "teamwork",
                "people",
                "community_service"
            ),
            "score_fields": (
                "recognition_value_score",
                "emotional_impact_score",
                "recruitment_value_score",
                "storytelling_score"
            ),
            "editorial_angles": (
                "Volunteer Spotlight",
                "Community Trust",
                "Recruitment"
            ),
            "platforms": ("Facebook", "Instagram", "LinkedIn"),
            "audiences": ("Morden residents", "Department supporters"),
            "formats": ("firefighter profile", "single photo", "recognition post"),
            "posting_window": "This evening"
        },
        {
            "category": "Apparatus and Equipment",
            "topic": "apparatus_equipment",
            "title": "Apparatus and Equipment Opportunity",
            "terms": (
                "apparatus",
                "engine",
                "pumper",
                "rescue",
                "ladder",
                "tanker",
                "equipment",
                "hose"
            ),
            "score_fields": (
                "visual_impact_score",
                "educational_value_score",
                "trust_building_score",
                "technical_score"
            ),
            "editorial_angles": (
                "Apparatus Feature",
                "Technical Education",
                "Website Feature"
            ),
            "platforms": ("Facebook", "Instagram", "Website"),
            "audiences": ("Morden residents", "Community partners"),
            "formats": ("apparatus feature", "single photo", "website feature"),
            "posting_window": "This afternoon"
        },
        {
            "category": "Community Trust",
            "topic": "community_trust",
            "title": "Community Trust Opportunity",
            "terms": (
                "community",
                "trust_building",
                "public_education",
                "open_house",
                "children",
                "families",
                "recognition"
            ),
            "score_fields": (
                "trust_building_score",
                "community_engagement_score",
                "emotional_impact_score",
                "storytelling_score"
            ),
            "editorial_angles": (
                "Community Trust",
                "Community Education",
                "Behind the Scenes"
            ),
            "platforms": ("Facebook", "Instagram", "Website"),
            "audiences": ("Morden residents", "Families", "Community partners"),
            "formats": ("photo carousel", "community post", "website feature"),
            "posting_window": "This afternoon"
        },
        {
            "category": "Public Education",
            "topic": "public_education",
            "title": "Public Education Opportunity",
            "terms": (
                "public_education",
                "fire_prevention",
                "smoke_alarm",
                "hydrant_heroes",
                "travelling_sparky",
                "safety",
                "prevention"
            ),
            "score_fields": (
                "public_education_value_score",
                "educational_value_score",
                "seasonal_relevance_score",
                "community_engagement_score"
            ),
            "editorial_angles": (
                "Public Education",
                "Community Education",
                "Seasonal Safety"
            ),
            "platforms": ("Facebook", "Instagram", "Website"),
            "audiences": ("Residents", "Students", "Families"),
            "formats": ("educational post", "campaign post", "photo carousel"),
            "posting_window": "This morning"
        },
        {
            "category": "Department Programs",
            "topic": "department_programs",
            "title": "Department Program Opportunity",
            "terms": (
                "hydrant_heroes",
                "travelling_sparky",
                "program",
                "school",
                "community",
                "public_education"
            ),
            "score_fields": (
                "public_education_value_score",
                "community_engagement_score",
                "trust_building_score",
                "seasonal_relevance_score"
            ),
            "editorial_angles": (
                "Public Education",
                "Community Trust",
                "Program Feature"
            ),
            "platforms": ("Facebook", "Instagram", "Website"),
            "audiences": ("Program audiences", "Families", "Residents"),
            "formats": ("program post", "photo carousel", "website feature"),
            "posting_window": "Next appropriate weekday"
        },
        {
            "category": "Community Events",
            "topic": "community_events",
            "title": "Community Event Opportunity",
            "terms": (
                "community_event",
                "community",
                "open_house",
                "parade",
                "families",
                "children",
                "partner"
            ),
            "score_fields": (
                "community_engagement_score",
                "trust_building_score",
                "emotional_impact_score",
                "storytelling_score"
            ),
            "editorial_angles": (
                "Community Event",
                "Community Trust",
                "Recognition"
            ),
            "platforms": ("Facebook", "Instagram"),
            "audiences": ("Morden residents", "Families"),
            "formats": ("photo carousel", "community post", "short-form video"),
            "posting_window": "Before the weekend"
        },
        {
            "category": "Behind the Scenes",
            "topic": "behind_the_scenes",
            "title": "Behind the Scenes Opportunity",
            "terms": (
                "behind_the_scenes",
                "station",
                "maintenance",
                "equipment",
                "training",
                "crew",
                "apparatus"
            ),
            "score_fields": (
                "storytelling_score",
                "visual_impact_score",
                "trust_building_score",
                "community_engagement_score"
            ),
            "editorial_angles": (
                "Behind the Scenes",
                "Community Trust",
                "Training Highlight"
            ),
            "platforms": ("Facebook", "Instagram"),
            "audiences": ("General followers", "Residents"),
            "formats": ("behind-the-scenes post", "single photo", "short-form video"),
            "posting_window": "This evening"
        },
        {
            "category": "Preparedness",
            "topic": "preparedness",
            "title": "Preparedness Opportunity",
            "terms": (
                "preparedness",
                "storm",
                "emergency",
                "safety",
                "public_education",
                "prevention"
            ),
            "score_fields": (
                "public_education_value_score",
                "educational_value_score",
                "time_sensitive_score",
                "trust_building_score"
            ),
            "editorial_angles": (
                "Preparedness",
                "Community Education",
                "Seasonal Safety"
            ),
            "platforms": ("Facebook", "Instagram"),
            "audiences": ("Morden residents", "Families"),
            "formats": ("educational post", "campaign post", "media package"),
            "posting_window": "Within 48 hours"
        },
        {
            "category": "Volunteerism",
            "topic": "volunteerism",
            "title": "Volunteerism Opportunity",
            "terms": (
                "volunteer",
                "firefighter",
                "service",
                "community",
                "recruitment",
                "recognition"
            ),
            "score_fields": (
                "recruitment_value_score",
                "recognition_value_score",
                "emotional_impact_score",
                "community_engagement_score"
            ),
            "editorial_angles": (
                "Volunteer Spotlight",
                "Recruitment",
                "Community Trust"
            ),
            "platforms": ("Facebook", "Instagram", "LinkedIn"),
            "audiences": ("Prospective volunteers", "Residents"),
            "formats": ("firefighter profile", "recognition post", "photo carousel"),
            "posting_window": "This evening"
        },
        {
            "category": "Leadership",
            "topic": "leadership",
            "title": "Leadership Opportunity",
            "terms": (
                "leadership",
                "officer",
                "command",
                "training",
                "officer_development",
                "incident_command"
            ),
            "score_fields": (
                "trust_building_score",
                "educational_value_score",
                "storytelling_score",
                "recognition_value_score"
            ),
            "editorial_angles": (
                "Officer Development",
                "Leadership",
                "Technical Education"
            ),
            "platforms": ("LinkedIn", "Facebook", "Website"),
            "audiences": ("Community partners", "Fire service members"),
            "formats": ("leadership post", "website feature", "annual report content"),
            "posting_window": "Next appropriate weekday"
        },
        {
            "category": "Teamwork",
            "topic": "teamwork",
            "title": "Teamwork Opportunity",
            "terms": (
                "teamwork",
                "crew",
                "training",
                "firefighter",
                "community",
                "volunteer"
            ),
            "score_fields": (
                "storytelling_score",
                "emotional_impact_score",
                "recruitment_value_score",
                "community_engagement_score"
            ),
            "editorial_angles": (
                "Teamwork",
                "Recruitment",
                "Training Highlight"
            ),
            "platforms": ("Facebook", "Instagram", "LinkedIn"),
            "audiences": ("Residents", "Prospective firefighters"),
            "formats": ("photo carousel", "single photo", "short-form video"),
            "posting_window": "This evening"
        },
        {
            "category": "Incident Recap",
            "topic": "incident_recap",
            "title": "Incident Recap Opportunity",
            "terms": (
                "incident",
                "structure_fire",
                "vehicle_fire",
                "mvc",
                "emergency_response",
                "rescue",
                "medical"
            ),
            "score_fields": (
                "emergency_response_value_score",
                "trust_building_score",
                "storytelling_score",
                "historical_importance_score"
            ),
            "editorial_angles": (
                "Incident Recap",
                "Community Trust",
                "Annual Report"
            ),
            "platforms": ("Facebook", "Website", "News Release"),
            "audiences": ("Residents", "Media partners"),
            "formats": ("incident recap", "media release", "website feature"),
            "posting_window": "Hold until supporting information is confirmed"
        },
        {
            "category": "Historical Content",
            "topic": "historical_content",
            "title": "Historical Content Opportunity",
            "terms": (
                "historical",
                "archive",
                "throwback",
                "apparatus",
                "ceremony",
                "annual_report"
            ),
            "score_fields": (
                "historical_importance_score",
                "storytelling_score",
                "trust_building_score",
                "community_engagement_score"
            ),
            "editorial_angles": (
                "Historical / Throwback",
                "Community Trust",
                "Annual Report"
            ),
            "platforms": ("Facebook", "Instagram", "Website"),
            "audiences": ("Long-time residents", "Department supporters"),
            "formats": ("throwback post", "archive post", "website feature"),
            "posting_window": "Thursday morning"
        },
        {
            "category": "Annual Report Content",
            "topic": "annual_report_content",
            "title": "Annual Report Content Opportunity",
            "terms": (
                "annual_report",
                "training",
                "emergency_response",
                "community",
                "recognition",
                "public_education"
            ),
            "score_fields": (
                "storytelling_score",
                "trust_building_score",
                "historical_importance_score",
                "emergency_response_value_score"
            ),
            "editorial_angles": (
                "Annual Report",
                "Community Trust",
                "Website Feature"
            ),
            "platforms": ("Annual Report", "Website", "LinkedIn"),
            "audiences": ("Council", "Partners", "Residents"),
            "formats": ("annual report content", "website feature", "media package"),
            "posting_window": "Year-end planning"
        },
        {
            "category": "Website Feature",
            "topic": "website_feature",
            "title": "Website Feature Opportunity",
            "terms": (
                "website",
                "public_education",
                "apparatus",
                "training",
                "community",
                "recruitment"
            ),
            "score_fields": (
                "trust_building_score",
                "educational_value_score",
                "visual_impact_score",
                "evergreen_score"
            ),
            "editorial_angles": (
                "Website Feature",
                "Public Education",
                "Community Trust"
            ),
            "platforms": ("Website", "Facebook"),
            "audiences": ("Residents seeking information", "Community partners"),
            "formats": ("website feature", "single photo", "media package"),
            "posting_window": "Next appropriate weekday"
        }
    )

    def __init__(
        self,
        database=None,
        memory_service=None,
        knowledge_service=None,
        context_engine=None,
        graph_service=None
    ):

        self.db = database or context.database
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.context_engine = context_engine or ContextEngine()
        self.graph = graph_service or KnowledgeGraphService(
            database=self.db,
            knowledge_service=self.knowledge
        )
        self.last_metrics = {}

    ############################################################

    def build_candidates(self, as_of=None, limit=None):

        started = time.perf_counter()
        timings = {}
        limit = min(
            int(limit or self.MAX_CANDIDATES),
            self.MAX_CANDIDATES
        )
        step = time.perf_counter()
        snapshot = self.context_engine.snapshot(as_of)
        timings["context_seconds"] = round(time.perf_counter() - step, 3)
        step = time.perf_counter()
        media_rows = self.db.content_director_candidates(limit=limit)
        timings["media_query_seconds"] = round(time.perf_counter() - step, 3)
        media_ids = [
            row.get("media_id")
            for row in media_rows
            if row.get("media_id")
        ]
        step = time.perf_counter()
        fire_rows = self.db.fire_service_intelligence_for_media_ids(media_ids)
        timings["fire_query_seconds"] = round(time.perf_counter() - step, 3)
        step = time.perf_counter()
        correction_rows = self.db.active_media_corrections_for_media_ids(
            media_ids
        )
        timings["correction_query_seconds"] = round(
            time.perf_counter() - step,
            3
        )
        step = time.perf_counter()
        memory_rows = self.db.social_posts(limit=1000)
        timings["memory_query_seconds"] = round(time.perf_counter() - step, 3)
        step = time.perf_counter()
        recent_recommended = self.db.recent_recommended_media_ids(
            days=45,
            limit=500
        )
        recent_social = self.memory.recent_social_media_ids(days=120)
        timings["recent_usage_query_seconds"] = round(
            time.perf_counter() - step,
            3
        )
        step = time.perf_counter()
        effective_assets = []

        for row in media_rows:
            asset = self._effective_asset(
                row,
                fire_rows.get(row.get("media_id"), {}),
                correction_rows.get(row.get("media_id"), [])
            )
            asset["all_terms"] = sorted(self._asset_terms(asset))
            effective_assets.append(asset)

        timings["effective_asset_seconds"] = round(
            time.perf_counter() - step,
            3
        )
        profiles = []
        step = time.perf_counter()

        for profile in self.CATEGORY_PROFILES:
            terms = {
                self._token(value)
                for value in profile["terms"]
            }
            assets = []

            for asset in effective_assets:
                asset_terms = set(asset.get("all_terms", []))

                if not asset_terms & terms:
                    continue

                assets.append(
                    {
                        **asset,
                        "matched_terms": sorted(asset_terms & terms),
                        "all_terms": sorted(asset_terms)
                    }
                )

            if not assets:
                continue

            assets.sort(
                key=lambda item: (
                    int(item.get("communications_score") or 0),
                    int(item.get("intelligence_score") or 0),
                    item.get("filename", "")
                ),
                reverse=True
            )

            profiles.append(
                {
                    "profile": profile,
                    "assets": assets[:self.MAX_SUPPORTING_IDS],
                    "snapshot": snapshot,
                    "memory_profile": self._memory_profile(
                        profile,
                        memory_rows
                    ),
                    "recent_recommended": recent_recommended,
                    "recent_social": recent_social,
                    "knowledge_signals": self._knowledge_signals(profile)
                    }
                )

        timings["category_seconds"] = round(time.perf_counter() - step, 3)
        timings["total_seconds"] = round(time.perf_counter() - started, 3)
        self.last_metrics = {
            **timings,
            "media_sample_count": len(media_rows),
            "candidate_count": len(profiles),
            "limit": limit
        }
        logger.info(
            (
                "Built editorial recommendation candidates categories=%s "
                "media_sample=%s elapsed=%s timings=%s"
            ),
            len(profiles),
            len(media_rows),
            self.last_metrics["total_seconds"],
            timings
        )

        return profiles

    ############################################################

    def _effective_asset(self, row, fire, corrections):

        asset = dict(row)
        fire = dict(fire or {})
        corrections = corrections or []
        asset["fire_service_intelligence"] = fire
        asset["human_corrections"] = corrections
        asset["is_human_corrected"] = bool(corrections)
        asset["correction_count"] = len(corrections)

        for correction in corrections:
            self._apply_correction(
                asset,
                fire,
                correction.get("field_name"),
                correction.get("corrected_value")
            )

        return asset

    ############################################################

    def _apply_correction(self, asset, fire, field, value):

        if field == "people_count":
            count = self._to_int(value)
            fire["firefighter_count"] = count
            asset["people_tags"] = ["people"] if count else ["unknown_people"]

        elif field == "incident_classification":
            fire["incident_classification"] = str(value or "")
            asset["incident_type"] = str(value or "")

        elif field == "operational_context":
            fire["operational_context"] = str(value or "")
            asset["normalized_scene"] = str(value or "")

        elif field == "primary_activity":
            fire["operational_activity"] = str(value or "")
            asset["primary_activity"] = str(value or "")

        elif field == "operational_skills":
            fire["operational_skills"] = self._as_list(value)

        elif field == "ppe":
            fire["ppe"] = self._as_list(value)
            asset["ppe_tags"] = self._as_list(value)

        elif field == "equipment":
            fire["equipment"] = self._as_list(value)
            asset["equipment_tags"] = self._as_list(value)

        elif field == "apparatus":
            fire["apparatus"] = self._as_list(value)
            asset["apparatus_tags"] = self._as_list(value)

        elif field == "communications_uses":
            fire["communications_uses"] = self._as_list(value)
            asset["recommended_uses"] = self._as_list(value)

        elif field == "campaigns":
            asset["suggested_campaigns"] = self._as_list(value)

        elif field == "suggested_audience":
            asset["suggested_audience"] = self._as_list(value)

        elif field == "suggested_platforms":
            asset["suggested_platforms"] = self._as_list(value)

        elif field == "suggested_time_of_year":
            asset["suggested_time_of_year"] = str(value or "")

    ############################################################

    def _asset_terms(self, asset):

        values = []
        fire = asset.get("fire_service_intelligence") or {}

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "search_text",
            "suggested_platform",
            "suggested_time_of_year"
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
            values.extend(asset.get(key) or [])

        for key in (
            "incident_classification",
            "operational_activity",
            "operational_context",
            "group_size"
        ):
            values.extend(self._split(fire.get(key)))

        for key in (
            "ppe",
            "equipment",
            "apparatus",
            "communications_uses",
            "operational_skills",
            "communications_intent",
            "operational_reasoning"
        ):
            values.extend(fire.get(key) or [])

        terms = {
            self._token(value)
            for value in values
            if self._token(value)
        }

        terms |= self._graph_terms(terms)

        return terms

    ############################################################

    def _graph_terms(self, terms):

        if not terms:
            return set()

        try:
            context = self.graph.reasoning_context(list(terms)[:40])
        except Exception:
            return set()

        values = []

        for key in (
            "operational_skills",
            "communications_intent",
            "campaigns"
        ):
            values.extend(context.get(key) or [])

        for rows in context.get("expanded_terms", {}).values():
            values.extend(
                row.get("name", "")
                for row in rows
            )

        return {
            self._token(value)
            for value in values
            if self._token(value)
        }

    ############################################################

    def _memory_profile(self, profile, posts):

        terms = [
            self._token(value)
            for value in profile["terms"]
        ]
        matches = []

        for post in posts or []:
            text = " ".join(
                str(post.get(key, ""))
                for key in (
                    "caption",
                    "campaign",
                    "opportunity_type",
                    "writing_style",
                    "context"
                )
            ).lower().replace(" ", "_")

            if any(term and term in text for term in terms):
                matches.append(post)

        last_posted = ""

        if matches:
            last_posted = max(
                post.get("post_date", "")
                for post in matches
            )

        return {
            "matching_posts": len(matches),
            "last_posted": last_posted,
            "memory_available": bool(posts)
        }

    ############################################################

    def _knowledge_signals(self, profile):

        try:
            snapshot = self.knowledge.snapshot()
        except Exception:
            return []

        profile_terms = {
            self._token(value)
            for value in profile["terms"]
        }
        matches = []

        for key in (
            "programs",
            "annual_events",
            "apparatus",
            "community_partners",
            "locations"
        ):
            for item in snapshot.get(key, []):
                values = [item.get("name", ""), item.get("category", "")]
                values.extend(item.get("tags") or [])
                item_terms = {
                    self._token(value)
                    for value in values
                }

                if item_terms & profile_terms:
                    matches.append(item.get("name", ""))

        return [
            value
            for value in self._unique(matches)
            if value
        ][:5]

    ############################################################

    def _split(self, value):

        return [
            part.strip()
            for part in str(value or "").replace(",", " ").replace("_", " ").split()
            if part.strip()
        ]

    def _as_list(self, value):

        if value is None:
            return []

        if isinstance(value, list):
            return [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

        return [
            item.strip()
            for item in str(value).replace("\n", ",").split(",")
            if item.strip()
        ]

    def _token(self, value):

        return str(value or "").strip().lower().replace(" ", "_")

    def _to_int(self, value):

        try:
            return int(value)
        except Exception:
            return 0

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:
            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
