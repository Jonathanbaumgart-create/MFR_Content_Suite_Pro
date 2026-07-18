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
        first_option = options[0] if options else {}
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

        facebook = self._option_facebook_draft(
            interpreted,
            current_context,
            historical,
            media_package,
            details,
            strategy
        )
        instagram = self._option_instagram_draft(
            interpreted,
            current_context,
            historical,
            media_package,
            details,
            strategy
        )
        warnings = self._warnings(
            interpreted,
            current_context,
            media_package,
            historical
        )
        if media_package.get("no_suitable_media"):
            warnings.append(
                "This option is text/graphic-first because no suitable media passed the compatibility gate."
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
            "hashtags": self._unique(
                list(facebook.get("hashtags", [])) +
                list(instagram.get("hashtags", []))
            )[:5],
            "media_package": media_package,
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
            "state": "ready"
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
            "myth_versus_fact",
            "checklist"
        ):
            start = index if index < len(accepted) else 0
            selected = accepted[start:start + 4] or accepted[:1]

        primary = selected[0] if selected else {}
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

    def _option_instagram_draft(
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

    def _strategy_hook(self, interpreted, strategy):

        family = strategy.get("family", "")
        label = interpreted.get("label", "Community Safety")
        if family == "historical_campaign_refresh":
            return f"{label} is a message worth bringing back when the timing is right."
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
            return "The goal is simple: help people understand the risk before it becomes an emergency."
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
            return "This option should be handled as text/graphic-first unless Jonathan chooses suitable media."
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
                score -= 20
            if option_refs and option_refs & set(other.get("historical_reference_ids") or []):
                score -= 10
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
        return "Here is a timely safety reminder from Morden Fire & Rescue."

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
            return "No suitable current media was found for this topic, so this is best handled as a text or graphic-first post."

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
            warnings.append("No suitable current media passed the topic compatibility gate.")

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
