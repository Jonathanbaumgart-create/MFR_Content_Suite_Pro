from services.time_service import TimeService
from services.editorial_writing_service import EditorialWritingService


class EditorialFactSheetService:

    BANNED_PUBLIC_PHRASES = (
        "attached media",
        "selected media",
        "visual anchor",
        "confidence",
        "historical evidence",
        "pattern confidence",
        "similar seasonal reminders",
        "keeps the message familiar",
        "communications gap",
        "repetition risk",
        "provider",
        "model",
        "review state",
        "workflow status",
        "event collection",
        "package",
        "strategy family",
        "practical readiness",
        "timely update",
        "meaningful moment",
        "real local visual",
        "one task at a time",
        "highlights our commitment",
        "demonstrates dedication",
        "prepared for all situations",
        "prepared for anything",
        "ready for whatever comes",
        "whatever comes next",
        "department prepares",
        "prepared when called",
        "helps ensure readiness",
        "preparedness is important",
        "training prepares us",
        "our members trained",
        "great night of training",
        "another successful training",
        "#MordenFireRescue"
    )

    def __init__(self, memory_service=None):

        self.memory = memory_service
        self.writer = EditorialWritingService()

    ############################################################

    def voice_profile(self, memory=None):

        return self.writer.voice_profile(memory)

    def build_fact_sheet(self, option, media_package=None, context_snapshot=None):

        option = dict(option or {})
        media_package = media_package or {}
        event = option.get("event_collection") or {}
        title = option.get("title") or event.get("title", "")
        text = self._text(option, event)
        event_type = self._event_type(text)
        actual_activity = self._activity(event_type, title, text)
        what = self._what_happened(event_type, title)
        why = self._why_it_matters(event_type)
        timing = self._timing(event, context_snapshot)
        participants = self._participants(event_type, text)
        community = self._community_connection(event_type)
        uncertainty = []
        verified_media = self._verified_media(media_package)
        verified_media_ids = [
            item.get("media_id") or item.get("id")
            for item in verified_media
            if item.get("media_id") or item.get("id")
        ]
        photo_ids = [
            item.get("media_id") or item.get("id")
            for item in verified_media
            if item.get("media_type") in ("image", "photo")
        ]
        video_ids = [
            item.get("media_id") or item.get("id")
            for item in verified_media
            if item.get("media_type") == "video"
        ]

        if self._generic_title(title):
            uncertainty.append("Event title is not specific enough.")

        if not actual_activity:
            uncertainty.append("Actual activity is unclear.")

        if not verified_media_ids:
            uncertainty.append("No verified media available for this topic.")

        has_facts = bool(
            title
            and not self._generic_title(title)
            and actual_activity
            and what
            and why
            and verified_media_ids
        )

        return {
            "event": event,
            "event_title": title,
            "verified_event_ids": self._verified_event_ids(option, event),
            "verified_media": verified_media,
            "verified_media_ids": verified_media_ids,
            "photo_ids": photo_ids,
            "video_ids": video_ids,
            "helmet_camera_ids": [
                item.get("media_id") or item.get("id")
                for item in verified_media
                if "helmet" in self._media_text(item)
            ],
            "actual_activity": actual_activity,
            "date_or_timing": timing,
            "program_campaign": event.get("program_campaign", ""),
            "visible_participants": participants,
            "what_occurred": what,
            "why_it_matters": why,
            "community_connection": community,
            "equipment_apparatus": event.get("apparatus_equipment", []),
            "content_type": event_type,
            "story_family": event_type,
            "current_context": context_snapshot or {},
            "local_context": "Morden, Manitoba",
            "recommended_hook": "",
            "recommended_platforms": option.get("recommended_platforms") or ["Facebook", "Instagram"],
            "recommended_tone": self._tone(option),
            "emoji_recommendations": [],
            "hashtag_recommendations": [],
            "story_suitability": bool(photo_ids),
            "reel_suitability": bool(video_ids),
            "platform_notes": self._platform_notes(photo_ids, video_ids),
            "historical_communications_memory": option.get("historical_mfr_evidence") or {},
            "confidence": int(option.get("confidence", 0) or 0),
            "requires_verified_media": True,
            "package_status": "ready_for_writing" if verified_media_ids else "blocked_no_verified_media",
            "media_integrity": {
                "verified_media_count": len(verified_media_ids),
                "photo_count": len(photo_ids),
                "video_count": len(video_ids),
                "missing_media": not bool(verified_media_ids),
                "rejection_reason": "" if verified_media_ids else "No verified media available for this topic."
            },
            "factual_uncertainty": uncertainty,
            "prohibited_assumptions": [
                "Do not name people unless stored knowledge explicitly provides names.",
                "Do not invent dates, outcomes, locations, injuries, or incident details."
            ],
            "has_enough_facts": has_facts,
            "clarification_prompt": (
                "More event context is needed. Add a short event summary before publishing."
                if not has_facts
                else ""
            )
        }

    def _verified_media(self, media_package):

        media_package = media_package or {}
        values = []
        for key in (
            "primary_photo",
            "primary_video",
            "primary_image",
            "gallery_photos",
            "gallery_videos",
            "alternates",
            "carousel_order",
            "reel_options"
        ):
            item = media_package.get(key)
            if isinstance(item, dict):
                values.append(item)
            elif isinstance(item, list):
                values.extend(value for value in item if isinstance(value, dict))

        result = []
        seen = set()
        for item in values:
            media_id = item.get("media_id") or item.get("id")
            if not media_id or media_id in seen:
                continue
            if item.get("trust_state") in ("rejected_real", "failed", "mock"):
                continue
            seen.add(media_id)
            result.append(item)
        return result

    def _verified_event_ids(self, option, event):

        values = [
            option.get("event_id"),
            event.get("event_id"),
            event.get("id")
        ]
        return [value for value in values if value]

    def _media_text(self, item):

        return " ".join(
            str(value or "").lower()
            for value in (
                item.get("filename"),
                item.get("path"),
                item.get("description"),
                item.get("primary_activity"),
                item.get("search_text")
            )
        )

    def _platform_notes(self, photo_ids, video_ids):

        notes = {
            "Facebook": "Use the strongest verified media as the story anchor.",
            "Instagram": "Use verified visual media only."
        }
        if video_ids:
            notes["Reels"] = "Video media is available for reel consideration."
        if not photo_ids and not video_ids:
            notes["blocked"] = "No verified media available."
        return notes

    def generate_captions(self, fact_sheet, option=None, memory=None):

        fact_sheet = dict(fact_sheet or {})
        option = dict(option or {})

        result = self.writer.generate_from_fact_sheet(
            fact_sheet,
            option=option,
            memory=memory,
            tone=self._tone(option)
        )
        return {
            "facebook": result["facebook"],
            "instagram": result["instagram"],
            "hashtags": result.get("instagram_hashtags") or result.get("hashtags") or [],
            "facebook_hashtags": result.get("facebook_hashtags", []),
            "instagram_hashtags": result.get("instagram_hashtags", []),
            "quality": result.get("quality", {}),
            "scroll_stop_score": result.get("scroll_stop_score", {}),
            "selected_formula": result.get("selected_formula", ""),
            "selected_teaching_point": result.get("selected_teaching_point", ""),
            "hook_type": result.get("hook_type", ""),
            "recommended_tone": result.get("recommended_tone", ""),
            "variants": result.get("variants", []),
            "instagram_story_caption": result.get("instagram_story_caption", ""),
            "story_cta": result.get("story_cta", ""),
            "reel_hook": result.get("reel_hook", "")
        }

    def _tone(self, option):

        text = " ".join(
            str(value or "")
            for value in (
                option.get("strategy"),
                option.get("content_family"),
                option.get("opportunity_type"),
                option.get("title")
            )
        ).lower()
        if "light" in text or "daycare" in text or "spray" in text:
            return "light"
        if "education" in text or "safety" in text:
            return "educational"
        if "action" in text:
            return "action"
        if "recognition" in text or "promotion" in text:
            return "recognition"
        return "standard"

    def quality_gate(self, facebook, instagram, fact_sheet):

        combined = (facebook or "") + "\n" + (instagram or "")
        lower = combined.lower()
        findings = [
            phrase
            for phrase in self.BANNED_PUBLIC_PHRASES
            if phrase.lower() in lower
        ]
        generic = [
            phrase
            for phrase in (
                "practical readiness",
                "timely update",
                "meaningful moment",
                "one task at a time",
                "highlights our commitment",
                "demonstrates dedication",
                "prepared for all situations",
                "prepared for anything",
                "ready for whatever comes",
                "whatever comes next",
                "department prepares",
                "prepared when called",
                "helps ensure readiness",
                "preparedness is important",
                "training prepares us",
                "our members trained",
                "great night of training",
                "another successful training"
            )
            if phrase in lower
        ]
        same = self._normalize_public(facebook) == self._normalize_public(instagram)
        specificity = self._specificity_score(facebook, instagram, fact_sheet)
        passed = (
            specificity >= 70
            and not findings
            and not generic
            and not same
            and fact_sheet.get("has_enough_facts", False)
        )

        return {
            "passed": passed,
            "specificity_score": specificity,
            "generic_language_findings": generic,
            "internal_language_findings": findings,
            "facebook_instagram_distinct": not same,
            "missing_context": not fact_sheet.get("has_enough_facts", False),
            "blocking_issues": findings + generic + ([] if not same else ["Facebook and Instagram are too similar."])
        }

    ############################################################

    def _daycare_facebook(self, facts):

        return (
            "A little summer heat called for a lot of water.\n\n"
            "MFR members stopped by a local daycare for a spray-down, giving the kids a chance to cool off and spend time with the firefighters who serve their community.\n\n"
            "Safe to say, the hose line was a hit."
        )

    def _daycare_instagram(self, facts):

        return (
            "Best way to beat the heat? A firefighter-sized spray-down. 💦\n\n"
            "A fun visit with some of the youngest members of our community, and plenty of smiles along the way."
        )

    def _helmet_promotion_facebook(self, facts):

        return (
            "A new helmet can represent much more than new equipment.\n\n"
            "It marks responsibility, training, trust, and another step forward in service to the community.\n\n"
            "Congratulations on reaching this milestone."
        )

    def _helmet_promotion_instagram(self, facts):

        return (
            "A helmet promotion is more than a new piece of gear. 🚒\n\n"
            "It represents training, responsibility, and another step forward in serving Morden."
        )

    def _heat_facebook(self):

        return (
            "Heat can become dangerous quickly, especially for children, seniors, outdoor workers, and anyone without a cool place to rest.\n\n"
            "Drink water often, take breaks in the shade or air conditioning, check on neighbours and family members, and never leave people or pets in a parked vehicle.\n\n"
            "Small choices can prevent a medical emergency."
        )

    def _heat_instagram(self):

        return (
            "Heat safety matters. ☀️\n\n"
            "Hydrate, slow down during the hottest part of the day, check on each other, and never leave anyone in a parked vehicle."
        )

    def _training_facebook(self, facts):

        title = facts.get("event_title", "Training")
        activity = facts.get("actual_activity", "training")
        return (
            f"{title} is part of how skills stay sharp before they are needed on a call.\n\n"
            f"The focus was {activity.lower()}, with members working through the steps, communication, and teamwork that support safe operations.\n\n"
            "Training days like this help keep the department ready for Morden."
        )

    def _training_instagram(self, facts):

        title = facts.get("event_title", "Training")
        return (
            f"A look at {title.lower()} in action. 🚒\n\n"
            "Skills are built through repetition, communication, and teamwork before the next call comes in."
        )

    def _behind_facebook(self, facts):

        title = facts.get("event_title", "Behind the scenes")
        return (
            f"{title} gives a look at the people and preparation behind the scenes at MFR.\n\n"
            "Not every part of fire service happens at an emergency. Some of the most important work happens in the small moments that keep the team connected and ready."
        )

    def _behind_instagram(self, facts):

        title = facts.get("event_title", "Behind the scenes")
        return (
            f"A quick behind-the-scenes look at {title.lower()}. 👋\n\n"
            "Preparation, teamwork, and a bit of department personality."
        )

    def _community_facebook(self, facts):

        title = facts.get("event_title", "MFR community visit")
        return (
            f"{title} brought MFR together with the community in a practical, friendly way.\n\n"
            f"{facts.get('what_occurred')} {facts.get('why_it_matters')}"
        )

    def _community_instagram(self, facts):

        title = facts.get("event_title", "community visit")
        return (
            f"Community connection in action. 🚒\n\n"
            f"A local look at {title.lower()}."
        )

    ############################################################

    def _event_type(self, text):

        if "daycare" in text and ("spray" in text or "water" in text):
            return "daycare_spray_down"
        if "helmet promotion" in text or ("helmet" in text and "promotion" in text):
            return "helmet_promotion"
        if "heat" in text or "summer safety" in text:
            return "heat_safety"
        if "behind" in text or "station" in text:
            return "behind_the_scenes"
        if "training" in text or "drill" in text or "rescue" in text:
            return "training"
        if "community" in text or "public education" in text or "school" in text:
            return "community_event"
        return "general"

    def _activity(self, event_type, title, text):

        if event_type == "daycare_spray_down":
            return "local daycare spray-down and summer community visit"
        if event_type == "helmet_promotion":
            return "helmet promotion or recognition milestone"
        if event_type == "heat_safety":
            return "heat safety reminder"
        if event_type == "training":
            return title or "fire-service training"
        if event_type == "behind_the_scenes":
            return "behind-the-scenes department moment"
        if event_type == "community_event":
            return title or "community event"
        return title

    def _what_happened(self, event_type, title):

        values = {
            "daycare_spray_down": "MFR members visited a local daycare for a spray-down.",
            "helmet_promotion": "A helmet promotion or recognition milestone was marked.",
            "heat_safety": "MFR is sharing a heat safety reminder.",
            "training": f"Members took part in {str(title or 'training').lower()}.",
            "behind_the_scenes": "The media shows a behind-the-scenes department moment.",
            "community_event": f"MFR connected with the community through {str(title or 'a local event').lower()}."
        }
        return values.get(event_type, f"MFR documented {str(title or 'a local department activity').lower()}.")

    def _why_it_matters(self, event_type):

        values = {
            "daycare_spray_down": "It builds positive relationships with children and families in a light, memorable way.",
            "helmet_promotion": "It recognizes responsibility, training, and service to the community.",
            "heat_safety": "Heat can create real medical risk, and simple steps can prevent emergencies.",
            "training": "Regular training helps members work safely and effectively when the community needs them.",
            "behind_the_scenes": "It helps residents see the people and preparation behind the department.",
            "community_event": "Community contact builds familiarity and trust before emergencies happen."
        }
        return values.get(event_type, "It helps residents understand the work and people behind MFR.")

    def _participants(self, event_type, text):

        if event_type == "daycare_spray_down":
            return "firefighters and children, described without identifying individuals"
        if event_type == "helmet_promotion":
            return "department members, described without naming anyone unless confirmed"
        return "MFR members and community participants where visible"

    def _community_connection(self, event_type):

        if event_type == "daycare_spray_down":
            return "friendly interaction with local children during summer weather"
        if event_type == "helmet_promotion":
            return "recognition of service, trust, and responsibility"
        if event_type == "heat_safety":
            return "practical safety information for Morden residents"
        return "local connection between MFR and the community"

    def _timing(self, event, context_snapshot):

        date_range = event.get("when_it_occurred") or event.get("date_range") or {}
        start = date_range.get("start") if isinstance(date_range, dict) else ""
        if start:
            try:
                return TimeService.format_local(start)
            except Exception:
                return str(start)[:10]

        if context_snapshot:
            return context_snapshot.get("season", "current timing")
        return "current timing"

    def _specificity_score(self, facebook, instagram, facts):

        score = 0
        combined = ((facebook or "") + " " + (instagram or "")).lower()
        for key in ("event_title", "actual_activity", "why_it_matters", "community_connection"):
            value = str(facts.get(key) or "").lower()
            tokens = [token for token in value.replace("-", " ").split() if len(token) > 3]
            if any(token in combined for token in tokens[:6]):
                score += 20
        if len(set(combined.split())) > 28:
            score += 10
        if facts.get("content_type") in combined.replace("-", "_"):
            score += 10
        return min(100, score)

    def _text(self, option, event):

        values = [
            option.get("title", ""),
            option.get("topic", ""),
            option.get("content_family", ""),
            option.get("opportunity_type", ""),
            event.get("title", ""),
            event.get("what_occurred", "")
        ]
        values.extend(event.get("visible_activities") or [])
        values.extend(event.get("communication_angles") or [])
        return " ".join(str(value or "") for value in values).lower()

    def _generic_title(self, value):

        text = str(value or "").strip().lower()
        return text in ("", "unknown", "unnamed event", "activity", "training activity")

    def _clean(self, text):

        cleaned = str(text or "").strip()
        for phrase in self.BANNED_PUBLIC_PHRASES:
            cleaned = cleaned.replace(phrase, "")
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        return cleaned.strip()

    def _normalize_public(self, text):

        text = str(text or "").lower()
        for token in ("#morden", "#communitysafety", "#summerfun", "#recognition", "#fireservice"):
            text = text.replace(token, "")
        return " ".join(text.split())

    def _unique(self, values):

        result = []
        seen = set()
        for value in values:
            key = str(value).lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result
