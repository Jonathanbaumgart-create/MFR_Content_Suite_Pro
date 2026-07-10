from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TimeService:

    LOCAL_ZONE = "America/Winnipeg"

    @classmethod
    def local_timezone(cls, timezone_name=None):

        name = timezone_name or cls.LOCAL_ZONE

        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            try:
                from dateutil import tz
            except ImportError:
                return timezone.utc

            return tz.gettz(name) or timezone.utc

    @classmethod
    def utc_now(cls):

        return datetime.now(timezone.utc)

    ############################################################

    @classmethod
    def utc_now_iso(cls):

        return cls.utc_now().isoformat(timespec="seconds")

    ############################################################

    @classmethod
    def normalize_stored_timestamp(cls, value):

        if not value:
            return None

        if isinstance(value, datetime):
            parsed = value
        else:
            text = str(value).strip()

            if not text:
                return None

            if text.endswith("Z"):
                text = text[:-1] + "+00:00"

            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                try:
                    parsed = datetime.strptime(
                        text,
                        "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    ############################################################

    @classmethod
    def to_local(cls, value, timezone_name=None):

        utc_value = cls.normalize_stored_timestamp(value)

        if utc_value is None:
            return None

        return utc_value.astimezone(cls.local_timezone(timezone_name))

    ############################################################

    @classmethod
    def format_local(cls, value, timezone_name=None):

        local = cls.to_local(
            value,
            timezone_name=timezone_name
        )

        if local is None:
            return ""

        return local.strftime("%Y-%m-%d %I:%M %p %Z")

    ############################################################

    @classmethod
    def local_date(cls, value, timezone_name=None):

        local = cls.to_local(
            value,
            timezone_name=timezone_name
        )

        if local is None:
            return ""

        return local.date().isoformat()
