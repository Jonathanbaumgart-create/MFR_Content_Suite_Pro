from datetime import timedelta

from services.context_providers.base import ContextProvider


class SeasonProvider(ContextProvider):

    def get_context(self):

        today = self.today
        active = self.active_themes_for(today)
        upcoming = self.upcoming_themes(today)
        context = self.base_context()
        context.update(
            {
                "active_themes": active,
                "upcoming_themes": upcoming,
                "suggested_opportunities": self.suggested_opportunities(
                    active,
                    upcoming
                ),
                "priority_context": [
                    theme
                    for theme in active
                    if theme in (
                        "summer_heat_safety",
                        "winter_safety_season",
                        "ice_safety_season",
                        "spring_melt_flood_awareness",
                        "wildfire_grass_fire_season",
                        "carbon_monoxide_safety_season"
                    )
                ],
                "explanations": [
                    (
                        "Seasonal context includes " +
                        ", ".join(self.format_theme(theme) for theme in active[:4]) +
                        "."
                    )
                    if active
                    else "No seasonal safety context is active."
                ]
            }
        )

        return context

    ############################################################

    def active_themes_for(self, today):

        month = today.month
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

        if month in (11, 12, 1, 2, 3):
            themes.append("carbon_monoxide_safety_season")

        return self._unique(themes)

    ############################################################

    def upcoming_themes(self, today):

        upcoming = []

        for days_ahead in (14, 30, 45, 60):
            future = today + timedelta(days=days_ahead)
            upcoming.extend(self.active_themes_for(future))

        current = set(self.active_themes_for(today))

        return [
            theme
            for theme in self._unique(upcoming)
            if theme not in current
        ][:8]

    ############################################################

    def suggested_opportunities(self, active, upcoming):

        mapping = {
            "summer_heat_safety": "heat_warning",
            "water_safety_season": "water_safety",
            "winter_safety_season": "holiday_safety",
            "ice_safety_season": "storm_safety",
            "spring_melt_flood_awareness": "storm_safety",
            "wildfire_grass_fire_season": "fire_prevention_week",
            "carbon_monoxide_safety_season": "smoke_alarm_reminder"
        }
        opportunities = []

        for theme in active + upcoming[:3]:
            opportunity = mapping.get(theme)

            if opportunity:
                opportunities.append(opportunity)

        return self._unique(opportunities)
