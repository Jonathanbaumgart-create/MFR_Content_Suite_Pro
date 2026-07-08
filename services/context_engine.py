from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

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

    def snapshot(self, today=None):

        today = self._coerce_date(today)
        season = self.season(today)
        active = self.active_themes(today)
        upcoming = self.upcoming_themes(today)
        opportunities = self.suggested_opportunities(
            today,
            active,
            upcoming
        )
        priority = self.priority_context(
            active,
            opportunities
        )

        snapshot = ContextSnapshot(
            date=today.isoformat(),
            month=today.month,
            season=season,
            day_of_week=today.strftime("%A"),
            active_themes=active,
            upcoming_themes=upcoming,
            suggested_opportunities=opportunities,
            priority_context=priority,
            explanation=self.explanation(
                today,
                season,
                active,
                upcoming
            )
        )

        logger.info(
            "Generated context snapshot date=%s season=%s active=%s",
            snapshot.date,
            snapshot.season,
            snapshot.active_themes
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

        today = self._coerce_date(today)
        month = today.month
        day = today.day
        themes = []

        if month in (12, 1, 2):
            themes.append("winter_safety_season")

        if month in (12, 1, 2, 3):
            themes.append("ice_safety_season")

        if month in (3, 4):
            themes.append("spring_melt_flood_awareness")

        if month in (4, 5, 6):
            themes.append("wildfire_grass_fire_season")

        if month in (6, 7, 8):
            themes.append("summer_heat_safety")
            themes.append("water_safety_season")

        if month in (8, 9):
            themes.append("back_to_school_safety")

        if month == 10:
            themes.append("fire_prevention_week")

        if month == 10 and day >= 15:
            themes.append("halloween_safety")

        if month in (11, 12, 1, 2, 3):
            themes.append("carbon_monoxide_safety_season")

        if month in (12, 1):
            themes.append("holiday_fireplace_candle_safety")

        if (month == 12 and day >= 27) or (month == 1 and day <= 3):
            themes.append("new_year_safety")

        if self._is_emergency_preparedness_week(today):
            themes.append("emergency_preparedness_week")

        if month in (1, 2, 3, 4, 9, 10, 11):
            themes.append("recruitment_friendly_period")

        themes.append("community_engagement_opportunity")

        if today.strftime("%A") == "Thursday":
            themes.append("throwback_thursday")

        return self._unique(themes)

    ############################################################

    def upcoming_themes(self, today=None):

        today = self._coerce_date(today)
        upcoming = []

        for days_ahead in (14, 30, 45, 60):
            future = today + timedelta(days=days_ahead)
            upcoming.extend(
                theme
                for theme in self.active_themes(future)
                if theme != "community_engagement_opportunity"
            )

        current = set(self.active_themes(today))

        return [
            theme
            for theme in self._unique(upcoming)
            if theme not in current
        ][:8]

    ############################################################

    def suggested_opportunities(
        self,
        today=None,
        active_themes=None,
        upcoming_themes=None
    ):

        today = self._coerce_date(today)
        active_themes = active_themes or self.active_themes(today)
        upcoming_themes = upcoming_themes or self.upcoming_themes(today)
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
            "throwback_thursday": "throwback_thursday"
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
