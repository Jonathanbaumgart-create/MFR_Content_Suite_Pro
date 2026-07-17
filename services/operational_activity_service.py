import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from core.app_context import context
from services.current_context_service import CurrentContextService
from services.human_feedback_service import HumanFeedbackService
from services.logging_service import LoggingService
from services.media_topic_compatibility_service import MediaTopicCompatibilityService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class OperationalActivityService:

    DEFAULT_LIMIT = 300
    DEFAULT_DAYS = 30

    def __init__(
        self,
        database=None,
        feedback_service=None,
        memory_service=None,
        context_service=None,
        compatibility_service=None
    ):
        self.db = database or context.database
        self.feedback = feedback_service or HumanFeedbackService(database=self.db)
        self.memory = memory_service
        self.context = context_service or CurrentContextService()
        self.compatibility = compatibility_service or MediaTopicCompatibilityService()
        self.last_metrics = {}

    def clusters_for_window(self, days=DEFAULT_DAYS, limit=DEFAULT_LIMIT, now=None):
        started = TimeService.utc_now()
        rows = self.db.operational_activity_candidate_rows(
            since_days=days,
            limit=limit
        )
        candidates = [
            self._candidate(row, now=now)
            for row in rows
        ]
        candidates = [
            item
            for item in candidates
            if item
        ]
        groups = defaultdict(list)

        for candidate in candidates:
            groups[candidate["cluster_key"]].append(candidate)

        clusters = [
            self._cluster(key, items)
            for key, items in groups.items()
        ]
        clusters.sort(
            key=lambda item: (
                item.get("priority_score", 0),
                item.get("confidence", 0),
                item.get("start_time") or item.get("import_start") or ""
            ),
            reverse=True
        )
        self.last_metrics = {
            "candidate_rows": len(rows),
            "candidate_count": len(candidates),
            "cluster_count": len(clusters),
            "bounded_limit": limit,
            "window_days": days,
            "duration_seconds": round(
                (TimeService.utc_now() - started).total_seconds(),
                3
            )
        }
        return clusters

    def recent_activity_summary(self, now=None, limit=6):
        clusters = self.clusters_for_window(now=now)
        return clusters[:limit]

    def communication_opportunities(
        self,
        limit=3,
        clusters=None,
        current_context=None,
        include_unreviewed_fallback=True
    ):
        clusters = clusters if clusters is not None else self.clusters_for_window()
        current_context = current_context or self.context.current_context()
        opportunities = []

        for cluster in clusters:
            opportunity = self._opportunity_from_cluster(
                cluster,
                current_context,
                include_unreviewed_fallback=include_unreviewed_fallback
            )
            if opportunity:
                opportunities.append(opportunity)

        opportunities.extend(
            self._gap_opportunities(
                clusters,
                current_context
            )
        )
        opportunities.sort(
            key=lambda item: (
                item.get("priority_score", 0),
                item.get("confidence", 0),
                item.get("suitable_media_count", 0)
            ),
            reverse=True
        )
        return opportunities[:limit]

    def media_for_topic(self, topic, clusters=None, limit=8):
        clusters = clusters if clusters is not None else self.clusters_for_window()
        accepted = []
        excluded = []

        for cluster in clusters:
            for media in cluster.get("top_media_candidates", []):
                result = self.compatibility.evaluate(
                    topic,
                    media,
                    activity=cluster
                )
                item = {
                    **media,
                    "activity_id": cluster.get("activity_id"),
                    "activity_title": cluster.get("title", ""),
                    "compatibility": result
                }
                if result["compatible"]:
                    accepted.append(item)
                else:
                    excluded.append(item)

        accepted.sort(
            key=lambda item: (
                item.get("compatibility", {}).get("score", 0),
                item.get("communications_score", 0),
                item.get("confidence", 0)
            ),
            reverse=True
        )
        return {
            "topic": topic,
            "accepted": accepted[:limit],
            "excluded": excluded[:limit],
            "no_suitable_media": not accepted
        }

    def communications_gaps(self, clusters=None, current_context=None):
        clusters = clusters if clusters is not None else self.clusters_for_window()
        current_context = current_context or self.context.current_context()
        gaps = []

        if not clusters:
            gaps.append("No recent operational activity clusters were found in the bounded window.")

        for cluster in clusters[:8]:
            if cluster.get("reviewed_media_count", 0) == 0:
                gaps.append(
                    f"{cluster.get('title')} has no approved or corrected media yet."
                )
            elif not cluster.get("historical_matches"):
                gaps.append(
                    f"{cluster.get('title')} appears recent and has no close Communications Memory match."
                )

        active = [str(item).lower() for item in current_context.get("active_themes", [])]
        if any("water safety" in item for item in active):
            water = self.media_for_topic("water safety", clusters=clusters, limit=1)
            if water.get("no_suitable_media"):
                gaps.append("Water safety is seasonally relevant but no suitable current water-related media was found.")

        return gaps[:6]

    def _opportunity_from_cluster(
        self,
        cluster,
        current_context,
        include_unreviewed_fallback=True
    ):
        topic = cluster.get("inferred_type") or cluster.get("title", "")
        match = self.media_for_topic(
            topic,
            clusters=[cluster],
            limit=8
        )
        suitable = match.get("accepted", [])

        reviewed = [
            media
            for media in suitable
            if self._is_reviewed(media)
        ]
        selected = reviewed or (suitable if include_unreviewed_fallback else [])

        if not selected:
            return {
                "title": f"No suitable media for {cluster.get('title')}",
                "summary": "The activity exists, but no media passed the topic compatibility gate.",
                "supporting_recent_activity": cluster,
                "suitable_media_count": 0,
                "top_photo_candidates": [],
                "top_video_candidates": [],
                "last_similar_mfr_post": self._last_memory_match(cluster),
                "repetition_risk": "unknown",
                "recommended_platforms": [],
                "content_format": "Hold until suitable reviewed media is available",
                "confidence": max(0, cluster.get("confidence", 0) - 30),
                "priority_score": 0,
                "why_now": "Recent activity exists, but the media evidence is not compatible enough for a public recommendation.",
                "why_public_would_care": "",
                "why_it_should_outperform": "It should not be promoted until compatible media is available.",
                "positive_factors": cluster.get("evidence", [])[:3],
                "negative_factors": ["No suitable current media passed compatibility checks."],
                "confidence_limitations": ["No suitable media."],
                "source_signals": ["Operational Activity Intelligence", "Media-topic compatibility gate"]
            }

        photos = [
            media
            for media in selected
            if media.get("media_type") == "image"
        ][:5]
        videos = [
            media
            for media in selected
            if media.get("media_type") == "video"
        ][:3]
        historical = self._historical_matches(cluster)
        repetition = self._repetition_risk(historical)
        context_score = self._context_score(cluster, current_context)
        media_score = self._average(
            [media.get("communications_score", 0) for media in selected]
        )
        priority = round(
            cluster.get("priority_score", 0) * 0.42 +
            context_score * 0.18 +
            media_score * 0.22 +
            (15 if reviewed else -12) -
            self._repetition_penalty(repetition),
            1
        )
        confidence = max(
            0,
            min(
                100,
                int(cluster.get("confidence", 0) * 0.72 + media_score * 0.28)
            )
        )

        if not reviewed:
            confidence = max(0, confidence - 20)

        title = cluster.get("title", "")
        return {
            "title": title,
            "summary": f"{title} has recent media and {len(selected)} compatible asset(s).",
            "supporting_recent_activity": cluster,
            "suitable_media_count": len(selected),
            "top_photo_candidates": photos,
            "top_video_candidates": videos,
            "last_similar_mfr_post": historical[0] if historical else {},
            "historical_matches": historical[:3],
            "repetition_risk": repetition,
            "recommended_platforms": self._platforms(cluster, selected),
            "content_format": self._content_format(cluster, selected),
            "confidence": confidence,
            "priority_score": max(0, min(100, priority)),
            "why_now": self._why_now(cluster, current_context),
            "why_public_would_care": self._why_public_cares(cluster),
            "why_it_should_outperform": self._why_outperforms(cluster, context_score, media_score, repetition),
            "positive_factors": self._positive_factors(cluster, selected, current_context),
            "negative_factors": self._negative_factors(cluster, selected, repetition),
            "confidence_limitations": self._limitations(cluster, selected, current_context),
            "source_signals": [
                "Operational Activity Intelligence",
                "Effective Intelligence",
                "Human Review trust state",
                "Filesystem Intelligence",
                "Communications Memory",
                "Current Context"
            ],
            "media_package": self._media_package(selected, cluster),
            "uses_reviewed_media": bool(reviewed),
            "trust_level": "reviewed" if reviewed else "fallback_unreviewed",
            "trust_label": "Reviewed evidence" if reviewed else "Fallback: unreviewed evidence"
        }

    def _candidate(self, row, now=None):
        media_id = row.get("media_id")
        effective = self._quick_effective(media_id)

        trust = effective.get("trust_state") or row.get("trust_state") or ""
        review = effective.get("review_status") or row.get("review_status") or ""
        provider = row.get("provider") or ""
        failure = row.get("failure_reason") or ""

        if provider == "mock" or trust == "mock":
            return None
        if trust in ("rejected_real", "failed") or review in ("rejected", "failed") or failure:
            return None

        media = dict(row)
        media.update({
            "media_id": media_id,
            "trust_state": trust,
            "review_status": review,
            "provider": provider,
            "filesystem_intelligence": effective.get("filesystem_intelligence", {}),
            "fire_service_intelligence": effective.get("fire_service_intelligence", {}),
            "is_human_corrected": effective.get("is_human_corrected", False),
            "correction_count": effective.get("correction_count", 0)
        })
        intelligence = effective.get("media_intelligence", {})
        fire = effective.get("fire_service_intelligence", {})
        filesystem = effective.get("filesystem_intelligence", {})
        media.update(intelligence)
        media.update({
            "incident_type": effective.get("incident_classification") or intelligence.get("incident_type", ""),
            "primary_activity": effective.get("primary_activity") or intelligence.get("primary_activity", ""),
            "operational_context": effective.get("operational_context") or fire.get("operational_context", ""),
            "operational_skills": effective.get("operational_skills") or fire.get("operational_skills", []),
            "communications_uses": effective.get("communications_uses") or fire.get("communications_uses", []),
            "description": effective.get("description") or row.get("analysis_description", "")
        })
        recency = self._recency(media, now=now)
        title, activity_type = self._activity_title_and_type(media, filesystem)
        key = self._cluster_key(media, title, activity_type, recency)
        score = self._candidate_score(media, recency)
        media.update({
            "recency": recency,
            "activity_title": title,
            "activity_type": activity_type,
            "cluster_key": key,
            "candidate_score": score,
            "compatibility_terms": self._terms(media)
        })
        return media

    def _quick_effective(self, media_id):
        try:
            analysis = self.db.get_ai_analysis(media_id) or {}
            intelligence = self.db.get_media_intelligence(media_id) or {}
            fire = self.db.get_fire_service_intelligence(media_id) or {}
            filesystem = self.db.get_filesystem_intelligence(media_id) or {}
            corrections = self.feedback.corrections_for_media(media_id)
        except Exception as ex:
            logger.warning(
                "Could not resolve brief intelligence media_id=%s error=%s",
                media_id,
                ex
            )
            return {
                "analysis": {},
                "media_intelligence": {},
                "fire_service_intelligence": {},
                "filesystem_intelligence": {},
                "corrections": [],
                "is_human_corrected": False,
                "correction_count": 0,
                "trust_state": "",
                "review_status": ""
            }

        effective = {
            "analysis": analysis,
            "media_intelligence": intelligence,
            "fire_service_intelligence": fire,
            "filesystem_intelligence": filesystem,
            "corrections": corrections,
            "is_human_corrected": bool(corrections),
            "correction_count": len(corrections),
            "trust_state": self._trust_state(analysis, corrections),
            "review_status": analysis.get("review_status", ""),
            "description": analysis.get("description", "")
        }

        for key in (
            "incident_classification",
            "operational_context",
            "primary_activity",
            "operational_skills",
            "ppe",
            "equipment",
            "apparatus",
            "communications_uses"
        ):
            effective[key] = (
                intelligence.get(key)
                or fire.get(key)
                or analysis.get(key)
                or ""
            )

        for correction in corrections:
            field = correction.get("field_name", "")
            value = correction.get("corrected_value")
            if field:
                effective[field] = value
                if field in intelligence:
                    intelligence[field] = value
                if field in fire:
                    fire[field] = value

        return effective

    def _trust_state(self, analysis, corrections):
        if corrections:
            return "corrected_real"
        return analysis.get("trust_state", "")

    def _cluster(self, key, items):
        items = sorted(
            items,
            key=lambda item: item.get("candidate_score", 0),
            reverse=True
        )
        representative = items[0]
        media_ids = [
            item["media_id"]
            for item in items
        ]
        photo_count = sum(1 for item in items if item.get("media_type") == "image")
        video_count = sum(1 for item in items if item.get("media_type") == "video")
        reviewed = [
            item
            for item in items
            if self._is_reviewed(item)
        ]
        high_conf = [
            item
            for item in items
            if int(item.get("communications_score") or item.get("intelligence_score") or 0) >= 75
        ]
        reel = [
            item
            for item in items
            if item.get("media_type") == "video" and int(item.get("reel_potential") or 0) >= 60
        ]
        start, end = self._time_range(items, "capture_time")
        import_start, import_end = self._time_range(items, "first_seen_at")
        confidence = self._cluster_confidence(items)
        evidence = self._cluster_evidence(items)
        historical = self._historical_matches_for_terms(
            [representative.get("activity_title", ""), representative.get("activity_type", "")]
        )

        return {
            "activity_id": self._stable_id(key, media_ids),
            "title": representative.get("activity_title", "Recent MFR activity"),
            "inferred_type": representative.get("activity_type", "general_activity"),
            "start_time": start,
            "end_time": end,
            "import_start": import_start,
            "import_end": import_end,
            "recency_label": representative.get("recency", {}).get("label", ""),
            "recency_confidence": representative.get("recency", {}).get("confidence", ""),
            "evidence": evidence,
            "confidence": confidence,
            "photo_count": photo_count,
            "video_count": video_count,
            "reviewed_media_count": len(reviewed),
            "high_confidence_media_count": len(high_conf),
            "reel_candidates": [self._media_summary(item) for item in reel[:4]],
            "top_media_candidates": [self._media_summary(item) for item in items[:12]],
            "filesystem_evidence": self._filesystem_evidence(items),
            "effective_intelligence_evidence": self._effective_evidence(items),
            "historical_matches": historical[:3],
            "priority_score": self._cluster_priority(items, confidence, historical),
            "media_ids": media_ids[:25],
            "bounded_media_count": len(items)
        }

    def _activity_title_and_type(self, media, filesystem):
        sources = [
            filesystem.get("public_education_program"),
            filesystem.get("campaign"),
            filesystem.get("community_event"),
            filesystem.get("training_type"),
            media.get("primary_activity"),
            media.get("operational_context"),
            media.get("incident_type"),
            media.get("normalized_scene")
        ]
        text = " ".join(str(item or "") for item in sources).lower()
        path_text = self._path_terms(media.get("path", ""))
        combined = f"{text} {path_text}".lower()

        if "fire chief" in combined and "day" in combined:
            return "Fire Chief of the Day", "fire_chief_of_the_day"
        if "water rescue" in combined:
            return "Water Rescue Training", "water_rescue_training"
        if "water safety" in combined or "life jacket" in combined:
            return "Water Safety", "water_safety"
        if "scba" in combined:
            return "SCBA Training", "scba_training"
        if "extrication" in combined:
            return "Vehicle Extrication", "vehicle_extrication"
        if "hydrant heroes" in combined:
            return "Hydrant Heroes", "hydrant_heroes"
        if "open house" in combined:
            return "Community Open House", "community_open_house"
        if "recruit" in combined:
            return "Recruitment Activity", "recruitment"
        if "public education" in combined or "school" in combined:
            return "Public Education Visit", "public_education"
        if "apparatus" in combined or filesystem.get("apparatus_identifier"):
            return "Apparatus Activity", "apparatus"
        if "community" in combined:
            return "Community Event", "community_event"
        if "training" in combined:
            return "Training Activity", "training"
        if "incident" in combined or "response" in combined:
            return "Incident Response", "incident_response"

        label = self._human_label(sources[0] or filesystem.get("root_category") or "Recent MFR Activity")
        return label, self._slug(label)

    def _cluster_key(self, media, title, activity_type, recency):
        day = (
            TimeService.local_date(media.get("capture_time"))
            or TimeService.local_date(media.get("first_seen_at"))
            or ""
        )
        folder = self._folder_key(media.get("path", ""))
        program = self._slug(title)
        return "|".join([day, activity_type, program, folder])

    def _recency(self, media, now=None):
        now_utc = TimeService.normalize_stored_timestamp(now) or TimeService.utc_now()
        capture = TimeService.normalize_stored_timestamp(media.get("capture_time"))
        first_seen = TimeService.normalize_stored_timestamp(
            media.get("first_seen_at") or media.get("date_added")
        )
        analyzed = TimeService.normalize_stored_timestamp(media.get("last_analyzed"))

        if capture and (now_utc - capture).days <= self.DEFAULT_DAYS:
            return {
                "label": "recently_captured",
                "confidence": "high",
                "source": media.get("capture_time_source") or "capture_time",
                "timestamp": capture.isoformat(timespec="seconds")
            }

        if first_seen and (now_utc - first_seen).days <= self.DEFAULT_DAYS:
            label = "recently_imported_old_media" if capture else "recently_imported_capture_unknown"
            return {
                "label": label,
                "confidence": "medium" if capture else "low",
                "source": "first_seen_at",
                "timestamp": first_seen.isoformat(timespec="seconds")
            }

        if analyzed and (now_utc - analyzed).days <= self.DEFAULT_DAYS:
            return {
                "label": "recently_analyzed",
                "confidence": "medium",
                "source": "ai_analysis.last_analyzed",
                "timestamp": analyzed.isoformat(timespec="seconds")
            }

        return {
            "label": "older_context",
            "confidence": "low",
            "source": "",
            "timestamp": ""
        }

    def _candidate_score(self, media, recency):
        score = int(media.get("communications_score") or media.get("intelligence_score") or 0)

        if recency.get("label") == "recently_captured":
            score += 18
        elif recency.get("label") == "recently_imported_old_media":
            score -= 5
        elif recency.get("label") == "recently_analyzed":
            score += 4

        if self._is_reviewed(media):
            score += 12
        elif media.get("trust_state") == "unreviewed_real":
            score -= 12

        if media.get("is_human_corrected"):
            score += 8

        return max(0, min(100, score))

    def _cluster_confidence(self, items):
        if not items:
            return 0

        values = [item.get("candidate_score", 0) for item in items]
        reviewed_bonus = 8 if any(self._is_reviewed(item) for item in items) else -10
        capture_bonus = 8 if any(item.get("recency", {}).get("label") == "recently_captured" for item in items) else 0
        return max(0, min(100, int(sum(values) / len(values) + reviewed_bonus + capture_bonus)))

    def _cluster_priority(self, items, confidence, historical):
        recent_capture = any(item.get("recency", {}).get("label") == "recently_captured" for item in items)
        reviewed = sum(1 for item in items if self._is_reviewed(item))
        repetition_penalty = self._repetition_penalty(self._repetition_risk(historical))
        score = confidence + (14 if recent_capture else 0) + min(10, reviewed * 2) - repetition_penalty
        return max(0, min(100, score))

    def _cluster_evidence(self, items):
        evidence = []
        labels = Counter(item.get("recency", {}).get("label", "") for item in items)
        for label, count in labels.most_common(3):
            if label:
                evidence.append(f"{count} media item(s) are {label.replace('_', ' ')}.")

        for value in self._most_common_terms(items, ("primary_activity", "incident_type", "operational_context"))[:4]:
            evidence.append(f"Effective intelligence includes {value}.")

        return evidence[:8]

    def _filesystem_evidence(self, items):
        values = []
        for item in items:
            fs = item.get("filesystem_intelligence") or {}
            for key in ("root_category", "subcategory", "public_education_program", "campaign", "community_event", "training_type", "incident_type", "apparatus_identifier"):
                if fs.get(key):
                    values.append(f"{key}: {fs[key]}")
        return self._unique(values)[:8]

    def _effective_evidence(self, items):
        values = []
        for item in items:
            for key in ("primary_activity", "incident_type", "operational_context", "communications_uses"):
                values.extend(self._flatten(item.get(key)))
        return self._unique(values)[:10]

    def _historical_matches(self, cluster):
        terms = [
            cluster.get("title", ""),
            cluster.get("inferred_type", "")
        ] + list(cluster.get("effective_intelligence_evidence") or [])
        return self._historical_matches_for_terms(terms)

    def _historical_matches_for_terms(self, terms):
        if not self.memory:
            return []

        matches = []
        seen = set()
        for term in terms[:6]:
            term = str(term or "").strip()
            if not term:
                continue
            try:
                results = self.memory.search(term, limit=5)
            except Exception:
                results = []

            for result in results:
                key = result.get("id") or result.get("caption") or json.dumps(result, sort_keys=True, default=str)
                if key in seen:
                    continue
                seen.add(key)
                matches.append({
                    "id": result.get("id"),
                    "platform": result.get("platform", ""),
                    "post_date": result.get("post_date") or result.get("created_at") or "",
                    "campaign": result.get("campaign", ""),
                    "opportunity_type": result.get("opportunity_type", ""),
                    "caption_excerpt": str(result.get("caption", ""))[:180]
                })
                if len(matches) >= 5:
                    return matches
        return matches

    def _last_memory_match(self, cluster):
        matches = self._historical_matches(cluster)
        matches.sort(key=lambda item: item.get("post_date", ""), reverse=True)
        return matches[0] if matches else {}

    def _repetition_risk(self, historical):
        if not historical:
            return "low"

        latest = ""
        for item in historical:
            latest = max(latest, item.get("post_date", ""))
        latest_utc = TimeService.normalize_stored_timestamp(latest)
        if latest_utc is None:
            return "unknown"

        days = (TimeService.utc_now() - latest_utc).days
        if days <= 14:
            return "high"
        if days <= 45:
            return "medium"
        return "low"

    def _repetition_penalty(self, risk):
        return {"high": 18, "medium": 8, "unknown": 3}.get(risk, 0)

    def _context_score(self, cluster, current_context):
        text = " ".join(
            [
                cluster.get("title", ""),
                cluster.get("inferred_type", ""),
                " ".join(cluster.get("effective_intelligence_evidence") or [])
            ]
        ).lower()
        context_terms = " ".join(
            str(item)
            for item in (
                list(current_context.get("active_themes") or []) +
                list(current_context.get("priority_context") or [])
            )
        ).lower()
        score = 45

        for word in re.findall(r"[a-z0-9]+", text):
            if len(word) > 3 and word in context_terms:
                score += 10

        alerts = current_context.get("alerts") or []
        if alerts:
            score += 12

        return max(0, min(100, score))

    def _gap_opportunities(self, clusters, current_context):
        opportunities = []
        active = [str(item).lower() for item in current_context.get("active_themes", [])]

        if any("water safety" in item for item in active):
            water = self.media_for_topic("water safety", clusters=clusters, limit=5)
            if water["accepted"]:
                opportunities.append({
                    "title": "Water Safety",
                    "summary": "Seasonal context supports a water-safety reminder with compatible media.",
                    "supporting_recent_activity": {},
                    "suitable_media_count": len(water["accepted"]),
                    "top_photo_candidates": [item for item in water["accepted"] if item.get("media_type") == "image"][:5],
                    "top_video_candidates": [item for item in water["accepted"] if item.get("media_type") == "video"][:3],
                    "last_similar_mfr_post": {},
                    "historical_matches": [],
                    "repetition_risk": "unknown",
                    "recommended_platforms": ["Facebook", "Instagram"],
                    "content_format": "Seasonal safety reminder",
                    "confidence": 70,
                    "priority_score": 64,
                    "why_now": "Water safety is active in the current seasonal context.",
                    "why_public_would_care": "It helps residents make safer choices around water and recreation.",
                    "why_it_should_outperform": "It has seasonal relevance and compatible media.",
                    "positive_factors": ["Seasonal water safety context is active."],
                    "negative_factors": [],
                    "confidence_limitations": [],
                    "source_signals": ["Current Context", "Media-topic compatibility gate"],
                    "media_package": self._media_package(water["accepted"], {"title": "Water Safety"}),
                    "uses_reviewed_media": any(self._is_reviewed(item) for item in water["accepted"]),
                    "trust_level": "reviewed",
                    "trust_label": "Reviewed evidence"
                })
        return opportunities

    def _media_package(self, selected, cluster):
        photos = [item for item in selected if item.get("media_type") == "image"]
        videos = [item for item in selected if item.get("media_type") == "video"]
        scores = [int(item.get("communications_score") or 0) for item in selected]
        return {
            "best_photo": photos[0] if photos else {},
            "supporting_photos": photos[1:5],
            "best_video": videos[0] if videos else {},
            "supporting_videos": videos[1:3],
            "communications_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "story_strength": {
                "overall": cluster.get("confidence", 0),
                "strongest": cluster.get("effective_intelligence_evidence", [])[:3]
            },
            "media_count": len(selected),
            "story_relevance": self._average(
                [item.get("compatibility", {}).get("score", 0) for item in selected]
            )
        }

    def _media_summary(self, item):
        return {
            "media_id": item.get("media_id"),
            "filename": item.get("filename", ""),
            "path": item.get("path", ""),
            "media_type": item.get("media_type", ""),
            "trust_state": item.get("trust_state", ""),
            "review_status": item.get("review_status", ""),
            "provider": item.get("provider", ""),
            "capture_time": item.get("capture_time", ""),
            "first_seen_at": item.get("first_seen_at", ""),
            "communications_score": int(item.get("communications_score") or 0),
            "intelligence_score": int(item.get("intelligence_score") or 0),
            "confidence": int(item.get("confidence") or item.get("candidate_score") or 0),
            "primary_activity": item.get("primary_activity", ""),
            "incident_type": item.get("incident_type", ""),
            "content_tags": item.get("content_tags", []),
            "recommended_uses": item.get("recommended_uses", []),
            "filesystem_intelligence": item.get("filesystem_intelligence", {}),
            "fire_service_intelligence": item.get("fire_service_intelligence", {}),
            "recency": item.get("recency", {}),
            "is_human_corrected": item.get("is_human_corrected", False),
            "correction_count": item.get("correction_count", 0)
        }

    def _platforms(self, cluster, selected):
        platforms = ["Facebook"]
        if any(item.get("media_type") == "video" for item in selected):
            platforms.append("Instagram")
        if "training" in cluster.get("inferred_type", ""):
            platforms.append("LinkedIn")
        return self._unique(platforms)

    def _content_format(self, cluster, selected):
        if any(item.get("media_type") == "video" for item in selected):
            return "Photo/video story package"
        return "Photo story package"

    def _why_now(self, cluster, current_context):
        recency = cluster.get("recency_label", "").replace("_", " ")
        themes = ", ".join(current_context.get("active_themes", [])[:3])
        return (
            f"{cluster.get('title')} is timely because the activity is {recency} "
            f"and current context includes {themes or 'local calendar context'}."
        )

    def _why_public_cares(self, cluster):
        activity = cluster.get("inferred_type", "").replace("_", " ")
        return (
            f"The public would care because {activity} shows current MFR work, readiness, safety education, or community service."
        )

    def _why_outperforms(self, cluster, context_score, media_score, repetition):
        return (
            f"It ranks ahead of generic evergreen content with activity confidence {cluster.get('confidence', 0)}, "
            f"context score {context_score}, media score {round(media_score, 1)}, and {repetition} repetition risk."
        )

    def _positive_factors(self, cluster, selected, current_context):
        factors = list(cluster.get("evidence") or [])[:4]
        factors.append(f"{len(selected)} compatible media asset(s) passed the topic gate.")
        if current_context.get("active_themes"):
            factors.append("Current context: " + ", ".join(current_context["active_themes"][:3]) + ".")
        return factors[:8]

    def _negative_factors(self, cluster, selected, repetition):
        factors = []
        if cluster.get("recency_confidence") != "high":
            factors.append("Activity timing is not based on high-confidence capture evidence.")
        if not any(self._is_reviewed(item) for item in selected):
            factors.append("Only unreviewed media is available.")
        if repetition in ("high", "medium"):
            factors.append(f"Historical repetition risk is {repetition}.")
        return factors[:8]

    def _limitations(self, cluster, selected, current_context):
        limitations = []
        if cluster.get("recency_label") == "recently_imported_old_media":
            limitations.append("Imported recently, but capture date indicates older media.")
        if not current_context.get("weather") and not current_context.get("alerts"):
            limitations.append("Weather and alert context unavailable or disabled.")
        if not any(self._is_reviewed(item) for item in selected):
            limitations.append("Recommendation relies on unreviewed media because no reviewed alternative matched.")
        return limitations

    def _is_reviewed(self, media):
        return (
            media.get("trust_state") in ("approved_real", "corrected_real")
            or media.get("review_status") in ("approved", "corrected")
        )

    def _time_range(self, items, field):
        values = [
            TimeService.normalize_stored_timestamp(item.get(field))
            for item in items
        ]
        values = [value for value in values if value]
        if not values:
            return "", ""
        return min(values).isoformat(timespec="seconds"), max(values).isoformat(timespec="seconds")

    def _most_common_terms(self, items, fields):
        values = []
        for item in items:
            for field in fields:
                values.extend(self._flatten(item.get(field)))
        counts = Counter(str(value).strip() for value in values if str(value).strip())
        return [value for value, _ in counts.most_common(8)]

    def _terms(self, media):
        return set(
            self._slug(value).replace("-", "_")
            for value in self._flatten(media)
            if str(value).strip()
        )

    def _path_terms(self, path):
        parts = Path(str(path or "")).parts
        return " ".join(parts[-4:])

    def _folder_key(self, path):
        parts = Path(str(path or "")).parts
        if len(parts) >= 2:
            return self._slug(parts[-2])
        return ""

    def _stable_id(self, key, media_ids):
        source = key + "|" + "|".join(str(media_id) for media_id in sorted(media_ids)[:10])
        return "activity_" + hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]

    def _human_label(self, value):
        text = str(value or "").replace("_", " ").replace("-", " ").strip()
        return " ".join(part.capitalize() for part in text.split()) or "Recent MFR Activity"

    def _slug(self, value):
        return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")

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
        if value is None:
            return []
        if isinstance(value, dict):
            result = []
            for item in value.values():
                result.extend(self._flatten(item))
            return result
        if isinstance(value, (list, tuple, set)):
            result = []
            for item in value:
                result.extend(self._flatten(item))
            return result
        return [value]

    def _average(self, values):
        values = [float(value or 0) for value in values]
        if not values:
            return 0
        return round(sum(values) / len(values), 1)
