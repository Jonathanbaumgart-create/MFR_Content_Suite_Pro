import time

from core.app_context import context
from models.decision_explanation import DecisionExplanation
from services.communications_memory_service import CommunicationsMemoryService
from services.human_feedback_service import HumanFeedbackService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class DecisionExplainabilityService:

    EXPLANATION_VERSION = "decision-explainability-v1"
    MAX_FACTORS = 8
    MAX_ASSETS = 12
    MAX_COMMUNICATIONS = 5
    MAX_COMPARISONS = 5

    def __init__(self, database=None, memory_service=None):

        self.db = database or context.database
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.feedback = HumanFeedbackService(
            database=self.db
        )
        self.last_metrics = {}

    ############################################################

    def explain_recommendation(
        self,
        recommendation,
        alternatives=None,
        persist=True
    ):

        started = time.perf_counter()
        recommendation = recommendation or {}
        alternatives = alternatives or []
        assets = self._assets_for_recommendation(recommendation)
        positive, negative = self._factor_groups(
            recommendation.get("reasoning_factors", [])
        )
        decision_id = self._decision_id(
            recommendation,
            "recommendation"
        )

        explanation = DecisionExplanation(
            decision_id=decision_id,
            decision_type="recommendation",
            subject_type="editorial_recommendation",
            subject_id=decision_id,
            headline=(
                recommendation.get("headline") or
                recommendation.get("title", "")
            ),
            summary=recommendation.get("summary", ""),
            decision_score=self._score(
                recommendation.get("priority_score")
            ),
            confidence_score=self._score(
                recommendation.get("confidence_score")
            ),
            trust_label=self._trust_label(
                recommendation,
                assets
            ),
            evidence_count=len(assets),
            positive_factors=positive[:self.MAX_FACTORS],
            negative_factors=negative[:self.MAX_FACTORS],
            limiting_factors=list(
                recommendation.get("confidence_limitations") or []
            )[:self.MAX_FACTORS],
            source_signals=self._source_signals(recommendation),
            supporting_assets=self._asset_evidence(assets),
            supporting_communications=self._communications_evidence(
                recommendation
            ),
            supporting_campaigns=list(
                recommendation.get("supporting_campaigns") or []
            )[:self.MAX_FACTORS],
            supporting_programs=list(
                recommendation.get("supporting_programs") or []
            )[:self.MAX_FACTORS],
            historical_evidence=self._historical_evidence(
                recommendation
            ),
            seasonal_evidence=self._seasonal_evidence(
                recommendation
            ),
            trust_state_breakdown=self._trust_breakdown(assets),
            comparison_candidates=self._comparison_candidates(
                alternatives
            ),
            why_selected=self._why_recommendation_selected(
                recommendation,
                assets,
                positive
            ),
            why_not_selected=self._why_not_alternatives(
                recommendation,
                alternatives
            ),
            score_reconciliation=self._score_reconciliation(
                recommendation
            ),
            changed_since_previous=self._changed_since_previous(
                decision_id,
                recommendation
            ),
            generated_at=TimeService.utc_now_iso(),
            explanation_version=self.EXPLANATION_VERSION
        ).to_dict()

        self._finish(
            started,
            "recommendation",
            explanation,
            persist
        )
        return explanation

    ############################################################

    def explain_media_selection(
        self,
        media_or_asset,
        recommendation=None,
        compared_media=None,
        persist=True
    ):

        started = time.perf_counter()
        asset = self._asset(media_or_asset)
        recommendation = recommendation or {}
        compared = self._asset(compared_media) if compared_media else {}
        decision_id = (
            "media-selection-" +
            str(asset.get("media_id") or recommendation.get("recommendation_id") or "unknown")
        )
        comparisons = []

        if compared:
            comparisons.append(
                self._asset_comparison_summary(
                    asset,
                    compared
                )
            )

        explanation = DecisionExplanation(
            decision_id=decision_id,
            decision_type="media_selection",
            subject_type="media",
            subject_id=str(asset.get("media_id", "")),
            headline=asset.get("filename") or "Selected media",
            summary=self._media_summary(asset),
            decision_score=self._asset_score(asset),
            confidence_score=self._score(
                asset.get("intelligence_score")
            ),
            trust_label=asset.get("trust_state") or "unknown",
            evidence_count=1 if asset else 0,
            positive_factors=self._asset_positive_factors(asset),
            negative_factors=self._asset_negative_factors(asset),
            limiting_factors=self._asset_limitations(asset),
            source_signals=[
                "Stored Media Intelligence",
                "Human review trust state",
                "Communications Intelligence scores",
                "Communications Memory usage where available"
            ],
            supporting_assets=self._asset_evidence([asset]) if asset else [],
            historical_evidence=self._media_history(asset),
            trust_state_breakdown=self._trust_breakdown([asset] if asset else []),
            comparison_candidates=comparisons,
            why_selected=self._why_media_selected(
                asset,
                recommendation
            ),
            why_not_selected=self._why_not_media(
                asset,
                compared
            ),
            generated_at=TimeService.utc_now_iso(),
            explanation_version=self.EXPLANATION_VERSION
        ).to_dict()

        self._finish(
            started,
            "media_selection",
            explanation,
            persist
        )
        return explanation

    ############################################################

    def explain_campaign_or_program(
        self,
        name,
        subject_type="campaign",
        recommendation=None,
        persist=True
    ):

        started = time.perf_counter()
        recommendation = recommendation or {}
        name = str(name or "").strip()
        matches = self._memory_search(name)
        decision_id = f"{subject_type}-{self._slug(name)}"
        explanation = DecisionExplanation(
            decision_id=decision_id,
            decision_type=f"{subject_type}_fit",
            subject_type=subject_type,
            subject_id=name,
            headline=name,
            summary=(
                f"{name} appears in stored recommendation or communications "
                "signals." if name else "No campaign or program was selected."
            ),
            decision_score=self._score(
                recommendation.get("priority_score")
            ),
            confidence_score=self._score(
                recommendation.get("confidence_score")
            ),
            evidence_count=len(matches),
            source_signals=[
                "Communications Memory search",
                "Recommendation supporting campaigns/programs",
                "Stored Department Knowledge references"
            ],
            supporting_communications=matches,
            supporting_campaigns=list(
                recommendation.get("supporting_campaigns") or []
            )[:self.MAX_FACTORS],
            supporting_programs=list(
                recommendation.get("supporting_programs") or []
            )[:self.MAX_FACTORS],
            why_selected=[
                "The campaign or program is tied to the selected editorial angle.",
                "The explanation is grounded in stored communications and recommendation signals."
            ],
            limiting_factors=[
                "Campaign timing and program detail depend on stored knowledge quality."
            ],
            generated_at=TimeService.utc_now_iso(),
            explanation_version=self.EXPLANATION_VERSION
        ).to_dict()

        self._finish(
            started,
            f"{subject_type}_fit",
            explanation,
            persist
        )
        return explanation

    ############################################################

    def audit_package(self, package, recommendation=None, persist=True):

        started = time.perf_counter()
        package = package or {}
        recommendation = recommendation or {}
        media = package.get("media_package", {}) or {}
        assets = []

        for key in (
            "primary_photo",
            "primary_video"
        ):
            if media.get(key):
                assets.append(media[key])

        assets.extend(media.get("gallery_photos") or [])
        assets.extend(media.get("gallery_videos") or [])
        scoring = package.get("package_scoring", {}) or {}
        decision_id = (
            "package-" +
            self._slug(package.get("headline") or recommendation.get("title"))
        )
        explanation = DecisionExplanation(
            decision_id=decision_id,
            decision_type="communication_package",
            subject_type="communication_package",
            subject_id=package.get("package_type", ""),
            headline=package.get("headline", ""),
            summary=package.get("primary_story", ""),
            decision_score=self._score(scoring.get("overall_score")),
            confidence_score=self._score(package.get("confidence")),
            trust_label=package.get("trust_label", ""),
            evidence_count=len(assets),
            positive_factors=list(package.get("positive_factors") or [])[:self.MAX_FACTORS],
            negative_factors=list(package.get("negative_factors") or [])[:self.MAX_FACTORS],
            limiting_factors=list(package.get("confidence_limitations") or [])[:self.MAX_FACTORS],
            source_signals=[
                "Communication Package Service",
                "Stored editorial recommendation",
                "Bounded media package lookup",
                "Human trust-state filtering"
            ],
            supporting_assets=self._asset_evidence(assets),
            trust_state_breakdown=self._trust_breakdown(assets),
            why_selected=self._why_package_selected(package),
            package_audit=self._package_audit(package),
            generated_at=TimeService.utc_now_iso(),
            explanation_version=self.EXPLANATION_VERSION
        ).to_dict()

        self._finish(
            started,
            "communication_package",
            explanation,
            persist
        )
        return explanation

    ############################################################

    def audit_generated_content(
        self,
        generated_package,
        platform=None,
        persist=True
    ):

        started = time.perf_counter()
        generated_package = generated_package or {}
        platforms = (
            [platform]
            if platform
            else list((generated_package.get("copy_buttons") or {}).keys())
        )
        source_package = generated_package.get("source_package", {}) or {}
        decision_id = "generated-content-" + self._slug(
            source_package.get("headline") or generated_package.get("headline")
        )
        audit = self._generated_content_audit(
            generated_package,
            platforms
        )
        explanation = DecisionExplanation(
            decision_id=decision_id,
            decision_type="generated_content",
            subject_type="generated_content",
            subject_id=",".join(platforms),
            headline=source_package.get("headline") or generated_package.get("headline", ""),
            summary="Generated content is audited against the selected package and writing controls.",
            decision_score=self._score(
                (generated_package.get("editorial_review") or {}).get("overall_score")
            ),
            confidence_score=self._score(
                source_package.get("confidence")
            ),
            trust_label=source_package.get("trust_label", ""),
            evidence_count=len(platforms),
            positive_factors=audit.get("positive_factors", []),
            negative_factors=audit.get("negative_factors", []),
            limiting_factors=audit.get("limitations", []),
            source_signals=[
                "Content Generation Service",
                "Writing Provider status",
                "Prompt Engine output",
                "Editorial Review Service"
            ],
            generated_content_audit=audit,
            generated_at=TimeService.utc_now_iso(),
            explanation_version=self.EXPLANATION_VERSION
        ).to_dict()

        self._finish(
            started,
            "generated_content",
            explanation,
            persist
        )
        return explanation

    ############################################################

    def why_not_recommendation(self, selected, candidate):

        explanation = self.explain_recommendation(
            selected,
            alternatives=[candidate],
            persist=False
        )
        return explanation.get("why_not_selected", [])

    ############################################################

    def why_not_media(self, selected_media, candidate_media, recommendation=None):

        explanation = self.explain_media_selection(
            selected_media,
            recommendation=recommendation,
            compared_media=candidate_media,
            persist=False
        )
        return explanation.get("why_not_selected", [])

    ############################################################

    def format_explanation_text(self, explanation):

        explanation = explanation or {}
        sections = [
            (
                "Decision",
                [
                    explanation.get("headline", ""),
                    explanation.get("summary", ""),
                    f"Score: {explanation.get('decision_score', 0)}",
                    f"Confidence: {explanation.get('confidence_score', 0)}",
                    f"Trust: {explanation.get('trust_label', '')}"
                ]
            ),
            ("Why selected", explanation.get("why_selected", [])),
            ("Positive factors", self._factor_text(explanation.get("positive_factors", []))),
            ("Negative factors", self._factor_text(explanation.get("negative_factors", []))),
            ("Confidence limits", explanation.get("limiting_factors", [])),
            ("Source signals", explanation.get("source_signals", [])),
            ("Supporting assets", self._asset_text(explanation.get("supporting_assets", []))),
            ("Why not alternatives", explanation.get("why_not_selected", [])),
            ("Changed since previous", self._change_text(explanation.get("changed_since_previous", {}))),
            ("Audit", self._audit_text(explanation))
        ]
        lines = []

        for title, items in sections:
            items = [
                str(item)
                for item in (items or [])
                if str(item or "").strip()
            ]

            if not items:
                continue

            lines.append(title)
            lines.extend(items)
            lines.append("")

        return "\n".join(lines).strip()

    ############################################################

    def _finish(self, started, decision_type, explanation, persist):

        elapsed = round(time.perf_counter() - started, 4)
        self.last_metrics = {
            "decision_type": decision_type,
            "elapsed_seconds": elapsed,
            "evidence_count": explanation.get("evidence_count", 0)
        }

        if persist:
            try:
                self.db.save_decision_audit_snapshot(explanation)
                self.db.prune_decision_audit_history()
            except Exception:
                logger.warning(
                    "Decision audit snapshot could not be saved",
                    exc_info=True
                )

        logger.info(
            "Decision explanation generated type=%s subject=%s elapsed=%s",
            decision_type,
            explanation.get("subject_id", ""),
            elapsed
        )

    def _assets_for_recommendation(self, recommendation):

        ids = []
        ids.extend(recommendation.get("best_asset_ids") or [])
        ids.extend(recommendation.get("supporting_asset_ids") or [])
        ids = self._unique_ids(ids)[:self.MAX_ASSETS]

        if ids:
            assets = self.db.communications_officer_assets(
                ids,
                limit=self.MAX_ASSETS
            )
            return [
                self._effective_asset(asset)
                for asset in assets
            ]

        return [
            self._effective_asset(asset)
            for asset in list(recommendation.get("recommended_media") or [])[:self.MAX_ASSETS]
        ]

    def _asset(self, media_or_asset):

        if not media_or_asset:
            return {}

        if isinstance(media_or_asset, dict):
            return self._effective_asset(media_or_asset)

        media_id = self._int(media_or_asset)

        if not media_id:
            return {}

        assets = self.db.communications_officer_assets(
            [media_id],
            limit=1
        )
        return self._effective_asset(assets[0]) if assets else {"media_id": media_id}

    def _effective_asset(self, asset):

        media_id = asset.get("media_id") if asset else None

        if not media_id:
            return asset or {}

        try:
            effective = self.feedback.effective_media_intelligence_row(
                media_id
            )
        except Exception:
            return asset

        effective.update({
            "media_id": media_id,
            "filename": asset.get("filename", ""),
            "path": asset.get("path", ""),
            "media_type": asset.get("media_type", ""),
            "provider": asset.get("provider", ""),
            "model": asset.get("model", ""),
            "failure_reason": asset.get("failure_reason", "")
        })

        return effective

    def _factor_groups(self, factors):

        positive = []
        negative = []

        for factor in factors or []:
            item = dict(factor) if isinstance(factor, dict) else {
                "label": str(factor),
                "score": 0,
                "reason": str(factor)
            }

            if item.get("direction") == "negative" or self._score(item.get("score")) < 0:
                negative.append(item)
            else:
                positive.append(item)

        return positive, negative

    def _score_reconciliation(self, recommendation):

        factors = recommendation.get("reasoning_factors") or []
        raw_total = 0

        for factor in factors:
            if isinstance(factor, dict):
                raw_total += self._score(factor.get("score"))

        return {
            "raw_factor_total": round(raw_total, 2),
            "priority_score": self._score(recommendation.get("priority_score")),
            "confidence_score": self._score(recommendation.get("confidence_score")),
            "final_order_score": self._score(recommendation.get("final_order_score")),
            "diversity_adjustment": self._score(recommendation.get("diversity_adjustment")),
            "repetition_penalty": self._score(recommendation.get("repetition_penalty")),
            "generic_title_penalty": self._score(recommendation.get("generic_title_penalty")),
            "scoring_version": recommendation.get("scoring_version", ""),
            "normalization": "Scores are clamped to the local 0-100 recommendation scale."
        }

    def _source_signals(self, recommendation):

        signals = list(recommendation.get("source_signals") or [])
        required = [
            "Editorial Recommendation Engine",
            "Recommendation Scoring Service",
            "Recommendation Candidate Service",
            "Communications Memory",
            "Media Priority",
            "Human Review trust state",
            "Filesystem Intelligence"
        ]

        for item in required:
            if not any(item.lower() in str(signal).lower() for signal in signals):
                signals.append(item)

        return signals[:12]

    def _asset_evidence(self, assets):

        evidence = []

        for asset in assets[:self.MAX_ASSETS]:
            if not asset:
                continue

            evidence.append({
                "media_id": asset.get("media_id"),
                "filename": asset.get("filename", ""),
                "media_type": asset.get("media_type", ""),
                "trust_state": asset.get("trust_state", ""),
                "review_status": asset.get("review_status", ""),
                "communications_score": self._score(asset.get("communications_score")),
                "intelligence_score": self._score(asset.get("intelligence_score")),
                "description": (
                    asset.get("effective_description") or
                    asset.get("description", "")
                ),
                "incident_type": asset.get("incident_type", ""),
                "primary_activity": asset.get("primary_activity", ""),
                "recommended_uses": self._list(asset.get("recommended_uses"))[:5],
                "content_tags": self._list(asset.get("content_tags"))[:5],
                "reel_potential": self._score(asset.get("reel_potential")),
                "story_potential": self._score(asset.get("story_potential")),
                "clip_recommendations": self._list(
                    asset.get("clip_recommendations")
                )[:3],
                "cover_recommendation": asset.get("cover_recommendation") or {},
                "filesystem_context": self._filesystem_context(asset)
            })

        return evidence

    def _filesystem_context(self, asset):

        filesystem = asset.get("filesystem_intelligence") or {}

        if not filesystem:
            return {}

        return {
            "category": filesystem.get("root_category", ""),
            "subcategory": filesystem.get("subcategory", ""),
            "apparatus": (
                filesystem.get("apparatus_name") or
                filesystem.get("apparatus_identifier", "")
            ),
            "training_type": filesystem.get("training_type", ""),
            "incident_type": filesystem.get("incident_type", ""),
            "program": filesystem.get("public_education_program", ""),
            "campaign": filesystem.get("campaign", ""),
            "confidence": filesystem.get("filesystem_confidence", 0),
            "conflict_state": filesystem.get("conflict_state", "")
        }

    def _communications_evidence(self, recommendation):

        terms = []
        terms.extend(recommendation.get("supporting_topics") or [])
        terms.extend(recommendation.get("supporting_programs") or [])
        terms.extend(recommendation.get("supporting_campaigns") or [])
        terms.append(recommendation.get("topic", ""))
        terms.append(recommendation.get("category", ""))

        for term in terms:
            matches = self._memory_search(term)

            if matches:
                return matches

        return []

    def _historical_evidence(self, recommendation):

        evidence = []

        if recommendation.get("communications_gap"):
            evidence.append(
                "Communications gap: " + recommendation.get("communications_gap", "")
            )

        if recommendation.get("repetition_risk"):
            evidence.append(
                "Repetition risk: " + recommendation.get("repetition_risk", "")
            )

        return evidence

    def _seasonal_evidence(self, recommendation):

        evidence = []

        for factor in recommendation.get("reasoning_factors") or []:
            text = " ".join(
                str(factor.get(key, ""))
                for key in ("label", "reason", "category")
                if isinstance(factor, dict)
            )

            if "season" in text.lower() or "today" in text.lower():
                evidence.append(text)

        if recommendation.get("why_today_matters"):
            evidence.append(recommendation.get("why_today_matters", ""))

        return evidence[:self.MAX_FACTORS]

    def _trust_breakdown(self, assets):

        breakdown = {
            "approved_real": 0,
            "corrected_real": 0,
            "unreviewed_real": 0,
            "rejected_or_failed": 0,
            "mock": 0,
            "unknown": 0
        }

        for asset in assets:
            trust = str(asset.get("trust_state") or "").lower()
            provider = str(asset.get("provider") or "").lower()

            if provider == "mock":
                breakdown["mock"] += 1
            elif trust in breakdown:
                breakdown[trust] += 1
            elif trust in ("rejected", "failed") or asset.get("failure_reason"):
                breakdown["rejected_or_failed"] += 1
            else:
                breakdown["unknown"] += 1

        return breakdown

    def _comparison_candidates(self, alternatives):

        candidates = []

        for item in (alternatives or [])[:self.MAX_COMPARISONS]:
            candidates.append({
                "title": item.get("title", ""),
                "priority_score": self._score(item.get("priority_score")),
                "confidence_score": self._score(item.get("confidence_score")),
                "primary_reason": item.get("primary_reason", ""),
                "why_not_selected": self._why_single_alternative(item)
            })

        return candidates

    def _why_recommendation_selected(self, recommendation, assets, positive):

        reasons = []

        if recommendation.get("primary_reason"):
            reasons.append(recommendation.get("primary_reason", ""))

        for factor in positive[:4]:
            if isinstance(factor, dict):
                reasons.append(
                    factor.get("reason") or factor.get("label", "")
                )

        reviewed = [
            asset for asset in assets
            if str(asset.get("trust_state") or "").lower()
            in ("approved_real", "corrected_real")
        ]

        if reviewed:
            reasons.append(
                f"{len(reviewed)} reviewed real media asset(s) support this recommendation."
            )
        elif assets:
            reasons.append(
                "The recommendation uses available real intelligence, but reviewed evidence is limited."
            )

        return self._clean(reasons)[:self.MAX_FACTORS]

    def _why_not_alternatives(self, selected, alternatives):

        lines = []
        selected_score = self._score(selected.get("priority_score"))

        for item in (alternatives or [])[:self.MAX_COMPARISONS]:
            score = self._score(item.get("priority_score"))
            reason = self._why_single_alternative(item)
            lines.append(
                (
                    f"{item.get('title', 'Alternative')} scored {score}, "
                    f"compared with {selected_score}. {reason}"
                )
            )

        return self._clean(lines)

    def _why_single_alternative(self, item):

        limitations = list(item.get("confidence_limitations") or [])

        if limitations:
            return limitations[0]

        if item.get("repetition_risk"):
            return "Repetition risk: " + item.get("repetition_risk", "")

        if item.get("primary_reason"):
            return item.get("primary_reason", "")

        return "The selected option had stronger combined priority, confidence, or trust signals."

    def _changed_since_previous(self, decision_id, recommendation):

        try:
            rows = self.db.recent_decision_audit_snapshots(
                decision_id=decision_id,
                limit=1
            )
        except Exception:
            return {"available": False, "changes": []}

        if not rows:
            return {
                "available": False,
                "changes": ["No prior audit snapshot for this decision."]
            }

        previous = rows[0].get("snapshot", {}) or {}
        changes = []
        checks = (
            ("decision_score", self._score(recommendation.get("priority_score"))),
            ("confidence_score", self._score(recommendation.get("confidence_score"))),
            ("trust_label", recommendation.get("trust_label", "")),
        )

        for key, current in checks:
            old = previous.get(key)

            if old != current:
                changes.append(
                    f"{key} changed from {old} to {current}."
                )

        if not changes:
            changes.append("No material score, confidence, or trust change detected.")

        return {
            "available": True,
            "previous_generated_at": previous.get("generated_at", ""),
            "changes": changes
        }

    def _asset_score(self, asset):

        return round(
            (
                self._score(asset.get("communications_score")) * 0.55 +
                self._score(asset.get("intelligence_score")) * 0.25 +
                self._score(asset.get("trust_building_score")) * 0.2
            ),
            1
        )

    def _asset_positive_factors(self, asset):

        factors = []

        for key, label in (
            ("communications_score", "Communications score"),
            ("storytelling_score", "Storytelling"),
            ("community_engagement_score", "Community engagement"),
            ("educational_value_score", "Educational value"),
            ("recruitment_value_score", "Recruitment value"),
            ("trust_building_score", "Trust building")
        ):
            score = self._score(asset.get(key))

            if score >= 60:
                factors.append({
                    "label": label,
                    "score": score,
                    "reason": f"{label} is strong for this asset."
                })

        if asset.get("trust_state") in ("approved_real", "corrected_real"):
            factors.append({
                "label": "Reviewed intelligence",
                "score": 15,
                "reason": "Human review makes this asset safer to recommend."
            })

        return factors[:self.MAX_FACTORS]

    def _asset_negative_factors(self, asset):

        factors = []
        trust = str(asset.get("trust_state") or "").lower()

        if trust not in ("approved_real", "corrected_real"):
            factors.append({
                "label": "Review confidence",
                "score": -15,
                "reason": "This asset is not yet approved or corrected."
            })

        if asset.get("failure_reason"):
            factors.append({
                "label": "Provider failure",
                "score": -50,
                "reason": "A provider failure is attached to this media."
            })

        return factors

    def _asset_limitations(self, asset):

        limitations = []

        if not asset.get("incident_type"):
            limitations.append("Incident classification is missing or unknown.")

        if not asset.get("primary_activity"):
            limitations.append("Primary activity is missing or unknown.")

        if str(asset.get("trust_state") or "").lower() not in (
            "approved_real",
            "corrected_real"
        ):
            limitations.append("Human review is incomplete.")

        return limitations[:self.MAX_FACTORS]

    def _media_summary(self, asset):

        return " | ".join(
            self._clean(
                [
                    asset.get("incident_type", ""),
                    asset.get("primary_activity", ""),
                    ", ".join(self._list(asset.get("recommended_uses"))[:3])
                ]
            )
        )

    def _media_history(self, asset):

        if not asset.get("media_id"):
            return []

        try:
            usage = self.memory.media_memory(asset.get("media_id"))
        except Exception:
            return []

        lines = []

        if usage.get("times_used"):
            lines.append(
                f"Used in {usage.get('times_used')} historical communication(s)."
            )
        else:
            lines.append("No prior communications memory usage found for this media.")

        if usage.get("last_used_at"):
            lines.append("Last used: " + usage.get("last_used_at", ""))

        return lines

    def _why_media_selected(self, asset, recommendation):

        reasons = []

        if recommendation.get("title"):
            reasons.append(
                f"Supports the recommendation '{recommendation.get('title')}'."
            )

        if asset.get("communications_score"):
            reasons.append(
                f"Communications score is {asset.get('communications_score')}."
            )

        if asset.get("trust_state") in ("approved_real", "corrected_real"):
            reasons.append(
                "Reviewed real intelligence is available."
            )

        if asset.get("media_type") == "video":
            reasons.append("Video can support stronger platform variety.")

        return self._clean(reasons)[:self.MAX_FACTORS]

    def _why_not_media(self, selected, compared):

        if not compared:
            return []

        selected_score = self._asset_score(selected)
        compared_score = self._asset_score(compared)

        if compared_score > selected_score:
            return [
                (
                    "The compared asset scores higher, but may have weaker trust, "
                    "platform, or recommendation fit in the current package."
                )
            ]

        return [
            (
                f"{compared.get('filename', 'Compared media')} scored "
                f"{compared_score}, below selected media at {selected_score}."
            )
        ]

    def _asset_comparison_summary(self, selected, compared):

        return {
            "selected_media_id": selected.get("media_id"),
            "compared_media_id": compared.get("media_id"),
            "selected_score": self._asset_score(selected),
            "compared_score": self._asset_score(compared),
            "selected_trust": selected.get("trust_state", ""),
            "compared_trust": compared.get("trust_state", "")
        }

    def _package_audit(self, package):

        scoring = package.get("package_scoring", {}) or {}
        return {
            "package_type": package.get("package_type", ""),
            "overall_score": scoring.get("overall_score", 0),
            "story_score": scoring.get("story_score", 0),
            "media_score": scoring.get("media_score", 0),
            "platform_fit": scoring.get("platform_fit", 0),
            "review_score": scoring.get("review_score", 0),
            "writing_strategy_present": bool(package.get("writing_strategy")),
            "publishing_strategy_present": bool(package.get("publishing_strategy")),
            "copy_ready": False,
            "note": "This is a package recommendation, not a published post."
        }

    def _why_package_selected(self, package):

        reasons = []
        scoring = package.get("package_scoring", {}) or {}

        if scoring.get("overall_score"):
            reasons.append(
                f"Overall package score is {scoring.get('overall_score')}."
            )

        if package.get("trust_label"):
            reasons.append(
                "Trust level: " + package.get("trust_label", "")
            )

        if package.get("publishing_strategy", {}).get("decision_note"):
            reasons.append(
                package.get("publishing_strategy", {}).get("decision_note", "")
            )

        return self._clean(reasons)

    def _generated_content_audit(self, package, platforms):

        provider = package.get("writing_provider", {}) or {}

        if not isinstance(provider, dict):
            provider = {
                "provider": str(provider or ""),
                "fallback_used": package.get("writing_fallback_used", False),
                "error": package.get("writing_provider_error", "")
            }

        review = package.get("editorial_review", {}) or {}
        copy_buttons = package.get("copy_buttons", {}) or {}
        positives = []
        negatives = []
        limitations = []

        if provider.get("provider"):
            positives.append(
                "Writing provider: " + provider.get("provider", "")
            )

        if provider.get("fallback_used"):
            negatives.append(
                "Deterministic fallback was used after provider failure or unavailability."
            )

        if review.get("overall_score"):
            positives.append(
                f"Editorial review score: {review.get('overall_score')}."
            )

        for platform in platforms:
            text = copy_buttons.get(platform, "")
            hashtag_count = text.count("#")

            if hashtag_count > 5:
                negatives.append(
                    f"{platform} has more than five hashtags."
                )
            elif text:
                positives.append(
                    f"{platform} public copy is available and bounded."
                )

        if not copy_buttons:
            limitations.append("No platform copy buttons were generated.")

        return {
            "platforms": platforms,
            "provider": provider,
            "editorial_review": review,
            "positive_factors": self._clean(positives)[:self.MAX_FACTORS],
            "negative_factors": self._clean(negatives)[:self.MAX_FACTORS],
            "limitations": self._clean(limitations)[:self.MAX_FACTORS],
            "public_copy_keys": sorted(copy_buttons.keys()),
            "internal_metadata_is_separate": True
        }

    def _memory_search(self, term):

        term = str(term or "").strip()

        if not term:
            return []

        try:
            matches = self.memory.search(
                term,
                limit=self.MAX_COMMUNICATIONS
            )
        except Exception:
            return []

        evidence = []

        for item in matches[:self.MAX_COMMUNICATIONS]:
            evidence.append({
                "platform": item.get("platform", ""),
                "post_date": item.get("post_date", ""),
                "headline": item.get("headline", ""),
                "campaign": item.get("campaign", ""),
                "opportunity_type": item.get("opportunity_type", "")
            })

        return evidence

    def _trust_label(self, recommendation, assets):

        if recommendation.get("trust_label"):
            return recommendation.get("trust_label", "")

        breakdown = self._trust_breakdown(assets)

        if breakdown["approved_real"] or breakdown["corrected_real"]:
            return "Reviewed real intelligence"

        if breakdown["mock"]:
            return "Mock/test intelligence"

        if breakdown["unreviewed_real"]:
            return "Unreviewed real intelligence"

        return "Unknown trust state"

    def _factor_text(self, factors):

        lines = []

        for factor in factors or []:
            if isinstance(factor, dict):
                lines.append(
                    (
                        f"{factor.get('label', 'Factor')}: "
                        f"{factor.get('score', '')} - "
                        f"{factor.get('reason', '')}"
                    )
                )
            else:
                lines.append(str(factor))

        return self._clean(lines)

    def _asset_text(self, assets):

        lines = []

        for asset in assets or []:
            lines.append(
                (
                    f"{asset.get('filename', 'Media')} "
                    f"({asset.get('media_type', '')}) - "
                    f"communications {asset.get('communications_score', 0)}, "
                    f"trust {asset.get('trust_state', '')}"
                )
            )

        return self._clean(lines)

    def _change_text(self, changed):

        if not changed:
            return []

        return list(changed.get("changes") or [])

    def _audit_text(self, explanation):

        audit = (
            explanation.get("package_audit") or
            explanation.get("generated_content_audit") or
            explanation.get("score_reconciliation") or
            {}
        )

        if not audit:
            return []

        return [
            f"{key}: {value}"
            for key, value in audit.items()
            if value not in (None, "", [], {})
        ]

    def _unique_ids(self, values):

        seen = set()
        result = []

        for value in values:
            media_id = self._int(value)

            if media_id and media_id not in seen:
                seen.add(media_id)
                result.append(media_id)

        return result

    def _list(self, value):

        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, tuple):
            return list(value)

        return [
            item.strip()
            for item in str(value).split(",")
            if item.strip()
        ]

    def _clean(self, values):

        result = []

        for value in values or []:
            if value is None:
                continue

            text = str(value).strip()

            if text and text not in result:
                result.append(text)

        return result

    def _score(self, value):

        try:
            return round(float(value), 2)
        except Exception:
            return 0

    def _int(self, value):

        try:
            return int(value)
        except Exception:
            return 0

    def _decision_id(self, recommendation, prefix):

        return (
            recommendation.get("recommendation_id") or
            f"{prefix}-{self._slug(recommendation.get('title', 'unknown'))}"
        )

    def _slug(self, value):

        text = str(value or "unknown").lower()
        allowed = []

        for char in text:
            if char.isalnum():
                allowed.append(char)
            elif char in (" ", "-", "_"):
                allowed.append("-")

        slug = "".join(allowed).strip("-")

        while "--" in slug:
            slug = slug.replace("--", "-")

        return slug[:80] or "unknown"
