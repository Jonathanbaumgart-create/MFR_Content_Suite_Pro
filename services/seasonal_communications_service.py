from datetime import date, datetime, timedelta

from core.app_context import context
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class SeasonalCommunicationsService:

    DEFAULT_WINDOW_DAYS = 21
    DEFAULT_YEARS_BACK = 6
    DEFAULT_LIMIT = 12

    ALIASES = {
        "hydrant_heroes": ("hydrant heroes", "hydrant hero"),
        "fire_chief_of_the_day": ("fire chief of the day", "fire chief day"),
        "travelling_sparky": ("travelling sparky", "traveling sparky", "sparky"),
        "water_safety": ("water safety", "water safety wednesday", "swim safety", "boat safety"),
        "fire_prevention_week": ("fire prevention week", "fire prevention", "fpw"),
        "canada_day_fireworks": ("canada day", "fireworks", "july 1"),
        "safe_grad_fireworks": ("safe grad", "grad fireworks"),
        "volunteer_recruitment": ("volunteer recruitment", "recruitment", "join mfr", "volunteer firefighter"),
        "smoke_alarm": ("smoke alarm", "smoke alarms", "smoke alarm reminder", "smoke detector"),
        "ice_safety": ("ice safety", "thin ice", "ice rescue"),
        "heating_safety": ("heating safety", "fireplace", "space heater", "carbon monoxide"),
        "wildfire_smoke": ("wildfire smoke", "air quality", "aqhi", "smoke advisory"),
        "smoke_advisory": ("smoke advisory", "air quality advisory", "smoke haze"),
        "grass_fire": ("grass fire", "grass-fire", "wildland", "spring fire"),
        "school_public_education": ("school visit", "public education", "classroom", "students")
    }

    WEATHER_SENSITIVE = {
        "heat",
        "heat_warning",
        "smoke",
        "smoke_advisory",
        "aqhi",
        "air_quality",
        "fire_ban",
        "storm",
        "cold",
        "weather",
        "emergency"
    }

    STOPWORDS = {
        "and",
        "for",
        "from",
        "near",
        "of",
        "our",
        "the",
        "this",
        "with",
        "your"
    }

    def __init__(self, database=None, now=None):

        self.db = database or context.database
        self.now = now

    ############################################################

    def around_this_time(
        self,
        topic="",
        program="",
        campaign="",
        current_date=None,
        window_days=None,
        years_back=None,
        limit=None
    ):

        local_date = self._local_date(current_date)
        window_days = int(window_days or self.DEFAULT_WINDOW_DAYS)
        years_back = int(years_back or self.DEFAULT_YEARS_BACK)
        limit = int(limit or self.DEFAULT_LIMIT)
        requested = self._query_terms(topic, program, campaign)
        rows = []
        windows = []

        for offset in range(1, years_back + 1):
            target = self._safe_prior_year_date(local_date, offset)
            start = target - timedelta(days=window_days)
            end = target + timedelta(days=window_days + 1)
            windows.append(
                {
                    "year": target.year,
                    "target_date": target.isoformat(),
                    "start": start.isoformat(),
                    "end": (end - timedelta(days=1)).isoformat(),
                    "window_days": window_days
                }
            )
            rows.extend(
                self.db.effective_communication_memory_between(
                    start.isoformat(),
                    end.isoformat(),
                    limit=80
                )
            )

        current_year_rows = self.db.effective_communication_memory_between(
            date(local_date.year, 1, 1).isoformat(),
            (local_date + timedelta(days=1)).isoformat(),
            limit=200
        )
        scored = []

        for row in rows:
            post_date = self._post_date(row)
            if not post_date or post_date >= local_date:
                continue

            score, evidence = self._score_row(
                row,
                post_date,
                local_date,
                requested,
                window_days
            )
            if score <= 0:
                continue

            scored.append(
                {
                    "communication_id": row.get("communication_id"),
                    "date": post_date.isoformat(),
                    "year": post_date.year,
                    "caption_excerpt": self._excerpt(row.get("original_text", "")),
                    "topic": self._first(row.get("topics")),
                    "program": self._first(row.get("programs")),
                    "campaign": self._first(row.get("campaigns")),
                    "media_type": self._media_type(row),
                    "similarity_score": min(100, int(score)),
                    "seasonal_timing_evidence": evidence,
                    "source_layer": row.get("source_layer", ""),
                    "source_type": row.get("source_type", ""),
                    "published_at": row.get("original_date", ""),
                    "platform": self._platform(row),
                    "safe_reuse_note": self._safe_reuse_note(requested),
                    "raw": row
                }
            )

        scored.sort(
            key=lambda item: (
                item["similarity_score"],
                item["year"]
            ),
            reverse=True
        )
        scored = scored[:limit]
        years = sorted({item["year"] for item in scored})
        last_related = max(
            (item["date"] for item in scored),
            default=""
        )
        current_year_matches = self._current_year_matches(
            current_year_rows,
            requested
        )
        pattern_confidence = self._recurrence_confidence(
            scored,
            current_year_matches
        )
        gap = self._gap_status(
            scored,
            current_year_matches,
            pattern_confidence
        )

        result = {
            "query": {
                "topic": topic,
                "program": program,
                "campaign": campaign,
                "normalized_terms": sorted(requested),
                "current_date": local_date.isoformat(),
                "window_days": window_days,
                "years_back": years_back
            },
            "windows": windows,
            "matches": [
                {key: value for key, value in item.items() if key != "raw"}
                for item in scored
            ],
            "matching_years": years,
            "matching_year_count": len(years),
            "last_related_post": last_related,
            "recurring_annual_pattern_confidence": pattern_confidence,
            "current_year_already_communicated": bool(current_year_matches),
            "current_year_matches": current_year_matches[:5],
            "communications_gap_risk": gap,
            "summary": self._summary(scored, years, last_related, pattern_confidence, current_year_matches, requested),
            "limitations": self._limitations(requested),
            "memory_source": "Communications Memory",
            "bounded": True
        }

        logger.info(
            "Year-over-year communications lookup terms=%s matches=%s years=%s window=%s",
            sorted(requested),
            len(scored),
            years,
            window_days
        )

        return result

    ############################################################

    def opportunity_signal(self, opportunity, current_date=None, limit=3):

        terms = []
        terms.append(opportunity.get("topic", ""))
        terms.append(opportunity.get("title", ""))
        terms.extend(opportunity.get("supporting_topics") or [])
        terms.extend(opportunity.get("supporting_programs") or [])
        for key in ("program", "campaign", "editorial_angle"):
            value = opportunity.get(key)
            if value:
                terms.append(value)

        query = " ".join(str(term) for term in terms if term)
        result = self.around_this_time(
            topic=query,
            current_date=current_date,
            limit=limit
        )
        return self.concise_signal(result)

    def concise_signal(self, result):

        matches = result.get("matches", [])
        return {
            "summary": result.get("summary", ""),
            "matching_year_count": result.get("matching_year_count", 0),
            "matching_years": result.get("matching_years", []),
            "last_related_post": result.get("last_related_post", ""),
            "recurring_annual_pattern_confidence": result.get(
                "recurring_annual_pattern_confidence",
                0
            ),
            "current_year_already_communicated": result.get(
                "current_year_already_communicated",
                False
            ),
            "communications_gap_risk": result.get("communications_gap_risk", ""),
            "top_matches": matches[:3],
            "limitations": result.get("limitations", [])
        }

    ############################################################

    def _score_row(self, row, post_date, local_date, requested, window_days):

        evidence = []
        score = 0
        row_values = [
            row.get("title", ""),
            row.get("summary", ""),
            row.get("primary_story", ""),
            row.get("original_text", ""),
            row.get("category", ""),
            row.get("editorial_angle", "")
        ]
        row_programs = self._tokens(row.get("programs"))
        row_campaigns = self._tokens(row.get("campaigns"))
        row_topics = self._tokens(row.get("topics"))
        row_text = self._tokens(row_values)
        row_all = row_programs | row_campaigns | row_topics | row_text
        requested_canonicals = requested & set(self.ALIASES.keys())
        row_canonicals = self._row_canonicals(
            row_all,
            row.get("programs"),
            row.get("campaigns"),
            row.get("topics"),
            row_values
        )
        if requested_canonicals and not requested_canonicals & row_canonicals:
            return 0, []

        exact_program = requested & (row_programs | row_campaigns)
        exact_topic = requested & row_topics
        semantic = requested & row_all
        days = self._calendar_distance(local_date, post_date)

        if exact_program:
            score += 55
            evidence.append("Exact program/campaign match: " + ", ".join(sorted(exact_program)[:3]))

        if exact_topic:
            score += 40
            evidence.append("Exact normalized topic match: " + ", ".join(sorted(exact_topic)[:3]))

        if semantic:
            score += min(30, len(semantic) * 8)
            evidence.append("Caption/intelligence similarity: " + ", ".join(sorted(semantic)[:4]))

        if days <= window_days:
            score += max(5, 25 - days)
            evidence.append(f"Within {days} day(s) of current calendar date")

        if not (exact_program or exact_topic or semantic):
            return 0, []

        age = max(1, local_date.year - post_date.year)
        score += max(0, 10 - age)
        if age == 1:
            evidence.append("Published one year ago")
        elif age <= 3:
            evidence.append(f"Published {age} years ago")

        if row.get("source_layer") == "human_corrected":
            score += 7
            evidence.append("Human-reviewed communication intelligence")
        elif row.get("confidence_score"):
            score += min(6, int(row.get("confidence_score") or 0) // 20)

        if row.get("deliveries"):
            score += 4
            evidence.append("Delivery/platform details available")

        return score, evidence

    ############################################################

    def _row_canonicals(self, row_terms, *values):

        phrases = set()
        for value in values:
            phrases |= self._phrases(value)

        canonicals = set()
        for canonical, aliases in self.ALIASES.items():
            alias_phrases = self._phrases(aliases)
            if canonical in row_terms or phrases & alias_phrases:
                canonicals.add(canonical)
        return canonicals

    ############################################################

    def _query_terms(self, topic, program, campaign):

        values = [topic, program, campaign]
        terms = self._tokens(values)
        phrases = self._phrases(values)
        expanded = set(terms)

        for canonical, aliases in self.ALIASES.items():
            alias_phrases = self._phrases(aliases)
            alias_tokens = self._tokens(aliases)
            if canonical in terms or phrases & alias_phrases:
                expanded.add(canonical)
                expanded.update(alias_tokens)

        return {
            term
            for term in expanded
            if term
        }

    def _tokens(self, values):

        if values is None:
            return set()

        if isinstance(values, str):
            values = [values]

        terms = set()
        for value in values or []:
            text = str(value or "").lower()
            clean = "".join(char if char.isalnum() else " " for char in text)
            words = [
                word
                for word in clean.split()
                if len(word) > 2 and word not in self.STOPWORDS
            ]
            if text.strip():
                terms.add("_".join(words) if len(words) > 1 else (words[0] if words else ""))
            terms.update(words)

        return {
            term
            for term in terms
            if term
        }

    def _phrases(self, values):

        if values is None:
            return set()

        if isinstance(values, str):
            values = [values]

        phrases = set()
        for value in values or []:
            clean = "".join(
                char if char.isalnum() else " "
                for char in str(value or "").lower()
            )
            words = [
                word
                for word in clean.split()
                if len(word) > 2 and word not in self.STOPWORDS
            ]
            if words:
                phrases.add("_".join(words))
        return phrases

    def _current_year_matches(self, rows, requested):

        matches = []
        for row in rows or []:
            row_terms = (
                self._tokens(row.get("topics")) |
                self._tokens(row.get("programs")) |
                self._tokens(row.get("campaigns")) |
                self._tokens(row.get("original_text", ""))
            )
            if requested & row_terms:
                matches.append(
                    {
                        "date": self._post_date(row).isoformat() if self._post_date(row) else "",
                        "caption_excerpt": self._excerpt(row.get("original_text", "")),
                        "topic": self._first(row.get("topics")),
                        "program": self._first(row.get("programs")),
                        "campaign": self._first(row.get("campaigns"))
                    }
                )
        return matches

    def _recurrence_confidence(self, matches, current_year_matches):

        years = {item.get("year") for item in matches}
        confidence = min(100, len(years) * 25)
        if len(years) >= 2:
            confidence += 15
        if current_year_matches:
            confidence += 10
        return max(0, min(100, confidence))

    def _gap_status(self, matches, current_year_matches, confidence):

        if current_year_matches:
            return "Current year already covered"
        if confidence >= 65:
            return "Recurring campaign likely due or approaching"
        if len({item.get("year") for item in matches}) >= 2:
            return "Historical seasonal topic found; consider current-year coverage"
        if matches:
            return "One prior seasonal reference found; not enough for annual pattern"
        return "No historical same-period communication found"

    def _summary(self, matches, years, last_related, confidence, current_year_matches, requested):

        label = self._summary_label(requested)
        if not matches:
            return f"No {label} communication was found around this period in prior years."
        if len(years) >= 2:
            return (
                f"{label} was published during this period in "
                f"{', '.join(str(year) for year in years[-4:])}. "
                f"Last related post: {last_related}. Pattern confidence {confidence}%."
            )
        return (
            f"{label} has one prior same-period communication from {years[0]}. "
            f"Last related post: {last_related}. Pattern confidence {confidence}%."
        )

    def _limitations(self, requested):

        if requested & self.WEATHER_SENSITIVE:
            return [
                "Historical posts establish seasonal precedent only; they do not prove a current warning, AQHI, fire ban, storm, heat, cold, or emergency condition."
            ]
        return [
            "Historical evidence is local Communications Memory only and should not copy old dates, warnings, or event details into new public content."
        ]

    def _safe_reuse_note(self, requested):

        if requested & self.WEATHER_SENSITIVE:
            return "Use wording style only; verify current conditions separately."
        return "Use as a reference for tone and seasonal precedent, not as a direct repost."

    def _summary_label(self, requested):

        for canonical, aliases in self.ALIASES.items():
            if canonical in requested:
                return canonical.replace("_", " ").title()
        return "Requested topic"

    ############################################################

    def _calendar_distance(self, current, previous):

        aligned = self._safe_date(current.year, previous.month, previous.day)
        return abs((current - aligned).days)

    def _safe_prior_year_date(self, current, years_back):

        return self._safe_date(current.year - years_back, current.month, current.day)

    def _safe_date(self, year, month, day):

        try:
            return date(year, month, day)
        except ValueError:
            return date(year, month, 28)

    def _local_date(self, value):

        if value is None:
            value = self.now or TimeService.to_local(TimeService.utc_now())

        if isinstance(value, datetime):
            local = TimeService.to_local(value) or value
            return local.date()

        if isinstance(value, date):
            return value

        try:
            return datetime.fromisoformat(str(value)[:10]).date()
        except Exception:
            return TimeService.to_local(TimeService.utc_now()).date()

    def _post_date(self, row):

        raw = row.get("normalized_date_utc") or row.get("original_date") or ""
        if not raw:
            return None

        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
        except Exception:
            try:
                return datetime.fromisoformat(str(raw)[:10]).date()
            except Exception:
                return None

    def _media_type(self, row):

        deliveries = row.get("deliveries") or []
        photos = sum(int(item.get("photo_count") or 0) for item in deliveries)
        videos = sum(int(item.get("video_count") or 0) for item in deliveries)
        if videos and photos:
            return "photo/video"
        if videos:
            return "video"
        if photos:
            return "photo"
        return "unknown"

    def _platform(self, row):

        deliveries = row.get("deliveries") or []
        if deliveries:
            return deliveries[0].get("platform", "")
        return row.get("original_platform", "")

    def _first(self, values):

        if isinstance(values, (list, tuple)) and values:
            return str(values[0] or "")
        return str(values or "")

    def _excerpt(self, text, limit=180):

        clean = " ".join(str(text or "").split())
        if len(clean) <= limit:
            return clean
        return clean[:limit - 3].rstrip() + "..."
