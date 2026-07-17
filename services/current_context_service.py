from datetime import date, datetime

from services.cache_invalidation_service import CacheInvalidationService
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("content")


class ContextProvider:

    def provider_name(self):
        return self.__class__.__name__

    def priority(self):
        return 50

    def enabled(self):
        return True

    def get_context(self, now=None):
        raise NotImplementedError


class LocalCalendarContextProvider(ContextProvider):

    HOLIDAYS = {
        (1, 1): "New Year's Day",
        (7, 1): "Canada Day",
        (11, 11): "Remembrance Day",
        (12, 25): "Christmas Day",
        (12, 26): "Boxing Day"
    }

    def priority(self):
        return 10

    def get_context(self, now=None):
        local_now = TimeService.to_local(now or TimeService.utc_now())
        today = local_now.date()
        season = self._season(today)
        active_themes = self._active_themes(today, season)
        upcoming_themes = self._upcoming_themes(today)
        holiday = self.HOLIDAYS.get((today.month, today.day), "")

        return {
            "provider": self.provider_name(),
            "retrieved_at": TimeService.utc_now_iso(),
            "freshness": "fresh",
            "local_datetime": local_now.isoformat(timespec="seconds"),
            "local_date": today.isoformat(),
            "month": today.strftime("%B"),
            "weekday": today.strftime("%A"),
            "is_weekend": today.weekday() >= 5,
            "season": season,
            "holidays": [holiday] if holiday else [],
            "active_themes": active_themes,
            "upcoming_themes": upcoming_themes,
            "priority_context": active_themes[:3],
            "alerts": [],
            "weather": {},
            "explanation": (
                "Local Winnipeg date, season, and deterministic fire-service campaign context."
            )
        }

    def _season(self, today):
        month = today.month

        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "fall"

    def _active_themes(self, today, season):
        themes = []
        month = today.month

        if season == "winter":
            themes.extend([
                "winter safety",
                "carbon monoxide safety",
                "ice safety"
            ])
        elif season == "spring":
            themes.extend([
                "spring melt awareness",
                "grass fire prevention",
                "emergency preparedness"
            ])
        elif season == "summer":
            themes.extend([
                "heat safety",
                "water safety",
                "wildfire awareness"
            ])
        else:
            themes.extend([
                "back-to-school safety",
                "fire prevention",
                "carbon monoxide safety"
            ])

        if month == 10:
            themes.insert(0, "Fire Prevention Week")
        if month in (9, 10):
            themes.append("fire prevention campaign preparation")
        if month in (5, 6, 9, 10, 11):
            themes.append("recruitment")

        return self._unique(themes)

    def _upcoming_themes(self, today):
        month = today.month

        if month in (8, 9):
            return ["Fire Prevention Week", "back-to-school safety"]
        if month in (11, 12):
            return ["holiday fire safety", "carbon monoxide safety"]
        if month in (4, 5):
            return ["Emergency Preparedness Week", "wildfire awareness"]
        if month in (6, 7):
            return ["summer heat safety", "water safety"]
        return ["community engagement", "recruitment"]

    def _unique(self, values):
        seen = set()
        result = []

        for value in values:
            key = str(value).lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)

        return result


class StaticContextProvider(ContextProvider):

    def __init__(self, context=None, is_enabled=False, provider_name="static_context"):
        self.context = dict(context or {})
        self.is_enabled = bool(is_enabled)
        self.name = provider_name

    def provider_name(self):
        return self.name

    def priority(self):
        return 20

    def enabled(self):
        return self.is_enabled

    def get_context(self, now=None):
        data = dict(self.context)
        data.setdefault("provider", self.provider_name())
        data.setdefault("retrieved_at", TimeService.utc_now_iso())
        data.setdefault("freshness", "fresh")
        data.setdefault("alerts", [])
        data.setdefault("weather", {})
        return data


class CurrentContextService:

    CACHE_TTL_SECONDS = 900

    def __init__(self, providers=None):
        self.providers = providers or [LocalCalendarContextProvider()]
        self._cache = None

    def current_context(self, now=None, force=False):
        local_now = TimeService.to_local(now or TimeService.utc_now())

        if not force and self._cache:
            cached_date = self._cache.get("local_date")
            age = TimeService.elapsed_seconds_since_utc(
                self._cache.get("generated_at")
            )
            if cached_date == local_now.date().isoformat() and age < self.CACHE_TTL_SECONDS:
                return dict(self._cache)

        started = datetime.now()
        provider_results = []
        errors = []

        for provider in sorted(self.providers, key=lambda item: item.priority()):
            if not provider.enabled():
                continue

            provider_started = datetime.now()
            try:
                data = provider.get_context(now=now)
                data["provider_timing_seconds"] = round(
                    (datetime.now() - provider_started).total_seconds(),
                    3
                )
                provider_results.append(data)
            except Exception as ex:
                errors.append({
                    "provider": provider.provider_name(),
                    "error": str(ex)
                })
                logger.warning(
                    "Current context provider failed provider=%s error=%s",
                    provider.provider_name(),
                    ex
                )

        merged = self._merge(provider_results, local_now)
        merged["provider_errors"] = errors
        merged["provider_count"] = len(provider_results)
        merged["generated_at"] = TimeService.utc_now_iso()
        merged["generation_seconds"] = round(
            (datetime.now() - started).total_seconds(),
            3
        )
        self._cache = dict(merged)

        if provider_results:
            CacheInvalidationService.invalidate(
                reason="current context refreshed",
                scopes=["current_context", "communications_officer"]
            )

        return merged

    def _merge(self, results, local_now):
        base = {
            "local_datetime": local_now.isoformat(timespec="seconds"),
            "local_date": local_now.date().isoformat(),
            "month": local_now.strftime("%B"),
            "weekday": local_now.strftime("%A"),
            "season": "",
            "is_weekend": local_now.weekday() >= 5,
            "active_themes": [],
            "upcoming_themes": [],
            "priority_context": [],
            "holidays": [],
            "weather": {},
            "alerts": [],
            "freshness": "unavailable",
            "data_freshness": "Weather and alert context unavailable; local calendar context only.",
            "sources": [],
            "explanation": "No current context provider returned data."
        }

        if not results:
            return base

        for result in results:
            base["sources"].append({
                "provider": result.get("provider", ""),
                "retrieved_at": result.get("retrieved_at", ""),
                "freshness": result.get("freshness", "unknown")
            })

            for key in ("season", "month", "weekday", "local_datetime", "local_date"):
                if result.get(key):
                    base[key] = result[key]

            for key in ("active_themes", "upcoming_themes", "priority_context", "holidays", "alerts"):
                base[key] = self._unique(list(base.get(key) or []) + list(result.get(key) or []))

            if result.get("weather"):
                base["weather"].update(result["weather"])

            if result.get("freshness") == "fresh":
                base["freshness"] = "fresh"

            if result.get("explanation"):
                base["explanation"] = result["explanation"]

        if base["freshness"] == "fresh" and not base["weather"] and not base["alerts"]:
            base["data_freshness"] = (
                "Local context fresh; weather and alert providers are unavailable or disabled."
            )
        elif base["freshness"] == "fresh":
            base["data_freshness"] = "Current context is fresh."

        return base

    def _unique(self, values):
        seen = set()
        result = []

        for value in values:
            key = str(value).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(value)

        return result
