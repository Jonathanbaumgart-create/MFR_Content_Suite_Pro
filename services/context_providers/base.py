from datetime import date, datetime, timedelta


class ContextProvider:

    def __init__(self, settings=None, today=None):

        self.settings = settings or {}
        self.today = self._coerce_date(today)

    ############################################################

    def get_context(self):

        raise NotImplementedError

    ############################################################

    def provider_name(self):

        return self.settings.get(
            "name",
            self.__class__.__name__.replace("Provider", "").lower()
        )

    ############################################################

    def priority(self):

        return int(
            self.settings.get(
                "priority",
                100
            )
        )

    ############################################################

    def enabled(self):

        return bool(
            self.settings.get(
                "enabled",
                True
            )
        )

    ############################################################

    def set_date(self, today=None):

        self.today = self._coerce_date(today)

    ############################################################

    def base_context(self):

        today = self.today

        return {
            "date": today.isoformat(),
            "month": today.month,
            "season": self.season(today),
            "day_of_week": today.strftime("%A"),
            "active_themes": [],
            "upcoming_themes": [],
            "suggested_opportunities": [],
            "priority_context": [],
            "explanations": []
        }

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

    def format_theme(self, value):

        return str(value).replace(
            "_",
            " "
        ).title()

    ############################################################

    def _is_emergency_preparedness_week(self, today):

        today = self._coerce_date(today)

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
