from datetime import timedelta

from services.context_providers.base import ContextProvider


class CampaignProvider(ContextProvider):

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
                        "fire_prevention_week",
                        "emergency_preparedness_week"
                    )
                ],
                "campaign_windows": active,
                "explanations": [
                    (
                        "Campaign context includes " +
                        ", ".join(self.format_theme(theme) for theme in active[:4]) +
                        "."
                    )
                    if active
                    else "No formal campaign window is active."
                ]
            }
        )

        return context

    ############################################################

    def active_themes_for(self, today):

        themes = []

        if today.month == 10:
            themes.append("fire_prevention_week")

        if self._is_emergency_preparedness_week(today):
            themes.append("emergency_preparedness_week")

        if today.month in (1, 2, 3, 4, 9, 10, 11):
            themes.append("recruitment_friendly_period")

        themes.append("community_engagement_opportunity")

        return self._unique(themes)

    ############################################################

    def upcoming_themes(self, today):

        upcoming = []

        for days_ahead in (14, 30, 45, 60):
            future = today + timedelta(days=days_ahead)
            upcoming.extend(
                theme
                for theme in self.active_themes_for(future)
                if theme != "community_engagement_opportunity"
            )

        current = set(self.active_themes_for(today))

        return [
            theme
            for theme in self._unique(upcoming)
            if theme not in current
        ][:8]

    ############################################################

    def suggested_opportunities(self, active, upcoming):

        mapping = {
            "fire_prevention_week": "fire_prevention_week",
            "emergency_preparedness_week": "storm_safety",
            "recruitment_friendly_period": "recruitment",
            "community_engagement_opportunity": "community_appreciation"
        }
        opportunities = []
        themes = active + upcoming[:3]

        for theme in themes:
            opportunity = mapping.get(theme)

            if opportunity:
                opportunities.append(opportunity)

        if "fire_prevention_week" in themes:
            opportunities.append("smoke_alarm_reminder")

        opportunities.extend(
            (
                "training_highlight",
                "general_engagement"
            )
        )

        return self._unique(opportunities)
