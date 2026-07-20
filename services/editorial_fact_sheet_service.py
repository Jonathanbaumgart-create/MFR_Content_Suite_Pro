from services.time_service import TimeService


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
        "#MordenFireRescue"
    )

    def __init__(self, memory_service=None):

        self.memory = memory_service

    ############################################################

    def voice_profile(self, memory=None):

        count = 0
        if isinstance(memory, dict):
            count = len(memory.get("matches") or [])

        return {
            "sample_count": count,
            "tone": "plain, community-focused, concise",
            "formality": "friendly but professional",
            "emoji_use": "light",
            "hashtag_policy": "up to five, never #MordenFireRescue",
            "preferences": [
                "concise readable captions",
                "plain language",
                "community connection",
                "avoid generic corporate wording",
                "Facebook and Instagram should differ",
                "light-hearted content is acceptable when safe"
            ]
        }

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

        if self._generic_title(title):
            uncertainty.append("Event title is not specific enough.")

        if not actual_activity:
            uncertainty.append("Actual activity is unclear.")

        has_facts = bool(title and not self._generic_title(title) and actual_activity and what and why)

        return {
            "event_title": title,
            "actual_activity": actual_activity,
            "date_or_timing": timing,
            "program_campaign": event.get("program_campaign", ""),
            "visible_participants": participants,
            "what_occurred": what,
            "why_it_matters": why,
            "community_connection": community,
            "equipment_apparatus": event.get("apparatus_equipment", []),
            "content_type": event_type,
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

    def generate_captions(self, fact_sheet, option=None, memory=None):

        fact_sheet = dict(fact_sheet or {})
        option = dict(option or {})

        if not fact_sheet.get("has_enough_facts"):
            text = "More event context is needed before this can become a public post."
            return {
                "facebook": text,
                "instagram": text,
                "hashtags": ["#Morden", "#CommunitySafety"],
                "quality": self.quality_gate(text, text, fact_sheet)
            }

        event_type = fact_sheet.get("content_type", "")

        if event_type == "daycare_spray_down":
            facebook = self._daycare_facebook(fact_sheet)
            instagram = self._daycare_instagram(fact_sheet)
            hashtags = ["#Morden", "#CommunityConnection", "#SummerFun"]
        elif event_type == "helmet_promotion":
            facebook = self._helmet_promotion_facebook(fact_sheet)
            instagram = self._helmet_promotion_instagram(fact_sheet)
            hashtags = ["#Morden", "#FireService", "#Recognition"]
        elif event_type == "heat_safety":
            facebook = self._heat_facebook()
            instagram = self._heat_instagram()
            hashtags = ["#Morden", "#HeatSafety", "#CommunitySafety"]
        elif event_type == "training":
            facebook = self._training_facebook(fact_sheet)
            instagram = self._training_instagram(fact_sheet)
            hashtags = ["#Morden", "#FirefighterTraining", "#CommunitySafety"]
        elif event_type == "behind_the_scenes":
            facebook = self._behind_facebook(fact_sheet)
            instagram = self._behind_instagram(fact_sheet)
            hashtags = ["#Morden", "#BehindTheScenes", "#Community"]
        else:
            facebook = self._community_facebook(fact_sheet)
            instagram = self._community_instagram(fact_sheet)
            hashtags = ["#Morden", "#CommunityConnection", "#CommunitySafety"]

        hashtags = [tag for tag in self._unique(hashtags) if tag != "#MordenFireRescue"][:5]
        facebook = self._clean(facebook)
        instagram = self._clean(instagram + "\n\n" + " ".join(hashtags))
        return {
            "facebook": facebook,
            "instagram": instagram,
            "hashtags": hashtags,
            "quality": self.quality_gate(facebook, instagram, fact_sheet)
        }

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
                "demonstrates dedication"
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
