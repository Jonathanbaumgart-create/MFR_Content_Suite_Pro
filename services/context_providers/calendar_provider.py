from datetime import date, timedelta

from services.context_providers.base import ContextProvider


class CalendarProvider(ContextProvider):

    def get_context(self):

        today = self.today
        context = self.base_context()
        active = []
        holidays = self.holidays(today)
        recurring = self.recurring_events(today)

        if today.month in (8, 9):
            active.append("back_to_school_safety")

        if today.month == 10 and today.day >= 15:
            active.append("halloween_safety")

        if today.month in (12, 1):
            active.append("holiday_fireplace_candle_safety")

        if (today.month == 12 and today.day >= 27) or (
            today.month == 1 and today.day <= 3
        ):
            active.append("new_year_safety")

        if holidays:
            active.append("holiday_safety")

        if today.strftime("%A") == "Thursday":
            active.append("throwback_thursday")

        active.append("community_engagement_opportunity")

        upcoming = self.upcoming_calendar_themes(today)
        context.update(
            {
                "active_themes": self._unique(active),
                "upcoming_themes": upcoming,
                "suggested_opportunities": self.suggested_opportunities(
                    active,
                    upcoming
                ),
                "priority_context": [
                    theme
                    for theme in active
                    if theme in (
                        "holiday_fireplace_candle_safety",
                        "halloween_safety",
                        "holiday_safety"
                    )
                ],
                "holidays": holidays,
                "recurring_events": recurring,
                "explanations": [
                    (
                        f"{today.strftime('%B %d, %Y')} is a "
                        f"{today.strftime('%A')} in {self.season(today)}."
                    )
                ]
            }
        )

        return context

    ############################################################

    def holidays(self, today):

        holidays = []

        fixed = {
            (1, 1): "new_year_day",
            (7, 1): "canada_day",
            (11, 11): "remembrance_day",
            (12, 25): "christmas_day",
            (12, 26): "boxing_day"
        }
        holiday = fixed.get(
            (
                today.month,
                today.day
            )
        )

        if holiday:
            holidays.append(holiday)

        if today.month == 2 and self._nth_weekday(today.year, 2, 0, 3) == today:
            holidays.append("louis_riel_day")

        if today.month == 5 and self._victoria_day(today.year) == today:
            holidays.append("victoria_day")

        if today.month == 9 and self._nth_weekday(today.year, 9, 0, 1) == today:
            holidays.append("labour_day")

        if today.month == 10 and self._nth_weekday(today.year, 10, 0, 2) == today:
            holidays.append("thanksgiving")

        return holidays

    ############################################################

    def recurring_events(self, today):

        events = []

        if today.month == 10:
            events.append("fire_prevention_month")

        if today.month in (12, 1):
            events.append("winter_holiday_safety")

        if today.month in (8, 9):
            events.append("back_to_school_period")

        return events

    ############################################################

    def upcoming_calendar_themes(self, today):

        upcoming = []

        for days_ahead in (14, 30, 45, 60):
            future = today + timedelta(days=days_ahead)
            future_active = []

            if future.month in (8, 9):
                future_active.append("back_to_school_safety")

            if future.month == 10 and future.day >= 15:
                future_active.append("halloween_safety")

            if future.month in (12, 1):
                future_active.append("holiday_fireplace_candle_safety")

            if (future.month == 12 and future.day >= 27) or (
                future.month == 1 and future.day <= 3
            ):
                future_active.append("new_year_safety")

            if self.holidays(future):
                future_active.append("holiday_safety")

            if future.strftime("%A") == "Thursday":
                future_active.append("throwback_thursday")

            upcoming.extend(future_active)

        current = set(self.get_context_active_only(today))

        return [
            theme
            for theme in self._unique(upcoming)
            if theme not in current
        ][:8]

    ############################################################

    def get_context_active_only(self, today):

        current = []

        if today.month in (8, 9):
            current.append("back_to_school_safety")

        if today.month == 10 and today.day >= 15:
            current.append("halloween_safety")

        if today.month in (12, 1):
            current.append("holiday_fireplace_candle_safety")

        if (today.month == 12 and today.day >= 27) or (
            today.month == 1 and today.day <= 3
        ):
            current.append("new_year_safety")

        if self.holidays(today):
            current.append("holiday_safety")

        if today.strftime("%A") == "Thursday":
            current.append("throwback_thursday")

        current.append("community_engagement_opportunity")

        return self._unique(current)

    ############################################################

    def suggested_opportunities(self, active, upcoming):

        mapping = {
            "back_to_school_safety": "community_appreciation",
            "halloween_safety": "holiday_safety",
            "holiday_fireplace_candle_safety": "holiday_safety",
            "new_year_safety": "general_engagement",
            "holiday_safety": "holiday_safety",
            "community_engagement_opportunity": "community_appreciation",
            "throwback_thursday": "throwback_thursday"
        }
        opportunities = []

        for theme in active + upcoming[:3]:
            opportunity = mapping.get(theme)

            if opportunity:
                opportunities.append(opportunity)

        opportunities.append("general_engagement")

        return self._unique(opportunities)

    ############################################################

    def _nth_weekday(self, year, month, weekday, occurrence):

        current = date(year, month, 1)
        offset = (weekday - current.weekday()) % 7

        return current + timedelta(days=offset + ((occurrence - 1) * 7))

    ############################################################

    def _victoria_day(self, year):

        current = date(year, 5, 24)

        while current.weekday() != 0:
            current -= timedelta(days=1)

        return current
