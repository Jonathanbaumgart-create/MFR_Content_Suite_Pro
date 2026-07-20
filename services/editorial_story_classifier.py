class EditorialStoryClassifier:

    FAMILIES = (
        "incident_operational_response",
        "training_readiness",
        "technical_rescue",
        "public_education",
        "community_event",
        "prevention_safety",
        "recruitment",
        "team_member_culture",
        "behind_the_scenes",
        "this_is_what_we_do",
        "action_first_visual",
        "light_hearted_professional_personality",
        "equipment_apparatus",
        "annual_campaign",
        "program_update",
        "accomplishment_milestone",
        "follow_up_story",
        "timely_weather_seasonal_topic"
    )

    def classify(self, item):

        text = self._text(item)
        risks = self._risks(text, item)
        primary = self._primary_family(text)
        secondary = self._secondary_families(text, primary)
        light = self.light_hearted_suitability(item)

        if light["suitable"] and "light_hearted_professional_personality" not in secondary:
            secondary.append("light_hearted_professional_personality")

        return {
            "primary_family": primary,
            "secondary_families": secondary[:5],
            "likely_audience": self._audience(primary),
            "seriousness": self._seriousness(primary, risks),
            "emotional_tone": self._tone(primary, light),
            "editorial_value": self._editorial_value(primary, item),
            "best_platform": self._best_platform(primary, item),
            "recommended_format": self._format(primary, item),
            "story_hook": self._hook(primary),
            "possible_cta": self._cta(primary),
            "reasons": self._reasons(primary, text),
            "risks": risks,
            "light_hearted": light
        }

    def light_hearted_suitability(self, item):

        text = self._text(item)
        unsafe = [
            "patient",
            "victim",
            "fatal",
            "medical",
            "injury",
            "distressed",
            "graphic",
            "private property",
            "unsafe",
            "radio traffic"
        ]

        if any(token in text for token in unsafe):
            return {
                "suitable": False,
                "reason": "Sensitive or serious context blocks light-hearted framing.",
                "risk_level": "high",
                "recommended_tone": "Professional",
                "review_requirement": "manual_review_required"
            }

        positive = any(
            token in text
            for token in (
                "team",
                "behind",
                "station",
                "training",
                "cleanup",
                "preparation",
                "helmet",
                "candid",
                "community",
                "celebration"
            )
        )
        return {
            "suitable": bool(positive),
            "reason": (
                "Benign team, preparation, or behind-the-scenes evidence exists."
                if positive
                else "No clear personality evidence found."
            ),
            "risk_level": "low" if positive else "normal",
            "recommended_tone": "Light-hearted" if positive else "Community-focused",
            "review_requirement": "package_review"
        }

    ############################################################

    def _primary_family(self, text):

        checks = [
            (("daycare", "spray down", "spray-down", "children"), "community_event"),
            (("helmet promotion", "promotion", "milestone", "recognition"), "accomplishment_milestone"),
            (("technical rescue", "rope", "low angle", "extrication"), "technical_rescue"),
            (("training", "readiness", "drill"), "training_readiness"),
            (("recruit", "volunteer", "join"), "recruitment"),
            (("helmet", "action", "hose", "ladder", "tool"), "action_first_visual"),
            (("community", "public education", "school", "event"), "community_event"),
            (("heat", "winter", "water", "smoke", "prevention", "safety"), "prevention_safety"),
            (("apparatus", "engine", "rescue", "pumper", "truck"), "equipment_apparatus"),
            (("behind", "station", "prep", "cleanup"), "behind_the_scenes")
        ]

        for tokens, family in checks:
            if any(token in text for token in tokens):
                return family

        return "this_is_what_we_do"

    def _secondary_families(self, text, primary):

        values = []

        if "team" in text or "member" in text:
            values.append("team_member_culture")
        if "behind" in text or "prep" in text:
            values.append("behind_the_scenes")
        if "safety" in text or "education" in text:
            values.append("public_education")
        if "action" in text or "helmet" in text:
            values.append("action_first_visual")
        if "campaign" in text or "week" in text:
            values.append("annual_campaign")

        return [value for value in values if value != primary]

    def _risks(self, text, item):

        risks = []
        if any(token in text for token in ("patient", "victim", "medical", "injury")):
            risks.append("sensitivity_or_privacy_review_required")
        if "mock" in str(item.get("provider", "")).lower():
            risks.append("mock_analysis_excluded")
        if item.get("failure_reason"):
            risks.append("provider_failure")
        return risks

    def _audience(self, family):

        if family == "recruitment":
            return "Potential volunteers and community supporters"
        if family in ("training_readiness", "technical_rescue", "action_first_visual"):
            return "Morden residents interested in how firefighters prepare"
        if family == "community_event":
            return "Families, residents, and community partners"
        return "Morden residents"

    def _seriousness(self, family, risks):

        if risks or family in ("incident_operational_response", "prevention_safety"):
            return "serious"
        if family == "light_hearted_professional_personality":
            return "light"
        return "balanced"

    def _tone(self, family, light):

        if light.get("suitable") and family in ("behind_the_scenes", "team_member_culture"):
            return "Light-hearted but professional"
        if family == "recruitment":
            return "Encouraging"
        if family in ("training_readiness", "technical_rescue", "action_first_visual"):
            return "Action-focused"
        return "Community-focused"

    def _editorial_value(self, family, item):

        base = 60
        if item.get("communications_score"):
            base = max(base, min(95, int(item.get("communications_score") or 0)))
        if family in ("action_first_visual", "recruitment", "community_event"):
            base += 5
        return min(100, base)

    def _best_platform(self, family, item):

        if item.get("media_type") == "video" or family == "action_first_visual":
            return "Instagram"
        return "Facebook"

    def _format(self, family, item):

        if item.get("media_type") == "video":
            return "Reel/video"
        if family in ("community_event", "training_readiness"):
            return "Photo carousel"
        return "Photo post"

    def _hook(self, family):

        hooks = {
            "recruitment": "Ever wondered what it takes to serve?",
            "training_readiness": "Readiness is built before the call.",
            "action_first_visual": "A firefighter's-eye view of the work.",
            "behind_the_scenes": "A look at the work behind the scenes.",
            "community_event": "Community connection in action.",
            "prevention_safety": "A timely safety reminder for Morden."
        }
        return hooks.get(family, "This is what readiness looks like.")

    def _cta(self, family):

        if family == "recruitment":
            return "Reach out to learn more about volunteering."
        if family == "prevention_safety":
            return "Share this reminder with someone who may need it."
        return "Follow along for more from MFR."

    def _reasons(self, family, text):

        return [
            f"Matched editorial family {family.replace('_', ' ')}.",
            "Classification uses stored intelligence, folder/date context, and visible media metadata."
        ]

    def _text(self, item):

        values = []
        for key in (
            "title",
            "filename",
            "path",
            "primary_activity",
            "incident_type",
            "normalized_scene",
            "search_text",
            "description"
        ):
            values.append(str(item.get(key) or ""))

        for key in (
            "content_tags",
            "content_themes",
            "recommended_uses",
            "equipment_tags",
            "apparatus_tags"
        ):
            values.extend(str(value) for value in (item.get(key) or []))

        return " ".join(values).lower()
