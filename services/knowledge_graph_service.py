from core.app_context import context
from services.knowledge_service import KnowledgeService
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class KnowledgeGraphService:

    ENTITY_TYPES = (
        "Apparatus",
        "Equipment",
        "Buildings",
        "Stations",
        "Schools",
        "Parks",
        "Hospitals",
        "Businesses",
        "Neighbourhoods",
        "Roads",
        "Districts",
        "Hydrants",
        "Firefighters",
        "Officer Roles",
        "Programs",
        "Campaigns",
        "Training Evolutions",
        "Incident Types",
        "Operational Skills",
        "Community Partners",
        "Mutual Aid Partners",
        "Special Teams",
        "Public Education Topics",
        "Seasonal Topics",
        "Media Collections"
    )

    CATEGORIES = (
        "operations",
        "communications",
        "public_education",
        "training",
        "apparatus",
        "community",
        "seasonal",
        "location",
        "media"
    )

    DEFAULT_ENTITIES = (
        {
            "name": "Ground Ladder",
            "type": "Equipment",
            "description": "Portable ladder used for access, rescue, and training.",
            "aliases": ["ladder", "ground_ladder"],
            "confidence": 95
        },
        {
            "name": "Attack Hose",
            "type": "Equipment",
            "description": "Hose line used for fire attack and hose evolutions.",
            "aliases": ["attack_hose", "hose", "hose line"],
            "confidence": 95
        },
        {
            "name": "SCBA",
            "type": "Equipment",
            "description": "Self-contained breathing apparatus used in hazardous atmospheres.",
            "aliases": ["air pack", "breathing apparatus"],
            "confidence": 95
        },
        {
            "name": "Ladder Operations",
            "type": "Operational Skills",
            "description": "Fire service ladder deployment, placement, and climbing operations.",
            "aliases": ["ladder_operations", "ladder evolution"],
            "confidence": 95
        },
        {
            "name": "Fire Attack",
            "type": "Operational Skills",
            "description": "Coordinated hose and nozzle operations for fire control.",
            "aliases": ["fire_attack", "hose evolution"],
            "confidence": 95
        },
        {
            "name": "Search",
            "type": "Operational Skills",
            "description": "Search and survival skills including SCBA confidence training.",
            "aliases": ["search", "scba confidence"],
            "confidence": 90
        },
        {
            "name": "Training Tuesday",
            "type": "Campaigns",
            "description": "Recurring communications opportunity for training media.",
            "aliases": ["training_tuesday", "training highlight"],
            "confidence": 95
        },
        {
            "name": "Recruitment",
            "type": "Campaigns",
            "description": "Communications opportunity focused on future members.",
            "aliases": ["recruitment", "join", "volunteer"],
            "confidence": 95
        },
        {
            "name": "Travelling Sparky",
            "type": "Programs",
            "description": "School-year public education program.",
            "aliases": ["travelling_sparky", "sparky"],
            "confidence": 95
        },
        {
            "name": "Hydrant Heroes",
            "type": "Programs",
            "description": "Winter community education and engagement program.",
            "aliases": ["hydrant_heroes"],
            "confidence": 95
        },
        {
            "name": "Winter",
            "type": "Seasonal Topics",
            "description": "Winter and ice safety communications season.",
            "aliases": ["winter", "winter_safety"],
            "confidence": 95
        },
        {
            "name": "Grade 1 Students",
            "type": "Public Education Topics",
            "description": "Audience for school public education programming.",
            "aliases": ["grade_1", "students", "children"],
            "confidence": 90
        },
        {
            "name": "Training Photos",
            "type": "Media Collections",
            "description": "Media useful for training, recruitment, and annual reporting.",
            "aliases": ["training_photos", "training media"],
            "confidence": 90
        }
    )

    DEFAULT_RELATIONSHIPS = (
        ("Ground Ladder", "related_to", "Ladder Operations", 95, "Equipment supports ladder operations."),
        ("Ladder Operations", "related_to", "Training Tuesday", 92, "Ladder training is strong Training Tuesday content."),
        ("Ladder Operations", "related_to", "Recruitment", 88, "Visible skills help explain volunteer training."),
        ("Attack Hose", "related_to", "Fire Attack", 95, "Attack hose is a fire attack signal."),
        ("Fire Attack", "related_to", "Training Tuesday", 90, "Hose evolutions are recurring training content."),
        ("SCBA", "related_to", "Search", 88, "SCBA supports search and confidence training."),
        ("Search", "related_to", "Training Tuesday", 86, "Search training supports training content."),
        ("Training Tuesday", "uses", "Training Photos", 90, "Training photos support recurring campaign content."),
        ("Travelling Sparky", "targets", "Grade 1 Students", 95, "Program audience relationship."),
        ("Hydrant Heroes", "runs_during", "Winter", 95, "Hydrant Heroes is winter-aligned."),
        ("Hydrant Heroes", "related_to", "Recruitment", 70, "Community programs can support recruitment awareness.")
    )

    def __init__(self, database=None, knowledge_service=None):

        self.db = database or context.database
        self.knowledge = knowledge_service or KnowledgeService(
            database=self.db
        )
        self.ensure_defaults()

    ############################################################

    def ensure_defaults(self):

        if not self.db:
            return

        self.db.ensure_knowledge_graph_defaults(
            self.ENTITY_TYPES,
            self.CATEGORIES
        )
        self._seed_entities()
        self._seed_department_knowledge()
        self._seed_relationships()

        logger.info("Knowledge graph defaults verified")

    ############################################################

    def create_entity(
        self,
        name,
        entity_type,
        description="",
        aliases=None,
        confidence=80,
        active=True,
        source="manual"
    ):

        entity = {
            "name": name,
            "type": entity_type,
            "description": description,
            "aliases": aliases or [],
            "confidence": confidence,
            "active": active,
            "source": source
        }

        return self.db.save_graph_entity(entity)

    ############################################################

    def create_relationship(
        self,
        source,
        relationship_type,
        target,
        confidence=80,
        description="",
        active=True,
        source_name="manual"
    ):

        source_entity = self.resolve_entity(source)
        target_entity = self.resolve_entity(target)

        if not source_entity or not target_entity:
            return None

        relationship = {
            "source_entity_id": source_entity["id"],
            "target_entity_id": target_entity["id"],
            "relationship_type": self._token(relationship_type),
            "description": description,
            "confidence": confidence,
            "active": active,
            "source": source_name
        }

        return self.db.save_graph_relationship(relationship)

    ############################################################

    def resolve_entity(self, value):

        return self.db.graph_entity_by_name_or_alias(value)

    ############################################################

    def search(self, query="", limit=25):

        return self.db.search_graph_entities(
            query,
            limit=limit
        )

    ############################################################

    def related_entities(self, entity, depth=1, limit=50):

        resolved = self.resolve_entity(entity)

        if not resolved:
            return []

        return self.db.graph_related_entities(
            resolved["id"],
            depth=depth,
            limit=limit
        )

    ############################################################

    def expand_terms(self, terms, depth=2):

        expanded = {}

        for term in terms or []:
            entity = self.resolve_entity(term)

            if not entity:
                continue

            values = [
                {
                    "name": entity["name"],
                    "type": entity["type"],
                    "relationship": "self",
                    "confidence": entity["confidence"],
                    "reason": "Matched knowledge graph entity or alias."
                }
            ]
            values.extend(
                self.related_entities(
                    entity["name"],
                    depth=depth
                )
            )
            expanded[self._token(term)] = values

        logger.info(
            "Expanded knowledge graph terms terms=%s matches=%s",
            len(terms or []),
            sum(len(value) for value in expanded.values())
        )

        return expanded

    ############################################################

    def reasoning_context(self, terms):

        expansions = self.expand_terms(
            terms,
            depth=2
        )
        intents = []
        skills = []
        campaigns = []
        evidence = []

        for source, rows in expansions.items():
            for row in rows:
                entity_type = row.get("type", "")
                name = row.get("name", "")
                token = self._token(name)

                if entity_type == "Operational Skills":
                    skills.append(token)

                if entity_type == "Campaigns":
                    campaigns.append(token)
                    intents.append(token)

                if entity_type == "Programs":
                    intents.append(token)

                if row.get("relationship") != "self":
                    evidence.append(
                        {
                            "source": source,
                            "entity": name,
                            "relationship": row.get("relationship", ""),
                            "confidence": row.get("confidence", 0),
                            "reason": row.get("reason", "")
                        }
                    )

        return {
            "expanded_terms": expansions,
            "operational_skills": self._unique(skills),
            "communications_intent": self._unique(intents),
            "campaigns": self._unique(campaigns),
            "evidence": evidence[:10],
            "reasoning": self._reasoning_lines(evidence)
        }

    ############################################################

    def health(self):

        return self.db.knowledge_graph_health()

    ############################################################

    def top_entity_types(self, limit=8):

        return self.db.graph_top_entity_types(limit=limit)

    ############################################################

    def recent_entities(self, limit=8):

        return self.db.graph_recent_entities(limit=limit)

    ############################################################

    def relationships(self, limit=50):

        return self.db.graph_relationships(limit=limit)

    ############################################################

    def _seed_entities(self):

        for entity in self.DEFAULT_ENTITIES:
            existing = self.resolve_entity(entity["name"])

            if existing:
                continue

            self.create_entity(
                entity["name"],
                entity["type"],
                description=entity.get("description", ""),
                aliases=entity.get("aliases", []),
                confidence=entity.get("confidence", 80),
                source="default"
            )

    ############################################################

    def _seed_department_knowledge(self):

        mapping = {
            "apparatus": "Apparatus",
            "programs": "Programs",
            "annual_events": "Campaigns",
            "locations": "Buildings",
            "response_area": "Districts",
            "community_partners": "Community Partners"
        }

        for table, entity_type in mapping.items():
            for item in self.knowledge.items(table):

                if not item.get("active"):
                    continue

                if self.resolve_entity(item.get("name")):
                    continue

                self.create_entity(
                    item.get("name", ""),
                    entity_type,
                    description=item.get("description", ""),
                    aliases=item.get("tags", []),
                    confidence=85,
                    source=f"department_knowledge:{table}"
                )

    ############################################################

    def _seed_relationships(self):

        for source, relationship, target, confidence, description in self.DEFAULT_RELATIONSHIPS:
            self.create_relationship(
                source,
                relationship,
                target,
                confidence=confidence,
                description=description,
                source_name="default"
            )

    ############################################################

    def _reasoning_lines(self, evidence):

        if not evidence:
            return []

        lines = []

        for row in evidence[:5]:
            lines.append(
                (
                    f"Knowledge graph connects {row['source']} to "
                    f"{row['entity']} via {row['relationship']}."
                )
            )

        return lines

    ############################################################

    def _token(self, value):

        return str(value or "").strip().lower().replace(
            " ",
            "_"
        )

    ############################################################

    def _unique(self, values):

        unique = []
        seen = set()

        for value in values:
            value = self._token(value)

            if not value or value in seen:
                continue

            seen.add(value)
            unique.append(value)

        return unique
