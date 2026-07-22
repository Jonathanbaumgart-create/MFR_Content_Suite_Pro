import json
import re
import sqlite3
import time
from datetime import datetime

from core.app_context import context
from services.communications_memory_service import CommunicationsMemoryService
from services.current_context_service import CurrentContextService
from services.logging_service import LoggingService
from services.media_topic_compatibility_service import MediaTopicCompatibilityService
from services.operational_activity_service import OperationalActivityService
from services.seasonal_communications_service import SeasonalCommunicationsService
from services.time_service import TimeService
from services.editorial_writing_service import EditorialWritingService
from services.recommendation_freshness_service import RecommendationFreshnessService


logger = LoggingService.get_logger("content")


class ContentDirectorRetrievalService:

    QUERY_VERSION = "content-director-retrieval-v1"
    DEFAULT_OPTION_COUNT = 3
    MAX_OPTION_COUNT = 5

    TOPIC_MAP = (
        (
            "smoke_advisory",
            (
                "smoke advisory",
                "air quality",
                "air quality warning",
                "wildfire smoke",
                "smoke haze",
                "haze",
                "visibility",
                "respiratory"
            )
        ),
        (
            "heat_warning",
            (
                "heat warning",
                "extreme heat",
                "heat",
                "hot weather",
                "hydration"
            )
        ),
        (
            "water_safety",
            (
                "water safety",
                "water rescue",
                "life jacket",
                "boating",
                "lake",
                "shoreline",
                "ice safety"
            )
        ),
        (
            "rope_rescue",
            (
                "rope rescue",
                "low angle rope",
                "low-angle rope",
                "steep embankment",
                "rescue rope",
                "technical rescue"
            )
        ),
        (
            "recruitment",
            (
                "volunteer recruitment",
                "recruitment",
                "volunteer",
                "join",
                "firefighter recruitment"
            )
        ),
        (
            "fire_prevention_week",
            (
                "fire prevention week",
                "fire prevention",
                "fpw",
                "home fire safety",
                "escape planning"
            )
        ),
        (
            "smoke_alarm",
            (
                "smoke alarm",
                "smoke detector",
                "test your alarms",
                "alarm reminder"
            )
        ),
        (
            "fireworks",
            (
                "fireworks",
                "fireworks safety",
                "canada day fireworks",
                "firework"
            )
        ),
        (
            "daycare",
            (
                "daycare",
                "spray down",
                "spraydown",
                "hose spray",
                "children visit"
            )
        ),
        (
            "hydrant_heroes",
            (
                "hydrant heroes",
                "hydrant",
                "clear hydrant",
                "snow hydrant"
            )
        ),
        (
            "grass_fire",
            (
                "grass fire",
                "wildland",
                "wildfire",
                "burn ban",
                "dry grass"
            )
        ),
        (
            "school_visit",
            (
                "school visit",
                "school",
                "public education visit",
                "travelling sparky"
            )
        ),
        (
            "helmet_promotion",
            (
                "helmet promotion",
                "promotion",
                "new helmet",
                "milestone"
            )
        ),
        (
            "historical_apparatus",
            (
                "historical apparatus",
                "apparatus history",
                "old apparatus",
                "vintage apparatus",
                "department history"
            )
        ),
        (
            "serious_incident",
            (
                "serious incident",
                "incident update",
                "emergency incident",
                "confirmed incident",
                "structure fire",
                "vehicle fire"
            )
        )
    )

    TOPIC_DETAILS = {
        "smoke_advisory": {
            "label": "Smoke Advisory",
            "secondary": [
                "air quality",
                "wildfire smoke",
                "respiratory exposure precautions",
                "visibility",
                "outdoor activity considerations"
            ],
            "hashtags": [
                "#AirQuality",
                "#WildfireSmoke",
                "#CommunitySafety",
                "#Morden",
                "#MordenFireRescue"
            ],
            "cta": "Check current conditions from official sources and adjust outdoor activity if smoke is affecting your area.",
            "type": "general safety reminder"
        },
        "heat_warning": {
            "label": "Heat Warning",
            "secondary": [
                "heat safety",
                "hydration",
                "checking on neighbours",
                "vehicle safety"
            ],
            "hashtags": [
                "#HeatSafety",
                "#SummerSafety",
                "#CommunitySafety",
                "#Morden",
                "#MordenFireRescue"
            ],
            "cta": "Drink water, find shade or cooling spaces, and check on people who may be more vulnerable to heat.",
            "type": "public safety reminder"
        },
        "water_safety": {
            "label": "Water Safety",
            "secondary": [
                "water rescue",
                "life jackets",
                "shoreline safety",
                "boating",
                "ice or water rescue"
            ],
            "hashtags": [
                "#WaterSafety",
                "#LifeJackets",
                "#CommunitySafety",
                "#Morden",
                "#MordenFireRescue"
            ],
            "cta": "Wear a life jacket, supervise children closely, and call 911 if someone is in trouble on or near the water.",
            "type": "seasonal safety reminder"
        },
        "rope_rescue": {
            "label": "Rope Rescue Training",
            "secondary": [
                "low-angle rope rescue",
                "steep terrain",
                "patient movement",
                "EMS access",
                "technical rescue training"
            ],
            "hashtags": [
                "#RopeRescue",
                "#FirefighterTraining",
                "#EmergencyPreparedness",
                "#FireService",
                "#MordenMB"
            ],
            "cta": "Learn why realistic training helps firefighters solve access problems safely.",
            "type": "training explainer"
        },
        "recruitment": {
            "label": "Volunteer Recruitment",
            "secondary": [
                "volunteer firefighters",
                "training",
                "teamwork",
                "community service"
            ],
            "hashtags": [
                "#JoinMFR",
                "#VolunteerFirefighter",
                "#ServeYourCommunity",
                "#Morden",
                "#MordenFireRescue"
            ],
            "cta": "Reach out to learn more about serving your community with Morden Fire & Rescue.",
            "type": "recruitment"
        },
        "smoke_alarm": {
            "label": "Smoke Alarm Reminder",
            "secondary": [
                "smoke alarms",
                "home fire safety",
                "testing alarms",
                "escape planning"
            ],
            "hashtags": [
                "#SmokeAlarms",
                "#FirePrevention",
                "#HomeSafety",
                "#Morden",
                "#MordenFireRescue"
            ],
            "cta": "Test your smoke alarms, replace expired units, and make sure everyone knows two ways out.",
            "type": "fire prevention reminder"
        },
        "fire_prevention_week": {
            "label": "Fire Prevention Week",
            "secondary": [
                "fire prevention",
                "smoke alarms",
                "escape planning",
                "home fire safety",
                "public education"
            ],
            "hashtags": [
                "#FirePreventionWeek",
                "#FirePrevention",
                "#SmokeAlarms",
                "#CommunitySafety",
                "#MordenFireRescue"
            ],
            "cta": "Test alarms, talk through your escape plan, and look for simple ways to reduce fire risk at home.",
            "type": "fire prevention campaign"
        },
        "fireworks": {
            "label": "Fireworks Safety",
            "secondary": [
                "fireworks",
                "Canada Day",
                "distance",
                "supervision",
                "local rules"
            ],
            "hashtags": [
                "#FireworksSafety",
                "#PublicSafety",
                "#SummerSafety",
                "#MordenMB"
            ],
            "cta": "Follow local rules, keep water nearby, supervise carefully, and call 911 for emergencies.",
            "type": "public safety reminder"
        },
        "daycare": {
            "label": "Daycare Visit",
            "secondary": [
                "daycare",
                "spray-down",
                "children",
                "community visit"
            ],
            "hashtags": [
                "#CommunityEvent",
                "#SummerFun",
                "#TeamMFR",
                "#MordenMB"
            ],
            "cta": "Celebrate a friendly MFR community visit.",
            "type": "community event"
        },
        "hydrant_heroes": {
            "label": "Hydrant Heroes",
            "secondary": [
                "hydrants",
                "snow clearing",
                "winter safety",
                "community help"
            ],
            "hashtags": [
                "#HydrantHeroes",
                "#WinterSafety",
                "#PublicSafety",
                "#MordenMB"
            ],
            "cta": "Keep hydrants visible and clear when snow builds up.",
            "type": "seasonal safety reminder"
        },
        "grass_fire": {
            "label": "Grass Fire Safety",
            "secondary": [
                "grass fire",
                "wildland",
                "dry conditions",
                "burning safety"
            ],
            "hashtags": [
                "#GrassFireSafety",
                "#WildfirePrevention",
                "#PublicSafety",
                "#MordenMB"
            ],
            "cta": "Watch dry conditions and follow local burning rules.",
            "type": "seasonal safety reminder"
        },
        "school_visit": {
            "label": "School Visit",
            "secondary": [
                "school visit",
                "public education",
                "children",
                "Travelling Sparky"
            ],
            "hashtags": [
                "#PublicEducation",
                "#SchoolVisit",
                "#CommunityEvent",
                "#MordenMB"
            ],
            "cta": "Share a public education moment with local students.",
            "type": "public education event"
        },
        "helmet_promotion": {
            "label": "Helmet Promotion",
            "secondary": [
                "helmet promotion",
                "recognition",
                "milestone",
                "leadership"
            ],
            "hashtags": [
                "#FireService",
                "#Leadership",
                "#TeamMFR",
                "#MordenMB"
            ],
            "cta": "Recognize a department milestone.",
            "type": "recognition"
        },
        "historical_apparatus": {
            "label": "Historical Apparatus",
            "secondary": [
                "apparatus history",
                "department history",
                "equipment evolution",
                "fire service heritage"
            ],
            "hashtags": [
                "#MFRHistory",
                "#FireService",
                "#Apparatus",
                "#MordenMB"
            ],
            "cta": "Share a department history moment without overstating unverified details.",
            "type": "historical feature"
        },
        "serious_incident": {
            "label": "Serious Incident",
            "secondary": [
                "confirmed incident information",
                "public safety",
                "operational response",
                "community update",
                "incident response",
                "emergency response",
                "structure fire",
                "vehicle fire",
                "mvc",
                "hazmat"
            ],
            "hashtags": [
                "#PublicSafety",
                "#CommunityUpdate",
                "#MordenMB"
            ],
            "cta": "Share only confirmed information and direct residents to official updates when needed.",
            "type": "incident information"
        },
        "general_engagement": {
            "label": "Community Safety",
            "secondary": [
                "community safety",
                "public education",
                "MFR update"
            ],
            "hashtags": [
                "#CommunitySafety",
                "#Morden",
                "#MordenFireRescue"
            ],
            "cta": "Follow Morden Fire & Rescue for local safety updates.",
            "type": "community update"
        }
    }

    WARNING_TOPICS = {
        "smoke_advisory",
        "heat_warning"
    }

    def __init__(
        self,
        database=None,
        memory_service=None,
        operational_service=None,
        context_service=None,
        compatibility_service=None
    ):
        self.db = database or context.database
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.context = context_service or CurrentContextService()
        self.compatibility = compatibility_service or MediaTopicCompatibilityService()
        self.operational = operational_service or OperationalActivityService(
            database=self.db,
            memory_service=self.memory,
            context_service=self.context,
            compatibility_service=self.compatibility
        )
        self.seasonal = SeasonalCommunicationsService(database=self.db)
        self.writer = EditorialWritingService()
        self.freshness = RecommendationFreshnessService(database=self.db)
        self.last_metrics = {}

    def build_prompt_package(self, prompt, limit=5, now=None, option_count=None):
        started = time.perf_counter()
        interpreted = self.interpret_query(prompt)
        option_count = self._option_count(option_count)
        current_context = self.context.current_context(now=now)
        historical = self.historical_matches(
            interpreted,
            current_context=current_context,
            limit=6
        )
        around_this_time = self.seasonal.around_this_time(
            topic=interpreted.get("label", ""),
            current_date=now,
            limit=6
        )
        if (
            interpreted.get("primary_topic") == "general_engagement"
            and not interpreted.get("matched_terms")
        ):
            empty_media = {
                "accepted": [],
                "excluded": [],
                "recoverable_candidates": [],
                "no_suitable_media": True,
                "unmatched_prompt": True
            }
            return self._blocked_package(
                prompt,
                interpreted,
                current_context,
                historical,
                around_this_time,
                empty_media,
                "No verified media or topic match was found for this search."
            )
        clusters = self.operational.clusters_for_window(
            days=30,
            limit=140,
            now=now
        )
        media = self.media_candidates(
            interpreted,
            clusters=clusters,
            limit=max(limit, option_count * 2)
        )
        package = self._package(
            prompt,
            interpreted,
            current_context,
            historical,
            around_this_time,
            media,
            option_count=option_count
        )
        self.last_metrics = {
            "total_seconds": round(time.perf_counter() - started, 3),
            "historical_count": len(historical),
            "around_this_time_count": len(
                around_this_time.get("matches", [])
            ),
            "accepted_media_count": len(media.get("accepted", [])),
            "excluded_media_count": len(media.get("excluded", [])),
            "option_count": len(package.get("options", [])),
            "cluster_count": len(clusters),
            "version": self.QUERY_VERSION
        }
        logger.info(
            "Content Director prompt package prompt=%s topic=%s media=%s history=%s elapsed=%s",
            prompt,
            interpreted.get("primary_topic"),
            self.last_metrics["accepted_media_count"],
            self.last_metrics["historical_count"],
            self.last_metrics["total_seconds"]
        )
        return package

    def interpret_query(self, prompt):
        text = self._normalize(prompt)
        primary = "general_engagement"
        matched = []

        for topic, terms in self.TOPIC_MAP:
            hits = [
                term
                for term in terms
                if term in text
            ]
            if hits:
                primary = topic
                matched.extend(hits)
                break

        details = self.TOPIC_DETAILS[primary]
        platforms = []
        for platform in ("facebook", "instagram", "linkedin", "website"):
            if platform in text:
                platforms.append(platform.title())

        if not platforms:
            platforms = ["Facebook", "Instagram"]

        urgency = "normal"
        if any(term in text for term in ("warning", "advisory", "alert", "today", "now")):
            urgency = "elevated"

        return {
            "raw_prompt": prompt,
            "primary_topic": primary,
            "label": details["label"],
            "secondary_topics": list(details["secondary"]),
            "matched_terms": matched,
            "urgency": urgency,
            "seasonality": self._seasonality(primary),
            "desired_platforms": platforms,
            "communication_type": details["type"],
            "location_constraints": ["Morden", "Morden Fire & Rescue"],
            "topic_terms": self._topic_terms(primary)
        }

    def historical_matches(self, interpreted, current_context=None, limit=6):
        current_context = current_context or {}
        raw = []
        seen = set()

        try:
            rows = self.db.effective_communication_memory(limit=500)
        except Exception:
            rows = []

        if not rows:
            try:
                rows = self.db.social_posts(limit=500)
            except Exception:
                rows = []

        for row in rows:
            record_id = row.get("communication_id") or row.get("id") or row.get("post_id")
            key = record_id or row.get("caption") or row.get("original_text")
            if not key or key in seen:
                continue
            seen.add(key)
            scored = self._score_history(row, interpreted, current_context)
            if scored["similarity_score"] <= 0:
                continue
            raw.append(scored)

        raw.sort(
            key=lambda item: (
                item.get("similarity_score", 0),
                item.get("post_date", "")
            ),
            reverse=True
        )
        return raw[:limit]

    def media_candidates(self, interpreted, clusters=None, limit=5):
        topic_label = interpreted.get("label") or interpreted.get("primary_topic")
        topic_terms = list(interpreted.get("topic_terms") or [])
        compatibility_topic = topic_terms or [topic_label]
        accepted = []
        excluded = []

        cluster_result = self.operational.media_for_topic(
            compatibility_topic,
            clusters=clusters,
            limit=max(limit * 2, 10)
        )
        accepted.extend(cluster_result.get("accepted", []))
        excluded.extend(cluster_result.get("excluded", []))

        for term in topic_terms[:8]:
            for row in self._filesystem_media_rows(term, limit=30):
                result = self.compatibility.evaluate(
                    compatibility_topic,
                    row,
                    activity={
                        "title": row.get("filesystem_intelligence", {}).get(
                            "subcategory",
                            ""
                        )
                    }
                )
                item = {
                    **row,
                    "compatibility": result,
                    "filesystem_media": True
                }
                if result.get("compatible"):
                    accepted.append(item)
                else:
                    excluded.append(item)

        for term in topic_terms[:6]:
            for row in self._historical_media_rows(term, limit=30):
                result = self.compatibility.evaluate(
                    compatibility_topic,
                    row,
                    activity={}
                )
                item = {
                    **row,
                    "compatibility": result,
                    "historical_media": True
                }
                if result.get("compatible"):
                    accepted.append(item)
                else:
                    excluded.append(item)

        if interpreted.get("primary_topic") in self._reusable_topics():
            for term in topic_terms[:8]:
                for row in self._stored_media_rows(term, limit=30):
                    result = self.compatibility.evaluate(
                        compatibility_topic,
                        row,
                        activity={}
                    )
                    item = {
                        **row,
                        "compatibility": result,
                        "stored_media_search": True
                    }
                    if result.get("compatible"):
                        accepted.append(item)
                    else:
                        excluded.append(item)

        accepted = self._dedupe_media(accepted)
        excluded = self._dedupe_media(excluded)
        accepted.sort(
            key=lambda item: (
                1 if item.get("trust_state") == "corrected_real" else 0,
                1 if item.get("trust_state") == "approved_real" else 0,
                item.get("compatibility", {}).get("score", 0),
                int(item.get("communications_score") or 0)
            ),
            reverse=True
        )
        return {
            "accepted": accepted[:limit],
            "excluded": excluded[:10],
            "recoverable_candidates": [
                item for item in excluded
                if not item.get("compatibility", {}).get("hard_reject")
            ][:10],
            "no_suitable_media": not accepted,
            "source": "operational_activity_and_stored_media"
        }

    def _package(
        self,
        prompt,
        interpreted,
        current_context,
        historical,
        around_this_time,
        media,
        option_count=None
    ):
        details = self.TOPIC_DETAILS[interpreted["primary_topic"]]
        accepted = media.get("accepted", [])
        if not accepted:
            return self._blocked_package(
                prompt,
                interpreted,
                current_context,
                historical,
                around_this_time,
                media,
                "No verified media available for this topic."
            )
        primary = accepted[0] if accepted else {}
        alternates = accepted[1:5]
        warnings = self._warnings(
            interpreted,
            current_context,
            media,
            historical
        )
        opportunity = {
            "what": details["label"],
            "why_now": self._why_now(interpreted, current_context),
            "current_context_evidence": self._context_evidence(current_context),
            "historical_mfr_evidence": self._history_evidence(historical),
            "year_over_year_evidence": self._year_over_year_evidence(
                around_this_time
            ),
            "confidence": self._confidence(interpreted, current_context, media, historical)
        }
        facebook = self._facebook_draft(
            interpreted,
            current_context,
            historical,
            media,
            details
        )
        instagram = self._instagram_draft(
            interpreted,
            current_context,
            historical,
            media,
            details
        )
        options = self._build_options(
            prompt,
            interpreted,
            current_context,
            historical,
            around_this_time,
            media,
            details,
            option_count or self.DEFAULT_OPTION_COUNT
        )
        options = self.freshness.apply_to_packages(
            options,
            page="Content Director Search",
            limit=option_count or self.DEFAULT_OPTION_COUNT,
            record=True,
            now=TimeService.utc_now(),
            preserve_order=True
        )
        first_option = options[0] if options else {}
        if not first_option:
            return self._blocked_package(
                prompt,
                interpreted,
                current_context,
                historical,
                around_this_time,
                media,
                "No publishable package passed editorial media integrity."
            )
        if first_option:
            facebook = first_option.get("facebook_draft", facebook)
            instagram = first_option.get("instagram_draft", instagram)
        package = {
            "request_id": self._request_id(prompt),
            "prompt": prompt,
            "option_count_requested": option_count or self.DEFAULT_OPTION_COUNT,
            "option_count_returned": len(options),
            "options": options,
            "option_limit_reason": self._option_limit_reason(
                options,
                option_count or self.DEFAULT_OPTION_COUNT,
                media
            ),
            "interpreted_topic": interpreted,
            "current_context": current_context,
            "opportunity_summary": opportunity,
            "facebook_draft": facebook,
            "instagram_draft": instagram,
            "facebook_caption": facebook["copy_text"],
            "instagram_caption": instagram["copy_text"],
            "media_package": first_option.get("media_package") or {
                "primary_image": primary if primary.get("media_type") == "image" else {},
                "primary_video": primary if primary.get("media_type") == "video" else {},
                "alternates": alternates,
                "carousel_order": accepted[:5],
                "reel_options": [
                    item
                    for item in accepted
                    if item.get("media_type") == "video"
                ][:3],
                "no_suitable_media": media.get("no_suitable_media"),
                "compatibility_evidence": [
                    {
                        "filename": item.get("filename", ""),
                        "trust_state": item.get("trust_state", ""),
                        "capture_time": item.get("capture_time", ""),
                        "historical_media": bool(item.get("historical_media")),
                        "reasons": item.get("compatibility", {}).get("reasons", [])
                    }
                    for item in accepted[:5]
                ],
                "excluded_conflicts": [
                    {
                        "filename": item.get("filename", ""),
                        "activity": item.get("activity_title", ""),
                        "hard_reject": item.get("compatibility", {}).get("hard_reject", False),
                        "exclusions": item.get("compatibility", {}).get("exclusions", [])
                    }
                    for item in media.get("excluded", [])[:8]
                ]
            },
            "historical_references": historical,
            "around_this_time": around_this_time,
            "validation_warnings": warnings,
            "trust_explanation": self._trust_explanation(accepted),
            "search_diagnostics": self._search_diagnostics(
                interpreted,
                media,
                story_family=first_option.get("strategy_family", ""),
                teaching_point=first_option.get("teaching_point", ""),
                package_status=first_option.get("package_status", "ready")
            ),
            "package_status": first_option.get("package_status", "ready"),
            "search_result_status": first_option.get(
                "search_result_status",
                "Publish Ready"
            ),
            "package_state": first_option.get(
                "package_state",
                "Publish Ready"
            ),
            "recommendation_fingerprint": first_option.get(
                "recommendation_fingerprint",
                ""
            ),
            "freshness": first_option.get("freshness", {}),
            "freshness_penalty": first_option.get("freshness_penalty", 0),
            "quality_gate": first_option.get("quality_gate", {}),
            "progressive_sections": [
                "interpreted_topic",
                "historical_references",
                "media_package",
                "generated_package"
            ],
            "source_signals": [
                "Communications Memory",
                "Year-over-year Communications Memory",
                "Operational Activity Intelligence",
                "Media-topic compatibility gate",
                "Effective Intelligence",
                "Current Context"
            ],
            "benchmark_inspiration": [],
            "generation_version": self.QUERY_VERSION,
            "generated_at": TimeService.utc_now_iso()
        }
        return package

    def _blocked_package(
        self,
        prompt,
        interpreted,
        current_context,
        historical,
        around_this_time,
        media,
        reason
    ):

        diagnostics = self._search_diagnostics(
            interpreted,
            media,
            story_family="",
            teaching_point="",
            package_status="blocked_no_verified_media"
        )
        search_status = diagnostics.get("search_result_status", "Needs Media")
        blocked_copy = {
            "platform": "",
            "copy_text": reason,
            "hashtags": [],
            "quality": {
                "passed": False,
                "blocking_issues": [reason],
                "failure_reasons": [reason]
            },
            "scroll_stop_score": {
                "total_score": 0,
                "strongest_factor": "",
                "weakest_factor": "verified media",
                "suggested_improvement": "Select verified media from the matching event before generating copy."
            }
        }
        warnings = self._warnings(
            interpreted,
            current_context,
            media,
            historical
        )
        warnings.insert(0, reason)
        year_over_year = self._year_over_year_evidence(around_this_time)
        return {
            "request_id": self._request_id(prompt),
            "prompt": prompt,
            "option_count_requested": self.DEFAULT_OPTION_COUNT,
            "option_count_returned": 0,
            "options": [],
            "option_limit_reason": reason,
            "interpreted_topic": interpreted,
            "current_context": current_context,
            "opportunity_summary": {
                "what": interpreted.get("label", ""),
                "why_now": self._why_now(interpreted, current_context),
                "year_over_year_evidence": year_over_year,
                "confidence": 0
            },
            "facebook_draft": blocked_copy,
            "instagram_draft": blocked_copy,
            "facebook_caption": reason,
            "instagram_caption": reason,
            "media_package": {
                "primary_image": {},
                "primary_video": {},
                "alternates": [],
                "carousel_order": [],
                "reel_options": [],
                "no_suitable_media": True,
                "verified_media_ids": [],
                "excluded_conflicts": diagnostics["rejected_media"]
            },
            "historical_references": historical,
            "around_this_time": around_this_time,
            "validation_warnings": self._unique(warnings),
            "trust_explanation": reason,
            "progressive_sections": [
                "interpreted_topic",
                "search_diagnostics"
            ],
            "source_signals": [
                "Media-topic compatibility gate",
                "Editorial media integrity gate",
                "Year-over-year Communications Memory"
            ],
            "search_diagnostics": diagnostics,
            "search_result_status": search_status,
            "user_guidance": diagnostics.get("user_guidance", reason),
            "year_over_year_evidence": year_over_year,
            "package_status": "blocked_no_verified_media",
            "package_state": (
                "Blocked"
                if search_status == "Blocked for Privacy or Safety"
                else "Needs Media"
            ),
            "quality_gate": {
                "passed": False,
                "blocking_issues": [reason],
                "checks": {
                    "verified_media": False,
                    "caption_quality": False
                }
            },
            "benchmark_inspiration": [],
            "generation_version": self.QUERY_VERSION,
            "generated_at": TimeService.utc_now_iso()
        }

    def _search_diagnostics(
        self,
        interpreted,
        media,
        story_family="",
        teaching_point="",
        package_status=""
    ):

        accepted = list(media.get("accepted") or [])
        rejected = list(media.get("excluded") or [])
        recoverable = list(media.get("recoverable_candidates") or [])
        status = self._search_result_status(
            interpreted,
            accepted,
            rejected,
            recoverable,
            package_status
        )
        return {
            "search_result_status": status,
            "user_guidance": self._search_user_guidance(
                interpreted,
                status,
                recoverable
            ),
            "matched_events": self._unique([
                item.get("activity_title")
                or item.get("event_title")
                or (item.get("filesystem_intelligence") or {}).get("community_event")
                or (item.get("filesystem_intelligence") or {}).get("campaign")
                or (item.get("filesystem_intelligence") or {}).get("public_education_program")
                for item in accepted
            ]),
            "matched_media": [
                {
                    "media_id": item.get("media_id") or item.get("id"),
                    "filename": item.get("filename", ""),
                    "media_type": item.get("media_type", ""),
                    "trust_state": item.get("trust_state", ""),
                    "reasons": item.get("compatibility", {}).get("reasons", [])
                }
                for item in accepted[:10]
            ],
            "rejected_media": [
                {
                    "media_id": item.get("media_id") or item.get("id"),
                    "filename": item.get("filename", ""),
                    "media_type": item.get("media_type", ""),
                    "reason": (
                        item.get("reason")
                        or "; ".join(item.get("exclusions") or [])
                        or "; ".join(item.get("compatibility", {}).get("exclusions", []))
                        or "Media did not pass topic compatibility."
                    )
                }
                for item in rejected[:20]
            ],
            "recoverable_media": [
                {
                    "media_id": item.get("media_id") or item.get("id"),
                    "filename": item.get("filename", ""),
                    "media_type": item.get("media_type", ""),
                    "source_type": self._media_source_type(item),
                    "trust_state": item.get("trust_state", ""),
                    "current_tags": self._diagnostic_tags(item),
                    "compatibility_score": item.get("compatibility", {}).get("score", 0),
                    "compatibility_reason": "; ".join(
                        item.get("compatibility", {}).get("reasons", [])
                    ),
                    "uncertainty_reason": "; ".join(
                        item.get("compatibility", {}).get("exclusions", [])
                    ) or "Candidate needs human media review before use."
                }
                for item in recoverable[:10]
            ],
            "story_family": story_family,
            "teaching_point": teaching_point,
            "package_status": package_status,
            "topic": interpreted.get("primary_topic", ""),
            "label": interpreted.get("label", "")
        }

    def _historical_media_rows(self, term, limit=30):
        try:
            rows = self.db.search_intelligence(term, limit=limit)
        except Exception:
            return []

        result = []
        for row in rows:
            media_id = row.get("media_id") or row.get("id")
            if not media_id:
                continue
            try:
                assets = self.db.communications_officer_assets(
                    [media_id],
                    limit=1
                )
            except Exception:
                assets = []
            if assets:
                result.append(assets[0])
        return result

    def _search_result_status(
        self,
        interpreted,
        accepted,
        rejected,
        recoverable,
        package_status
    ):

        topic = interpreted.get("primary_topic", "")
        if accepted and not str(package_status or "").startswith("blocked"):
            return "Publish Ready"
        if recoverable:
            return "Needs Media Review"
        if topic == "serious_incident":
            if rejected:
                return "Blocked for Privacy or Safety"
            return "No Matching Event"
        if topic in self._reusable_topics():
            return "Needs Media"
        if rejected:
            return "No Relevant Content"
        return "No Matching Event"

    def _search_user_guidance(self, interpreted, status, recoverable):

        label = interpreted.get("label", "Search")
        topic = interpreted.get("primary_topic", "")
        if status == "Publish Ready":
            return f"{label} has verified compatible media and can be reviewed as a publish-ready package."
        if status == "Needs Media Review":
            return (
                f"{label} has possible media candidates, but they need human review "
                "before they can support a public package."
            )
        if topic == "serious_incident":
            return (
                "No public-safe, verified serious-incident event with compatible "
                "media was found. Avoid publishing incident details without confirmed "
                "public information and approved media."
            )
        if topic == "smoke_alarm":
            return (
                "No verified smoke-alarm media was found. Review candidate media, "
                "import a smoke-alarm photo or graphic, or mark an approved reusable "
                "campaign asset before generating a publish-ready package."
            )
        return (
            f"No verified compatible media was found for {label}. Review candidates "
            "or add stronger topic/campaign metadata before publishing."
        )

    def _media_source_type(self, item):

        if item.get("filesystem_media"):
            return "filesystem intelligence"
        if item.get("historical_media"):
            return "stored media intelligence"
        if item.get("stored_media_search"):
            return "stored media search"
        fs = item.get("filesystem_intelligence") or {}
        if fs.get("campaign") or fs.get("public_education_program"):
            return "campaign or education asset"
        return item.get("media_type", "media")

    def _diagnostic_tags(self, item):

        tags = []
        for key in (
            "content_tags",
            "content_themes",
            "recommended_uses",
            "communications_uses"
        ):
            tags.extend(self._flatten(item.get(key)))
        fs = item.get("filesystem_intelligence") or {}
        for key in (
            "normalized_tags",
            "campaign",
            "public_education_program",
            "community_event"
        ):
            tags.extend(self._flatten(fs.get(key)))
        return self._unique(str(tag) for tag in tags if tag)[:10]

    def _filesystem_media_rows(self, term, limit=30):
        term = str(term or "").strip()
        if not term:
            return []

        normalized = term.replace("_", " ")
        patterns = self._unique([
            term,
            normalized,
            normalized.replace(" ", "_")
        ])

        try:
            conn = self.db.connection()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            clauses = []
            params = []
            for pattern in patterns:
                like = f"%{pattern}%"
                clauses.append(
                    """
                    filesystem_intelligence.relative_path LIKE ?
                    OR filesystem_intelligence.folder_hierarchy LIKE ?
                    OR filesystem_intelligence.root_category LIKE ?
                    OR filesystem_intelligence.subcategory LIKE ?
                    OR filesystem_intelligence.normalized_tags LIKE ?
                    OR filesystem_intelligence.public_education_program LIKE ?
                    OR filesystem_intelligence.campaign LIKE ?
                    OR filesystem_intelligence.community_event LIKE ?
                    OR filesystem_intelligence.training_type LIKE ?
                    OR filesystem_intelligence.source_folders LIKE ?
                    """
                )
                params.extend([like] * 10)

            cur.execute(f"""
            SELECT media.id AS media_id
                , media.filename
                , media.path
                , media.media_type
                , filesystem_intelligence.relative_path
                , filesystem_intelligence.folder_hierarchy
                , filesystem_intelligence.root_category
                , filesystem_intelligence.subcategory
                , filesystem_intelligence.normalized_tags
                , filesystem_intelligence.apparatus_identifier
                , filesystem_intelligence.apparatus_name
                , filesystem_intelligence.incident_type
                , filesystem_intelligence.training_type
                , filesystem_intelligence.public_education_program
                , filesystem_intelligence.campaign
                , filesystem_intelligence.community_event
                , filesystem_intelligence.location_context
                , filesystem_intelligence.source_folders
                , filesystem_intelligence.filesystem_confidence
                , filesystem_intelligence.conflict_state
                , ai_analysis.trust_state
                , ai_analysis.review_status
                , ai_analysis.failure_reason
                , ai_analysis.provider
            FROM filesystem_intelligence
            JOIN media
            ON media.id=filesystem_intelligence.media_id
            LEFT JOIN ai_analysis
            ON ai_analysis.media_id=media.id
            WHERE ({' OR '.join('(' + clause + ')' for clause in clauses)})
            AND (
                ai_analysis.trust_state IS NULL
                OR ai_analysis.trust_state NOT IN ('rejected_real', 'failed', 'mock')
            )
            ORDER BY
                filesystem_intelligence.filesystem_confidence DESC,
                media.id DESC
            LIMIT ?
            """, tuple(params + [limit]))
            rows = cur.fetchall()
            ids = [
                row["media_id"]
                for row in rows
            ]
            conn.close()
        except Exception:
            return []

        if not ids:
            return []

        try:
            assets = self.db.communications_officer_assets(ids, limit=len(ids))
        except Exception:
            assets = []

        by_id = {
            item.get("media_id"): item
            for item in assets
        }
        results = []

        for row in rows:
            media_id = row["media_id"]
            asset = by_id.get(media_id)
            if asset:
                fs = asset.setdefault("filesystem_intelligence", {})
                fs["relative_path"] = row["relative_path"] or ""
                fs["folder_hierarchy"] = self._from_json(row["folder_hierarchy"])
                fs["source_folders"] = self._from_json(row["source_folders"])
                results.append(asset)
                continue

            results.append({
                "media_id": media_id,
                "filename": row["filename"] or "",
                "path": row["path"] or "",
                "media_type": row["media_type"] or "",
                "trust_state": row["trust_state"] or "unreviewed_real",
                "review_status": row["review_status"] or "review_required",
                "failure_reason": row["failure_reason"] or "",
                "provider": row["provider"] or "",
                "description": "",
                "effective_description": "",
                "normalized_scene": "",
                "incident_type": "",
                "primary_activity": "",
                "content_tags": [],
                "content_themes": [],
                "recommended_uses": [],
                "search_text": row["relative_path"] or "",
                "communications_score": 0,
                "filesystem_intelligence": {
                    "relative_path": row["relative_path"] or "",
                    "folder_hierarchy": self._from_json(row["folder_hierarchy"]),
                    "root_category": row["root_category"] or "",
                    "subcategory": row["subcategory"] or "",
                    "normalized_tags": self._from_json(row["normalized_tags"]),
                    "apparatus_identifier": row["apparatus_identifier"] or "",
                    "apparatus_name": row["apparatus_name"] or "",
                    "incident_type": row["incident_type"] or "",
                    "training_type": row["training_type"] or "",
                    "public_education_program": row["public_education_program"] or "",
                    "campaign": row["campaign"] or "",
                    "community_event": row["community_event"] or "",
                    "location_context": row["location_context"] or "",
                    "source_folders": self._from_json(row["source_folders"]),
                    "filesystem_confidence": row["filesystem_confidence"] or 0,
                    "conflict_state": row["conflict_state"] or ""
                }
            })

        return results

    def _stored_media_rows(self, term, limit=30):

        term = str(term or "").strip()
        if not term:
            return []

        normalized = term.replace("_", " ")
        like = f"%{normalized}%"
        compact_like = f"%{normalized.replace(' ', '_')}%"
        try:
            limit_value = max(1, min(100, int(limit or 30)))
        except (TypeError, ValueError):
            limit_value = 30
        try:
            conn = self.db.connection()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
            SELECT DISTINCT media.id AS media_id
            FROM media
            LEFT JOIN ai_analysis
            ON ai_analysis.media_id=media.id
            LEFT JOIN media_intelligence
            ON media_intelligence.media_id=media.id
            LEFT JOIN fire_service_intelligence
            ON fire_service_intelligence.media_id=media.id
            LEFT JOIN filesystem_intelligence
            ON filesystem_intelligence.media_id=media.id
            WHERE (
                media.filename LIKE ?
                OR media.path LIKE ?
                OR ai_analysis.description LIKE ?
                OR ai_analysis.visible_text LIKE ?
                OR media_intelligence.search_text LIKE ?
                OR media_intelligence.content_tags LIKE ?
                OR media_intelligence.recommended_uses LIKE ?
                OR fire_service_intelligence.communications_uses LIKE ?
                OR fire_service_intelligence.reasoning_evidence LIKE ?
                OR filesystem_intelligence.relative_path LIKE ?
                OR filesystem_intelligence.normalized_tags LIKE ?
                OR filesystem_intelligence.campaign LIKE ?
                OR filesystem_intelligence.public_education_program LIKE ?
                OR media.filename LIKE ?
                OR media.path LIKE ?
            )
            AND (
                ai_analysis.trust_state IS NULL
                OR ai_analysis.trust_state NOT IN ('rejected_real', 'failed', 'mock')
            )
            ORDER BY media.id DESC
            LIMIT ?
            """, tuple([like] * 13 + [compact_like, compact_like, limit_value]))
            ids = [
                row["media_id"]
                for row in cur.fetchall()
                if row["media_id"]
            ]
            conn.close()
        except Exception:
            return []

        if not ids:
            return []
        try:
            return self.db.communications_officer_assets(
                ids,
                limit=len(ids)
            )
        except Exception:
            return []

    def _reusable_topics(self):

        return {
            "smoke_alarm",
            "recruitment",
            "fireworks",
            "water_safety",
            "fire_prevention_week",
            "heat_warning",
            "smoke_advisory",
            "hydrant_heroes"
        }

    ############################################################

    def _build_options(
        self,
        prompt,
        interpreted,
        current_context,
        historical,
        around_this_time,
        media,
        details,
        option_count
    ):

        strategies = self._strategy_blueprints(interpreted)
        accepted = list(media.get("accepted") or [])
        options = []
        attempts = 0

        for strategy in strategies:
            if len(options) >= option_count:
                break
            attempts += 1
            if attempts > self.MAX_OPTION_COUNT * 2:
                break

            option_media = self._option_media_package(
                media,
                strategy,
                len(options),
                accepted
            )
            if option_media.get("no_suitable_media"):
                continue
            references = self._option_historical_references(
                historical,
                around_this_time,
                len(options)
            )
            option = self._option(
                prompt,
                interpreted,
                current_context,
                references,
                around_this_time,
                option_media,
                details,
                strategy,
                len(options) + 1
            )

            score = self._diversity_score(option, options)
            option["diversity_score"] = score
            if option.get("state") != "ready":
                continue
            if score < 45:
                continue
            options.append(option)

        if len(options) < option_count:
            for strategy in self._fallback_text_strategies(interpreted):
                if len(options) >= option_count:
                    break
                option_media = self._option_media_package(
                    media,
                    strategy,
                    len(options),
                    accepted
                )
                if option_media.get("no_suitable_media"):
                    continue
                references = self._option_historical_references(
                    historical,
                    around_this_time,
                    len(options)
                )
                option = self._option(
                    prompt,
                    interpreted,
                    current_context,
                    references,
                    around_this_time,
                    option_media,
                    details,
                    strategy,
                    len(options) + 1
                )
                score = self._diversity_score(option, options)
                option["diversity_score"] = score
                if option.get("state") != "ready":
                    continue
                if score >= 45:
                    options.append(option)

        return options[:self.MAX_OPTION_COUNT]

    def _strategy_blueprints(self, interpreted):

        topic = interpreted.get("primary_topic", "")
        common = [
            {
                "family": "direct_safety_reminder",
                "title": "Direct Safety Reminder",
                "angle": "Give residents a clear, timely safety action.",
                "format": "single-image post",
                "platform": "Facebook",
                "audience": ["Morden residents", "families"],
                "cta": interpreted.get("communication_type", "public safety reminder")
            },
            {
                "family": "historical_campaign_refresh",
                "title": "Historical Campaign Refresh",
                "angle": "Refresh a proven MFR seasonal message using current wording.",
                "format": "carousel",
                "platform": "Facebook",
                "audience": ["returning followers", "community members"],
                "cta": "Review the reminder and share it with someone who may need it."
            },
            {
                "family": "educational_explainer",
                "title": "Educational Explainer",
                "angle": "Explain the why behind the safety action in plain language.",
                "format": "text/graphic-first post",
                "platform": "Instagram",
                "audience": ["families", "new residents"],
                "cta": "Save the checklist and talk it through at home."
            },
            {
                "family": "community_story",
                "title": "Community-Oriented Story",
                "angle": "Connect the topic to looking out for neighbours.",
                "format": "single-image post",
                "platform": "Facebook",
                "audience": ["Morden community"],
                "cta": "Check in with someone nearby."
            },
            {
                "family": "reel_video",
                "title": "Short Video/Reel",
                "angle": "Use motion or a quick sequence when suitable video exists.",
                "format": "Reel/video",
                "platform": "Instagram",
                "audience": ["visual-first followers"],
                "cta": "Share the reminder."
            }
        ]

        topic_specific = {
            "water_safety": [
                {
                    "family": "direct_safety_reminder",
                    "title": "Water Safety Reminder",
                    "angle": "Focus on immediate water-safety actions before people head outside.",
                    "format": "single-image post",
                    "platform": "Facebook",
                    "audience": ["families", "lake users"],
                    "cta": "Wear a life jacket and supervise children closely."
                },
                {
                    "family": "historical_campaign_refresh",
                    "title": "Water Safety Wednesday Refresh",
                    "angle": "Build on MFR's prior Water Safety Wednesday rhythm.",
                    "format": "carousel",
                    "platform": "Instagram",
                    "audience": ["followers familiar with MFR safety campaigns"],
                    "cta": "Save and share the reminder before heading near the water."
                },
                {
                    "family": "educational_explainer",
                    "title": "Water Rescue Education",
                    "angle": "Explain safe choices around rescue, life jackets, and supervision.",
                    "format": "text/graphic-first post",
                    "platform": "Facebook",
                    "audience": ["parents", "caregivers", "boaters"],
                    "cta": "Call 911 if someone is in trouble on or near the water."
                }
            ],
            "recruitment": [
                {
                    "family": "recruitment_appeal",
                    "title": "Volunteer Recruitment Appeal",
                    "angle": "Invite residents to consider joining MFR.",
                    "format": "single-image post",
                    "platform": "Facebook",
                    "audience": ["potential volunteers"],
                    "cta": "Reach out to learn how to serve."
                },
                {
                    "family": "training_story",
                    "title": "Training and Skills Story",
                    "angle": "Show that training builds confidence, teamwork, and service.",
                    "format": "carousel",
                    "platform": "Instagram",
                    "audience": ["curious applicants"],
                    "cta": "Ask what training with MFR looks like."
                },
                {
                    "family": "community_service_story",
                    "title": "Community Service Impact",
                    "angle": "Frame volunteering as a practical way to help neighbours.",
                    "format": "single-image post",
                    "platform": "Facebook",
                    "audience": ["community-minded residents"],
                    "cta": "Share with someone who would make a strong volunteer firefighter."
                }
            ],
            "smoke_advisory": [
                {
                    "family": "urgent_safety_advisory",
                    "title": "Smoke Conditions Advisory",
                    "angle": "Use only if current official context confirms an advisory.",
                    "format": "text/graphic-first post",
                    "platform": "Facebook",
                    "audience": ["residents affected by smoke"],
                    "cta": "Check current official conditions before changing outdoor plans."
                },
                {
                    "family": "general_safety_reminder",
                    "title": "Wildfire Smoke Safety Reminder",
                    "angle": "Give evergreen smoke-safety guidance without claiming a current advisory.",
                    "format": "single-image post",
                    "platform": "Facebook",
                    "audience": ["families", "outdoor workers", "seniors"],
                    "cta": "Limit exposure and follow official local updates."
                },
                {
                    "family": "checklist",
                    "title": "Air Quality Checklist",
                    "angle": "Turn prior MFR wording into a simple checklist.",
                    "format": "text/graphic-first post",
                    "platform": "Instagram",
                    "audience": ["visual-first followers"],
                    "cta": "Save the checklist for smoky days."
                }
            ],
            "smoke_alarm": [
                {
                    "family": "checklist",
                    "title": "Smoke Alarm Checklist",
                    "angle": "Make the household action quick and specific.",
                    "format": "text/graphic-first post",
                    "platform": "Facebook",
                    "audience": ["households"],
                    "cta": "Test alarms and review two ways out."
                },
                {
                    "family": "historical_campaign_refresh",
                    "title": "Fire Prevention Reminder",
                    "angle": "Refresh previous fire-prevention messaging with current wording.",
                    "format": "carousel",
                    "platform": "Instagram",
                    "audience": ["families", "homeowners"],
                    "cta": "Replace expired alarms and talk about the escape plan."
                },
                {
                    "family": "educational_explainer",
                    "title": "Test and Replace Explainer",
                    "angle": "Explain why working alarms buy time to escape.",
                    "format": "single-image post",
                    "platform": "Facebook",
                    "audience": ["new homeowners", "renters"],
                    "cta": "Check the date on every smoke alarm."
                }
            ],
            "fire_prevention_week": [
                {
                    "family": "historical_campaign_refresh",
                    "title": "Fire Prevention Week Campaign Refresh",
                    "angle": "Use MFR's prior fire-prevention rhythm with current wording.",
                    "format": "carousel",
                    "platform": "Facebook",
                    "audience": ["families", "homeowners", "renters"],
                    "cta": "Test alarms and review your home escape plan."
                },
                {
                    "family": "educational_explainer",
                    "title": "Home Fire Safety Explainer",
                    "angle": "Explain one practical home fire-prevention action clearly.",
                    "format": "text/graphic-first post",
                    "platform": "Instagram",
                    "audience": ["households"],
                    "cta": "Pick one safety improvement to complete this week."
                },
                {
                    "family": "checklist",
                    "title": "Fire Prevention Checklist",
                    "angle": "Give residents a short checklist they can act on today.",
                    "format": "text/graphic-first post",
                    "platform": "Facebook",
                    "audience": ["Morden residents"],
                    "cta": "Walk through the checklist with everyone at home."
                }
            ],
            "historical_apparatus": [
                {
                    "family": "apparatus_history",
                    "title": "Apparatus History Feature",
                    "angle": "Show how department tools and apparatus have changed over time.",
                    "format": "carousel",
                    "platform": "Facebook",
                    "audience": ["MFR followers", "community history followers"],
                    "cta": "Share a memory or question about MFR apparatus history."
                },
                {
                    "family": "behind_the_scenes",
                    "title": "Then and Now Equipment Story",
                    "angle": "Connect a verified apparatus detail to the work it supports.",
                    "format": "single-image post",
                    "platform": "Instagram",
                    "audience": ["visual-first followers"],
                    "cta": "Look for the details that show how the fire service has evolved."
                },
                {
                    "family": "community_story",
                    "title": "MFR History Moment",
                    "angle": "Frame the apparatus as part of local fire-service history.",
                    "format": "single-image post",
                    "platform": "Facebook",
                    "audience": ["Morden community"],
                    "cta": "Follow along for more MFR history moments."
                }
            ],
            "serious_incident": [
                {
                    "family": "incident_information",
                    "title": "Confirmed Incident Information",
                    "angle": "Share only confirmed details and practical public context.",
                    "format": "single-image post",
                    "platform": "Facebook",
                    "audience": ["Morden residents", "affected community members"],
                    "cta": "Use official updates and call 911 for emergencies."
                },
                {
                    "family": "incident_follow_up",
                    "title": "Incident Follow-Up",
                    "angle": "Explain the public-safety context after the immediate response.",
                    "format": "single-image post",
                    "platform": "Facebook",
                    "audience": ["community members"],
                    "cta": "Avoid speculation and rely on confirmed information."
                },
                {
                    "family": "community_update",
                    "title": "Community Update",
                    "angle": "Keep the public informed without adding unverified incident facts.",
                    "format": "text/graphic-first post",
                    "platform": "Instagram",
                    "audience": ["Morden followers"],
                    "cta": "Watch for official updates when more information is available."
                }
            ]
        }

        return (topic_specific.get(topic) or common) + common

    def _fallback_text_strategies(self, interpreted):

        return [
            {
                "family": "text_graphic_first",
                "title": "Text/Graphic-First Reminder",
                "angle": "Use clear copy when no suitable media passes compatibility.",
                "format": "text/graphic-first post",
                "platform": "Facebook",
                "audience": ["Morden residents"],
                "cta": "Share the reminder with someone who may need it."
            },
            {
                "family": "myth_versus_fact",
                "title": "Myth Versus Fact",
                "angle": "Correct a common misconception with a short educational format.",
                "format": "myth-versus-fact",
                "platform": "Instagram",
                "audience": ["families", "younger followers"],
                "cta": "Save this for later."
            }
        ]

    def _option(
        self,
        prompt,
        interpreted,
        current_context,
        historical,
        around_this_time,
        media_package,
        details,
        strategy,
        index
    ):

        writing = self._option_writing(
            interpreted,
            current_context,
            historical,
            media_package,
            details,
            strategy
        )
        facebook = writing["facebook_draft"]
        instagram = writing["instagram_draft"]
        warnings = self._warnings(
            interpreted,
            current_context,
            media_package,
            historical
        )
        if media_package.get("no_suitable_media"):
            warnings.append(
                "No verified media available for this topic."
            )

        option_id = f"{self._normalize(interpreted.get('primary_topic'))}_{index}"
        reference_ids = [
            item.get("source_record_id") or item.get("communication_id")
            for item in historical[:3]
            if item.get("source_record_id") or item.get("communication_id")
        ]
        primary = (
            media_package.get("primary_image")
            or media_package.get("primary_video")
            or {}
        )
        confidence = self._confidence(
            interpreted,
            current_context,
            media_package,
            historical
        )
        if strategy.get("family") in ("historical_campaign_refresh", "checklist"):
            confidence += 5 if historical or around_this_time.get("matches") else -5
        if media_package.get("no_suitable_media"):
            confidence -= 8
        quality = writing.get("quality", {}) or {}
        ready = bool(
            not media_package.get("no_suitable_media")
            and media_package.get("verified_media_ids")
            and quality.get("passed")
        )

        return {
            "option_id": option_id,
            "title": strategy.get("title", ""),
            "strategic_angle": strategy.get("angle", ""),
            "strategy_family": strategy.get("family", ""),
            "why_relevant_now": self._why_now(interpreted, current_context),
            "target_audience": strategy.get("audience", []),
            "recommended_platform": strategy.get("platform", "Facebook"),
            "recommended_format": strategy.get("format", "single-image post"),
            "facebook_draft": facebook,
            "instagram_draft": instagram,
            "facebook_caption": facebook.get("copy_text", ""),
            "instagram_caption": instagram.get("copy_text", ""),
            "selected_formula": writing.get("selected_formula", ""),
            "communication_objective": writing.get("communication_objective", ""),
            "secondary_objective": writing.get("secondary_objective", ""),
            "narrative_angle": writing.get("narrative_angle", {}),
            "narrative_focus": writing.get("narrative_focus", ""),
            "selected_teaching_point": writing.get("selected_teaching_point", ""),
            "teaching_point": writing.get("selected_teaching_point", ""),
            "hook_type": writing.get("hook_type", ""),
            "recommended_tone": writing.get("recommended_tone", ""),
            "scroll_stop_score": writing.get("scroll_stop_score", {}),
            "caption_quality": writing.get("quality", {}),
            "caption_variants": writing.get("variants", []),
            "hashtags": self._merge_hashtags(
                list(facebook.get("hashtags", [])) +
                list(instagram.get("hashtags", []))
            ),
            "media_package": media_package,
            "package_status": "ready" if ready else "blocked",
            "search_result_status": (
                "Publish Ready"
                if ready
                else (
                    "Needs Media"
                    if media_package.get("no_suitable_media")
                    else "Needs Review"
                )
            ),
            "package_state": (
                "Publish Ready"
                if ready
                else (
                    "Needs Media"
                    if media_package.get("no_suitable_media")
                    else "Needs Review"
                )
            ),
            "quality_gate": {
                "passed": ready,
                "checks": {
                    "verified_media": bool(media_package.get("verified_media_ids")),
                    "caption_quality": bool(quality.get("passed")),
                    "topic_media_alignment": not media_package.get("no_suitable_media")
                },
                "blocking_issues": (
                    ([] if media_package.get("verified_media_ids") else ["No verified media available for this topic."])
                    + list(quality.get("blocking_issues") or [])
                )
            },
            "search_diagnostics": self._search_diagnostics(
                interpreted,
                {
                    "accepted": media_package.get("carousel_order") or [],
                    "excluded": media_package.get("excluded_conflicts") or []
                },
                story_family=writing.get("story_family", ""),
                teaching_point=writing.get("selected_teaching_point", ""),
                package_status="ready" if ready else "blocked"
            ),
            "historical_references": historical[:3],
            "historical_reference_ids": reference_ids,
            "year_over_year_evidence": self._year_over_year_evidence(
                around_this_time
            ),
            "around_this_time": around_this_time,
            "current_context_evidence": self._context_evidence(current_context),
            "repetition_risk": around_this_time.get(
                "communications_gap_risk",
                "unknown"
            ),
            "confidence": max(0, min(100, confidence)),
            "validation_warnings": self._unique(warnings),
            "explainability_evidence": self._option_evidence(
                strategy,
                media_package,
                historical,
                around_this_time
            ),
            "primary_media_id": primary.get("media_id"),
            "publication_draft": self._publication_draft(
                prompt,
                option_id,
                strategy,
                media_package,
                facebook,
                instagram,
                historical,
                confidence
            ),
            "state": "ready" if ready else "blocked"
        }

    def _option_media_package(self, media, strategy, index, accepted):

        selected = []
        family = strategy.get("family", "")
        wants_video = "video" in strategy.get("format", "").lower()
        if wants_video:
            selected = [
                item
                for item in accepted
                if item.get("media_type") == "video"
            ][:3]
        if not selected and accepted and family not in (
            "text_graphic_first",
            "myth_versus_fact"
        ):
            start = index if index < len(accepted) else 0
            selected = accepted[start:start + 4] or accepted[:1]

        primary = selected[0] if selected else {}
        verified_ids = [
            item.get("media_id") or item.get("id")
            for item in selected
            if item.get("media_id") or item.get("id")
        ]
        return {
            "primary_image": primary if primary.get("media_type") == "image" else {},
            "primary_video": primary if primary.get("media_type") == "video" else {},
            "alternates": selected[1:5],
            "carousel_order": selected[:5],
            "reel_options": [
                item
                for item in selected
                if item.get("media_type") == "video"
            ][:3],
            "no_suitable_media": not bool(selected),
            "verified_media_ids": verified_ids,
            "photo_ids": [
                item.get("media_id") or item.get("id")
                for item in selected
                if item.get("media_type") in ("image", "photo")
            ],
            "video_ids": [
                item.get("media_id") or item.get("id")
                for item in selected
                if item.get("media_type") == "video"
            ],
            "compatibility_evidence": [
                {
                    "filename": item.get("filename", ""),
                    "trust_state": item.get("trust_state", ""),
                    "previously_used": bool(item.get("previously_used")),
                    "reasons": item.get("compatibility", {}).get("reasons", [])
                }
                for item in selected[:5]
            ],
            "excluded_conflicts": [
                {
                    "filename": item.get("filename", ""),
                    "activity": item.get("activity_title", ""),
                    "hard_reject": item.get("compatibility", {}).get("hard_reject", False),
                    "exclusions": item.get("compatibility", {}).get("exclusions", [])
                }
                for item in media.get("excluded", [])[:8]
            ],
            "source": media.get("source", "")
        }

    def _option_historical_references(self, historical, around_this_time, index):

        references = list(historical or [])
        seasonal = [
            {
                "source_record_id": item.get("communication_id"),
                "post_date": item.get("date", ""),
                "caption_excerpt": item.get("caption_excerpt", ""),
                "topic": item.get("topic", ""),
                "campaign": item.get("campaign", ""),
                "similarity_score": item.get("similarity_score", 0),
                "evidence": item.get("seasonal_timing_evidence", []),
                "source": "Year-over-year Communications Memory"
            }
            for item in (around_this_time or {}).get("matches", [])
        ]
        combined = self._dedupe_references(
            seasonal[index:index + 2] +
            references[index:index + 2] +
            seasonal +
            references
        )
        return combined[:4]

    def _option_facebook_draft(
        self,
        interpreted,
        current_context,
        historical,
        media,
        details,
        strategy
    ):

        writing = self._option_writing(
            interpreted,
            current_context,
            historical,
            media,
            details,
            strategy
        )
        return writing["facebook_draft"]

    def _option_instagram_draft(
        self,
        interpreted,
        current_context,
        historical,
        media,
        details,
        strategy
    ):

        writing = self._option_writing(
            interpreted,
            current_context,
            historical,
            media,
            details,
            strategy
        )
        return writing["instagram_draft"]

    def _option_writing(
        self,
        interpreted,
        current_context,
        historical,
        media,
        details,
        strategy
    ):

        primary = media.get("primary_image") or media.get("primary_video") or {}
        available = list(media.get("carousel_order") or [])
        if primary and primary not in available:
            available.insert(0, primary)
        known_facts = self._topic_known_facts(
            interpreted,
            media,
            details,
            strategy
        )
        fact_sheet = self.writer.topic_fact_sheet(
            topic=details.get("label") or interpreted.get("label", ""),
            current_relevance=self._why_now(interpreted, current_context),
            historical={
                "matches": historical[:3],
                "last_related_post": (
                    historical[0].get("post_date", "")
                    if historical
                    else ""
                )
            },
            media=available[:6],
            known_facts=known_facts,
            unknown_facts=self._topic_unknown_facts(media),
            platforms=["Facebook", "Instagram"]
        )
        verified_media_ids = [
            item.get("media_id") or item.get("id")
            for item in available[:6]
            if item.get("media_id") or item.get("id")
        ]
        fact_sheet["verified_media"] = available[:6]
        fact_sheet["verified_media_ids"] = verified_media_ids
        fact_sheet["photo_ids"] = [
            item.get("media_id") or item.get("id")
            for item in available[:6]
            if item.get("media_type") in ("image", "photo")
        ]
        fact_sheet["video_ids"] = [
            item.get("media_id") or item.get("id")
            for item in available[:6]
            if item.get("media_type") == "video"
        ]
        fact_sheet["requires_verified_media"] = True
        fact_sheet["package_status"] = (
            "ready_for_writing"
            if verified_media_ids
            else "blocked_no_verified_media"
        )
        fact_sheet["recommended_angle"] = strategy.get("angle", "")
        fact_sheet["story_family"] = self._writer_family(
            interpreted,
            strategy,
            fact_sheet
        )
        fact_sheet["content_type"] = fact_sheet["story_family"]
        if (
            strategy.get("family") in ("training_story", "educational_explainer")
            or interpreted.get("primary_topic") in (
                "water_safety",
                "smoke_alarm",
                "fireworks",
                "hydrant_heroes"
            )
        ):
            fact_sheet["teaching_point"] = self._teaching_point_for_topic(
                interpreted,
                media
            )
        tone = self._tone_for_strategy(strategy)
        copy = self.writer.generate_from_fact_sheet(
            fact_sheet,
            option={
                "title": strategy.get("title", ""),
                "topic": interpreted.get("primary_topic", ""),
                "opportunity_type": interpreted.get("primary_topic", ""),
                "content_family": strategy.get("family", "")
            },
            memory={"matches": historical},
            tone=tone
        )
        copy = self._strategy_specific_writer_copy(
            copy,
            fact_sheet,
            interpreted,
            strategy
        )
        facebook = {
            "platform": "facebook",
            "copy_text": copy.get("facebook", ""),
            "hashtags": copy.get("facebook_hashtags", []),
            "reference_note": self._reference_note(historical),
            "quality": copy.get("quality", {}),
            "scroll_stop_score": copy.get("scroll_stop_score", {})
        }
        instagram = {
            "platform": "instagram",
            "copy_text": copy.get("instagram", ""),
            "hashtags": copy.get("instagram_hashtags", []),
            "quality": copy.get("quality", {}),
            "scroll_stop_score": copy.get("scroll_stop_score", {})
        }
        return {
            "facebook_draft": facebook,
            "instagram_draft": instagram,
            "selected_formula": copy.get("selected_formula", ""),
            "communication_objective": copy.get("communication_objective", ""),
            "secondary_objective": copy.get("secondary_objective", ""),
            "narrative_angle": copy.get("narrative_angle", {}),
            "narrative_focus": copy.get("narrative_focus", ""),
            "selected_teaching_point": copy.get("selected_teaching_point", ""),
            "hook_type": copy.get("hook_type", ""),
            "recommended_tone": copy.get("recommended_tone", ""),
            "scroll_stop_score": copy.get("scroll_stop_score", {}),
            "quality": copy.get("quality", {}),
            "variants": copy.get("variants", []),
            "topic_fact_sheet": fact_sheet
        }

    def _strategy_specific_writer_copy(self, copy, fact_sheet, interpreted, strategy):

        fact_sheet = dict(fact_sheet or {})
        if copy.get("communication_objective"):
            fact_sheet["communication_objective"] = copy.get("communication_objective")
        if copy.get("secondary_objective"):
            fact_sheet["secondary_objective"] = copy.get("secondary_objective")
        if copy.get("narrative_angle"):
            fact_sheet["narrative_angle"] = copy.get("narrative_angle")
        if copy.get("narrative_focus"):
            fact_sheet["narrative_focus"] = copy.get("narrative_focus")
        family = strategy.get("family", "")
        topic = interpreted.get("primary_topic", "")
        if (
            not copy.get("quality", {}).get("passed")
            and copy.get("quality", {}).get("banned_phrases")
        ):
            return copy

        if topic == "water_safety" and family == "direct_safety_reminder":
            facebook = (
                "Water safety starts before anyone is in trouble. \u2705\n\n"
                "The risk is often how quickly a normal outing can change when supervision, distance, weather, or a missing life jacket becomes part of the situation.\n\n"
                "Choose one action before you head out: wear a life jacket, keep children within arm's reach near water, and call 911 if someone is in trouble.\n\n"
                "Supervision and life jackets matter because they give families more time to respond before a problem becomes an emergency.\n\n"
                "#WaterSafety #PublicSafety #SummerSafety #MordenMB"
            )
            instagram = (
                "Water safety starts before anyone is in trouble. \u2705\n\n"
                "Life jackets and close supervision can change the outcome near water.\n\n"
                "#WaterSafety #SummerSafety #CommunityEducation #MordenMB"
            )
        elif topic == "water_safety" and family == "community_story":
            facebook = (
                "Looking out for each other starts before anyone steps near the water. \u2705\n\n"
                "For families, supervision and life jackets matter because water conditions can change faster than people expect.\n\n"
                "Before the outing starts, choose the water watcher, check that life jackets fit, and keep a phone nearby in case help is needed.\n\n"
                "Those simple decisions help keep summer safer around Morden.\n\n"
                "#WaterSafety #FamilySafety #CommunityEducation #MordenMB"
            )
            instagram = (
                "Pick the water watcher before the outing starts. \u2705\n\n"
                "Supervision and life jackets matter around water.\n\n"
                "#WaterSafety #FamilySafety #SummerSafety #MordenMB"
            )
        elif topic == "smoke_alarm" and family == "historical_campaign_refresh":
            facebook = (
                "Fire prevention reminders are worth repeating because the basics save lives. \u2705\n\n"
                "Working smoke alarms give families the early warning they need to get out and call 911.\n\n"
                "Refresh the habit this week with smoke alarm testing and replacement: test alarms, replace expired units, and make sure everyone knows the escape plan.\n\n"
                "A familiar reminder can still make a real difference for Morden families.\n\n"
                "#FirePrevention #SmokeAlarms #HomeSafety #MordenMB"
            )
            instagram = (
                "A familiar reminder for a reason. \u2705\n\n"
                "Test smoke alarms and review the escape plan before you need it.\n\n"
                "#FirePrevention #SmokeAlarms #HomeSafety #MordenMB"
            )
        elif family == "historical_campaign_refresh":
            if topic == "water_safety":
                facebook = (
                    "Water safety is worth repeating before the busiest summer days. \u2705\n\n"
                    "The risk often appears when a normal outing changes quickly: a child gets too far away, a life jacket is skipped, or the weather shifts.\n\n"
                    "Make the decision before you reach the water. Wear a life jacket, keep children close, and call 911 if someone is in trouble.\n\n"
                    "Supervision and life jackets matter because they give families more time to respond.\n\n"
                    "A familiar reminder can still prevent a new emergency.\n\n"
                    "#WaterSafety #PublicSafety #SummerSafety #MordenMB"
                )
                instagram = (
                    "Before the water, make the plan. \u2705\n\n"
                    "Life jackets, close supervision, and quick calls for help matter before anyone is in trouble.\n\n"
                    "#WaterSafety #SummerSafety #CommunityEducation #MordenMB"
                )
            else:
                facebook = (
                    f"{interpreted.get('label', 'This topic')} has come up before because the risk is still real. \u2705\n\n"
                    "Use the current verified event and media facts, not old wording or old dates.\n\n"
                    f"{strategy.get('cta', '')}\n\n"
                    "#PublicSafety #CommunityEducation #MordenMB"
                )
                instagram = (
                    f"{interpreted.get('label', 'Safety')} with a fresh angle. \u2705\n\n"
                    f"{strategy.get('cta', '')}\n\n"
                    "#PublicSafety #MordenMB"
                )
        elif topic == "smoke_alarm" and family == "checklist":
            facebook = (
                "Smoke alarms only help if they are working when you need them. \u2705\n\n"
                "Smoke alarm testing and replacement are the focus: take a few minutes today to test each alarm, check the date, and talk through two ways out of every sleeping area.\n\n"
                "If an alarm is expired or not working, replace it before the reminder gets forgotten.\n\n"
                "Small checks at home can buy precious time for families in Morden.\n\n"
                "#SmokeAlarms #FirePrevention #HomeSafety #MordenMB"
            )
            instagram = (
                "Test. Check the date. Talk through two ways out. \u2705\n\n"
                "Working smoke alarms buy time when every second matters.\n\n"
                "#SmokeAlarms #FirePrevention #HomeSafety #MordenMB"
            )
        elif topic == "smoke_alarm" and family == "educational_explainer":
            facebook = (
                "A working smoke alarm does one critical job: it gives you time. \u2705\n\n"
                "Fire can spread quickly, especially at night when people are sleeping. Early warning helps everyone get moving, follow the escape plan, and call 911 from outside.\n\n"
                "Check the date on each alarm and replace units that are expired or not working.\n\n"
                "For homes in Morden, the best alarm is the one that works before there is smoke in the hallway.\n\n"
                "#SmokeAlarms #FireSafety #HomeSafety #MordenMB"
            )
            instagram = (
                "Smoke alarms buy time. \u2705\n\n"
                "Check the date, test the alarm, and know two ways out.\n\n"
                "#SmokeAlarms #FireSafety #HomeSafety #MordenMB"
            )
        elif family == "educational_explainer" and topic == "water_safety":
            facebook = (
                "Water emergencies can happen quietly and faster than most people expect. \u2705\n\n"
                "Life jackets, close supervision, and knowing when to call 911 are not extra steps. They are the steps that give someone the best chance when a day near the water changes suddenly.\n\n"
                "Before you head out, decide who is watching the water, make sure life jackets fit, and keep a phone close enough to call for help.\n\n"
                "A few calm choices before the outing can prevent panic later.\n\n"
                "#WaterSafety #PublicSafety #FamilySafety #MordenMB"
            )
            instagram = (
                "Water safety is preparation, not panic. \u2705\n\n"
                "Fit the life jacket. Pick the water watcher. Know when to call 911.\n\n"
                "#WaterSafety #FamilySafety #SummerSafety #MordenMB"
            )
        elif topic == "recruitment" and family == "training_story":
            facebook = (
                "A lot of firefighting happens before the emergency call ever comes in. \U0001faa2\n\n"
                "Training builds the confidence, teamwork, and decision-making that volunteers rely on when neighbours need help.\n\n"
                "If you have wondered what joining Morden Fire & Rescue actually involves, training is where many members find their footing.\n\n"
                "Reach out if you want to learn what serving your community could look like.\n\n"
                "#VolunteerFirefighter #FirefighterTraining #CommunityService #MordenMB"
            )
            instagram = (
                "Training is where confidence starts. \U0001faa2\n\n"
                "Volunteer firefighting is teamwork, learning, and service to neighbours.\n\n"
                "#VolunteerFirefighter #FirefighterTraining #JoinMFR #MordenMB"
            )
        elif topic == "recruitment" and family in ("community_service_story", "community_story"):
            facebook = (
                "Some people help their community by coaching, serving on boards, or checking in on neighbours. Others answer the call when emergencies happen. \U0001f91d\n\n"
                "Volunteer firefighting is one practical way to serve Morden with training, teamwork, and purpose.\n\n"
                "You do not need to know everything on day one. You need a willingness to learn and a heart for helping people.\n\n"
                "Share this with someone who would make a strong volunteer firefighter.\n\n"
                "#VolunteerFirefighter #CommunityService #JoinMFR #MordenMB"
            )
            instagram = (
                "Serving Morden can look like this. \U0001f91d\n\n"
                "Training, teamwork, and showing up for neighbours when it matters.\n\n"
                "#VolunteerFirefighter #CommunityService #JoinMFR #MordenMB"
            )
        elif topic == "recruitment" and family == "text_graphic_first":
            facebook = (
                "Thinking about volunteering, but not sure where to start? \U0001f91d\n\n"
                "Start with the basics: ask what training looks like, what time commitment is expected, and how different skills can support the team.\n\n"
                "Morden Fire & Rescue needs people who are willing to learn, work as a team, and serve the community when help is needed.\n\n"
                "Save this as a reminder to ask the first question.\n\n"
                "#VolunteerFirefighter #JoinMFR #CommunityService #MordenMB"
            )
            instagram = (
                "Curious about volunteering? \U0001f91d\n\n"
                "Ask about training, time commitment, and where your skills could fit.\n\n"
                "#VolunteerFirefighter #JoinMFR #CommunityService #MordenMB"
            )
        elif topic == "smoke_advisory" and family == "general_safety_reminder":
            facebook = (
                "Smoky days can change plans quickly, even when there is no emergency at your door. \u2705\n\n"
                "Wildfire smoke can bother children, seniors, outdoor workers, and anyone with heart or lung conditions.\n\n"
                "When the air looks or smells smoky, consider moving strenuous activity indoors, keeping windows closed, and checking official local updates before heading out.\n\n"
                "A simple plan before conditions worsen can make the day safer.\n\n"
                "#AirQuality #PublicSafety #CommunityEducation #MordenMB"
            )
            instagram = (
                "Smoky outside? Check before you head out. \u2705\n\n"
                "Move heavy activity indoors when conditions are poor and follow official local updates.\n\n"
                "#AirQuality #PublicSafety #MordenMB"
            )
        elif topic == "smoke_advisory" and family == "urgent_safety_advisory":
            facebook = (
                "If smoke or poor air quality is affecting Morden, start with the current official alert. \u2705\n\n"
                "Conditions can change quickly, and wildfire smoke may affect children, seniors, outdoor workers, and anyone with heart or lung conditions.\n\n"
                "Use the alert to decide whether to move strenuous activity indoors, reduce exposure, and check on people who may need a cooler or cleaner-air space.\n\n"
                "Confirm the official conditions before publishing this as an active advisory.\n\n"
                "#AirQuality #PublicSafety #CommunityEducation #MordenMB"
            )
            instagram = (
                "Smoke in the air? Check the current official alert first. \u2705\n\n"
                "Reduce exposure when conditions are poor and look out for people at higher risk.\n\n"
                "#AirQuality #PublicSafety #MordenMB"
            )
        elif topic == "smoke_advisory" and family == "checklist":
            facebook = (
                "A smoky day plan does not need to be complicated. \u2705\n\n"
                "Start with three checks: look for current official air-quality information, reduce heavy outdoor activity when conditions are poor, and make a cooler indoor option available for anyone who may be more affected by smoke.\n\n"
                "Children, seniors, outdoor workers, and people with heart or lung conditions may need extra care when the air quality changes.\n\n"
                "Check the conditions before the day gets away from you.\n\n"
                "#AirQuality #PublicSafety #CommunityEducation #MordenMB"
            )
            instagram = (
                "Three checks for smoky days. \u2705\n\n"
                "Check official updates. Reduce heavy outdoor activity. Look out for people at higher risk.\n\n"
                "#AirQuality #PublicSafety #CommunityEducation #MordenMB"
            )
        elif family in ("checklist", "myth_versus_fact"):
            label = interpreted.get("label", "Safety")
            facebook = (
                f"{label} works best when the action is simple. \u2705\n\n"
                f"One thing to do today: {strategy.get('cta', 'choose one practical safety step and complete it.')}.\n\n"
                "Short, specific actions are easier to remember when conditions change.\n\n"
                "#PublicSafety #CommunityEducation #MordenMB"
            )
            instagram = (
                f"One clear step. \u2705\n\n{strategy.get('cta', '')}\n\n"
                "#PublicSafety #CommunityEducation #MordenMB"
            )
        else:
            return copy

        selected_teaching_point = (
            fact_sheet.get("teaching_point")
            or copy.get("selected_teaching_point", "")
        )
        quality = self.writer.quality_gate(
            facebook,
            instagram,
            fact_sheet,
            selected_teaching_point
        )
        if (
            not quality.get("passed")
            and quality.get("banned_phrases")
        ):
            return copy
        copy = dict(copy)
        copy["facebook"] = facebook
        copy["instagram"] = instagram
        copy["communication_objective"] = (
            copy.get("communication_objective")
            or quality.get("communication_objective", "")
        )
        copy["secondary_objective"] = (
            copy.get("secondary_objective")
            or fact_sheet.get("secondary_objective", "")
        )
        copy["narrative_angle"] = (
            copy.get("narrative_angle")
            or fact_sheet.get("narrative_angle", {})
            or quality.get("narrative_angle", {})
        )
        copy["narrative_focus"] = (
            copy.get("narrative_focus")
            or fact_sheet.get("narrative_focus", "")
            or quality.get("narrative_focus", "")
        )
        copy["facebook_hashtags"] = self.writer.hashtags(
            copy.get("story_family", "public_education"),
            fact_sheet,
            "facebook"
        )
        copy["instagram_hashtags"] = self.writer.hashtags(
            copy.get("story_family", "public_education"),
            fact_sheet,
            "instagram"
        )
        copy["selected_teaching_point"] = selected_teaching_point
        copy["quality"] = quality
        copy["scroll_stop_score"] = self.writer.scroll_stop_score(
            facebook,
            fact_sheet,
            copy.get("selected_teaching_point", "")
        )
        return copy

    def _legacy_option_facebook_draft(
        self,
        interpreted,
        current_context,
        historical,
        media,
        details,
        strategy
    ):

        alert = self._alert_phrase(interpreted, current_context)
        reference = self._reference_note(historical)
        media_phrase = self._option_media_phrase(media)
        hook = self._strategy_hook(interpreted, strategy)
        body = self._strategy_body(interpreted, strategy, details)
        paragraphs = [
            hook,
            alert,
            body,
            media_phrase,
            strategy.get("cta", details["cta"]),
            "Stay safe, Morden."
        ]
        text = "\n\n".join(part for part in paragraphs if part)
        hashtags = self._option_hashtags(details, strategy, "facebook")
        return {
            "platform": "facebook",
            "copy_text": f"{text}\n\n{' '.join(hashtags)}",
            "hashtags": hashtags,
            "reference_note": reference
        }

    def _legacy_option_instagram_draft(
        self,
        interpreted,
        current_context,
        historical,
        media,
        details,
        strategy
    ):

        alert = self._alert_phrase(interpreted, current_context)
        hook = self._strategy_hook(interpreted, strategy)
        media_phrase = self._option_media_phrase(media)
        text = "\n\n".join(
            part
            for part in [
                hook,
                alert,
                media_phrase,
                strategy.get("cta", details["cta"])
            ]
            if part
        )
        hashtags = self._option_hashtags(details, strategy, "instagram")
        return {
            "platform": "instagram",
            "copy_text": f"{text}\n\n{' '.join(hashtags)}",
            "hashtags": hashtags
        }

    def _topic_known_facts(self, interpreted, media, details, strategy):

        facts = [
            strategy.get("angle", ""),
            details.get("cta", ""),
            interpreted.get("label", "")
        ]
        primary = media.get("primary_image") or media.get("primary_video") or {}
        if primary:
            for key in (
                "primary_activity",
                "incident_type",
                "description",
                "search_text"
            ):
                value = primary.get(key)
                if value:
                    facts.append(str(value))
            for key in (
                "content_tags",
                "content_themes",
                "recommended_uses",
                "equipment_tags"
            ):
                facts.extend(str(item) for item in primary.get(key, []) if item)
        else:
            facts.append("No single event is confirmed; write from the topic and known public safety point only.")
        return self._unique(
            item for item in facts
            if item
        )[:10]

    def _topic_unknown_facts(self, media):

        if media.get("primary_image") or media.get("primary_video"):
            return []
        return [
            "No specific current event is confirmed.",
            "No individual people, dates, or incident outcomes are confirmed."
        ]

    def _writer_family(self, interpreted, strategy, fact_sheet):

        family = strategy.get("family", "")
        topic = interpreted.get("primary_topic", "")
        if topic in ("water_safety", "smoke_alarm", "fire_prevention_week", "heat_warning", "fireworks", "hydrant_heroes"):
            return "public_education"
        if topic in ("daycare", "school_visit"):
            return "community_event"
        if topic == "helmet_promotion":
            return "recognition"
        if topic == "historical_apparatus":
            return "apparatus"
        if topic == "serious_incident":
            return "incident_follow_up"
        if family in ("training_story", "reel_video"):
            return "training"
        if family == "recruitment_appeal":
            return "recruitment"
        if family in ("historical_campaign_refresh", "checklist", "educational_explainer"):
            return "public_education"
        if family == "community_story":
            return "community_event"
        if topic == "rope_rescue":
            return "training"
        return fact_sheet.get("story_family", "public_education")

    def _tone_for_strategy(self, strategy):

        text = " ".join(
            str(strategy.get(key, ""))
            for key in ("family", "title", "angle")
        ).lower()
        if "light" in text or "community" in text:
            return "community"
        if "educational" in text or "checklist" in text:
            return "educational"
        if "recruit" in text:
            return "standard"
        return "standard"

    def _teaching_point_for_topic(self, interpreted, media):

        topic = interpreted.get("primary_topic", "")
        if topic == "water_safety":
            return "why supervision and life jackets matter near water"
        if topic == "smoke_alarm":
            return "why smoke alarms need testing and replacement"
        if topic == "fireworks":
            return "why fireworks safety depends on distance, supervision, and local rules"
        if topic == "hydrant_heroes":
            return "why hydrants must remain visible and accessible"
        text = topic + " "
        primary = media.get("primary_image") or media.get("primary_video") or {}
        text += " ".join(
            str(primary.get(key, ""))
            for key in ("primary_activity", "description", "search_text")
        )
        return self.writer.teaching_points(
            self.writer.story_family({}, text),
            text,
            interpreted.get("label", "")
        )[0]

    def _strategy_hook(self, interpreted, strategy):

        family = strategy.get("family", "")
        label = interpreted.get("label", "Community Safety")
        if family == "historical_campaign_refresh":
            return f"{label} is useful when the timing and verified media support it."
        if family in ("checklist", "myth_versus_fact"):
            return f"Here is a quick {label.lower()} checklist to keep handy."
        if family in ("recruitment_appeal", "training_story"):
            return "Serving your community starts with people willing to learn and show up."
        if family == "urgent_safety_advisory":
            return f"If {label.lower()} conditions are active, take the update seriously."
        return self._hook(interpreted)

    def _strategy_body(self, interpreted, strategy, details):

        family = strategy.get("family", "")
        if family == "educational_explainer":
            return "Explain the verified risk using the selected event and media facts."
        if family == "historical_campaign_refresh":
            return "MFR has shared similar seasonal reminders before; this version should use today's context and avoid copying old dates or details."
        if family == "community_service_story":
            return "Volunteer firefighters make a practical difference for neighbours, families, and the wider community."
        if family == "training_story":
            return "Training builds the skills, teamwork, and confidence needed when the call comes in."
        if family == "checklist":
            return "Keep the message simple, specific, and easy to act on."
        return details["cta"]

    def _option_media_phrase(self, media):

        primary = media.get("primary_image") or media.get("primary_video") or {}
        if not primary:
            return "No verified media available for this topic."
        return (
            "Use the attached photo or video after review confirms it matches the topic "
            "and does not create a misleading connection."
        )

    def _option_hashtags(self, details, strategy, platform):

        tags = list(details.get("hashtags") or [])
        family = strategy.get("family", "")
        if family in ("recruitment_appeal", "training_story"):
            tags = ["#JoinMFR", "#VolunteerFirefighter"] + tags
        elif family == "historical_campaign_refresh":
            tags = ["#MFR", "#CommunitySafety"] + tags
        elif family == "checklist":
            tags = ["#SafetyChecklist"] + tags
        if platform == "instagram":
            tags.append("#Morden")
        return self._unique(tags)[:5]

    def _option_evidence(self, strategy, media, historical, around_this_time):

        evidence = [
            "Strategy family: " + strategy.get("family", ""),
            "Format: " + strategy.get("format", ""),
            "CTA: " + strategy.get("cta", "")
        ]
        primary = media.get("primary_image") or media.get("primary_video") or {}
        if primary:
            evidence.append(
                "Attached media passed compatibility: " +
                primary.get("filename", "")
            )
        else:
            evidence.append("No media attached because no suitable media passed compatibility.")
        if historical:
            evidence.append(
                "Historical reference: " +
                str(historical[0].get("post_date", ""))
            )
        if around_this_time.get("summary"):
            evidence.append("Year-over-year: " + around_this_time["summary"])
        return self._unique(evidence)[:8]

    def _publication_draft(
        self,
        prompt,
        option_id,
        strategy,
        media,
        facebook,
        instagram,
        historical,
        confidence
    ):

        media_ids = [
            item.get("media_id")
            for item in media.get("carousel_order", [])
            if item.get("media_id")
        ]
        return {
            "package_id": option_id,
            "source_prompt": prompt,
            "source_option_id": option_id,
            "selected_historical_references": [
                item.get("source_record_id")
                for item in historical[:3]
                if item.get("source_record_id")
            ],
            "media_ids": media_ids,
            "facebook_caption": facebook.get("copy_text", ""),
            "instagram_caption": instagram.get("copy_text", ""),
            "platform": strategy.get("platform", ""),
            "format": strategy.get("format", ""),
            "confidence": confidence,
            "evidence_version": self.QUERY_VERSION,
            "generated_at": TimeService.utc_now_iso()
        }

    def create_publication_draft(self, package, option_id):

        for option in (package or {}).get("options", []):
            if option.get("option_id") == option_id:
                draft = dict(option.get("publication_draft") or {})
                draft["story_title"] = option.get("title", "")
                draft["headline"] = option.get("title", "")
                draft["version"] = self.QUERY_VERSION
                try:
                    self.db.save_communication_package_history(draft)
                    draft["persisted"] = True
                except Exception:
                    logger.warning(
                        "Publication draft could not be saved",
                        exc_info=True
                    )
                    draft["persisted"] = False
                return draft
        return {
            "persisted": False,
            "error": "Option not found"
        }

    def regenerate_option(self, package, option_id, requested_angle=""):

        package = dict(package or {})
        interpreted = package.get("interpreted_topic", {}) or {}
        current_context = package.get("current_context", {}) or {}
        historical = package.get("historical_references", []) or []
        around_this_time = package.get("around_this_time", {}) or {}
        details = self.TOPIC_DETAILS.get(
            interpreted.get("primary_topic", ""),
            self.TOPIC_DETAILS["general_engagement"]
        )
        existing = list(package.get("options") or [])
        used = {
            item.get("strategy_family", "")
            for item in existing
            if item.get("option_id") != option_id
        }
        media = {
            "accepted": [],
            "excluded": [],
            "no_suitable_media": True,
            "source": "regenerated_from_existing_options"
        }
        for item in existing:
            option_media = item.get("media_package", {}) or {}
            media["accepted"].extend(option_media.get("carousel_order", []) or [])
            media["excluded"].extend(option_media.get("excluded_conflicts", []) or [])
        media["accepted"] = self._dedupe_media(media["accepted"])
        media["excluded"] = self._dedupe_media(media["excluded"])
        media["no_suitable_media"] = not media["accepted"]

        strategies = self._strategy_blueprints(interpreted) + self._fallback_text_strategies(interpreted)
        if requested_angle:
            strategies.insert(
                0,
                {
                    "family": "custom_angle",
                    "title": requested_angle[:60],
                    "angle": requested_angle,
                    "format": "text/graphic-first post",
                    "platform": "Facebook",
                    "audience": ["Morden residents"],
                    "cta": details["cta"]
                }
            )

        replacement = None
        for strategy in strategies:
            if strategy.get("family") in used:
                continue
            candidate = self._option(
                package.get("prompt", ""),
                interpreted,
                current_context,
                self._option_historical_references(
                    historical,
                    around_this_time,
                    len(existing)
                ),
                around_this_time,
                self._option_media_package(
                    media,
                    strategy,
                    len(existing),
                    media["accepted"]
                ),
                details,
                strategy,
                len(existing) + 1
            )
            candidate["option_id"] = option_id
            candidate["regenerated"] = True
            if self._diversity_score(
                candidate,
                [item for item in existing if item.get("option_id") != option_id]
            ) >= 45:
                replacement = candidate
                break

        if not replacement:
            return {
                "status": "failed",
                "reason": "No distinct replacement option was available."
            }

        package["options"] = [
            replacement if item.get("option_id") == option_id else item
            for item in existing
        ]
        return {
            "status": "ready",
            "package": package,
            "option": replacement
        }

    def _diversity_score(self, option, existing):

        if not existing:
            return 100
        score = 100
        option_terms = self._tokens([
            option.get("title", ""),
            option.get("strategic_angle", ""),
            option.get("facebook_caption", "")
        ])
        option_media = option.get("primary_media_id")
        option_refs = set(option.get("historical_reference_ids") or [])
        for other in existing:
            if option.get("strategy_family") == other.get("strategy_family"):
                score -= 35
            if option.get("recommended_format") == other.get("recommended_format"):
                score -= 10
            if option_media and option_media == other.get("primary_media_id"):
                score -= 10
            if option_refs and option_refs & set(other.get("historical_reference_ids") or []):
                score -= 5
            other_terms = self._tokens([
                other.get("title", ""),
                other.get("strategic_angle", ""),
                other.get("facebook_caption", "")
            ])
            overlap = len(option_terms & other_terms)
            total = max(1, len(option_terms | other_terms))
            if overlap / total > 0.65:
                score -= 25
        return max(0, min(100, score))

    def _option_limit_reason(self, options, requested, media):

        if len(options) >= requested:
            return ""
        if not media.get("accepted"):
            return (
                "Fewer media-backed options were available because no suitable "
                "media passed the topic compatibility gate; text/graphic-first "
                "options were used where possible."
            )
        return (
            "Fewer distinct options were returned because additional candidates "
            "were too similar in strategy, media, reference, or CTA."
        )

    def _option_count(self, value):

        try:
            count = int(value or self.DEFAULT_OPTION_COUNT)
        except Exception:
            count = self.DEFAULT_OPTION_COUNT
        return max(1, min(self.MAX_OPTION_COUNT, count))

    def _merge_hashtags(self, values):

        tags = [
            tag
            for tag in self._unique(values)
            if str(tag).lower() != "#mordenfirerescue"
        ]
        tags = [
            tag
            for tag in tags
            if str(tag).lower() != "#mordenmb"
        ][:4]
        tags.append("#MordenMB")
        return tags

    def _dedupe_references(self, references):

        seen = set()
        result = []
        for item in references or []:
            key = (
                item.get("source_record_id")
                or item.get("communication_id")
                or item.get("post_date")
                or item.get("caption_excerpt")
            )
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    ############################################################

    def _score_history(self, row, interpreted, current_context):
        caption = row.get("caption") or row.get("original_text") or row.get("summary") or ""
        topics = " ".join(str(item) for item in row.get("topics") or row.get("topics_extracted") or [])
        campaign = row.get("campaign", "")
        haystack = self._normalize(" ".join([caption, topics, campaign, row.get("opportunity_type", "")]))
        topic_terms = self._topic_terms(interpreted["primary_topic"])
        matches = [
            term
            for term in topic_terms
            if self._normalize(term).replace("_", " ") in haystack
            or self._normalize(term) in haystack
        ]
        score = len(matches) * 20

        if "morden" in haystack or "mfr" in haystack or "morden fire" in haystack:
            score += 8

        if campaign and self._normalize(interpreted["label"]) in self._normalize(campaign):
            score += 15

        post_date = row.get("post_date") or row.get("original_date") or row.get("created_at") or ""
        seasonal = self._seasonal_match(post_date, current_context)
        if seasonal:
            score += 8

        duplicate = self._duplicate_risk(post_date)
        if duplicate == "high":
            score -= 12

        return {
            "source_record_id": row.get("communication_id") or row.get("id") or row.get("post_id"),
            "post_date": post_date,
            "caption_excerpt": caption[:240],
            "topic": interpreted["label"],
            "campaign": campaign,
            "media_type": row.get("media_type") or row.get("platform") or "",
            "similarity_score": max(0, min(100, score)),
            "evidence": [
                "matched " + ", ".join(matches[:5]) if matches else "bounded historical memory candidate",
                "seasonal match" if seasonal else "seasonal match not detected"
            ],
            "duplicate_risk": duplicate,
            "use_as_reference": True,
            "source": "MFR Communications Memory"
        }

    def _facebook_draft(self, interpreted, current_context, historical, media, details):
        alert_phrase = self._alert_phrase(interpreted, current_context)
        media_phrase = self._media_phrase(media)
        reference_note = self._reference_note(historical)
        paragraphs = [
            self._hook(interpreted),
            alert_phrase,
            details["cta"],
            "Small steps can make a real difference for safety in our community.",
            "Stay safe, Morden."
        ]

        if media_phrase:
            paragraphs.insert(2, media_phrase)

        text = "\n\n".join(part for part in paragraphs if part)
        hashtags = " ".join(details["hashtags"][:5])
        return {
            "platform": "facebook",
            "copy_text": f"{text}\n\n{hashtags}",
            "hashtags": details["hashtags"][:5],
            "reference_note": reference_note
        }

    def _instagram_draft(self, interpreted, current_context, historical, media, details):
        alert_phrase = self._alert_phrase(interpreted, current_context)
        text = "\n\n".join(
            part
            for part in [
                self._hook(interpreted),
                alert_phrase,
                details["cta"],
                "Save this reminder and share it with someone who may need it."
            ]
            if part
        )
        hashtags = " ".join(details["hashtags"][:5])
        return {
            "platform": "instagram",
            "copy_text": f"{text}\n\n{hashtags}",
            "hashtags": details["hashtags"][:5]
        }

    def _hook(self, interpreted):
        topic = interpreted["primary_topic"]
        if topic == "smoke_advisory":
            return "If smoke or haze is affecting the area, take it seriously."
        if topic == "heat_warning":
            return "Heat can become dangerous quickly, especially for people at higher risk."
        if topic == "water_safety":
            return "A good day near the water should also be a safe one."
        if topic == "recruitment":
            return "Looking for a meaningful way to serve your community?"
        if topic == "smoke_alarm":
            return "Working smoke alarms give you and your family time to get out."
        return "Here is a useful safety note for Morden."

    def _alert_phrase(self, interpreted, current_context):
        alerts = current_context.get("alerts") or []

        if interpreted["primary_topic"] in self.WARNING_TOPICS:
            if alerts:
                summaries = [
                    str(item.get("summary") or item.get("type") or "")
                    for item in alerts[:2]
                ]
                return (
                    "Current context includes: " +
                    "; ".join(item for item in summaries if item) +
                    ". Please confirm official conditions before publishing."
                )
            return (
                "We do not have a fresh official alert connected here, so treat this as a general safety reminder and confirm current conditions before publishing."
            )

        return ""

    def _media_phrase(self, media):
        if media.get("no_suitable_media"):
            return "No verified media available for this topic."

        accepted = media.get("accepted") or []
        if not accepted:
            return ""

        return (
            "Use the selected supporting media after review confirms it matches "
            "the story and current conditions."
        )

    def _warnings(self, interpreted, current_context, media, historical):
        warnings = []

        if interpreted["primary_topic"] in self.WARNING_TOPICS and not current_context.get("alerts"):
            warnings.append("No fresh official alert is available in the local context provider.")

        if current_context.get("freshness") != "fresh":
            warnings.append("Current context is unavailable or stale.")

        if media.get("no_suitable_media"):
            warnings.append("No verified media available for this topic.")

        if any(item.get("trust_state") == "unreviewed_real" for item in media.get("accepted", [])):
            warnings.append("Some suitable media is still unreviewed.")

        if historical:
            latest = historical[0].get("post_date", "")
            if self._duplicate_risk(latest) == "high":
                warnings.append("A similar MFR post appears recent; review repetition risk.")

        warnings.append("Human review is required before publishing.")
        return self._unique(warnings)

    def _trust_explanation(self, accepted):
        if not accepted:
            return [
                "No media was selected.",
                "Rejected, failed, and mock media are excluded.",
                "Approvals confirm stored interpretation; corrections provide effective intelligence."
            ]

        corrected = sum(1 for item in accepted if item.get("trust_state") == "corrected_real")
        approved = sum(1 for item in accepted if item.get("trust_state") == "approved_real")
        unreviewed = sum(1 for item in accepted if item.get("trust_state") == "unreviewed_real")
        return [
            f"{corrected} corrected media item(s) use human Effective Intelligence.",
            f"{approved} approved media item(s) have confirmed stored interpretation.",
            f"{unreviewed} unreviewed media item(s) are lower trust.",
            "Rejected, failed, and mock media are excluded.",
            "Communications Learning is separate and requires engagement data."
        ]

    def _confidence(self, interpreted, current_context, media, historical):
        score = 45
        if historical:
            score += 12
        if media.get("accepted"):
            score += 20
        else:
            score -= 10
        if current_context.get("freshness") == "fresh":
            score += 8
        if interpreted["primary_topic"] in self.WARNING_TOPICS and not current_context.get("alerts"):
            score -= 8
        return max(0, min(100, score))

    def _why_now(self, interpreted, current_context):
        themes = " ".join(str(item).lower() for item in current_context.get("active_themes", []))
        label = interpreted["label"]
        if interpreted["primary_topic"] in ("smoke_advisory", "heat_warning"):
            return f"{label} is timely if current local conditions support it; verify official alerts before publishing."
        if self._normalize(label) in themes:
            return f"{label} aligns with the current seasonal context."
        return f"{label} was requested by Jonathan and can be prepared from stored local evidence."

    def _context_evidence(self, current_context):
        return {
            "season": current_context.get("season", ""),
            "active_themes": current_context.get("active_themes", [])[:5],
            "alerts": current_context.get("alerts", [])[:3],
            "data_freshness": current_context.get("data_freshness", ""),
            "sources": current_context.get("sources", [])[:3]
        }

    def _history_evidence(self, historical):
        return [
            {
                "post_date": item.get("post_date", ""),
                "similarity_score": item.get("similarity_score", 0),
                "caption_excerpt": item.get("caption_excerpt", "")
            }
            for item in historical[:3]
        ]

    def _year_over_year_evidence(self, around_this_time):

        around_this_time = around_this_time or {}
        return {
            "summary": around_this_time.get("summary", ""),
            "matching_years": around_this_time.get("matching_years", []),
            "matching_year_count": around_this_time.get("matching_year_count", 0),
            "last_related_post": around_this_time.get("last_related_post", ""),
            "recurring_annual_pattern_confidence": around_this_time.get(
                "recurring_annual_pattern_confidence",
                0
            ),
            "current_year_already_communicated": around_this_time.get(
                "current_year_already_communicated",
                False
            ),
            "communications_gap_risk": around_this_time.get(
                "communications_gap_risk",
                ""
            ),
            "limitations": around_this_time.get("limitations", [])[:2],
            "top_matches": around_this_time.get("matches", [])[:3]
        }

    def _history_queries(self, interpreted):
        return self._unique(
            [
                interpreted.get("label", ""),
                interpreted.get("primary_topic", "").replace("_", " "),
            ] +
            list(interpreted.get("secondary_topics") or []) +
            list(interpreted.get("matched_terms") or [])
        )[:8]

    def _topic_terms(self, topic):
        details = self.TOPIC_DETAILS.get(topic, self.TOPIC_DETAILS["general_engagement"])
        terms = [details["label"], topic.replace("_", " ")]
        terms.extend(details["secondary"])
        if topic == "smoke_advisory":
            terms.extend(["smoke", "haze", "wildfire", "air quality", "visibility"])
        return self._unique(terms)

    def _seasonality(self, topic):
        return {
            "smoke_advisory": "summer wildfire and air-quality season",
            "heat_warning": "summer heat season",
            "water_safety": "summer water safety or winter ice safety depending on context",
            "recruitment": "year-round with campaign timing",
            "smoke_alarm": "year-round, strong during fire prevention season",
            "fire_prevention_week": "September preparation and October campaign window"
        }.get(topic, "year-round")

    def _seasonal_match(self, post_date, current_context):
        parsed = TimeService.normalize_stored_timestamp(post_date)
        local_date = TimeService.to_local(parsed) if parsed else None
        if not local_date:
            return False
        current_month = str(current_context.get("month", "")).lower()
        return local_date.strftime("%B").lower() == current_month

    def _duplicate_risk(self, post_date):
        parsed = TimeService.normalize_stored_timestamp(post_date)
        if not parsed:
            return "unknown"
        days = (TimeService.utc_now() - parsed).days
        if days <= 14:
            return "high"
        if days <= 45:
            return "medium"
        return "low"

    def _reference_note(self, historical):
        if not historical:
            return "No close historical MFR reference was found."
        return (
            "Use prior MFR post from " +
            (historical[0].get("post_date") or "unknown date") +
            " as voice reference only; do not copy stale details."
        )

    def _request_id(self, prompt):
        source = f"{prompt}|{TimeService.utc_now_iso()}"
        return "cdr_" + str(abs(hash(source)))[:12]

    def _normalize(self, value):
        return str(value or "").strip().lower()

    def _tokens(self, values):

        if isinstance(values, str):
            values = [values]

        tokens = set()
        for value in values or []:
            clean = "".join(
                char.lower() if char.isalnum() else " "
                for char in str(value or "")
            )
            tokens.update(
                word
                for word in clean.split()
                if len(word) > 2
            )
        return tokens

    def _unique(self, values):
        seen = set()
        result = []
        for value in values:
            text = str(value or "").strip()
            key = text.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    def _flatten(self, value):

        if value in (None, ""):
            return []
        if isinstance(value, dict):
            items = []
            for nested in value.values():
                items.extend(self._flatten(nested))
            return items
        if isinstance(value, (list, tuple, set)):
            items = []
            for nested in value:
                items.extend(self._flatten(nested))
            return items
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") or stripped.startswith("{"):
                parsed = self._from_json(stripped)
                if parsed != [stripped]:
                    return self._flatten(parsed)
            return [stripped]
        return [value]

    def _from_json(self, value):
        if value in (None, ""):
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        try:
            parsed = json.loads(value)
        except Exception:
            return [str(value)]
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return parsed
        return [parsed]

    def _dedupe_media(self, items):
        seen = set()
        result = []
        for item in items:
            media_id = item.get("media_id")
            if not media_id or media_id in seen:
                continue
            seen.add(media_id)
            result.append(item)
        return result
