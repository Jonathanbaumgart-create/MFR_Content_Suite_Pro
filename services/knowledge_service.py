from core.app_context import context
from datetime import date, datetime
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class KnowledgeService:

    TABLES = (
        "apparatus",
        "programs",
        "annual_events",
        "locations",
        "response_area",
        "community_partners"
    )

    DEFAULT_PROFILE = {
        "department_name": "Morden Fire & Rescue",
        "short_name": "MFR",
        "community": "Morden",
        "province": "Manitoba",
        "voice": "professional, friendly, public-safety focused"
    }

    DEFAULT_ITEMS = {
        "programs": (
            {
                "name": "Hydrant Heroes",
                "category": "community",
                "description": "Community-facing fire service education and engagement program.",
                "tags": ["community", "public_education", "children", "school"],
                "active_months": [12, 1, 2],
                "inactive_months": [3, 4, 5, 6, 7, 8, 9, 10, 11],
                "season": "winter",
                "audience": "community",
                "notes": "Winter community education content."
            },
            {
                "name": "Travelling Sparky",
                "category": "public_education",
                "description": "Public education program for safety visits and fire prevention messaging.",
                "tags": ["public_education", "fire_prevention", "school", "safety"],
                "active_months": [11, 12, 1, 2, 3, 4, 5, 6],
                "inactive_months": [7, 8, 9, 10],
                "audience": "Grade 1 students",
                "school_year_program": True,
                "notes": "School-year program active roughly November through June."
            }
        ),
        "apparatus": (
            {
                "name": "Engine 1",
                "category": "engine",
                "description": "Front-line engine used for fire response and public education appearances.",
                "tags": ["engine", "apparatus", "fire_response"]
            },
        ),
        "annual_events": (
            {
                "name": "Fire Prevention Week",
                "category": "public_education",
                "description": "Annual October campaign focused on fire prevention and home safety.",
                "tags": ["fire_prevention", "public_education", "october"],
                "active_months": [9, 10],
                "event_date": "October",
                "campaign_window": "September through October",
                "notes": "September prep window and October campaign content."
            },
            {
                "name": "Canada Day Fireworks",
                "category": "community",
                "description": "Canada Day fireworks safety and community event messaging.",
                "tags": ["community", "holiday", "fireworks", "safety"],
                "active_months": [6, 7],
                "event_date": "July 1",
                "campaign_window": "June through July",
                "notes": "Fireworks safety and Canada Day community messaging."
            },
        ),
        "locations": (
            {
                "name": "Morden Fire Hall",
                "category": "station",
                "description": "Primary station and community contact point for Morden Fire & Rescue.",
                "tags": ["station", "community", "morden"]
            },
        ),
        "response_area": (
            {
                "name": "Morden",
                "category": "primary",
                "description": "Primary response community served by Morden Fire & Rescue.",
                "tags": ["morden", "response_area"]
            },
        ),
        "community_partners": (
            {
                "name": "City of Morden",
                "category": "municipal",
                "description": "Municipal partner for public safety and community messaging.",
                "tags": ["morden", "municipal", "community"]
            },
        )
    }

    OPPORTUNITY_TAGS = {
        "community_appreciation": ("community",),
        "fire_prevention_week": ("fire_prevention", "public_education"),
        "smoke_alarm_reminder": ("public_education", "safety"),
        "recruitment": ("recruitment", "training"),
        "training_highlight": ("training",),
        "apparatus_showcase": ("apparatus", "engine"),
        "volunteer_recognition": ("community", "recruitment"),
        "behind_the_scenes": ("station", "training"),
        "heat_warning": ("public_education", "safety"),
        "storm_safety": ("public_education", "safety"),
        "water_safety": ("public_education", "safety"),
        "holiday_safety": ("public_education", "safety")
    }

    MONTH_NAMES = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12
    }

    def __init__(self, database=None):

        self.db = database or context.database
        self.ensure_defaults()

    ############################################################

    def ensure_defaults(self):

        profile = self.db.department_profile()

        for key, value in self.DEFAULT_PROFILE.items():

            if key not in profile:
                self.db.save_department_profile_value(
                    key,
                    value
                )

        for table, defaults in self.DEFAULT_ITEMS.items():

            if self.db.knowledge_items(table):
                self._ensure_default_timing(table, defaults)
                continue

            for item in defaults:
                self.db.save_knowledge_item(
                    table,
                    item
                )

        logger.info("Department knowledge defaults verified")

    ############################################################

    def profile(self):

        profile = self.db.department_profile()

        for key, value in self.DEFAULT_PROFILE.items():
            profile.setdefault(
                key,
                value
            )

        return profile

    ############################################################

    def save_profile(self, values):

        for key, value in values.items():
            self.db.save_department_profile_value(
                key,
                value
            )

    ############################################################

    def items(self, table):

        return self.db.knowledge_items(table)

    ############################################################

    def save_item(self, table, item):

        return self.db.save_knowledge_item(
            table,
            item
        )

    ############################################################

    def delete_item(self, table, item_id):

        self.db.delete_knowledge_item(
            table,
            item_id
        )

    ############################################################

    def snapshot(self):

        return {
            "profile": self.profile(),
            "apparatus": self.items("apparatus"),
            "programs": self.items("programs"),
            "annual_events": self.items("annual_events"),
            "locations": self.items("locations"),
            "response_area": self.items("response_area"),
            "community_partners": self.items("community_partners")
        }

    ############################################################

    def statistics(self):

        counts = {
            "programs": len(self.items("programs")),
            "apparatus": len(self.items("apparatus")),
            "events": len(self.items("annual_events")),
            "partners": len(self.items("community_partners")),
            "locations": (
                len(self.items("locations")) +
                len(self.items("response_area"))
            ),
            "documents_imported": self.db.knowledge_document_count()
        }
        required = (
            "programs",
            "apparatus",
            "events",
            "partners",
            "locations"
        )
        complete = sum(
            1
            for key in required
            if counts[key] > 0
        )
        counts["knowledge_completeness_score"] = int(
            (complete / len(required)) * 100
        )

        return counts

    ############################################################

    def apply_import(self, import_result):

        from services.knowledge_ingestion_service import KnowledgeIngestionService

        service = KnowledgeIngestionService(
            database=self.db,
            knowledge_service=self
        )

        return service.apply_import(import_result)

    ############################################################

    def label_for_opportunity(
        self,
        opportunity_type,
        fallback,
        today=None,
        explicit_program=None
    ):

        program = self.program_for_opportunity(
            opportunity_type,
            today=today,
            explicit_program=explicit_program
        )

        if program:
            return f"{program['name']} {fallback}"

        if opportunity_type == "apparatus_showcase":
            apparatus = self.first_active("apparatus")

            if apparatus:
                return f"{apparatus['name']} Feature"

        return fallback

    ############################################################

    def caption_strategy(
        self,
        opportunity_type,
        fallback,
        today=None,
        explicit_program=None
    ):

        profile = self.profile()
        program = self.program_for_opportunity(
            opportunity_type,
            today=today,
            explicit_program=explicit_program
        )
        department = profile.get(
            "department_name",
            "Morden Fire & Rescue"
        )

        if program:
            return (
                f"{fallback} featuring {program['name']} from {department}"
            )

        return f"{fallback} from {department}"

    ############################################################

    def call_to_action(
        self,
        opportunity_type,
        fallback,
        today=None,
        explicit_program=None
    ):

        profile = self.profile()
        department = profile.get(
            "department_name",
            "Morden Fire & Rescue"
        )
        community = profile.get(
            "community",
            "Morden"
        )
        program = self.program_for_opportunity(
            opportunity_type,
            today=today,
            explicit_program=explicit_program
        )

        if program:
            return (
                f"Follow {department} for {program['name']} updates "
                f"and practical safety information for {community}."
            )

        return fallback

    ############################################################

    def reasoning_context(
        self,
        opportunity_type,
        today=None,
        explicit_program=None
    ):

        profile = self.profile()
        parts = [
            (
                "Department context: " +
                profile.get(
                    "department_name",
                    "Morden Fire & Rescue"
                )
            )
        ]
        program = self.program_for_opportunity(
            opportunity_type,
            today=today,
            explicit_program=explicit_program
        )

        if program:
            parts.append(
                f"Relevant active program: {program['name']}."
            )

        apparatus = self.first_active("apparatus")

        if apparatus and opportunity_type == "apparatus_showcase":
            parts.append(
                f"Apparatus focus: {apparatus['name']}."
            )

        return " ".join(parts)

    ############################################################

    def program_for_opportunity(
        self,
        opportunity_type,
        today=None,
        explicit_program=None,
        include_inactive=False
    ):

        tags = self.OPPORTUNITY_TAGS.get(
            opportunity_type,
            ()
        )
        tokens = {
            self._token(tag)
            for tag in tags
        }

        explicit_name = self._token(
            explicit_program.get("name")
            if isinstance(explicit_program, dict)
            else explicit_program
        )

        for program in self.items("programs"):

            if not program.get("active"):
                continue

            if explicit_name and self._token(program.get("name")) == explicit_name:
                return program

            if not include_inactive and not self.program_status(
                program,
                today=today
            )["active"]:
                continue

            category = self._token(
                program.get("category")
            )

            if category in tokens:
                return program

        for program in self.items("programs"):

            if not program.get("active"):
                continue

            if not include_inactive and not self.program_status(
                program,
                today=today
            )["active"]:
                continue

            item_tags = {
                self._token(tag)
                for tag in program.get("tags", [])
            }
            category = self._token(
                program.get("category")
            )

            if category in tokens or item_tags & tokens:
                return program

        return None

    ############################################################

    def explicit_program_from_prompt(self, prompt):

        text = self._token(prompt)

        if not text:
            return None

        for program in self.items("programs"):
            name = self._token(program.get("name"))

            if name and name in text:
                return program

        for event in self.items("annual_events"):
            name = self._token(event.get("name"))

            if name and name in text:
                return event

        return None

    ############################################################

    def opportunity_keys_for_knowledge_item(self, item):

        if not item:
            return []

        category = self._token(item.get("category"))
        tags = {
            self._token(tag)
            for tag in item.get("tags", [])
        }
        values = tags | {category}
        keys = []

        for opportunity, opportunity_tags in self.OPPORTUNITY_TAGS.items():
            tokens = {
                self._token(tag)
                for tag in opportunity_tags
            }

            if values & tokens:
                keys.append(opportunity)

        return keys or ["general_engagement"]

    ############################################################

    def program_timing_context(
        self,
        opportunity_type,
        today=None,
        explicit_program=None
    ):

        today = self._coerce_date(today)
        context = {
            "active_program": None,
            "out_of_season": [],
            "upcoming": [],
            "explicit_program": explicit_program
        }

        program = self.program_for_opportunity(
            opportunity_type,
            today=today,
            explicit_program=explicit_program
        )

        if program:
            context["active_program"] = {
                "program": program,
                "status": self.program_status(
                    program,
                    today=today
                )
            }

        for candidate in self._program_candidates(opportunity_type):
            status = self.program_status(
                candidate,
                today=today
            )

            if status["active"]:
                continue

            entry = {
                "program": candidate,
                "status": status
            }

            if status["upcoming"]:
                context["upcoming"].append(entry)
            else:
                context["out_of_season"].append(entry)

        return context

    ############################################################

    def program_status(self, program, today=None):

        today = self._coerce_date(today)
        month = today.month
        active_months = self._month_values(
            program.get("active_months")
        )
        inactive_months = self._month_values(
            program.get("inactive_months")
        )
        season = self._token(
            program.get("season")
        )
        active = True

        if active_months:
            active = month in active_months

        if inactive_months and month in inactive_months:
            active = False

        if season and not active_months:
            active = season == self._season(today)

        upcoming = False

        if active_months and not active:
            upcoming = self._months_until_active(
                month,
                active_months
            ) <= 3

        if season and not active:
            upcoming = upcoming or season in self._upcoming_seasons(today)

        month_name = today.strftime("%B")
        active_text = self._month_text(active_months)

        if active:
            reason = (
                f"{program['name']} is active in {month_name}."
                if active_text
                else f"{program['name']} is active."
            )
        else:
            reason = (
                f"{program['name']} is not recommended today because "
                f"{month_name} is outside its active window"
            )

            if active_text:
                reason += f" ({active_text})"

            if program.get("school_year_program"):
                reason += " and it is a school-year program"

            reason += "."

        return {
            "active": active,
            "upcoming": upcoming,
            "month": month,
            "active_months": active_months,
            "inactive_months": inactive_months,
            "season": program.get("season", ""),
            "reason": reason
        }

    ############################################################

    def event_status(self, event, today=None):

        return self.program_status(
            event,
            today=today
        )

    ############################################################

    def first_active(self, table):

        for item in self.items(table):

            if item.get("active"):
                return item

        return None

    ############################################################

    def _ensure_default_timing(self, table, defaults):

        existing = {
            self._token(item.get("name")): item
            for item in self.db.knowledge_items(table)
        }

        for default in defaults:
            item = existing.get(
                self._token(default.get("name"))
            )

            if not item:
                self.db.save_knowledge_item(
                    table,
                    default
                )
                continue

            changed = False

            for key in (
                "active_months",
                "inactive_months",
                "season",
                "event_date",
                "campaign_window",
                "audience",
                "school_year_program",
                "notes"
            ):

                if item.get(key):
                    continue

                if key not in default:
                    continue

                item[key] = default[key]
                changed = True

            if changed:
                self.db.save_knowledge_item(
                    table,
                    item
                )

    ############################################################

    def _program_candidates(self, opportunity_type):

        tags = self.OPPORTUNITY_TAGS.get(
            opportunity_type,
            ()
        )
        tokens = {
            self._token(tag)
            for tag in tags
        }
        candidates = []

        for program in self.items("programs"):

            if not program.get("active"):
                continue

            category = self._token(
                program.get("category")
            )
            item_tags = {
                self._token(tag)
                for tag in program.get("tags", [])
            }

            if category in tokens or item_tags & tokens:
                candidates.append(program)

        return candidates

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

    def _month_values(self, values):

        months = []

        for value in values or []:
            month = None

            try:
                month = int(value)
            except Exception:
                month = self.MONTH_NAMES.get(
                    str(value).strip().lower()
                )

            if month and 1 <= month <= 12 and month not in months:
                months.append(month)

        return months

    ############################################################

    def _month_text(self, months):

        if not months:
            return ""

        names = [
            date(2000, month, 1).strftime("%B")
            for month in months
        ]

        return ", ".join(names)

    ############################################################

    def _months_until_active(self, current_month, active_months):

        return min(
            (
                (month - current_month) % 12
                for month in active_months
            ),
            default=12
        )

    ############################################################

    def _season(self, today):

        if today.month in (12, 1, 2):
            return "winter"

        if today.month in (3, 4, 5):
            return "spring"

        if today.month in (6, 7, 8):
            return "summer"

        return "fall"

    ############################################################

    def _upcoming_seasons(self, today):

        order = ("winter", "spring", "summer", "fall")
        current = self._season(today)
        index = order.index(current)

        return {
            order[(index + 1) % len(order)]
        }

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )
