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
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class ContentDirectorRetrievalService:

    QUERY_VERSION = "content-director-retrieval-v1"

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
        self.last_metrics = {}

    def build_prompt_package(self, prompt, limit=5, now=None):
        started = time.perf_counter()
        interpreted = self.interpret_query(prompt)
        current_context = self.context.current_context(now=now)
        historical = self.historical_matches(
            interpreted,
            current_context=current_context,
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
            limit=limit
        )
        package = self._package(
            prompt,
            interpreted,
            current_context,
            historical,
            media
        )
        self.last_metrics = {
            "total_seconds": round(time.perf_counter() - started, 3),
            "historical_count": len(historical),
            "accepted_media_count": len(media.get("accepted", [])),
            "excluded_media_count": len(media.get("excluded", [])),
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
        media
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
        package = {
            "request_id": self._request_id(prompt),
            "prompt": prompt,
            "interpreted_topic": interpreted,
            "current_context": current_context,
            "opportunity_summary": opportunity,
            "facebook_draft": facebook,
            "instagram_draft": instagram,
            "facebook_caption": facebook["copy_text"],
            "instagram_caption": instagram["copy_text"],
            "media_package": {
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
            "smoke_alarm": "year-round, strong during fire prevention season"
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
