import re
import time
from collections import Counter, defaultdict

from core.app_context import context
from services.communications_memory_service import CommunicationsMemoryService
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class CommunicationsIntelligenceService:

    PROFILE_VERSION = "communications-intelligence-v1"
    CACHE_SECONDS = 3600
    PLATFORMS = (
        "facebook",
        "instagram",
        "linkedin",
        "website",
        "news_release",
        "newsletter"
    )
    CAMPAIGN_TERMS = {
        "Hydrant Heroes": ("hydrant heroes", "hydrant"),
        "Travelling Sparky": ("travelling sparky", "sparky"),
        "Fire Prevention Week": ("fire prevention", "prevention week"),
        "Training Tuesday": ("training tuesday", "training"),
        "Volunteer Recruitment": ("recruit", "volunteer", "join"),
        "Safe Grad": ("safe grad", "graduation"),
        "Canada Day": ("canada day", "fireworks"),
        "Open House": ("open house",),
        "School Visits": ("school", "classroom", "students"),
        "Emergency Incidents": ("incident", "responded", "scene"),
        "Public Advisories": ("advisory", "notice", "warning"),
        "Public Education": ("public education", "safety", "prevent"),
        "Community Events": ("community", "event", "families")
    }
    SEASON_TERMS = {
        "spring": ("flood", "wildfire", "burn permit", "spring"),
        "summer": ("heat", "water safety", "fireworks", "summer"),
        "fall": ("harvest", "smoke alarm", "recruitment", "fall"),
        "winter": ("heating", "ice safety", "holiday safety", "winter")
    }

    def __init__(
        self,
        database=None,
        memory_service=None,
        knowledge_service=None
    ):

        self.db = database or context.database
        self.memory = memory_service or CommunicationsMemoryService(
            database=self.db
        )
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.last_metrics = {}

    ############################################################

    def profile(self, force=False):

        started = time.perf_counter()
        source_signature = self.source_signature()

        if not force:
            cached = self.db.latest_communications_intelligence_profile()

            if (
                cached and
                cached.get("version") == self.PROFILE_VERSION and
                self._fresh(cached.get("generated_at")) and
                cached.get("source_summary", {}) == source_signature
            ):
                profile = dict(cached.get("profile") or {})
                profile["profile_id"] = cached.get("id")
                profile["generated_at"] = cached.get("generated_at", "")
                profile["sample_count"] = cached.get("sample_count", 0)
                profile["learning_confidence"] = cached.get("confidence", 0)
                self.last_metrics = {
                    "total_seconds": round(time.perf_counter() - started, 3),
                    "cache_hit": True,
                    "sample_count": profile["sample_count"]
                }
                return profile

        profile = self.rebuild_profile()
        self.last_metrics = {
            "total_seconds": round(time.perf_counter() - started, 3),
            "cache_hit": False,
            "sample_count": profile.get("sample_count", 0)
        }

        return profile

    ############################################################

    def rebuild_profile(self):

        posts = self._learning_posts()
        edits = self.db.communication_edit_learning_samples(limit=500)
        source_signature = self.source_signature(posts=posts, edits=edits)
        patterns = self._pattern_statistics(posts)
        knowledge = self.knowledge.snapshot()
        platform_profiles = self._platform_profiles(posts)
        campaign_profiles = self._campaign_profiles(posts)
        seasonal_profiles = self._seasonal_profiles(posts)
        vocabulary = self._vocabulary(posts, knowledge)
        fingerprint = self._fingerprint(posts, patterns)
        sample_count = len(posts) + len(edits)
        confidence = self._confidence(sample_count)
        profile = {
            "version": self.PROFILE_VERSION,
            "generated_at": TimeService.utc_now_iso(),
            "sample_count": sample_count,
            "approved_communication_count": len(posts),
            "approved_edit_count": len(edits),
            "learning_confidence": confidence,
            "department_voice": self._department_voice(fingerprint, sample_count),
            "writing_characteristics": self._writing_characteristics(posts, patterns),
            "platform_profiles": platform_profiles,
            "campaign_profiles": campaign_profiles,
            "seasonal_profiles": seasonal_profiles,
            "engagement_intelligence": self._engagement_intelligence(posts),
            "preferred_vocabulary": vocabulary,
            "communication_fingerprint": fingerprint,
            "human_learning": self._human_learning(edits),
            "explainability": self._explainability(sample_count, platform_profiles),
            "profile_freshness": "fresh",
            "last_profile_update": TimeService.utc_now_iso()
        }
        self.db.save_communications_intelligence_profile(
            {
                "profile_type": "department",
                "profile_key": "morden_fire_rescue",
                "version": self.PROFILE_VERSION,
                "generated_at": profile["generated_at"],
                "sample_count": sample_count,
                "confidence": confidence,
                "profile": profile,
                "source_summary": source_signature
            }
        )

        logger.info(
            "Communications intelligence profile rebuilt samples=%s confidence=%s",
            sample_count,
            confidence
        )

        return profile

    ############################################################

    def source_signature(self, posts=None, edits=None):

        report = self.source_report(posts=posts, edits=edits)

        return {
            "version": self.PROFILE_VERSION,
            "eligible_count": report["eligible_count"],
            "excluded_mock_count": report["excluded_mock_count"],
            "excluded_unreviewed_count": report["excluded_unreviewed_count"],
            "excluded_rejected_count": report["excluded_rejected_count"],
            "excluded_failed_count": report["excluded_failed_count"],
            "approved_edit_count": report["approved_edit_count"],
            "oldest_eligible_sample_date": report["oldest_eligible_sample_date"],
            "newest_eligible_sample_date": report["newest_eligible_sample_date"],
            "latest_edit_sample_date": report["latest_edit_sample_date"],
            "total_memory_records": report["total_memory_records"]
        }

    def source_report(self, posts=None, edits=None):

        all_posts = self.memory.search("", limit=5000)
        eligible = posts if posts is not None else self._learning_posts(
            all_posts=all_posts
        )
        edits = edits if edits is not None else self.db.communication_edit_learning_samples(
            limit=500
        )
        excluded = {
            "mock": 0,
            "unreviewed": 0,
            "rejected": 0,
            "failed": 0
        }

        for post in all_posts:
            source = str(post.get("source", "")).lower()

            for key in excluded:
                if key in source:
                    excluded[key] += 1
                    break

        dates = [
            str(post.get("post_date", ""))
            for post in eligible
            if post.get("post_date")
        ]
        edit_dates = [
            str(edit.get("created_at", ""))
            for edit in edits
            if edit.get("created_at")
        ]

        return {
            "eligible_count": len(eligible),
            "excluded_mock_count": excluded["mock"],
            "excluded_unreviewed_count": excluded["unreviewed"],
            "excluded_rejected_count": excluded["rejected"],
            "excluded_failed_count": excluded["failed"],
            "approved_edit_count": len(edits),
            "platform_sample_counts": self._counts(
                self._platform(post.get("platform"))
                for post in eligible
            ),
            "campaign_sample_counts": self._counts(
                post.get("campaign", "")
                for post in eligible
            ),
            "oldest_eligible_sample_date": min(dates) if dates else "",
            "newest_eligible_sample_date": max(dates) if dates else "",
            "latest_edit_sample_date": max(edit_dates) if edit_dates else "",
            "total_memory_records": len(all_posts)
        }

    ############################################################

    def record_approved_edit(
        self,
        original_text,
        final_text,
        platform="",
        source="human_approved_edit"
    ):

        summary = self.compare_edit(
            original_text,
            final_text
        )

        edit_id = self.db.save_communication_edit_learning(
            {
                "platform": platform,
                "original_text": original_text or "",
                "final_text": final_text or "",
                "change_summary": summary,
                "source": source,
                "approved": 1,
                "created_at": TimeService.utc_now_iso()
            }
        )

        return {
            "edit_id": edit_id,
            "summary": summary
        }

    ############################################################

    def compare_edit(self, original_text, final_text):

        original = str(original_text or "")
        final = str(final_text or "")

        return {
            "removed_word_count": max(0, self._word_count(original) - self._word_count(final)),
            "added_word_count": max(0, self._word_count(final) - self._word_count(original)),
            "headline_changed": self._first_line(original) != self._first_line(final),
            "cta_changed": self._last_line(original) != self._last_line(final),
            "emoji_delta": self._emoji_count(final) - self._emoji_count(original),
            "hashtag_delta": len(self._hashtags(final)) - len(self._hashtags(original)),
            "paragraph_delta": len(self._paragraphs(final)) - len(self._paragraphs(original)),
            "opening_changed": self._first_sentence(original) != self._first_sentence(final),
            "closing_changed": self._last_sentence(original) != self._last_sentence(final),
            "learning_extracted": self._common_phrases(final)[:8]
        }

    ############################################################

    def voice_match(self, generated_output, platform="facebook", profile=None):

        profile = profile or self.profile()
        platform_profile = profile.get("platform_profiles", {}).get(
            platform,
            {}
        )
        text = str(generated_output or "")
        avg_sentence = platform_profile.get("average_sentence_length", 0)
        avg_hashtags = platform_profile.get("average_hashtags", 0)
        avg_emojis = platform_profile.get("average_emojis", 0)
        platform_confidence = platform_profile.get("confidence", 0)
        sample_count = platform_profile.get("sample_count", 0)
        reasons = []
        sentence_length = self._average_sentence_length(text)
        hashtags = len(self._hashtags(text))
        emojis = self._emoji_count(text)
        opening_score = self._opening_style_score(
            text,
            platform_profile
        )
        sentence_score = self._closeness_score(
            sentence_length,
            avg_sentence,
            tolerance=5
        )
        cta_score = self._cta_score(
            text,
            platform_profile
        )
        emoji_score = self._closeness_score(
            emojis,
            avg_emojis,
            tolerance=1
        )
        hashtag_score = self._closeness_score(
            hashtags,
            avg_hashtags,
            tolerance=1
        )
        vocabulary_score = self._vocabulary_score(
            text,
            profile.get("preferred_vocabulary", [])[:20]
        )
        platform_fit_score = min(100, platform_confidence + sample_count * 3)

        if sentence_score >= 75:
            reasons.append("Sentence length matches department pattern.")
        elif avg_sentence:
            reasons.append("Sentence length differs from department pattern.")

        if hashtag_score >= 75:
            reasons.append("Hashtag count matches department average.")
        else:
            reasons.append("Hashtag use differs from department average.")

        if emoji_score >= 75:
            reasons.append("Emoji use matches department average.")
        else:
            reasons.append("Emoji usage slightly differs from department average.")

        if opening_score >= 75:
            reasons.append("Opening style resembles approved department communications.")

        if cta_score >= 75:
            reasons.append("Call to action resembles approved department communications.")

        if vocabulary_score >= 40:
            reasons.append("Preferred department vocabulary is present.")

        score = round(
            (
                opening_score * 0.16 +
                sentence_score * 0.16 +
                cta_score * 0.14 +
                emoji_score * 0.12 +
                hashtag_score * 0.12 +
                vocabulary_score * 0.12 +
                platform_fit_score * 0.18
            )
        )

        if sample_count < 3:
            reasons.append(
                "Platform-specific confidence is limited by a small approved sample set."
            )
            score = min(score, 74)

        return {
            "score": max(0, min(100, score)),
            "opening_style_score": opening_score,
            "sentence_length_score": sentence_score,
            "cta_score": cta_score,
            "emoji_score": emoji_score,
            "hashtag_score": hashtag_score,
            "vocabulary_score": vocabulary_score,
            "platform_fit_score": platform_fit_score,
            "confidence": min(
                profile.get("learning_confidence", 0),
                platform_confidence
            ),
            "reasons": reasons,
            "platform": platform,
            "profile_sample_count": profile.get("sample_count", 0)
        }

    ############################################################

    def _learning_posts(self, all_posts=None):

        posts = []

        for post in all_posts or self.memory.search("", limit=1000):
            source = str(post.get("source", "")).lower()

            if any(term in source for term in ("mock", "rejected", "failed", "unreviewed")):
                continue

            if post.get("imported") or post.get("manually_created"):
                posts.append(post)
                continue

            if source in ("approved", "corrected", "accepted_editorial_strategy"):
                posts.append(post)

        return posts

    def _platform_profiles(self, posts):

        by_platform = defaultdict(list)

        for post in posts:
            by_platform[self._platform(post.get("platform"))].append(post)

        profiles = {}

        for platform in self.PLATFORMS:
            rows = by_platform.get(platform, [])
            profiles[platform] = self._profile_for_posts(rows)

        return profiles

    def _profile_for_posts(self, posts):

        if not posts:
            return {
                "sample_count": 0,
                "confidence": 0,
                "tone": "insufficient history",
                "average_sentence_length": 0,
                "average_paragraph_length": 0,
                "average_emojis": 0,
                "average_hashtags": 0,
                "common_ctas": [],
                "common_openings": [],
                "style_notes": ["Insufficient approved communications for this platform."]
            }

        captions = [post.get("caption", "") for post in posts]
        hashtags = [len(post.get("hashtags") or []) for post in posts]
        emojis = [len(post.get("emojis") or []) for post in posts]

        return {
            "sample_count": len(posts),
            "confidence": self._confidence(len(posts)),
            "tone": self._dominant(post.get("writing_style", "") for post in posts),
            "average_sentence_length": round(self._average(self._average_sentence_length(text) for text in captions), 1),
            "average_paragraph_length": round(self._average(self._average_paragraph_length(text) for text in captions), 1),
            "average_emojis": round(self._average(emojis), 1),
            "average_hashtags": round(self._average(hashtags), 1),
            "common_ctas": self._top(post.get("cta", "") for post in posts),
            "common_openings": self._top(self._first_sentence(text) for text in captions),
            "common_closings": self._top(self._last_sentence(text) for text in captions),
            "style_notes": self._style_notes(posts)
        }

    def _campaign_profiles(self, posts):

        profiles = {}

        for campaign, terms in self.CAMPAIGN_TERMS.items():
            rows = [
                post
                for post in posts
                if self._matches(post, terms) or campaign.lower() == str(post.get("campaign", "")).lower()
            ]
            profiles[campaign] = {
                **self._profile_for_posts(rows),
                "typical_timing": self._top(post.get("post_date", "")[:7] for post in rows),
                "typical_platforms": self._top(post.get("platform", "") for post in rows),
                "typical_hashtags": self._top(tag for post in rows for tag in post.get("hashtags", [])),
                "typical_audience": self._campaign_audience(campaign),
                "typical_media": self._campaign_media(campaign)
            }

        return profiles

    def _seasonal_profiles(self, posts):

        profiles = {}

        for season, terms in self.SEASON_TERMS.items():
            rows = [
                post
                for post in posts
                if self._matches(post, terms) or season == str(post.get("season", "")).lower()
            ]
            profiles[season] = self._profile_for_posts(rows)

        return profiles

    def _engagement_intelligence(self, posts):

        return {
            "available": False,
            "note": "No reliable engagement metrics are available in Communications Memory.",
            "platform_usage": self._top(post.get("platform", "") for post in posts),
            "common_campaigns": self._top(post.get("campaign", "") for post in posts),
            "posting_cadence": self._top(post.get("post_date", "")[:7] for post in posts)
        }

    def _pattern_statistics(self, posts):

        if not posts:
            return {
                "average_caption_length": 0,
                "average_hashtags": 0,
                "average_emojis": 0,
                "question_rate": 0,
                "storytelling_rate": 0,
                "educational_rate": 0,
                "recognition_rate": 0,
                "recruitment_rate": 0,
                "incident_recap_rate": 0,
                "community_engagement_rate": 0,
                "safety_message_rate": 0,
                "common_openings": [],
                "common_ctas": [],
                "cta_frequency": 0
            }

        captions = [
            post.get("caption", "")
            for post in posts
        ]
        lower = [
            caption.lower()
            for caption in captions
        ]
        count = len(posts)

        return {
            "average_caption_length": round(
                self._average(self._word_count(caption) for caption in captions),
                1
            ),
            "average_hashtags": round(
                self._average(len(post.get("hashtags") or []) for post in posts),
                1
            ),
            "average_emojis": round(
                self._average(len(post.get("emojis") or []) for post in posts),
                1
            ),
            "question_rate": self._rate(captions, "?"),
            "storytelling_rate": self._term_rate(lower, ("story", "remember", "because")),
            "educational_rate": self._term_rate(lower, ("safety", "learn", "check", "prepare")),
            "recognition_rate": self._term_rate(lower, ("thank", "appreciate", "proud")),
            "recruitment_rate": self._term_rate(lower, ("volunteer", "join", "recruit")),
            "incident_recap_rate": self._term_rate(lower, ("incident", "responded", "scene")),
            "community_engagement_rate": self._term_rate(lower, ("community", "morden", "neighbour")),
            "safety_message_rate": self._term_rate(lower, ("safety", "safe", "prevent")),
            "common_openings": [
                (value, captions.count(value))
                for value in self._top(self._first_sentence(text) for text in captions)
            ],
            "common_ctas": [
                (value, count)
                for value, count in Counter(
                    post.get("cta", "")
                    for post in posts
                    if post.get("cta")
                ).most_common(5)
            ],
            "cta_frequency": (
                sum(1 for post in posts if post.get("cta")) / max(1, count)
            )
        }

    def _vocabulary(self, posts, knowledge):

        preferred = [
            "firefighter",
            "crew",
            "training evolution",
            "public education",
            "incident",
            "volunteer",
            "community",
            "preparedness"
        ]
        text = " ".join(post.get("caption", "") for post in posts).lower()

        for phrase in (
            "morden",
            "neighbours",
            "families",
            "safety",
            "training",
            "service"
        ):
            if phrase in text:
                preferred.append(phrase)

        for table in ("programs", "annual_events", "community_partners"):
            for item in knowledge.get(table, [])[:10]:
                name = item.get("name", "")

                if name and name.lower() in text:
                    preferred.append(name)

        return self._unique(preferred)[:30]

    def _fingerprint(self, posts, patterns):

        count = max(1, len(posts))
        captions = " ".join(post.get("caption", "") for post in posts).lower()

        return {
            "community_focus": self._score_terms(captions, ("community", "morden", "neighbours", "families"), count),
            "educational_focus": round((patterns.get("educational_rate", 0) or 0) * 100),
            "operational_focus": self._score_terms(captions, ("crew", "training", "incident", "apparatus"), count),
            "volunteer_focus": round((patterns.get("recruitment_rate", 0) or 0) * 100),
            "leadership_focus": self._score_terms(captions, ("leadership", "partnership", "service"), count),
            "emergency_focus": round((patterns.get("incident_recap_rate", 0) or 0) * 100),
            "celebration_focus": round((patterns.get("recognition_rate", 0) or 0) * 100),
            "professional_tone": 80 if posts else 0,
            "friendliness": self._score_terms(captions, ("thank", "proud", "community", "together"), count),
            "confidence": self._confidence(len(posts)),
            "reading_level": "plain public-service language",
            "emoji_usage": round(patterns.get("average_emojis", 0) or 0, 1),
            "cta_strength": 80 if patterns.get("common_ctas") else 30,
            "platform_consistency": self._platform_consistency(posts)
        }

    def _department_voice(self, fingerprint, sample_count):

        if sample_count < 3:
            return "Insufficient approved communications history."

        return (
            "Professional, community-first, practical, and public-safety focused."
        )

    def _writing_characteristics(self, posts, patterns):

        captions = [post.get("caption", "") for post in posts]

        return {
            "typical_sentence_length": round(self._average(self._average_sentence_length(text) for text in captions), 1),
            "typical_paragraph_length": round(self._average(self._average_paragraph_length(text) for text in captions), 1),
            "headline_style": "clear public-service headline",
            "opening_hook_style": [item[0] for item in patterns.get("common_openings", [])[:5]],
            "closing_style": self._top(self._last_sentence(text) for text in captions),
            "cta_frequency": round((patterns.get("cta_frequency", 0) or 0) * 100),
            "emoji_frequency": round(patterns.get("average_emojis", 0) or 0, 1),
            "hashtag_count": round(patterns.get("average_hashtags", 0) or 0, 1),
            "question_usage": round((patterns.get("question_rate", 0) or 0) * 100),
            "exclamation_frequency": self._punctuation_rate(captions, "!"),
            "positive_wording": self._score_terms(" ".join(captions).lower(), ("thank", "proud", "appreciate", "together"), max(1, len(posts))),
            "action_wording": self._score_terms(" ".join(captions).lower(), ("check", "learn", "join", "prepare", "follow"), max(1, len(posts)))
        }

    def _human_learning(self, edits):

        return {
            "approved_edit_count": len(edits),
            "common_added_phrases": self._top(
                phrase
                for edit in edits
                for phrase in edit.get("change_summary", {}).get("learning_extracted", [])
            ),
            "headline_edits": sum(1 for edit in edits if edit.get("change_summary", {}).get("headline_changed")),
            "cta_edits": sum(1 for edit in edits if edit.get("change_summary", {}).get("cta_changed")),
            "emoji_edits": sum(1 for edit in edits if edit.get("change_summary", {}).get("emoji_delta")),
            "hashtag_edits": sum(1 for edit in edits if edit.get("change_summary", {}).get("hashtag_delta"))
        }

    def _explainability(self, sample_count, platform_profiles):

        facebook = platform_profiles.get("facebook", {})

        return {
            "summary": (
                "Facebook style: community-first, friendly, education-focused, "
                f"average {facebook.get('average_emojis', 0)} emojis, "
                f"average {facebook.get('average_hashtags', 0)} hashtags, "
                f"based on {facebook.get('sample_count', 0)} approved communications."
            ),
            "sample_count": sample_count,
            "limits": (
                "Engagement performance is only reported when reliable Communications Memory metrics exist."
            )
        }

    ############################################################

    def _fresh(self, value):

        return TimeService.elapsed_seconds_since_utc(value) < self.CACHE_SECONDS

    def _matches(self, post, terms):

        text = " ".join(
            str(post.get(key, ""))
            for key in ("headline", "caption", "campaign", "opportunity_type", "context")
        ).lower()

        return any(term in text for term in terms)

    def _platform(self, value):

        value = str(value or "").lower().replace(" ", "_")

        if value in ("website_article", "website"):
            return "website"

        if value in ("news_release", "release"):
            return "news_release"

        if value in self.PLATFORMS:
            return value

        return "facebook"

    def _style_notes(self, posts):

        profile = []
        captions = " ".join(post.get("caption", "") for post in posts).lower()

        if "community" in captions:
            profile.append("Community language appears frequently.")

        if "safety" in captions:
            profile.append("Safety education language is part of the voice.")

        if not profile:
            profile.append("Approved sample set is still small.")

        return profile

    def _campaign_audience(self, campaign):

        if campaign in ("Travelling Sparky", "School Visits"):
            return "students and families"

        if campaign == "Volunteer Recruitment":
            return "prospective volunteers"

        return "Morden residents"

    def _campaign_media(self, campaign):

        if campaign in ("Training Tuesday", "Volunteer Recruitment"):
            return "training and firefighter interaction media"

        if campaign in ("Hydrant Heroes", "Travelling Sparky"):
            return "program and community education media"

        return "approved supporting media"

    def _platform_consistency(self, posts):

        platforms = {
            self._platform(post.get("platform"))
            for post in posts
        }

        if not posts:
            return 0

        return min(100, 40 + len(platforms) * 10)

    def _opening_style_score(self, text, platform_profile):

        opening = self._first_sentence(text).lower()
        common = [
            value.lower()
            for value in platform_profile.get("common_openings", [])
            if value
        ]

        if not opening or not common:
            return 35 if opening else 0

        if any(opening.startswith(value[:24]) for value in common):
            return 95

        common_words = {
            word
            for value in common
            for word in re.findall(r"\b[A-Za-z]{4,}\b", value)
        }
        opening_words = set(
            re.findall(r"\b[A-Za-z]{4,}\b", opening)
        )

        if not common_words:
            return 45

        overlap = len(opening_words & common_words) / max(1, len(common_words))

        return min(85, round(35 + overlap * 80))

    def _cta_score(self, text, platform_profile):

        lower = str(text or "").lower()
        common = [
            value.lower()
            for value in platform_profile.get("common_ctas", [])
            if value
        ]

        if common and any(value[:32] in lower for value in common):
            return 95

        action_terms = (
            "check",
            "learn",
            "join",
            "follow",
            "share",
            "prepare",
            "visit",
            "contact",
            "look out"
        )

        if any(term in lower for term in action_terms):
            return 70

        return 30 if lower else 0

    def _closeness_score(self, value, target, tolerance):

        value = float(value or 0)
        target = float(target or 0)

        if target <= 0:
            return 50 if value <= tolerance else 35

        difference = abs(value - target)

        if difference <= tolerance:
            return 90

        return max(
            20,
            round(90 - ((difference - tolerance) / max(1, target)) * 100)
        )

    def _vocabulary_score(self, text, preferred):

        preferred = [
            str(value).lower()
            for value in preferred
            if value
        ]

        if not preferred:
            return 30

        lower = str(text or "").lower()
        hits = sum(1 for value in preferred if value in lower)

        return min(100, round((hits / max(1, min(len(preferred), 8))) * 100))

    def _score_terms(self, text, terms, count):

        hits = sum(text.count(term) for term in terms)

        return min(100, round((hits / max(1, count)) * 35))

    def _punctuation_rate(self, captions, mark):

        if not captions:
            return 0

        return round(
            sum(1 for text in captions if mark in text) / len(captions) * 100
        )

    def _rate(self, values, needle):

        values = list(values or [])

        if not values:
            return 0

        return sum(1 for value in values if needle in value) / len(values)

    def _term_rate(self, values, terms):

        values = list(values or [])

        if not values:
            return 0

        return (
            sum(
                1
                for value in values
                if any(term in value for term in terms)
            ) / len(values)
        )

    def _average_sentence_length(self, text):

        sentences = self._sentences(text)

        if not sentences:
            return 0

        return self._average(self._word_count(sentence) for sentence in sentences)

    def _average_paragraph_length(self, text):

        paragraphs = self._paragraphs(text)

        if not paragraphs:
            return 0

        return self._average(self._word_count(paragraph) for paragraph in paragraphs)

    def _word_count(self, text):

        return len(re.findall(r"\b[\w']+\b", str(text or "")))

    def _emoji_count(self, text):

        return len(re.findall(r"[\U0001f300-\U0001faff\u2600-\u27bf]", str(text or "")))

    def _hashtags(self, text):

        return re.findall(r"#[A-Za-z0-9_]+", str(text or ""))

    def _paragraphs(self, text):

        return [
            part.strip()
            for part in str(text or "").split("\n\n")
            if part.strip()
        ]

    def _sentences(self, text):

        return [
            part.strip()
            for part in re.split(r"[.!?]+", str(text or ""))
            if part.strip()
        ]

    def _first_line(self, text):

        return str(text or "").strip().splitlines()[0] if str(text or "").strip() else ""

    def _last_line(self, text):

        lines = [
            line.strip()
            for line in str(text or "").splitlines()
            if line.strip()
        ]

        return lines[-1] if lines else ""

    def _first_sentence(self, text):

        sentences = self._sentences(text)

        return sentences[0] if sentences else ""

    def _last_sentence(self, text):

        sentences = self._sentences(text)

        return sentences[-1] if sentences else ""

    def _common_phrases(self, text):

        words = [
            word.lower()
            for word in re.findall(r"\b[A-Za-z][A-Za-z']+\b", str(text or ""))
        ]
        phrases = []

        for index in range(0, max(0, len(words) - 2)):
            phrases.append(" ".join(words[index:index + 3]))

        return [
            phrase
            for phrase, _count in Counter(phrases).most_common(10)
        ]

    def _top(self, values, limit=5):

        counter = Counter(
            value
            for value in values
            if value
        )

        return [
            value
            for value, _count in counter.most_common(limit)
        ]

    def _dominant(self, values):

        top = self._top(values, limit=1)

        return top[0] if top else "community-focused"

    def _counts(self, values):

        return dict(
            Counter(
                value
                for value in values
                if value
            )
        )

    def _average(self, values):

        values = [
            float(value or 0)
            for value in values
        ]

        if not values:
            return 0

        return sum(values) / len(values)

    def _confidence(self, sample_count):

        if sample_count >= 150:
            return 95

        if sample_count >= 50:
            return 80

        if sample_count >= 15:
            return 60

        if sample_count >= 3:
            return 35

        return 10 if sample_count else 0

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:
            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
