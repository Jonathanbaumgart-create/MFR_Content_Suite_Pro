from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import time

from config.context_config import CONTEXT_CONFIG
from services.context_providers import (
    CalendarProvider,
    CampaignProvider,
    SeasonProvider
)
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


@dataclass
class ContextSnapshot:

    date: str
    month: int
    season: str
    day_of_week: str
    active_themes: list
    upcoming_themes: list
    suggested_opportunities: list
    priority_context: list
    explanation: str

    def to_dict(self):

        return asdict(self)


class ContextEngine:

    PROVIDERS = {
        "calendar": CalendarProvider,
        "season": SeasonProvider,
        "campaign": CampaignProvider
    }

    def __init__(self, providers=None, config=None, today=None):

        self.config = config or CONTEXT_CONFIG
        self.today = self._coerce_date(today) if today is not None else None
        self.providers = providers or self._configured_providers()

    ############################################################

    def snapshot(self, today=None):

        today = self._coerce_date(
            today
            if today is not None
            else self.today
        )
        provider_results = []
        contexts = []

        for provider in self._enabled_providers(today):
            start = time.perf_counter()

            try:
                context = provider.get_context()
                elapsed = time.perf_counter() - start
                provider_results.append(provider.provider_name())
                contexts.append(
                    (
                        provider.priority(),
                        provider.provider_name(),
                        context
                    )
                )
                logger.info(
                    "Context provider ran provider=%s priority=%s duration=%.4fs",
                    provider.provider_name(),
                    provider.priority(),
                    elapsed
                )

            except Exception as ex:
                logger.error(
                    "Context provider failed provider=%s",
                    provider.provider_name(),
                    exc_info=(
                        type(ex),
                        ex,
                        ex.__traceback__
                    )
                )

        snapshot = self._merge_contexts(
            today,
            contexts
        )

        logger.info(
            "Merged context snapshot providers=%s date=%s active=%s suggested=%s",
            provider_results,
            snapshot.date,
            snapshot.active_themes,
            snapshot.suggested_opportunities
        )

        return snapshot

    ############################################################

    def season(self, today=None):

        month = self._coerce_date(today).month

        if month in (12, 1, 2):
            return "winter"

        if month in (3, 4, 5):
            return "spring"

        if month in (6, 7, 8):
            return "summer"

        return "fall"

    ############################################################

    def active_themes(self, today=None):

        return self.snapshot(today).active_themes

    ############################################################

    def upcoming_themes(self, today=None):

        return self.snapshot(today).upcoming_themes

    ############################################################

    def suggested_opportunities(
        self,
        today=None,
        active_themes=None,
        upcoming_themes=None
    ):

        if active_themes is None and upcoming_themes is None:
            return self.snapshot(today).suggested_opportunities

        return self._suggested_from_themes(
            self._coerce_date(today),
            active_themes or [],
            upcoming_themes or []
        )

    ############################################################

    def priority_context(self, active_themes, opportunities):

        priority = []

        high_priority_themes = {
            "summer_heat_safety",
            "winter_safety_season",
            "ice_safety_season",
            "spring_melt_flood_awareness",
            "wildfire_grass_fire_season",
            "fire_prevention_week",
            "carbon_monoxide_safety_season",
            "holiday_fireplace_candle_safety",
            "emergency_preparedness_week"
        }

        for theme in active_themes:

            if theme in high_priority_themes:
                priority.append(theme)

        if not priority and opportunities:
            priority.append(opportunities[0])

        return self._unique(priority)

    ############################################################

    def explanation(self, today, season, active, upcoming):

        parts = [
            f"{today.strftime('%B %d, %Y')} falls in {season}."
        ]

        if active:
            parts.append(
                "Active context: " +
                ", ".join(self.format_theme(theme) for theme in active[:5]) +
                "."
            )

        if upcoming:
            parts.append(
                "Upcoming context: " +
                ", ".join(self.format_theme(theme) for theme in upcoming[:4]) +
                "."
            )

        return " ".join(parts)

    ############################################################

    def format_theme(self, value):

        return str(value).replace(
            "_",
            " "
        ).title()

    ############################################################

    def _configured_providers(self):

        provider_config = self.config.get(
            "providers",
            {}
        )
        providers = []

        for key, provider_class in self.PROVIDERS.items():
            settings = dict(
                provider_config.get(
                    key,
                    {}
                )
            )
            settings["name"] = key
            providers.append(
                provider_class(
                    settings=settings,
                    today=self.today
                )
            )

        return providers

    ############################################################

    def _enabled_providers(self, today):

        providers = []

        for provider in self.providers:
            self._set_provider_date(
                provider,
                today
            )

            if provider.enabled():
                providers.append(provider)
            else:
                logger.info(
                    "Context provider disabled provider=%s",
                    provider.provider_name()
                )

        return sorted(
            providers,
            key=lambda item: item.priority()
        )

    ############################################################

    def _set_provider_date(self, provider, today):

        if hasattr(provider, "set_date"):
            provider.set_date(today)
            return

        provider.today = today

    ############################################################

    def _merge_contexts(self, today, contexts):

        contexts = sorted(
            contexts,
            key=lambda item: item[0]
        )
        active = []
        upcoming = []
        opportunities = []
        priority = []
        explanations = []
        date_value = today.isoformat()
        month = today.month
        season = self.season(today)
        day_of_week = today.strftime("%A")

        for _, _, context in contexts:
            date_value = context.get("date") or date_value
            month = context.get("month") or month
            season = context.get("season") or season
            day_of_week = context.get("day_of_week") or day_of_week
            active.extend(context.get("active_themes") or [])
            upcoming.extend(context.get("upcoming_themes") or [])
            opportunities.extend(context.get("suggested_opportunities") or [])
            priority.extend(context.get("priority_context") or [])
            explanations.extend(context.get("explanations") or [])

            if context.get("explanation"):
                explanations.append(context["explanation"])

        active = self._unique(active)
        upcoming = [
            theme
            for theme in self._unique(upcoming)
            if theme not in active
        ][:8]
        opportunities = self._unique(
            opportunities +
            self._suggested_from_themes(
                today,
                active,
                upcoming
            )
        )
        priority = self._unique(
            priority +
            self.priority_context(
                active,
                opportunities
            )
        )
        explanation = self._merged_explanation(
            today,
            season,
            active,
            upcoming,
            explanations
        )

        return ContextSnapshot(
            date=date_value,
            month=month,
            season=season,
            day_of_week=day_of_week,
            active_themes=active,
            upcoming_themes=upcoming,
            suggested_opportunities=opportunities,
            priority_context=priority,
            explanation=explanation
        )

    ############################################################

    def _merged_explanation(
        self,
        today,
        season,
        active,
        upcoming,
        explanations
    ):

        merged = self._unique(explanations)

        if merged:
            return " ".join(merged)

        return self.explanation(
            today,
            season,
            active,
            upcoming
        )

    ############################################################

    def _suggested_from_themes(self, today, active_themes, upcoming_themes):

        active_themes = active_themes or []
        upcoming_themes = upcoming_themes or []
        opportunities = []
        themes = set(active_themes + upcoming_themes[:3])
        mapping = {
            "summer_heat_safety": "heat_warning",
            "water_safety_season": "water_safety",
            "winter_safety_season": "holiday_safety",
            "ice_safety_season": "storm_safety",
            "spring_melt_flood_awareness": "storm_safety",
            "wildfire_grass_fire_season": "fire_prevention_week",
            "back_to_school_safety": "community_appreciation",
            "fire_prevention_week": "fire_prevention_week",
            "halloween_safety": "holiday_safety",
            "carbon_monoxide_safety_season": "smoke_alarm_reminder",
            "holiday_fireplace_candle_safety": "holiday_safety",
            "new_year_safety": "general_engagement",
            "emergency_preparedness_week": "storm_safety",
            "recruitment_friendly_period": "recruitment",
            "community_engagement_opportunity": "community_appreciation",
            "throwback_thursday": "throwback_thursday",
            "holiday_safety": "holiday_safety"
        }

        for theme in active_themes:
            opportunity = mapping.get(theme)

            if opportunity:
                opportunities.append(opportunity)

        if today.strftime("%A") == "Thursday":
            opportunities.append("throwback_thursday")

        if "fire_prevention_week" in themes:
            opportunities.append("smoke_alarm_reminder")

        opportunities.extend(
            (
                "training_highlight",
                "general_engagement"
            )
        )

        return self._unique(opportunities)

    ############################################################

    def _is_emergency_preparedness_week(self, today):

        if today.month != 5:
            return False

        first = date(today.year, 5, 1)
        days_until_sunday = (6 - first.weekday()) % 7
        first_sunday = first + timedelta(days=days_until_sunday)

        return first_sunday <= today <= first_sunday + timedelta(days=6)

    ############################################################

    def _coerce_date(self, value):

        if value is None:
            return datetime.now().date()

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        return datetime.fromisoformat(str(value)).date()

    ############################################################

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
