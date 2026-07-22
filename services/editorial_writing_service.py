import re
from collections import Counter


class EditorialWritingService:
    """MFR public-caption writing and quality gate."""

    FAIL_CLOSED_TEXT = "More event context is needed before a publishable caption can be created."

    VOICE_PROFILE = {
        "tone": "direct, informative, local, conversational, competent, grounded",
        "style": "short paragraphs, natural Canadian English, plain language",
        "avoid": [
            "advertising tone",
            "self-congratulation",
            "generic AI copy",
            "empty engagement questions",
            "internal metadata"
        ]
    }

    BANNED_PUBLIC_PHRASES = (
        "attached photo",
        "attached video",
        "attached media",
        "use the attached",
        "visual anchor",
        "after review confirms",
        "this package",
        "media-backed",
        "communication opportunity",
        "content opportunity",
        "timely reminder",
        "here is a timely reminder",
        "practical readiness",
        "operational readiness",
        "commitment to safety",
        "committed to serving",
        "demonstrates our commitment",
        "highlights our commitment",
        "reinforces our commitment",
        "meaningful reminder",
        "message worth bringing back",
        "when the timing is right",
        "today's context",
        "historical reminder",
        "suitable media",
        "content family",
        "story family",
        "provider",
        "confidence score",
        "event trust",
        "semantic review",
        "recommendation engine",
        "publication package",
        "the main takeaway is simple",
        "one clear action is easier to remember",
        "one clear action is easier to remember than a long list",
        "that is why local safety messages work best",
        "one practical action residents can take today",
        "specific, practical, and easy to act on",
        "public safety messages work best",
        "the goal is simple",
        "the message is simple",
        "prepares for all situations",
        "prepared for anything",
        "helps ensure readiness",
        "training prepares us",
        "our members trained",
        "great night of training",
        "#mordenfirerescue"
    )

    PENALIZED_PHRASES = (
        "great night of training",
        "honing our skills",
        "building stronger teams",
        "always training",
        "ready when called",
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
        "another successful training",
        "dedicated members",
        "committed to excellence",
        "another successful",
        "proud to serve",
        "keeping our skills sharp",
        "here is",
        "community safety is",
        "morden fire & rescue conducted"
    )

    TECH_TRANSLATIONS = {
        "low-angle rope rescue": "a rope system used to safely move someone over steep or difficult terrain",
        "rescue litter": "a rigid patient-carrying device used when a regular stretcher cannot safely reach the patient",
        "stabilization": "securing a vehicle or object so it cannot move while rescuers work",
        "scba": "the breathing equipment firefighters wear in smoke or hazardous air",
        "forcible entry": "gaining access when normal doors or openings cannot be used",
        "thermal imaging camera": "a camera that helps firefighters look for heat through smoke, darkness, or hidden spaces"
    }

    EMOJI_BY_FAMILY = {
        "training": ["\U0001faa2", "\U0001f692"],
        "public_education": ["\u2705", "\U0001f3e0"],
        "safety": ["\u26a0\ufe0f", "\u2705"],
        "community_event": ["\U0001f4a6", "\U0001f692"],
        "recognition": ["\U0001f44f", "\U0001f692"],
        "recruitment": ["\U0001f91d", "\U0001f692"],
        "behind_the_scenes": ["\U0001f4f8", "\U0001f692"],
        "apparatus": ["\U0001f692", "\U0001f6e0\ufe0f"],
        "light_hearted": ["\U0001f4a6"],
        "seasonal": ["\u26a0\ufe0f", "\u2705"],
        "incident_follow_up": []
    }

    SERIOUS_TERMS = (
        "fatal",
        "fatality",
        "death",
        "serious injury",
        "investigation",
        "victim",
        "patient privacy",
        "under investigation"
    )

    def voice_profile(self, memory=None):

        profile = dict(self.VOICE_PROFILE)
        profile["memory_sample_count"] = 0
        if isinstance(memory, dict):
            profile["memory_sample_count"] = (
                memory.get("sample_count")
                or len(memory.get("matches") or [])
                or len(memory.get("common_openings") or [])
            )
        profile["hashtag_policy"] = "maximum five, never #MordenFireRescue, #MordenMB last"
        profile["emoji_policy"] = "maximum five, meaningful only"
        return profile

    ############################################################

    def topic_fact_sheet(
        self,
        topic,
        current_relevance="",
        historical=None,
        media=None,
        local_programs=None,
        known_facts=None,
        unknown_facts=None,
        platforms=None
    ):

        topic = str(topic or "").strip()
        text = self._normalize(" ".join([
            topic,
            current_relevance,
            " ".join(str(item) for item in (known_facts or []))
        ]))
        family = self.story_family({"content_type": "", "event_title": topic}, text)
        teaching_points = self.teaching_points(family, text, topic)
        history_has_evidence = bool(
            self._last_publication(historical)
            or (isinstance(historical, dict) and historical.get("matches"))
            or (historical and not isinstance(historical, dict))
        )
        return {
            "fact_sheet_type": "topic",
            "topic": topic,
            "event_title": topic,
            "content_type": family,
            "story_family": family,
            "current_relevance": current_relevance,
            "historical_mfr_evidence": historical or {},
            "local_program_evidence": local_programs or [],
            "available_media": media or [],
            "last_publication_date": self._last_publication(historical),
            "recommended_angle": self._angle_for_family(family, text),
            "teaching_points": teaching_points,
            "teaching_point": teaching_points[0] if teaching_points else "",
            "known_facts": known_facts or self._known_facts_from_topic(topic, text),
            "unknown_facts": unknown_facts or [],
            "prohibited_assumptions": [
                "Do not invent dates, locations, people, injuries, outcomes, or active warnings.",
                "Use Communications Memory as voice evidence only; do not copy old captions."
            ],
            "recommended_platforms": platforms or ["Facebook", "Instagram"],
            "has_enough_facts": bool(
                topic
                and (
                    known_facts
                    or current_relevance
                    or media
                    or local_programs
                    or history_has_evidence
                )
            )
        }

    ############################################################

    def generate_from_fact_sheet(
        self,
        fact_sheet,
        option=None,
        memory=None,
        tone="standard",
        teaching_point=None
    ):

        facts = dict(fact_sheet or {})
        option = dict(option or {})
        family = self.story_family(facts, self._combined_text(facts, option))
        facts["story_family"] = family
        facts.setdefault("content_type", family)
        objective = self.communication_objective(family, facts, option)
        facts["communication_objective"] = objective["primary"]
        facts["secondary_objective"] = objective["secondary"]
        angle = self.narrative_angle(family, facts, option, objective)
        facts["narrative_angle"] = angle
        facts["narrative_focus"] = angle["central_fact"]
        computed_teaching = self.teaching_points(
            family,
            self._combined_text(facts, option),
            facts.get("event_title", "")
        )
        if family == "incident_follow_up":
            facts["teaching_points"] = computed_teaching
        else:
            facts.setdefault("teaching_points", computed_teaching)
        selected_teaching = (
            teaching_point
            or facts.get("teaching_point")
            or self._first(facts.get("teaching_points"))
            or facts.get("narrative_focus")
            or ""
        )
        facts["teaching_point"] = selected_teaching
        has_enough = facts.get("has_enough_facts", False)
        requires_media = bool(facts.get("requires_verified_media"))
        verified_media = list(facts.get("verified_media_ids") or [])

        if requires_media and not verified_media:
            return self.fail_closed(
                facts,
                family,
                message="No verified media available for this topic.",
                reason="missing verified media"
            )

        if not has_enough or not facts.get("narrative_focus"):
            return self.fail_closed(facts, family)

        formula = self.formula_for(family, tone)
        hook_type, hook = self.hook_for(family, facts, selected_teaching, tone)
        facebook_body = self._facebook_body(family, facts, selected_teaching, hook, tone)
        instagram_body = self._instagram_body(family, facts, selected_teaching, hook, tone)
        facebook_tags = self.hashtags(family, facts, "facebook")
        instagram_tags = self.hashtags(family, facts, "instagram")
        facebook = self._caption_with_emoji(
            facebook_body,
            family,
            facts,
            platform="facebook"
        )
        instagram = self._caption_with_emoji(
            instagram_body,
            family,
            facts,
            platform="instagram"
        )
        facebook = self._append_hashtags(facebook, facebook_tags)
        instagram = self._append_hashtags(instagram, instagram_tags)
        quality = self.quality_gate(facebook, instagram, facts, selected_teaching)
        scroll = self.scroll_stop_score(facebook, facts, selected_teaching)

        if not quality["passed"]:
            return {
                **self.fail_closed(facts, family),
                "attempted_facebook": facebook,
                "attempted_instagram": instagram,
                "quality": quality,
                "scroll_stop_score": scroll
            }

        return {
            "facebook": facebook,
            "instagram": instagram,
            "facebook_hashtags": facebook_tags,
            "instagram_hashtags": instagram_tags,
            "hashtags": instagram_tags,
            "story_family": family,
            "selected_formula": formula,
            "communication_objective": objective["primary"],
            "secondary_objective": objective["secondary"],
            "narrative_angle": angle,
            "narrative_focus": facts.get("narrative_focus", ""),
            "selected_teaching_point": selected_teaching,
            "teaching_point": selected_teaching,
            "hook_type": hook_type,
            "hook": hook,
            "recommended_tone": tone,
            "voice_profile": self.voice_profile(memory),
            "quality": quality,
            "scroll_stop_score": scroll,
            "instagram_story_caption": self._story_caption(facts, selected_teaching),
            "story_cta": self._story_cta(family),
            "reel_hook": hook if family in ("training", "behind_the_scenes", "light_hearted") else "",
            "facebook_reel_caption": self._short_reel_caption(facebook),
            "instagram_reel_caption": self._short_reel_caption(instagram),
            "variants": self.variants(facts, option, memory)
        }

    def fail_closed(self, facts=None, family="", message=None, reason=None):

        facts = dict(facts or {})
        facebook = message or self.FAIL_CLOSED_TEXT
        instagram = message or self.FAIL_CLOSED_TEXT
        quality = self.quality_gate(
            facebook,
            instagram,
            facts,
            facts.get("teaching_point", "")
        )
        quality["passed"] = False
        failure_reason = reason or "insufficient verified facts"
        if failure_reason not in quality["failure_reasons"]:
            quality["failure_reasons"].append(failure_reason)
        if failure_reason not in quality["blocking_issues"]:
            quality["blocking_issues"].append(failure_reason)
        return {
            "facebook": facebook,
            "instagram": instagram,
            "facebook_hashtags": [],
            "instagram_hashtags": [],
            "hashtags": [],
            "story_family": family or facts.get("story_family", ""),
            "selected_formula": "",
            "selected_teaching_point": "",
            "teaching_point": "",
            "hook_type": "",
            "hook": "",
            "recommended_tone": "context needed",
            "quality": quality,
            "scroll_stop_score": {
                "total_score": 0,
                "strongest_factor": "",
                "weakest_factor": "insufficient verified facts",
                "suggested_improvement": "Add a short event summary or confirm one teaching point."
            },
            "variants": []
        }

    ############################################################

    def variants(self, facts, option=None, memory=None):

        facts = dict(facts or {})
        supported = []
        for tone in ("educational", "community", "light"):
            if tone == "light" and self.story_family(facts, self._combined_text(facts, option or {})) not in (
                "community_event",
                "behind_the_scenes",
                "light_hearted"
            ):
                continue
            copy = self._variant_copy(facts, tone)
            if copy:
                supported.append(copy)
        return supported

    def communication_objective(self, family, facts, option=None):

        option = dict(option or {})
        text = self._combined_text(facts, option)
        if family == "incident_follow_up" or self._contains_any(text, self.SERIOUS_TERMS):
            return {"primary": "Serious Incident Information", "secondary": "Inform"}
        if self._contains_any(text, ("daycare", "spray down", "spray-down", "hose line")):
            return {"primary": "Build Community Connection", "secondary": "Entertain"}
        if family == "recruitment" or self._contains_any(text, ("recruit", "volunteer", "join")):
            return {"primary": "Recruit", "secondary": "Explain Operations"}
        if family == "recognition" or self._contains_any(text, ("promotion", "milestone", "recognition")):
            return {"primary": "Recognize", "secondary": "Celebrate"}
        if family == "training" or self._contains_any(text, ("rope", "training", "drill", "rescue")):
            return {"primary": "Explain Operations", "secondary": "Educate"}
        if self._contains_any(text, ("fireworks", "canada day")):
            return {"primary": "Promote Event", "secondary": "Inform"}
        if self._contains_any(text, ("smoke alarm", "hydrant", "heat", "water safety", "air quality", "smoke advisory")):
            return {"primary": "Educate", "secondary": "Warn"}
        if family == "behind_the_scenes":
            return {"primary": "Document Department Activity", "secondary": "Build Community Connection"}
        if family == "apparatus":
            return {"primary": "Explain Operations", "secondary": "Inform"}
        if family == "community_event":
            return {"primary": "Build Community Connection", "secondary": "Inform"}
        return {"primary": "Inform", "secondary": "Document Department Activity"}

    def narrative_angle(self, family, facts, option, objective):

        text = self._combined_text(facts, option)
        title = self._plain_title(facts.get("event_title") or facts.get("topic") or option.get("title", ""))
        activity = self._plain_sentence(facts.get("actual_activity") or facts.get("what_occurred") or title)
        if self._contains_any(text, ("daycare", "spray down", "spray-down", "hose line")):
            return {
                "angle_name": "The hose line was the highlight",
                "communication_objective": "Build Community Connection",
                "story_family": "light_hearted",
                "hook_question": "What happens when a daycare visit meets a charged hose line?",
                "central_fact": "children participated in a supervised daycare spray-down",
                "human_interest": "children meeting firefighters in a fun setting",
                "operational_context": "friendly public education visit",
                "community_relevance": "positive interaction with local children",
                "call_to_action": "Thank the visitors and keep the tone light.",
                "tone": "Light-hearted",
                "prohibited_claims": ["Do not invent the daycare name.", "Do not turn the post into a safety lecture."],
                "confidence": 90
            }
        if objective["primary"] == "Recruit":
            return {
                "angle_name": "More than emergency calls",
                "communication_objective": "Recruit",
                "story_family": "recruitment",
                "hook_question": "What does volunteer firefighting actually involve?",
                "central_fact": "volunteers train, check equipment, attend community events, and respond to emergencies",
                "human_interest": "local people serving the community where they live",
                "operational_context": "training, teamwork, equipment checks, and emergency response",
                "community_relevance": "Morden benefits when residents step forward to serve",
                "call_to_action": "Invite interested residents to learn more if a verified instruction is available.",
                "tone": "Direct recruitment",
                "prohibited_claims": ["Do not invent dates, pay, eligibility, or application steps."],
                "confidence": 88
            }
        if "smoke alarm" in text:
            central = "smoke alarms need testing and replacement"
        elif "fireworks" in text:
            central = "fireworks safety depends on distance, supervision, and local rules"
        elif "hydrant" in text:
            central = "hydrants must remain visible and accessible"
        elif "water" in text:
            central = "supervision and life jackets matter near water"
        elif "rope" in text:
            central = "rope systems help move patients when terrain makes a simple carry unsafe"
        else:
            central = activity or "verified local department activity"
        return {
            "angle_name": self._angle_for_family(family, text),
            "communication_objective": objective["primary"],
            "story_family": family,
            "hook_question": self.hook_for(family, facts, central, tone=option.get("tone", "standard"))[1],
            "central_fact": central,
            "human_interest": facts.get("visible_participants", ""),
            "operational_context": facts.get("actual_activity", ""),
            "community_relevance": facts.get("community_connection", "local relevance for Morden"),
            "call_to_action": self._story_cta(family),
            "tone": facts.get("recommended_tone") or option.get("tone") or "standard",
            "prohibited_claims": facts.get("prohibited_assumptions", []),
            "confidence": int(facts.get("confidence", 75) or 75)
        }

    def quality_gate(self, facebook, instagram, facts=None, teaching_point=""):

        facts = dict(facts or {})
        combined = (facebook or "") + "\n" + (instagram or "")
        lower = combined.lower()
        banned = [phrase for phrase in self.BANNED_PUBLIC_PHRASES if phrase in lower]
        penalties = [phrase for phrase in self.PENALIZED_PHRASES if phrase in lower]
        fb_tags = self._hashtags_in(facebook)
        ig_tags = self._hashtags_in(instagram)
        emoji_count = self.emoji_count(combined)
        specificity = self._specificity_score(combined, facts)
        genericity = self._genericity_score(combined, facts)
        hook_score = self._hook_score(facebook)
        objective = facts.get("communication_objective") or ""
        action_objective = objective in ("Educate", "Warn", "Promote Event", "Serious Incident Information")
        narrative_focus = facts.get("narrative_focus") or teaching_point
        teaching_score = 100 if narrative_focus and self._mentions_teaching(combined, narrative_focus) else 65 if narrative_focus and not action_objective else 0
        community_score = 85 if self._contains_any(lower, ("morden", "neighbour", "resident", "community", "local")) else 35
        platform_fit = 85 if self._normalize_caption(facebook) != self._normalize_caption(instagram) else 25
        grounded_count = self._grounded_fact_count(combined, facts)
        missing = []
        if not facts.get("has_enough_facts", facts.get("fact_sheet_type") == "topic"):
            missing.append("verified event or topic facts")
        if facts.get("requires_verified_media") and not facts.get("verified_media_ids"):
            missing.append("verified media")
        if action_objective and not narrative_focus:
            missing.append("narrative focus")
        failures = []
        if banned:
            failures.append("banned public-copy language")
        if emoji_count > 5:
            failures.append("too many emojis")
        if (
            emoji_count == 0
            and facts.get("requires_verified_media")
            and not self._contains_any(lower, self.SERIOUS_TERMS)
        ):
            failures.append("missing platform emoji")
        if not self._hashtag_compliant(fb_tags):
            failures.append("Facebook hashtag rule violation")
        if not self._hashtag_compliant(ig_tags):
            failures.append("Instagram hashtag rule violation")
        if specificity < 45:
            failures.append("not specific enough")
        if genericity > 65:
            failures.append("too generic")
        if platform_fit < 50:
            failures.append("Facebook and Instagram are too similar")
        if grounded_count < 2 and len(facts.get("verified_media_ids") or []) > 0:
            failures.append("not enough grounded event facts")
        if not action_objective and self._contains_any(
            lower,
            ("one action", "practical action", "residents can take", "safety messages work")
        ):
            failures.append("resident-action language in non-action post")
        failures.extend("missing " + item for item in missing)
        score = max(
            0,
            min(
                100,
                int((specificity + hook_score + teaching_score + community_score + platform_fit) / 5 - len(penalties) * 8 - len(banned) * 18)
            )
        )
        return {
            "passed": not failures and score >= 70,
            "score": score,
            "genericity_score": genericity,
            "specificity_score": specificity,
            "hook_score": hook_score,
            "teaching_point_score": teaching_score,
            "community_relevance_score": community_score,
            "platform_fit_score": platform_fit,
            "grounded_fact_count": grounded_count,
            "generic_template_rejected": bool(banned or genericity > 65),
            "communication_objective": objective,
            "story_family": facts.get("story_family", ""),
            "narrative_angle": facts.get("narrative_angle", {}).get("angle_name", ""),
            "narrative_focus": facts.get("narrative_focus", ""),
            "emoji_compliance": emoji_count <= 5,
            "emoji_count": emoji_count,
            "hashtag_compliance": self._hashtag_compliant(fb_tags) and self._hashtag_compliant(ig_tags),
            "facebook_hashtags": fb_tags,
            "instagram_hashtags": ig_tags,
            "banned_phrases": banned,
            "penalized_phrases": penalties,
            "missing_facts": missing,
            "failure_reasons": failures,
            "blocking_issues": failures
        }

    def scroll_stop_score(self, caption, facts=None, teaching_point=""):

        facts = facts or {}
        first = self._first_line(caption).lower()
        text = str(caption or "").lower()
        factors = {
            "curiosity": 12 if "?" in first or first.startswith(("what", "why", "most people", "water rescue", "a blocked")) else 5,
            "clear_problem": 12 if self._contains_any(first, ("what happens", "why", "cannot", "blocked", "dangerous", "risk")) else 4,
            "unexpected_insight": 10 if self._contains_any(text, ("instead of", "does not always", "most people", "normal access")) else 4,
            "local_relevance": 10 if "morden" in text else 3,
            "human_interest": 10 if self._contains_any(text, ("children", "families", "firefighters", "neighbours", "members")) else 4,
            "visual_alignment": 10 if facts.get("available_media") or facts.get("actual_activity") else 5,
            "plain_language": 12 if not self._contains_any(text, ("operational", "utilize", "apparatus-centred")) else 2,
            "first_line": min(12, max(3, len(first.split()))),
            "one_teaching_point": 10 if teaching_point and self._mentions_teaching(text, teaching_point) else 2,
            "community_usefulness": 12 if self._contains_any(text, ("safe", "prevent", "prepare", "check", "learn", "look out")) else 4
        }
        penalties = 0
        if self._contains_any(first, ("here is", "today we", "another great", "community safety is")):
            penalties += 15
        if any(phrase in text for phrase in self.PENALIZED_PHRASES):
            penalties += 10
        score = max(0, min(100, sum(factors.values()) - penalties))
        strongest = max(factors, key=factors.get)
        weakest = min(factors, key=factors.get)
        return {
            "total_score": score,
            "strongest_factor": strongest.replace("_", " "),
            "weakest_factor": weakest.replace("_", " "),
            "suggested_improvement": self._scroll_suggestion(weakest)
        }

    ############################################################

    def story_family(self, facts, text=""):

        explicit = self._normalize(
            facts.get("story_family", "") or facts.get("content_type", "")
        )
        explicit_key = explicit.replace(" ", "_")
        known = {
            "training",
            "public_education",
            "community_event",
            "recognition",
            "recruitment",
            "behind_the_scenes",
            "apparatus",
            "light_hearted",
            "seasonal",
            "incident_follow_up"
        }
        if explicit_key in known:
            return explicit_key
        text = self._normalize(" ".join([
            text,
            facts.get("content_type", ""),
            facts.get("event_title", ""),
            facts.get("actual_activity", ""),
            facts.get("topic", "")
        ]))
        if self._contains_any(text, self.SERIOUS_TERMS):
            return "incident_follow_up"
        if self._contains_any(text, ("spray", "daycare", "school visit", "fire chief of the day")):
            return "light_hearted" if "spray" in text else "community_event"
        if self._contains_any(text, ("helmet promotion", "promotion", "milestone", "recognition")):
            return "recognition"
        if self._contains_any(text, ("rope rescue", "low-angle")):
            return "training"
        if self._contains_any(text, ("recruit", "volunteer", "join")):
            return "recruitment"
        if self._contains_any(text, ("training", "drill", "scba", "ladder evolution")):
            return "training"
        if self._contains_any(text, ("water safety", "smoke alarm", "fire prevention", "hydrant", "fireworks", "heat", "ice safety")):
            return "public_education"
        if self._contains_any(text, ("behind", "apparatus check", "station", "equipment check")):
            return "behind_the_scenes"
        if self._contains_any(text, ("engine", "apparatus", "ladder truck", "rescue truck")):
            return "apparatus"
        if self._contains_any(text, ("seasonal", "hydant heroes", "hydrant heroes", "travelling sparky", "canada day")):
            return "seasonal"
        if self._contains_any(text, ("community", "open house", "parade")):
            return "community_event"
        return "public_education"

    def formula_for(self, family, tone="standard"):

        formulas = {
            "training": "Hook -> Scenario -> Why -> Community Connection -> Close",
            "public_education": "Problem -> Misconception -> Action -> Local relevance",
            "community_event": "Human moment -> What happened -> Community response -> Connection",
            "recognition": "Achievement -> Meaning -> Journey -> Recognition",
            "recruitment": "Hook -> Reality -> Opportunity -> Community impact",
            "behind_the_scenes": "Reveal -> Preparation -> Why it matters",
            "apparatus": "Problem -> Function -> Community outcome",
            "light_hearted": "Unexpected moment -> Simple description -> Human connection -> Light close",
            "seasonal": "Timing -> Fresh angle -> Action -> Local connection",
            "incident_follow_up": "Public need -> Confirmed update -> Action -> Limits"
        }
        return formulas.get(family, formulas["public_education"])

    def teaching_points(self, family, text="", topic=""):

        text = self._normalize(text + " " + topic)
        if self._contains_any(text, ("rope", "embankment", "steep", "water rescue")):
            return [
                "why ropes may be safer than carrying a patient over steep or difficult terrain",
                "why realistic terrain changes the rescue plan"
            ]
        if "stabilization" in text or "extrication" in text:
            return ["why securing a vehicle or object happens before rescuers work close to it"]
        if "thermal" in text:
            return ["why thermal imaging cameras help firefighters look for heat in hard-to-see places"]
        if "hydrant" in text:
            return ["why hydrants must remain visible and accessible"]
        if "smoke alarm" in text:
            return ["why smoke alarms need testing and replacement"]
        if "water safety" in text:
            return ["why supervision and life jackets matter near water"]
        if "fireworks" in text:
            return ["why fireworks safety depends on distance, supervision, and local rules"]
        if "smoke" in text or "air quality" in text:
            return ["why checking the official alert helps residents reduce smoke exposure"]
        if "heat" in text:
            return ["why heat can become dangerous quickly for vulnerable people"]
        if family == "incident_follow_up":
            return ["what residents should know from confirmed public information"]
        if family == "recruitment":
            return ["what volunteer firefighting actually involves beyond emergency calls"]
        if family == "recognition":
            return ["why a promotion reflects training, responsibility, and trust"]
        if family == "light_hearted":
            return ["why friendly moments help children see firefighters as approachable helpers"]
        if family == "behind_the_scenes":
            return ["why preparation before a call affects the help residents receive later"]
        if family == "apparatus":
            return ["what problem the equipment helps solve for the community"]
        return ["the verified local activity and why it matters to the community"]

    def hook_for(self, family, facts, teaching_point, tone="standard"):

        text = self._combined_text(facts, {})
        if family == "training" and "rope" in text:
            return "direct question", "What happens when a patient cannot be safely carried to an ambulance?"
        if family == "training":
            return "behind-the-scenes reveal", "Most people never see the problem-solving that happens during fire-service training."
        if family == "public_education" and "smoke alarm" in text:
            return "misconception correction", "A smoke alarm only helps if it works when you need it."
        if family == "public_education" and "fireworks" in text:
            return "timely warning", "Fireworks can turn risky quickly when distance and supervision are overlooked."
        if family == "public_education" and "water" in text:
            return "outcome-first statement", "Water safety starts before anyone is in trouble."
        if family == "light_hearted":
            return "human moment", "Safe to say, the hose line was a hit."
        if family == "recognition":
            return "outcome-first statement", "A new helmet can represent much more than new equipment."
        if family == "recruitment":
            return "direct question", "Have you ever wondered where you might fit in during an emergency?"
        if family == "behind_the_scenes":
            return "behind-the-scenes reveal", "Most people never see what happens before the trucks leave the hall."
        if family == "apparatus":
            return "problem-first", "The right equipment matters most when access, time, or terrain creates a problem."
        if family == "incident_follow_up":
            return "public need", "Residents should rely on confirmed information only."
        return "local relevance", self._plain_title(facts.get("event_title") or facts.get("topic") or "A local safety note")

    ############################################################

    def _facebook_body(self, family, facts, teaching_point, hook, tone):

        title = self._plain_title(facts.get("event_title") or facts.get("topic") or "")
        activity = self._plain_sentence(facts.get("actual_activity") or facts.get("what_occurred") or title)
        community = facts.get("community_connection") or "It helps residents understand the work and people behind MFR."
        text = self._combined_text(facts, {})
        if self._contains_any(text, ("daycare", "spray down", "spray-down", "hose line")):
            return "\n\n".join([
                "Safe to say, the hose line was a hit.",
                "MFR members stopped by a local daycare for a supervised spray-down, giving children a chance to cool off and meet firefighters in a fun setting.",
                "Visits like this help children see firefighters as approachable helpers before an emergency ever happens.",
                "Thanks for spending part of the day with us."
            ])
        if family == "training" and "rope" in self._combined_text(facts, {}):
            return "\n\n".join([
                hook,
                "During recent training, MFR firefighters worked through a scenario where a patient needed to be moved over steep or difficult terrain. When normal access is too far away, a low-angle rope system can help move the patient to a place where care can continue.",
                "Why use ropes instead of simply carrying the patient? Poor footing, weather, distance, and limited access can make a manual carry unsafe for both the patient and rescuers.",
                "Training in realistic environments helps firefighters prepare for problems that do not come with an easy route out.",
                "Here For You."
            ])
        if family == "training":
            return "\n\n".join([
                hook,
                f"During {title.lower()}, MFR members worked through {activity.lower()}.",
                f"The focus was {self._translate(facts.get('narrative_focus') or teaching_point)}.",
                "It is a practical look at the decisions, communication, and teamwork firefighters practise before those skills are needed.",
                "For Morden, that means the preparation behind the scenes stays connected to real service when calls come in."
            ])
        if family == "light_hearted":
            return "\n\n".join([
                hook,
                "MFR members stopped by a local daycare for a spray-down, giving children a chance to cool off and spend time with the firefighters who serve their community.",
                "It was simple, memorable, and full of smiles.",
                "A little water can go a long way on a hot day."
            ])
        if family == "recognition":
            return "\n\n".join([
                hook,
                "It marks training, responsibility, and the trust that comes with taking another step in fire service.",
                "Milestones like this are earned over time through learning, showing up, and serving the community.",
                "Congratulations on reaching this step."
            ])
        if family == "recruitment":
            return "\n\n".join([
                "Volunteer firefighting involves a lot more than answering emergency calls.",
                "Members train, check equipment, support public education, attend community events, and respond when the pager sounds.",
                "It takes time, teamwork, and a willingness to keep learning, but it is also a direct way to serve the community you call home.",
                "Interested in learning more about joining Morden Fire & Rescue? Reach out to the department for current recruitment information."
            ])
        if family == "behind_the_scenes":
            return "\n\n".join([
                hook,
                "Equipment checks, truck checks, training, and station work are not the loudest parts of fire service, but they matter.",
                "The work done before a call helps make the response safer and more organized when someone needs help.",
                "It is one more look at the preparation behind the service."
            ])
        if family == "apparatus":
            return "\n\n".join([
                hook,
                f"In plain language, {self._translate(teaching_point)}.",
                "The equipment is not the story by itself. The story is what it helps firefighters do when access, time, or safety becomes difficult.",
                "That capability matters for Morden and the surrounding area."
            ])
        if family == "incident_follow_up":
            return "\n\n".join([
                hook,
                f"The public takeaway should stay limited to confirmed information: {activity}.",
                "Only confirmed public information should be shared here. Details that are not confirmed, sensitive, or under investigation should stay out of the caption.",
                "Follow official updates if more information becomes available."
            ])
        return self._education_facebook(facts, teaching_point, hook, family)

    def _instagram_body(self, family, facts, teaching_point, hook, tone):

        title = self._plain_title(facts.get("event_title") or facts.get("topic") or "")
        text = self._combined_text(facts, {})
        if self._contains_any(text, ("daycare", "spray down", "spray-down", "hose line")):
            return "\n\n".join([
                "Best way to beat the heat? A firefighter-sized spray-down.",
                "A supervised spray-down, a visit with firefighters, and plenty of smiles.",
                "Thanks for stopping by."
            ])
        if family == "training" and "rope" in self._combined_text(facts, {}):
            return "\n\n".join([
                hook,
                "Steep terrain can change the whole rescue plan.",
                "Rope systems give firefighters another way to move someone safely when a simple carry is not the safest option.",
                "Realistic training matters."
            ])
        if family == "light_hearted":
            return "\n\n".join([
                "Best way to beat the heat? A firefighter-sized spray-down.",
                "A fun visit with some of the youngest members of our community, and plenty of smiles along the way."
            ])
        if family == "recognition":
            return "\n\n".join([
                "A helmet promotion is more than a new piece of gear.",
                "It represents training, responsibility, and another step forward in serving Morden."
            ])
        if family == "recruitment":
            return "\n\n".join([
                "The emergency call is only one part of the role.",
                "Training, equipment checks, community events, and teamwork all come with serving Morden.",
                "Curious about joining? Reach out for current recruitment information."
            ])
        if family == "behind_the_scenes":
            return "\n\n".join([
                hook,
                "A look at the preparation that happens before the next call."
            ])
        if family == "incident_follow_up":
            return "\n\n".join([
                "Confirmed public information only.",
                "We will share what residents need to know without speculating or adding sensitive details."
            ])
        return "\n\n".join([
            hook,
            self._instagram_takeaway(facts, teaching_point, title)
        ])

    def _education_facebook(self, facts, teaching_point, hook, family):

        text = self._combined_text(facts, {})
        if "heat" in text:
            return "\n\n".join([
                "Heat can become dangerous quickly, especially for children, seniors, outdoor workers, and anyone without access to a cool space.",
                "If heat is affecting your day, take it seriously. Drink water often, slow down during the hottest part of the day, check on neighbours and family members, and never leave people or pets in a parked vehicle.",
                "Small actions can prevent a medical emergency.",
                "Stay cool and look out for each other, Morden."
            ])
        if "smoke alarm" in text:
            return "\n\n".join([
                hook,
                "People often remember to install alarms, but forget that alarms age, batteries fail, and a warning only helps if it works.",
                "Test every alarm, check the date, replace expired alarms, and make sure everyone at home knows two ways out.",
                "That testing and replacement matters because early warning gives people time to get outside.",
                "A few minutes of prevention can buy the time needed to escape."
            ])
        if "fireworks" in text:
            return "\n\n".join([
                hook,
                "The problem usually starts when fireworks are too close to people, buildings, dry grass, or vehicles.",
                "Follow local rules, keep water nearby, supervise carefully, and leave the display to someone sober and prepared.",
                "A safe celebration is the one everyone gets to enjoy."
            ])
        if "water" in text:
            return "\n\n".join([
                hook,
                "The risk is often not the water itself. It is how quickly a normal outing can change when supervision, distance, weather, or a missing life jacket becomes part of the situation.",
                "Choose one action before you head out: wear a life jacket, keep children within arm's reach near water, and call 911 if someone is in trouble.",
                "Those choices matter for families in Morden and the surrounding area."
            ])
        if "smoke" in text or "air quality" in text:
            return "\n\n".join([
                "If smoke or poor air quality is affecting Morden, check the current official alert before changing your plans.",
                "Wildfire smoke can affect visibility and breathing, especially for children, seniors, outdoor workers, and anyone with heart or lung conditions.",
                "Limit heavy outdoor activity when conditions are poor, take breaks indoors, and follow official local updates.",
                "One checked alert can help you make a safer choice before heading outside."
            ])
        if "hydrant" in text:
            return "\n\n".join([
                "A blocked hydrant can cost firefighters time when every second matters.",
                "Snow, vehicles, landscaping, and stored items can all make access harder during an emergency.",
                "Keeping hydrants visible and reachable is a simple way residents can help before a call ever happens."
            ])
        title = self._plain_title(facts.get("event_title") or facts.get("topic") or "MFR activity")
        activity = self._plain_sentence(facts.get("actual_activity") or facts.get("what_occurred") or title)
        focus = self._translate(facts.get("narrative_focus") or teaching_point or activity)
        return "\n\n".join([
            hook,
            f"The verified focus is {activity.lower()}.",
            f"What matters most here is {focus}.",
            "Keep the final wording tied to the confirmed event facts before publishing."
        ])

    def _instagram_takeaway(self, facts, teaching_point, title):

        text = self._combined_text(facts, {})
        if "heat" in text:
            return "Hydrate, slow down during the hottest part of the day, check on each other, and never leave anyone in a parked vehicle."
        if "smoke alarm" in text:
            return "Test alarms, check the date, replace expired alarms, and talk through two ways out."
        if "fireworks" in text:
            return "Distance, supervision, local rules, and water nearby make the difference."
        if "water" in text:
            return "Life jackets, close supervision, and quick calls for help can change the outcome near water."
        if "smoke" in text or "air quality" in text:
            return "Check the official alert, limit exposure when conditions are poor, and look out for people at higher risk."
        title = self._plain_title(facts.get("event_title") or title or "this MFR activity")
        focus = self._translate(facts.get("narrative_focus") or teaching_point or title)
        return f"{title}: {focus}."

    ############################################################

    def hashtags(self, family, facts, platform):

        text = self._combined_text(facts, {})
        tags = []
        if family == "training":
            tags.extend(["#FirefighterTraining"])
            if "rope" in text:
                tags.append("#RopeRescue")
            tags.extend(["#EmergencyPreparedness", "#FireService"])
        elif family == "light_hearted":
            tags.extend(["#CommunityEvent", "#SummerFun", "#TeamMFR"])
        elif family == "community_event":
            tags.extend(["#CommunityVisit", "#CommunityEvent", "#TeamMFR"])
        elif family == "recognition":
            tags.extend(["#FireService", "#Leadership", "#TeamMFR", "#CommunityService"])
        elif family == "recruitment":
            tags.extend(["#VolunteerFirefighter", "#JoinMFR", "#CommunityService"])
        elif "smoke alarm" in text:
            tags.extend(["#SmokeAlarms", "#FirePrevention", "#HomeSafety", "#PublicSafety"])
        elif "fireworks" in text:
            tags.extend(["#FireworksSafety", "#PublicSafety", "#SummerSafety"])
        elif "water" in text:
            tags.extend(["#WaterSafety", "#PublicSafety", "#SummerSafety", "#CommunityEducation"])
        elif "hydrant" in text:
            tags.extend(["#HydrantHeroes", "#WinterSafety", "#PublicSafety"])
        elif "heat" in text:
            tags.extend(["#HeatSafety", "#SummerSafety", "#CommunitySafety"])
        else:
            tags.extend(["#PublicSafety", "#CommunityEducation"])
        if platform == "facebook":
            tags = tags[:3]
        else:
            tags = tags[:4]
        tags.append("#MordenMB")
        return self._clean_hashtags(tags)

    ############################################################

    def _caption_with_emoji(self, text, family, facts, platform):

        if self._serious(facts, text):
            return text
        emojis = self.EMOJI_BY_FAMILY.get(family, ["\U0001f692"])[:2 if platform == "facebook" else 3]
        if not emojis:
            return text
        lines = str(text or "").splitlines()
        if not lines:
            return text
        lines[0] = lines[0].strip() + " " + " ".join(emojis[:1])
        if platform == "facebook" and family in ("training", "recognition") and len(lines) > 1:
            lines[-1] = lines[-1].strip() + " " + emojis[-1]
        return "\n".join(lines)

    def _append_hashtags(self, text, tags):

        return self._clean_public_copy(str(text or "").strip() + "\n\n" + " ".join(tags))

    def _variant_copy(self, facts, tone):

        family = self.story_family(facts, self._combined_text(facts, {}))
        point = self._first(facts.get("teaching_points")) or facts.get("teaching_point", "")
        hook_type, hook = self.hook_for(family, facts, point, tone=tone)
        if tone == "light":
            line = "Safe to say, the hose line was a hit." if family in ("light_hearted", "community_event") else hook
        elif tone == "educational":
            line = self._translate(point)
        else:
            line = hook
        return {
            "tone": tone,
            "hook_type": hook_type,
            "teaching_point": point,
            "preview": line
        }

    def _story_caption(self, facts, point):

        return self._shorten(self._translate(point), 120)

    def _story_cta(self, family):

        if family == "recruitment":
            return "Ask about joining."
        if family == "public_education":
            return "Save this reminder."
        return "Follow along."

    def _short_reel_caption(self, caption):

        body = "\n".join(
            line for line in str(caption or "").splitlines()
            if not line.strip().startswith("#")
        )
        return self._shorten(body, 220)

    ############################################################

    def _translate(self, text):

        value = str(text or "")
        lower = value.lower()
        for term, translation in self.TECH_TRANSLATIONS.items():
            if term in lower:
                return translation
        return value

    def _clean_public_copy(self, text):

        cleaned = str(text or "").strip()
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        return cleaned.strip()

    def _clean_hashtags(self, tags):

        result = []
        seen = set()
        for tag in tags:
            tag = str(tag or "").strip()
            if not tag.startswith("#"):
                continue
            if tag.lower() in ("#mordenfirerescue", "#morden"):
                continue
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(tag)
        result = [tag for tag in result if tag != "#MordenMB"]
        result = result[:4]
        result.append("#MordenMB")
        return result

    def _hashtag_compliant(self, tags):

        if len(tags) > 5:
            return False
        if len({tag.lower() for tag in tags}) != len(tags):
            return False
        if any(tag.lower() == "#mordenfirerescue" for tag in tags):
            return False
        return bool(tags) and tags[-1] == "#MordenMB"

    def _hashtags_in(self, text):

        return re.findall(r"#[A-Za-z0-9_]+", str(text or ""))

    def emoji_count(self, text):

        pattern = re.compile(
            "["
            "\U0001f300-\U0001f6ff"
            "\U0001f700-\U0001f77f"
            "\U0001f780-\U0001f7ff"
            "\U0001f800-\U0001f8ff"
            "\U0001f900-\U0001f9ff"
            "\U0001fa00-\U0001faff"
            "\u2600-\u27bf"
            "]+",
            flags=re.UNICODE
        )
        return sum(len(match.group(0)) for match in pattern.finditer(str(text or "")))

    def _specificity_score(self, text, facts):

        text = self._normalize(text)
        grounded = self._grounded_fact_count(text, facts)
        tokens = []
        for key in ("event_title", "actual_activity", "topic", "what_occurred", "community_connection"):
            tokens.extend(
                token for token in self._normalize(facts.get(key, "")).split()
                if len(token) > 4
            )
        score = 20
        score += min(45, len({token for token in tokens if token in text}) * 10)
        score += min(25, grounded * 12)
        if self._contains_any(text, ("morden", "local", "children", "patient", "steep", "hydrant", "water", "helmet")):
            score += 20
        if len(set(text.split())) > 35:
            score += 15
        return min(100, score)

    def _grounded_fact_count(self, text, facts):

        normalized = self._normalize(text)
        candidates = []
        for key in (
            "event_title",
            "actual_activity",
            "what_occurred",
            "community_connection",
            "narrative_focus"
        ):
            candidates.append(facts.get(key, ""))
        angle = facts.get("narrative_angle") or {}
        if isinstance(angle, dict):
            candidates.extend([
                angle.get("central_fact", ""),
                angle.get("human_interest", ""),
                angle.get("operational_context", ""),
                angle.get("community_relevance", "")
            ])
        candidates.extend(facts.get("known_facts") or [])
        candidates.extend(facts.get("equipment_apparatus") or [])
        media = facts.get("verified_media") or facts.get("available_media") or []
        for item in media:
            if isinstance(item, dict):
                candidates.extend([
                    item.get("filename", ""),
                    item.get("primary_activity", ""),
                    item.get("incident_type", ""),
                    " ".join(str(value) for value in item.get("content_tags", []) if value),
                    " ".join(str(value) for value in item.get("recommended_uses", []) if value)
                ])
        grounded = set()
        for value in candidates:
            value_text = self._normalize(value)
            if not value_text:
                continue
            tokens = [token for token in value_text.split() if len(token) > 3]
            if not tokens:
                continue
            if value_text in normalized or any(token in normalized for token in tokens[:6]):
                grounded.add(tokens[0])
        return len(grounded)

    def _genericity_score(self, text, facts):

        lower = self._normalize(text)
        generic = (
            "stay prepared",
            "look out for one another",
            "make safer choices",
            "serving the community",
            "important reminder",
            "skills sharp",
            "ready to respond"
        )
        score = sum(18 for phrase in generic if phrase in lower)
        if len(set(lower.split())) < 25:
            score += 25
        return min(100, score)

    def _hook_score(self, facebook):

        first = self._first_line(facebook).lower()
        if not first:
            return 0
        if first.startswith(("here is", "today we", "tonight we", "another great")):
            return 5
        if "?" in first:
            return 90
        if self._contains_any(first, ("what happens", "why", "most people", "blocked", "dangerous", "safe to say")):
            return 85
        if len(first.split()) <= 15:
            return 70
        return 55

    def _mentions_teaching(self, text, teaching_point):

        text = self._normalize(text)
        point_tokens = [
            token for token in self._normalize(teaching_point).split()
            if len(token) > 4
        ]
        return bool(point_tokens) and sum(1 for token in point_tokens if token in text) >= min(3, len(point_tokens))

    def _scroll_suggestion(self, weakest):

        return {
            "curiosity": "Open with a sharper question or problem.",
            "clear_problem": "Name the problem before explaining the solution.",
            "unexpected_insight": "Add one detail residents may not know.",
            "local_relevance": "Connect the point more clearly to Morden.",
            "human_interest": "Bring the people or scenario closer to the reader.",
            "visual_alignment": "Reference only visible, verified activity.",
            "plain_language": "Translate technical terms into everyday language.",
            "first_line": "Tighten the first line.",
            "one_teaching_point": "Focus on one takeaway.",
            "community_usefulness": "Make the resident benefit clearer."
        }.get(weakest, "Make the opening more specific.")

    def _known_facts_from_topic(self, topic, text):

        point = self._first(self.teaching_points(self.story_family({}, text), text, topic))
        return [point] if point else []

    def _angle_for_family(self, family, text):

        if family == "training":
            return "Explain one realistic fire-service problem and how training solves it."
        if family == "recruitment":
            return "Show what service with MFR actually involves."
        if family == "recognition":
            return "Recognize the milestone without inflating the language."
        if family == "light_hearted":
            return "Lead with the human moment and keep the tone natural."
        if family == "behind_the_scenes":
            return "Show useful preparation the public normally does not see."
        if family == "apparatus":
            return "Explain the problem the equipment helps solve."
        if family == "incident_follow_up":
            return "Share only confirmed information and practical public action."
        return "Teach one useful public-safety point with local relevance."

    def _last_publication(self, historical):

        if isinstance(historical, dict):
            return historical.get("last_related_post", "")
        if isinstance(historical, list) and historical:
            return historical[0].get("post_date") or historical[0].get("date", "")
        return ""

    def _plain_title(self, value):

        return str(value or "").strip().replace("_", " ")

    def _plain_sentence(self, value):

        text = self._plain_title(value)
        return text[:1].upper() + text[1:] if text else ""

    def _first_line(self, text):

        for line in str(text or "").splitlines():
            if line.strip():
                return line.strip()
        return ""

    def _first(self, values):

        if isinstance(values, (list, tuple)) and values:
            return values[0]
        if isinstance(values, str):
            return values
        return ""

    def _contains_any(self, text, values):

        return any(value in text for value in values)

    def _combined_text(self, facts, option):

        values = [
            facts.get("event_title", ""),
            facts.get("topic", ""),
            facts.get("actual_activity", ""),
            facts.get("what_occurred", ""),
            facts.get("why_it_matters", ""),
            facts.get("community_connection", ""),
            facts.get("content_type", ""),
            option.get("title", ""),
            option.get("topic", ""),
            option.get("opportunity_type", ""),
            option.get("content_family", "")
        ]
        values.extend(facts.get("known_facts") or [])
        values.extend(facts.get("teaching_points") or [])
        return self._normalize(" ".join(str(value or "") for value in values))

    def _normalize(self, text):

        return " ".join(str(text or "").lower().replace("_", " ").split())

    def _normalize_caption(self, text):

        text = self._normalize(re.sub(r"#[A-Za-z0-9_]+", "", str(text or "")))
        for emoji in ("\U0001f692", "\U0001f4a6", "\U0001faa2", "\U0001f44f", "\u2705", "\u26a0\ufe0f"):
            text = text.replace(emoji, "")
        return text

    def _shorten(self, text, limit):

        text = " ".join(str(text or "").split())
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)].rstrip() + "..."

    def _serious(self, facts, text):

        return self._contains_any(self._normalize(text + " " + self._combined_text(facts, {})), self.SERIOUS_TERMS)
