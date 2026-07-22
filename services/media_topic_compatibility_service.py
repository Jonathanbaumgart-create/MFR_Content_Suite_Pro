import re


class MediaTopicCompatibilityService:

    WATER_TERMS = {
        "water rescue",
        "water_rescue",
        "water safety",
        "water_safety",
        "life jacket",
        "lifejacket",
        "boating",
        "lake",
        "shoreline",
        "ice rescue",
        "swift water",
        "drowning",
        "river"
    }
    FIRE_CHIEF_TERMS = {
        "fire chief of the day",
        "fire_chief_of_the_day",
        "chief of the day"
    }
    NEGATIVE_PROGRAMS = {
        "fire chief of the day",
        "fire_chief_of_the_day",
        "hydrant heroes",
        "hydrant_heroes",
        "daycare",
        "spraydown",
        "spray down",
        "public education",
        "public_education"
    }
    RECRUITMENT_TERMS = {
        "recruitment",
        "recruit",
        "volunteer recruitment",
        "volunteer_recruitment",
        "recruit class",
        "recruit_class",
        "training",
        "firefighter training",
        "teamwork",
        "station orientation",
        "application"
    }
    SMOKE_TERMS = {
        "smoke advisory",
        "smoke_advisory",
        "air quality",
        "air_quality",
        "wildfire smoke",
        "wildfire_smoke",
        "haze",
        "visibility"
    }
    SMOKE_ALARM_TERMS = {
        "smoke alarm",
        "smoke alarms",
        "smoke_alarm",
        "smoke detector",
        "smoke_detector",
        "fire prevention",
        "home fire safety",
        "escape planning"
    }
    FIREWORKS_TERMS = {
        "fireworks",
        "firework",
        "fireworks safety",
        "fireworks_safety",
        "canada day fireworks"
    }
    DAYCARE_TERMS = {
        "daycare",
        "spray down",
        "spray_down",
        "spraydown",
        "hose spray",
        "children visit"
    }
    HYDRANT_TERMS = {
        "hydrant heroes",
        "hydrant_heroes",
        "hydrant",
        "clear hydrant",
        "snow hydrant"
    }
    GRASS_FIRE_TERMS = {
        "grass fire",
        "grass_fire",
        "wildland",
        "wildfire",
        "dry grass",
        "burn ban"
    }
    SCHOOL_TERMS = {
        "school visit",
        "school_visit",
        "travelling sparky",
        "public education visit"
    }
    HELMET_PROMOTION_TERMS = {
        "helmet promotion",
        "helmet_promotion",
        "new helmet",
        "milestone",
        "promotion"
    }
    SERIOUS_INCIDENT_TERMS = {
        "serious incident",
        "serious_incident",
        "incident update",
        "incident_update",
        "emergency incident",
        "confirmed incident",
        "structure fire",
        "vehicle fire",
        "mvc",
        "medical",
        "hazmat",
        "emergency response"
    }
    STRONG_EVENT_FIELDS = (
        "public_education_program",
        "campaign",
        "community_event",
        "event",
        "program"
    )

    def evaluate(self, topic, media, activity=None):
        topic_terms = self._terms(topic)
        media_terms = self._media_terms(media, activity=activity)
        reasons = []
        exclusions = []
        trust = str(media.get("trust_state") or "").lower()
        review = str(media.get("review_status") or "").lower()
        provider = str(media.get("provider") or "").lower()
        failure = str(media.get("failure_reason") or "").strip()

        if provider == "mock" or trust == "mock":
            return self._result(False, 0, reasons, ["Mock test analysis cannot support production recommendations."], True)

        if trust in ("rejected_real", "failed") or review in ("rejected", "failed") or failure:
            return self._result(False, 0, reasons, ["Rejected or failed analysis is excluded."], True)

        event_conflict = self._event_conflict(topic_terms, media_terms)
        if event_conflict:
            return self._result(False, 0, reasons, [event_conflict], True)

        tier_a = self._tier_a(topic_terms, media, activity or {}, media_terms)
        tier_b = self._tier_b(topic_terms, media, activity or {}, media_terms)
        tier_c = self._tier_c(media_terms)

        if self._is_water_topic(topic_terms):
            water_a = [
                item for item in tier_a
                if "water" in item.lower() or "ice rescue" in item.lower()
            ]
            water_b = [
                item for item in tier_b
                if (
                    "water" in item.lower()
                    or "life jacket" in item.lower()
                    or "pfd" in item.lower()
                    or "throw bag" in item.lower()
                    or "boat" in item.lower()
                    or "shoreline" in item.lower()
                    or "ice rescue" in item.lower()
                )
            ]
            if water_a:
                reasons.extend(water_a)
            elif len(water_b) >= 2:
                reasons.extend(water_b[:3])
            else:
                exclusions.append("No water rescue, life jacket, boating, shoreline, or ice/water-rescue evidence found.")
                if tier_c:
                    exclusions.append(
                        "Weak visual context cannot qualify water-safety media by itself: " +
                        ", ".join(tier_c[:3]) + "."
                    )
                return self._result(False, 0, reasons, exclusions, False)

        if self._is_recruitment_topic(topic_terms):
            recruitment_a = [
                item for item in tier_a
                if any(term in item.lower() for term in ("recruit", "training", "orientation"))
            ]
            recruitment_b = [
                item for item in tier_b
                if any(term in item.lower() for term in ("recruit", "training", "team", "firefighter"))
            ]
            if recruitment_a:
                reasons.extend(recruitment_a)
            elif len(recruitment_b) >= 2:
                reasons.extend(recruitment_b[:3])
            else:
                exclusions.append(
                    "No recruit class, firefighter training, team, station orientation, or explicit recruitment evidence found."
                )
                if tier_c:
                    exclusions.append(
                        "Weak visual context cannot qualify recruitment media by itself: " +
                        ", ".join(tier_c[:3]) + "."
                    )
                return self._result(False, 0, reasons, exclusions, False)

        if self._is_smoke_topic(topic_terms):
            smoke_a = [
                item for item in tier_a
                if any(term in item.lower() for term in ("smoke", "air quality", "haze", "wildfire"))
            ]
            smoke_b = [
                item for item in tier_b
                if any(term in item.lower() for term in ("smoke", "air quality", "haze", "wildfire", "visibility"))
            ]
            if smoke_a:
                reasons.extend(smoke_a)
            elif len(smoke_b) >= 2:
                reasons.extend(smoke_b[:3])
            else:
                exclusions.append(
                    "No explicit smoke, haze, wildfire smoke, visibility, or air-quality evidence found."
                )
                return self._result(False, 0, reasons, exclusions, False)

        if self._is_serious_incident_topic(topic_terms):
            incident_a = [
                item for item in tier_a
                if any(term in item.lower() for term in (
                    "incident",
                    "structure fire",
                    "vehicle fire",
                    "mvc",
                    "medical",
                    "hazmat",
                    "emergency response"
                ))
            ]
            incident_b = [
                item for item in tier_b
                if any(term in item.lower() for term in (
                    "incident",
                    "structure fire",
                    "vehicle fire",
                    "mvc",
                    "medical",
                    "hazmat",
                    "emergency response",
                    "fire attack",
                    "apparatus"
                ))
            ]
            if incident_a:
                reasons.extend(incident_a[:4])
            elif len(incident_b) >= 2:
                reasons.extend(incident_b[:4])
            else:
                exclusions.append(
                    "No public-safe verified incident, response, or incident-classification evidence found."
                )
                return self._result(False, 0, reasons, exclusions, False)

        explicit_event = self._explicit_event_terms(topic_terms)
        if explicit_event:
            explicit_a = [
                item for item in tier_a
                if any(term.replace("_", " ") in item.lower() for term in explicit_event)
            ]
            explicit_b = [
                item for item in tier_b
                if any(term.replace("_", " ") in item.lower() for term in explicit_event)
            ]
            explicit_terms = explicit_event & media_terms
            if explicit_a:
                reasons.extend(explicit_a[:4])
            elif explicit_terms and (tier_a or len(explicit_b) >= 1):
                reasons.extend(explicit_b[:3])
                reasons.append(
                    "Matched explicit event evidence: " +
                    ", ".join(sorted(explicit_terms)[:5]) + "."
                )
            else:
                exclusions.append(
                    "No explicit verified event evidence found for: " +
                    ", ".join(sorted(explicit_event)[:5]) + "."
                )
                return self._result(False, 0, reasons, exclusions, False)

        matches = sorted(topic_terms & media_terms)
        score = min(100, 25 + len(matches) * 7 + len(tier_a) * 24 + len(tier_b) * 13)

        if matches:
            reasons.append("Matched topic evidence: " + ", ".join(matches[:6]) + ".")

        if tier_a:
            reasons.extend(tier_a[:4])
        elif len(tier_b) >= 2:
            reasons.extend(tier_b[:4])
        elif not reasons:
            exclusions.append("Only generic media evidence matched this story.")
            if tier_c:
                exclusions.append("Tier C evidence is insufficient: " + ", ".join(tier_c[:3]) + ".")
            return self._result(False, 0, reasons, exclusions, False)

        if review in ("approved", "corrected") or trust in ("approved_real", "corrected_real"):
            score += 12
            reasons.append("Human review state is trusted.")
        elif trust == "unreviewed_real" or review == "review_required":
            score -= 20
            reasons.append("Analysis still requires review, so trust is lower.")

        filesystem = media.get("filesystem_intelligence") or {}
        if filesystem.get("filesystem_confidence", 0):
            score += 5
            reasons.append("Filesystem intelligence supports the media context.")

        if not topic_terms:
            score = max(score, 50)
            reasons.append("No specific topic was supplied; using general communications suitability.")

        compatible = score >= 55 and not exclusions
        return self._result(
            compatible,
            max(0, min(100, score)),
            reasons,
            exclusions,
            False
        )

    def _event_conflict(self, topic_terms, media_terms):
        if self.FIRE_CHIEF_TERMS & media_terms:
            allowed = (
                self.FIRE_CHIEF_TERMS |
                {"public education", "public_education", "school visit", "school_visit"}
            )
            if not (allowed & topic_terms):
                return (
                    "Fire Chief of the Day evidence conflicts with the requested topic."
                )

        if self._is_water_topic(topic_terms):
            if self.FIRE_CHIEF_TERMS & media_terms and not (self.WATER_TERMS & media_terms):
                return (
                    "Fire Chief of the Day evidence conflicts with the water-safety topic."
                )

            weak_water_context = {
                "lake",
                "river",
                "water",
                "outdoor"
            }
            explicit_water_safety = (
                (self.WATER_TERMS - weak_water_context) |
                {"pfd", "throw bag", "boat", "shoreline safety"}
            )
            rescue_training = {
                "low angle rescue",
                "low_angle_rescue",
                "rope rescue",
                "rope_rescue",
                "rescue training",
                "rescue_training"
            }
            if rescue_training & media_terms and not (explicit_water_safety & media_terms):
                return (
                    "Rescue-training or incidental water background evidence is not enough for water-safety content."
                )

        if self._is_recruitment_topic(topic_terms):
            negative_programs = self.NEGATIVE_PROGRAMS & media_terms
            explicit_recruitment = self.RECRUITMENT_TERMS & media_terms
            weak_training_only = explicit_recruitment <= {"training"}
            if negative_programs and (not explicit_recruitment or weak_training_only):
                return (
                    "Public education, spray, daycare, Hydrant Heroes, or Fire Chief program evidence conflicts with recruitment."
                )

        if self.FIREWORKS_TERMS & topic_terms and (
            {"wildfire", "wildland", "grass fire", "grass_fire"} & media_terms
        ) and not (self.FIREWORKS_TERMS & media_terms):
            return "Wildfire or grass-fire evidence conflicts with fireworks."

        if self.DAYCARE_TERMS & topic_terms and (
            {"wildfire", "wildland", "grass fire", "grass_fire", "value protection"} & media_terms
        ) and not (self.DAYCARE_TERMS & media_terms):
            return "Wildfire or value-protection evidence conflicts with daycare."

        return ""

    def _is_water_topic(self, topic_terms):
        return bool(self.WATER_TERMS & topic_terms)

    def _is_recruitment_topic(self, topic_terms):
        return bool(self.RECRUITMENT_TERMS & topic_terms)

    def _is_smoke_topic(self, topic_terms):
        return bool(self.SMOKE_TERMS & topic_terms)

    def _is_serious_incident_topic(self, topic_terms):
        return bool(self.SERIOUS_INCIDENT_TERMS & topic_terms)

    def _explicit_event_terms(self, topic_terms):
        for terms in (
            self.FIREWORKS_TERMS,
            self.DAYCARE_TERMS,
            self.SMOKE_ALARM_TERMS,
            self.HYDRANT_TERMS,
            self.GRASS_FIRE_TERMS,
            self.SCHOOL_TERMS,
            self.HELMET_PROMOTION_TERMS,
            self.SERIOUS_INCIDENT_TERMS
        ):
            if terms & topic_terms:
                return terms
        return set()

    def _tier_a(self, topic_terms, media, activity, media_terms):
        evidence = []
        filesystem = media.get("filesystem_intelligence") or {}
        authoritative_values = []

        for key in (
            "relative_path",
            "folder_hierarchy",
            "public_education_program",
            "campaign",
            "community_event",
            "training_type",
            "incident_type",
            "subcategory",
            "source_folders",
            "normalized_tags"
        ):
            authoritative_values.extend(self._flatten(filesystem.get(key)))

        for key in (
            "activity_title",
            "activity_type",
            "title",
            "inferred_type"
        ):
            authoritative_values.extend(self._flatten(activity.get(key)))
            authoritative_values.extend(self._flatten(media.get(key)))

        if media.get("is_human_corrected"):
            for key in (
                "primary_activity",
                "incident_type",
                "operational_context",
                "communications_uses",
                "content_tags",
                "recommended_uses"
            ):
                authoritative_values.extend(self._flatten(media.get(key)))

        for value in authoritative_values:
            value_text = str(value or "").replace("_", " ").lower()
            value_terms = self._terms(value)
            phrase_match = [
                term
                for term in topic_terms
                if str(term).replace("_", " ").lower() in value_text
            ]
            if value_terms & topic_terms or phrase_match:
                evidence.append("Tier A match: " + str(value).replace("_", " ") + ".")

        return self._unique(evidence)

    def _tier_b(self, topic_terms, media, activity, media_terms):
        evidence = []
        reviewed = (
            media.get("trust_state") in ("approved_real", "corrected_real")
            or media.get("review_status") in ("approved", "corrected")
        )

        if not reviewed:
            return evidence

        semantic_values = []
        for key in (
            "description",
            "effective_description",
            "normalized_scene",
            "incident_type",
            "primary_activity",
            "operational_context",
            "operational_skills",
            "communications_uses",
            "content_tags",
            "content_themes",
            "recommended_uses",
            "equipment_tags",
            "apparatus_tags",
            "search_text"
        ):
            semantic_values.extend(self._flatten(media.get(key)))
            semantic_values.extend(self._flatten(activity.get(key)))

        for value in semantic_values:
            value_text = str(value or "").replace("_", " ").lower()
            value_terms = self._terms(value)
            phrase_match = [
                term
                for term in topic_terms
                if str(term).replace("_", " ").lower() in value_text
            ]
            if value_terms & topic_terms or phrase_match:
                evidence.append("Tier B reviewed semantic match: " + str(value).replace("_", " ") + ".")

        return self._unique(evidence)

    def _tier_c(self, media_terms):
        weak = []
        for term in (
            "people",
            "children",
            "child",
            "community",
            "outdoor",
            "water",
            "lake",
            "apparatus",
            "firefighter",
            "truck"
        ):
            if term in media_terms:
                weak.append(term)
        return weak

    def _media_terms(self, media, activity=None):
        values = []
        activity = activity or {}

        for source in (media, activity):
            for key in (
                "title",
                "inferred_type",
                "activity_title",
                "activity_type",
                "description",
                "effective_description",
                "normalized_scene",
                "incident_type",
                "primary_activity",
                "operational_context",
                "operational_skills",
                "communications_uses",
                "content_tags",
                "content_themes",
                "recommended_uses",
                "equipment_tags",
                "apparatus_tags",
                "ppe_tags",
                "search_text",
                "evidence",
                "effective_intelligence_evidence"
            ):
                values.extend(self._flatten(source.get(key)))

        filesystem = media.get("filesystem_intelligence") or {}
        for key in (
            "relative_path",
            "folder_hierarchy",
            "root_category",
            "subcategory",
            "normalized_tags",
            "apparatus_identifier",
            "apparatus_name",
            "incident_type",
            "training_type",
            "public_education_program",
            "campaign",
            "community_event",
            "location_context",
            "source_folders"
        ):
            values.extend(self._flatten(filesystem.get(key)))
        fire = media.get("fire_service_intelligence") or {}
        for key in (
            "personnel",
            "ppe",
            "equipment",
            "apparatus",
            "incident_classification",
            "operational_activity",
            "communications_uses",
            "operational_context",
            "operational_skills",
            "communications_intent",
            "reasoning_evidence"
        ):
            values.extend(self._flatten(fire.get(key)))

        return self._terms(values)

    def _terms(self, value):
        terms = set()

        for item in self._flatten(value):
            text = str(item or "").strip().lower()
            if not text:
                continue

            text = text.replace("-", " ").replace("_", " ")
            terms.add(text)
            compact = re.sub(r"\s+", "_", text)
            terms.add(compact)

            for part in re.split(r"[,;/|]+", text):
                part = part.strip()
                if part:
                    terms.add(part)

        return terms

    def _flatten(self, value):
        if value is None:
            return []

        if isinstance(value, dict):
            values = []
            for item in value.values():
                values.extend(self._flatten(item))
            return values

        if isinstance(value, (list, tuple, set)):
            values = []
            for item in value:
                values.extend(self._flatten(item))
            return values

        return [value]

    def _result(self, compatible, score, reasons, exclusions, hard_reject):
        return {
            "compatible": bool(compatible),
            "score": int(score or 0),
            "reasons": list(reasons or []),
            "exclusions": list(exclusions or []),
            "hard_reject": bool(hard_reject),
            "evidence_tier": self._evidence_tier(reasons)
        }

    def _evidence_tier(self, reasons):
        text = " ".join(reasons or []).lower()
        if "tier a" in text:
            return "A"
        if "tier b" in text:
            return "B"
        return "C_or_none"

    def _unique(self, values):
        seen = set()
        result = []
        for value in values:
            text = str(value or "").strip()
            key = text.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(text)
        return result
