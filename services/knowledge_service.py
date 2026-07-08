from core.app_context import context
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
                "tags": ["community", "public_education", "children", "school"]
            },
            {
                "name": "Travelling Sparky",
                "category": "public_education",
                "description": "Public education program for safety visits and fire prevention messaging.",
                "tags": ["public_education", "fire_prevention", "school", "safety"]
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
                "tags": ["fire_prevention", "public_education", "october"]
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

    def label_for_opportunity(self, opportunity_type, fallback):

        program = self.program_for_opportunity(opportunity_type)

        if program:
            return f"{program['name']} {fallback}"

        if opportunity_type == "apparatus_showcase":
            apparatus = self.first_active("apparatus")

            if apparatus:
                return f"{apparatus['name']} Feature"

        return fallback

    ############################################################

    def caption_strategy(self, opportunity_type, fallback):

        profile = self.profile()
        program = self.program_for_opportunity(opportunity_type)
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

    def call_to_action(self, opportunity_type, fallback):

        profile = self.profile()
        department = profile.get(
            "department_name",
            "Morden Fire & Rescue"
        )
        community = profile.get(
            "community",
            "Morden"
        )
        program = self.program_for_opportunity(opportunity_type)

        if program:
            return (
                f"Follow {department} for {program['name']} updates "
                f"and practical safety information for {community}."
            )

        return fallback

    ############################################################

    def reasoning_context(self, opportunity_type):

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
        program = self.program_for_opportunity(opportunity_type)

        if program:
            parts.append(
                f"Relevant program: {program['name']}."
            )

        apparatus = self.first_active("apparatus")

        if apparatus and opportunity_type == "apparatus_showcase":
            parts.append(
                f"Apparatus focus: {apparatus['name']}."
            )

        return " ".join(parts)

    ############################################################

    def program_for_opportunity(self, opportunity_type):

        tags = self.OPPORTUNITY_TAGS.get(
            opportunity_type,
            ()
        )
        tokens = {
            self._token(tag)
            for tag in tags
        }

        for program in self.items("programs"):

            if not program.get("active"):
                continue

            category = self._token(
                program.get("category")
            )

            if category in tokens:
                return program

        for program in self.items("programs"):

            if not program.get("active"):
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

    def first_active(self, table):

        for item in self.items(table):

            if item.get("active"):
                return item

        return None

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )
