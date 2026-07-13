from datetime import datetime, timedelta, timezone

from services.time_service import TimeService


class MediaPriorityService:

    WINDOWS = (
        ("added_today", "Added today", "first_seen_at", 1000, 0),
        ("captured_today", "Captured today", "capture_time", 950, 0),
        ("added_last_7_days", "Added last 7 days", "first_seen_at", 850, 7),
        ("captured_last_7_days", "Captured last 7 days", "capture_time", 800, 7),
        ("added_last_30_days", "Added last 30 days", "first_seen_at", 700, 30),
        ("captured_last_30_days", "Captured last 30 days", "capture_time", 650, 30),
        ("added_last_12_months", "Added last 12 months", "first_seen_at", 500, 365),
        ("captured_last_12_months", "Captured last 12 months", "capture_time", 450, 365),
        ("historical", "Historical media", "best_available", 100, None)
    )

    PRESETS = {
        "today": ("added_today",),
        "captured_today": ("captured_today",),
        "last_7_days": (
            "added_today",
            "captured_today",
            "added_last_7_days",
            "captured_last_7_days"
        ),
        "last_30_days": (
            "added_today",
            "captured_today",
            "added_last_7_days",
            "captured_last_7_days",
            "added_last_30_days",
            "captured_last_30_days"
        ),
        "last_12_months": (
            "added_today",
            "captured_today",
            "added_last_7_days",
            "captured_last_7_days",
            "added_last_30_days",
            "captured_last_30_days",
            "added_last_12_months",
            "captured_last_12_months"
        ),
        "historical": ("historical",)
    }

    def __init__(self, database=None, now=None):

        self.db = database
        self.now = now or datetime.now(timezone.utc)

    ############################################################

    def candidates(
        self,
        preset="today",
        limit=200,
        include_photos=True,
        include_videos=True,
        only_unanalyzed=True,
        include_failed=False,
        force=False
    ):

        if self.db is None:
            raise RuntimeError("MediaPriorityService requires a database")

        since_days = self._since_days_for_preset(preset)
        rows = self.db.get_priority_media_rows(
            limit=max(int(limit or 200) * 3, int(limit or 200)),
            since_days=since_days,
            include_photos=include_photos,
            include_videos=include_videos,
            only_unanalyzed=only_unanalyzed,
            include_failed=include_failed,
            force=force
        )
        categories = set(self.preset_categories(preset))
        candidates = []

        for row in rows:
            priority = self.prioritize(row)

            if categories and priority["priority_category"] not in categories:
                continue

            item = dict(row)
            item.update(priority)
            candidates.append(item)

        candidates.sort(
            key=lambda item: (
                item["priority_score"],
                item.get("chosen_date", ""),
                item.get("id", 0)
            ),
            reverse=True
        )

        return candidates[:int(limit or 200)]

    ############################################################

    def preview(self, preset="today"):

        if self.db is None:
            raise RuntimeError("MediaPriorityService requires a database")

        if preset in ("today", "captured_today"):
            return self._preview_from_priorities(preset)

        return self.db.recent_media_counts(
            since_days=self._since_days_for_preset(preset)
        )

    ############################################################

    def prioritize(self, row):

        values = self._row_values(row)
        first_seen_at = self._parse(
            values.get("first_seen_at") or
            values.get("date_added")
        )
        capture_time = self._parse(values.get("capture_time"))
        modified = self._parse(values.get("file_modified_at"))
        created = self._parse(values.get("file_created_at"))
        best_date, source = self.best_date(
            capture_time,
            first_seen_at,
            modified,
            created
        )

        for key, label, field, score, days in self.WINDOWS:

            compare_date = {
                "first_seen_at": first_seen_at,
                "capture_time": capture_time,
                "best_available": best_date
            }.get(field)

            if key == "historical":
                return self._result(
                    key,
                    label,
                    score,
                    source,
                    best_date,
                    "No recent capture or discovery date matched."
                )

            if compare_date is None:
                continue

            if days == 0 and self._same_local_day(compare_date):
                return self._result(
                    key,
                    label,
                    score,
                    field,
                    compare_date,
                    f"{label} using {self._field_label(field)}."
                )

            if days and compare_date >= self.now - timedelta(days=days):
                age_hours = max(
                    0,
                    (self.now - compare_date).total_seconds() / 3600
                )
                recency_bonus = max(0, 50 - int(age_hours / 24))
                return self._result(
                    key,
                    label,
                    score + recency_bonus,
                    field,
                    compare_date,
                    f"{label} using {self._field_label(field)}."
                )

        return self._result(
            "historical",
            "Historical media",
            100,
            source,
            best_date,
            "No recent date was available."
        )

    ############################################################

    def best_date(self, capture_time, date_added, modified, created):

        for source, value in (
            ("capture_time", capture_time),
            ("first_seen_at", date_added),
            ("file_modified_at", modified),
            ("file_created_at", created)
        ):
            if value is not None:
                return value, source

        return None, "unknown"

    ############################################################

    def preset_categories(self, preset):

        return self.PRESETS.get(
            preset,
            self.PRESETS["today"]
        )

    ############################################################

    def _since_days_for_preset(self, preset):

        preset = str(preset or "today").lower()

        if preset == "today":
            return 1

        if preset == "last_7_days":
            return 7

        if preset == "last_30_days":
            return 30

        if preset == "last_12_months":
            return 365

        return None

    ############################################################

    def _preview_from_priorities(self, preset):

        rows = self.db.get_priority_media_rows(
            limit=10000,
            since_days=self._since_days_for_preset(preset),
            include_photos=True,
            include_videos=True,
            only_unanalyzed=False,
            include_failed=True,
            force=True
        )
        categories = set(self.preset_categories(preset))
        counts = {
            "total": 0,
            "photos": 0,
            "videos": 0,
            "unanalyzed": 0,
            "review_required": 0,
            "approved": 0,
            "corrected": 0,
            "failed": 0
        }

        for row in rows:
            priority = self.prioritize(row)

            if priority["priority_category"] not in categories:
                continue

            counts["total"] += 1

            if row.get("media_type") == "video":
                counts["videos"] += 1
            else:
                counts["photos"] += 1

            trust = row.get("trust_state") or ""
            review = row.get("review_status") or ""

            if not row.get("provider"):
                counts["unanalyzed"] += 1

            if trust == "unreviewed_real" or review == "review_required":
                counts["review_required"] += 1

            if trust == "approved_real" or review == "approved":
                counts["approved"] += 1

            if trust == "corrected_real" or review == "corrected":
                counts["corrected"] += 1

            if row.get("failure_reason"):
                counts["failed"] += 1

        return counts

    ############################################################

    def _same_local_day(self, value):

        local_value = self._local_datetime(value)
        local_now = self._local_datetime(self.now)

        return local_value.date() == local_now.date()

    ############################################################

    def _local_datetime(self, value):

        try:
            return TimeService.to_local(value)
        except Exception:
            return value.astimezone()

    ############################################################

    def _parse(self, value):

        if not value:
            return None

        if isinstance(value, datetime):
            parsed = value
        else:
            text = str(value).strip()

            if not text:
                return None

            normalized = TimeService.normalize_stored_timestamp(text)

            if normalized is not None:
                return normalized

            try:
                parsed = datetime.fromisoformat(text)
            except Exception:
                try:
                    parsed = datetime.strptime(
                        text[:19],
                        "%Y-%m-%d %H:%M:%S"
                    )
                except Exception:
                    return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    ############################################################

    def _result(self, category, label, score, date_source, date_value, reason):

        return {
            "priority_category": category,
            "priority_label": label,
            "priority_score": int(score),
            "date_source": date_source,
            "chosen_date": (
                date_value.isoformat()
                if date_value is not None
                else ""
            ),
            "priority_reason": reason
        }

    ############################################################

    def _row_values(self, row):

        if row is None:
            return {}

        if isinstance(row, dict):
            return row

        try:
            return {
                key: row[key]
                for key in row.keys()
            }
        except Exception:
            return {}

    ############################################################

    def _field_label(self, field):

        labels = {
            "first_seen_at": "first seen/imported timestamp",
            "capture_time": "capture metadata",
            "file_modified_at": "file modified timestamp",
            "file_created_at": "file created timestamp"
        }

        return labels.get(field, field.replace("_", " "))
