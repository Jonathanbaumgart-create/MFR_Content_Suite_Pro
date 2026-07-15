from collections import Counter
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
    MAX_TOPIC_CANDIDATES = 18

    TOPIC_DEFINITIONS = (
        {
            "topic": "water_safety",
            "label": "Water Safety",
            "terms": ("water_safety", "ice_rescue", "rescue_boat"),
            "category": "Public Education",
            "editorial_angle": "Seasonal Safety",
            "audience": "Families and outdoor users",
            "posting_window": "Before weekend recreation periods",
            "platforms": ("Facebook", "Instagram")
        },
        {
            "topic": "recruitment",
            "label": "Recruit Volunteer Firefighters",
            "terms": ("recruitment", "recruit", "volunteer"),
            "category": "Recruitment",
            "editorial_angle": "Recruitment",
            "audience": "Prospective firefighters",
            "posting_window": "This evening",
            "platforms": ("Facebook", "Instagram", "LinkedIn")
        },
        {
            "topic": "firefighter_training",
            "label": "Firefighter Training",
            "terms": ("training", "drill", "training_tuesday", "training_evolution"),
            "category": "Training",
            "editorial_angle": "Training Tuesday",
            "audience": "Morden residents and prospective firefighters",
            "posting_window": "Next appropriate weekday",
            "platforms": ("Facebook", "Instagram", "LinkedIn")
        },
        {
            "topic": "scba",
            "label": "SCBA Training",
            "terms": ("scba", "self_contained_breathing_apparatus", "breathing_apparatus"),
            "category": "Training",
            "editorial_angle": "Technical Education",
            "audience": "Residents and prospective firefighters",
            "posting_window": "Training Tuesday",
            "platforms": ("Facebook", "Instagram")
        },
        {
            "topic": "vehicle_extrication",
            "label": "Vehicle Extrication",
            "terms": ("vehicle_extrication", "extrication", "mvc", "rescue_tools", "spreaders", "cutters"),
            "category": "Technical Education",
            "editorial_angle": "Training Highlight",
            "audience": "Morden residents",
            "posting_window": "Next appropriate weekday",
            "platforms": ("Facebook", "Instagram", "Website")
        },
        {
            "topic": "smoke_alarms",
            "label": "Smoke Alarm Reminder",
            "terms": ("smoke_alarm", "smoke_alarms", "alarm", "carbon_monoxide"),
            "category": "Public Education",
            "editorial_angle": "Public Education",
            "audience": "Residents and families",
            "posting_window": "This morning",
            "platforms": ("Facebook", "Instagram")
        },
        {
            "topic": "fire_prevention",
            "label": "Fire Prevention Reminder",
            "terms": ("fire_prevention", "prevention", "public_education"),
            "category": "Public Education",
            "editorial_angle": "Fire Prevention",
            "audience": "Morden residents",
            "posting_window": "During prevention campaign windows",
            "platforms": ("Facebook", "Instagram", "Website")
        },
        {
            "topic": "community_event",
            "label": "Community Event",
            "terms": ("community_event", "open_house", "parade", "families", "children"),
            "category": "Community Events",
            "editorial_angle": "Community Trust",
            "audience": "Families and community partners",
            "posting_window": "Before the weekend",
            "platforms": ("Facebook", "Instagram")
        },
        {
            "topic": "sparky",
            "label": "Travelling Sparky Follow-up",
            "terms": ("sparky", "travelling_sparky"),
            "category": "Department Programs",
            "editorial_angle": "Public Education",
            "audience": "Students and families",
            "posting_window": "During the school year",
            "platforms": ("Facebook", "Instagram", "Website")
        },
        {
            "topic": "hydrant_heroes",
            "label": "Hydrant Heroes Follow-up",
            "terms": ("hydrant_heroes",),
            "category": "Department Programs",
            "editorial_angle": "Community Education",
            "audience": "Neighbourhood residents",
            "posting_window": "Winter safety season",
            "platforms": ("Facebook", "Instagram")
        },
        {
            "topic": "wildland_fire",
            "label": "Wildland Fire Awareness",
            "terms": ("wildland", "wildfire", "grass_fire", "brush_truck", "open_burning"),
            "category": "Seasonal Safety",
            "editorial_angle": "Seasonal Safety",
            "audience": "Rural and city residents",
            "posting_window": "Wildfire and grass fire season",
            "platforms": ("Facebook", "Instagram")
        },
        {
            "topic": "grass_fires",
            "label": "Grass Fire Prevention",
            "terms": ("grass_fire", "grass_fires", "open_burning", "wildland"),
            "category": "Seasonal Safety",
            "editorial_angle": "Preparedness",
            "audience": "Residents and property owners",
            "posting_window": "Spring and dry weather periods",
            "platforms": ("Facebook", "Instagram")
        },
        {
            "topic": "ice_safety",
            "label": "Ice Safety Reminder",
            "terms": ("ice_safety",),
            "category": "Seasonal Safety",
            "editorial_angle": "Seasonal Safety",
            "audience": "Families and outdoor users",
            "posting_window": "Winter safety season",
            "platforms": ("Facebook", "Instagram")
        },
        {
            "topic": "apparatus",
            "label": "Apparatus Spotlight",
            "terms": ("apparatus", "engine", "pumper", "ladder", "tanker", "rescue", "brush_truck"),
            "category": "Apparatus and Equipment",
            "editorial_angle": "Apparatus Feature",
            "audience": "Residents and community partners",
            "posting_window": "This afternoon",
            "platforms": ("Facebook", "Instagram", "Website")
        },
        {
            "topic": "ladder_operations",
            "label": "Ladder Operations Training",
            "terms": ("ladder_operations", "ground_ladder", "aerial_ladder", "ladder"),
            "category": "Training",
            "editorial_angle": "Training Highlight",
            "audience": "Residents and prospective firefighters",
            "posting_window": "Training Tuesday",
            "platforms": ("Facebook", "Instagram", "LinkedIn")
        },
        {
            "topic": "rope_rescue",
            "label": "Rope Rescue Training",
            "terms": ("rope_rescue", "life_safety_rope", "rope", "rescue_equipment"),
            "category": "Technical Education",
            "editorial_angle": "Technical Education",
            "audience": "Residents and fire service followers",
            "posting_window": "Next appropriate weekday",
            "platforms": ("Facebook", "Instagram", "Website")
        },
        {
            "topic": "medical_response",
            "label": "Medical Response Readiness",
            "terms": ("medical", "medical_response", "medical_bag", "ambulance"),
            "category": "Emergency Response",
            "editorial_angle": "Community Trust",
            "audience": "Morden residents",
            "posting_window": "This afternoon",
            "platforms": ("Facebook", "Website")
        },
        {
            "topic": "public_education",
            "label": "Public Education",
            "terms": ("public_education", "community_education", "education", "children", "school"),
            "category": "Public Education",
            "editorial_angle": "Community Education",
            "audience": "Families and students",
            "posting_window": "This morning",
            "platforms": ("Facebook", "Instagram", "Website")
        },
        {
            "topic": "firefighter_spotlight",
            "label": "Firefighter Spotlight",
            "terms": ("firefighter", "crew", "people", "recognition", "volunteer_spotlight"),
            "category": "Firefighter Spotlight",
            "editorial_angle": "Volunteer Spotlight",
            "audience": "Residents and prospective firefighters",
            "posting_window": "This evening",
            "platforms": ("Facebook", "Instagram", "LinkedIn")
        },
        {
            "topic": "mutual_aid",
            "label": "Mutual Aid Partnership",
            "terms": ("mutual_aid", "partner", "community_partner", "police", "ambulance", "public_works"),
            "category": "Community Trust",
            "editorial_angle": "Community Trust",
            "audience": "Residents and partners",
            "posting_window": "Next appropriate weekday",
            "platforms": ("Facebook", "LinkedIn", "Website")
        }
    )

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

    def build_candidates(self, as_of=None, limit=None, context="default"):

        started = time.perf_counter()
        timings = {}
        limit = min(
            int(limit or self.MAX_CANDIDATES),
            self.MAX_CANDIDATES
        )
        self._graph_term_cache = {}
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
        memory_rows = self.memory.search("", limit=1000)
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
        topic_seconds = 0

        for row in media_rows:
            asset = self._effective_asset(
                row,
                fire_rows.get(row.get("media_id"), {}),
                correction_rows.get(row.get("media_id"), [])
            )
            asset["all_terms"] = sorted(self._asset_terms(asset))
            topic_started = time.perf_counter()
            asset["topics"] = self.extract_topics(asset)
            topic_seconds += time.perf_counter() - topic_started
            effective_assets.append(asset)

        timings["effective_asset_seconds"] = round(
            time.perf_counter() - step,
            3
        )
        timings["topic_extraction_seconds"] = round(topic_seconds, 3)
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

        topic_profiles = self._topic_profiles(
            effective_assets,
            memory_rows,
            snapshot,
            recent_recommended,
            recent_social
        )
        profiles.extend(topic_profiles)

        timings["category_seconds"] = round(time.perf_counter() - step, 3)
        timings["total_seconds"] = round(time.perf_counter() - started, 3)
        self.last_metrics = {
            **timings,
            "media_sample_count": len(media_rows),
            "candidate_count": len(profiles),
            "topic_candidate_count": len(topic_profiles),
            "limit": limit,
            "context": context,
            "graph_cache_terms": len(getattr(self, "_graph_term_cache", {}))
        }
        logger.info(
            (
                "Built editorial recommendation candidates categories=%s "
                "topic_candidates=%s media_sample=%s elapsed=%s timings=%s"
            ),
            len(profiles),
            len(topic_profiles),
            len(media_rows),
            self.last_metrics["total_seconds"],
            timings
        )

        return profiles

    ############################################################

    def extract_topics(self, asset):

        terms = set(asset.get("all_terms", []))
        topics = []

        for definition in self.TOPIC_DEFINITIONS:
            definition_terms = {
                self._token(value)
                for value in definition["terms"]
            }
            matches = sorted(terms & definition_terms)

            if not matches:
                continue

            topics.append(
                {
                    "topic": definition["topic"],
                    "label": definition["label"],
                    "matches": matches,
                    "evidence_count": len(matches)
                }
            )

        return sorted(
            topics,
            key=lambda item: (
                item["evidence_count"],
                item["label"]
            ),
            reverse=True
        )

    ############################################################

    def _topic_profiles(
        self,
        assets,
        memory_rows,
        snapshot,
        recent_recommended,
        recent_social
    ):

        topic_assets = {}

        for asset in assets:
            for topic in asset.get("topics", []):
                topic_assets.setdefault(
                    topic["topic"],
                    []
                ).append(
                    {
                        **asset,
                        "matched_terms": topic["matches"],
                        "topic_label": topic["label"],
                        "topic_evidence_count": topic["evidence_count"]
                    }
                )

        profiles = []

        for definition in self.TOPIC_DEFINITIONS:
            assets_for_topic = topic_assets.get(
                definition["topic"],
                []
            )

            if not assets_for_topic:
                continue

            ranked_assets = sorted(
                assets_for_topic,
                key=self._asset_rank_key,
                reverse=True
            )
            profile = self._topic_profile(
                definition,
                ranked_assets
            )
            memory_profile = self._topic_memory_profile(
                definition,
                memory_rows
            )
            knowledge_signals = self._topic_knowledge_signals(definition)

            profiles.append(
                {
                    "profile": profile,
                    "assets": ranked_assets[:self.MAX_SUPPORTING_IDS],
                    "snapshot": snapshot,
                    "memory_profile": memory_profile,
                    "recent_recommended": recent_recommended,
                    "recent_social": recent_social,
                    "knowledge_signals": knowledge_signals,
                    "supporting_topics": [definition["label"]],
                    "supporting_programs": self._supporting_programs(
                        ranked_assets
                    ),
                    "topic_evidence": self._topic_evidence(
                        ranked_assets
                    ),
                    "is_topic_candidate": True
                }
            )

        profiles.sort(
            key=lambda item: (
                len(item["assets"]),
                self._average_asset_score(item["assets"]),
                item["profile"]["title"]
            ),
            reverse=True
        )

        return profiles[:self.MAX_TOPIC_CANDIDATES]

    ############################################################

    def _topic_profile(self, definition, assets):

        best = assets[0] if assets else {}
        label = definition["label"]
        title = self._topic_title(
            label,
            best
        )

        return {
            "category": definition["category"],
            "topic": definition["topic"],
            "title": title,
            "terms": definition["terms"],
            "score_fields": self._score_fields_for_topic(definition["topic"]),
            "editorial_angles": (
                definition["editorial_angle"],
                definition["category"]
            ),
            "platforms": definition["platforms"],
            "audiences": (definition["audience"],),
            "formats": ("single photo", "photo carousel", "short-form video"),
            "posting_window": definition["posting_window"],
            "evidence_label": label
        }

    def _topic_title(self, label, asset):

        terms = set(asset.get("all_terms", []))

        if label == "Firefighter Training":
            if "scba" in terms:
                return "Training Tuesday SCBA"
            if "ladder_operations" in terms or "ladder" in terms:
                return "Training Tuesday Ladder Operations"
            if "hose" in terms or "hose_operations" in terms:
                return "Training Tuesday Hose Operations"

        if label == "Apparatus Spotlight":
            for term, title in (
                ("ladder", "Ladder Truck Spotlight"),
                ("engine", "Engine Spotlight"),
                ("pumper", "Pumper Spotlight"),
                ("rescue", "Rescue Unit Spotlight"),
                ("tanker", "Tanker Spotlight"),
                ("brush_truck", "Brush Truck Spotlight")
            ):
                if term in terms:
                    return title

        return label

    def _score_fields_for_topic(self, topic):

        if topic in ("recruitment", "firefighter_spotlight"):
            return (
                "recruitment_value_score",
                "storytelling_score",
                "emotional_impact_score"
            )

        if topic in ("firefighter_training", "scba", "ladder_operations", "rope_rescue", "vehicle_extrication"):
            return (
                "educational_value_score",
                "recruitment_value_score",
                "storytelling_score",
                "visual_impact_score"
            )

        if topic in ("water_safety", "ice_safety", "fire_prevention", "smoke_alarms", "grass_fires", "wildland_fire"):
            return (
                "public_education_value_score",
                "educational_value_score",
                "seasonal_relevance_score",
                "time_sensitive_score"
            )

        return (
            "community_engagement_score",
            "trust_building_score",
            "storytelling_score",
            "visual_impact_score"
        )

    ############################################################

    def _topic_memory_profile(self, definition, posts):

        terms = {
            self._token(value)
            for value in definition["terms"]
        }
        terms.add(
            self._token(definition["label"])
        )
        matches = []

        for post in posts or []:
            text = self._post_text(post)

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
            "memory_available": bool(posts),
            "history_post_count": len(posts or []),
            "topic": definition["topic"],
            "topic_label": definition["label"]
        }

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

        if field == "description":
            asset["description"] = str(value or "")
            asset["effective_description"] = str(value or "")

        elif field == "people_count":
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
        filesystem = asset.get("filesystem_intelligence") or {}

        for key in (
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "description",
            "effective_description",
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
            values.extend(filesystem.get(key) or [])

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

        cache = getattr(self, "_graph_term_cache", None)
        if cache is None:
            cache = {}
            self._graph_term_cache = cache

        values = []
        ordered_terms = [
            term
            for term in sorted(terms)
            if term
        ][:40]

        for term in ordered_terms:
            if term not in cache:
                try:
                    context = self.graph.reasoning_context([term])
                except Exception:
                    context = {}

                term_values = []

                for key in (
                    "operational_skills",
                    "communications_intent",
                    "campaigns"
                ):
                    term_values.extend(context.get(key) or [])

                for rows in context.get("expanded_terms", {}).values():
                    term_values.extend(
                        row.get("name", "")
                        for row in rows
                    )

                cache[term] = {
                    self._token(value)
                    for value in term_values
                    if self._token(value)
                }

            values.extend(cache.get(term, set()))

        return set(values)

    ############################################################

    def _memory_profile(self, profile, posts):

        terms = [
            self._token(value)
            for value in profile["terms"]
        ]
        matches = []

        for post in posts or []:
            text = self._post_text(post)

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
            "memory_available": bool(posts),
            "history_post_count": len(posts or []),
            "topic": profile["topic"],
            "topic_label": profile["category"]
        }

    ############################################################

    def _post_text(self, post):

        values = []

        for key in (
            "caption",
            "headline",
            "campaign",
            "opportunity_type",
            "writing_style",
            "context",
            "platform"
        ):
            values.extend(self._split(post.get(key, "")))

        values.extend(post.get("hashtags") or [])
        values.extend(post.get("topics") or [])
        values.extend(post.get("programs") or [])
        values.extend(post.get("campaigns") or [])

        return " ".join(
            self._token(value)
            for value in values
            if self._token(value)
        )

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

    def _topic_knowledge_signals(self, definition):

        profile = {
            "terms": definition["terms"]
        }

        return self._knowledge_signals(profile)

    def _supporting_programs(self, assets):

        programs = []

        for asset in assets:
            for value in (
                list(asset.get("recommended_uses") or []) +
                list(asset.get("suggested_campaigns") or []) +
                list((asset.get("fire_service_intelligence") or {}).get("communications_uses") or [])
            ):
                token = self._token(value)

                if token in ("hydrant_heroes", "travelling_sparky", "sparky", "fire_prevention_week"):
                    programs.append(
                        str(value).replace("_", " ").title()
                    )

        return self._unique(programs)[:5]

    def _topic_evidence(self, assets):

        counts = Counter()

        for asset in assets:
            for topic in asset.get("topics", []):
                counts[topic["label"]] += topic["evidence_count"]

        return [
            {
                "topic": topic,
                "evidence_count": count
            }
            for topic, count in counts.most_common(8)
        ]

    def _asset_rank_key(self, asset):

        return (
            int(asset.get("communications_score") or 0),
            int(asset.get("storytelling_score") or 0),
            int(asset.get("intelligence_score") or 0),
            int((asset.get("fire_service_intelligence") or {}).get("operational_confidence") or 0),
            1 if asset.get("is_human_corrected") else 0,
            -1 if asset.get("media_type") == "video" else 0,
            asset.get("filename", "")
        )

    def _average_asset_score(self, assets):

        if not assets:
            return 0

        return sum(
            int(asset.get("communications_score") or 0)
            for asset in assets
        ) / len(assets)

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
