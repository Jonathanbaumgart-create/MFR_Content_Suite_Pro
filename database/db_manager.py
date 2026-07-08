import sqlite3
from pathlib import Path
import json

from services.logging_service import LoggingService


logger = LoggingService.get_logger("database")


class DatabaseManager:

    def __init__(self):

        Path("database").mkdir(exist_ok=True)

        self.db = Path("database") / "mfr_content.db"

        self.initialize()

    ############################################################

    def connection(self):

        return sqlite3.connect(self.db)

    ############################################################

    def initialize(self):

        conn = self.connection()

        cur = conn.cursor()

        ########################################################
        # Libraries
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS libraries(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            path TEXT UNIQUE,

            enabled INTEGER DEFAULT 1,

            last_scan TEXT,

            media_count INTEGER DEFAULT 0

        )

        """)

        ########################################################
        # Media
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS media(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            library_id INTEGER,

            filename TEXT,

            path TEXT UNIQUE,

            extension TEXT,

            media_type TEXT,

            filesize INTEGER,

            sha256 TEXT UNIQUE,

            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        ########################################################
        # AI Analysis
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS ai_analysis(

            media_id INTEGER PRIMARY KEY,

            description TEXT,

            scene_type TEXT,

            activity TEXT,

            people_count INTEGER,

            apparatus TEXT,

            equipment TEXT,

            keywords TEXT,

            community_score INTEGER,

            recruitment_score INTEGER,

            education_score INTEGER,

            technical_score INTEGER,

            overall_score INTEGER,

            facebook_caption TEXT,

            instagram_caption TEXT,

            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            model TEXT

        )

        """)

        ########################################################
        # Media Intelligence
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS media_intelligence(

            media_id INTEGER PRIMARY KEY,

            normalized_scene TEXT,

            incident_type TEXT,

            primary_activity TEXT,

            apparatus_tags TEXT,

            equipment_tags TEXT,

            ppe_tags TEXT,

            people_tags TEXT,

            content_tags TEXT,

            content_themes TEXT,

            recommended_uses TEXT,

            search_text TEXT,

            intelligence_score INTEGER,

            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            source_model TEXT

        )

        """)

        self._ensure_ai_analysis_columns(cur)
        self._ensure_media_intelligence_columns(cur)
        self._ensure_indexes(cur)

        conn.commit()

        conn.close()

    ############################################################

    def add_library(self, name, path):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR IGNORE INTO libraries(

            name,

            path

        )

        VALUES(?,?)

        """,

        (

            name,

            path

        ))

        conn.commit()

        conn.close()

    ############################################################

    def library_exists(self, path):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(

            "SELECT id FROM libraries WHERE path=?",

            (path,)

        )

        exists = cur.fetchone() is not None

        conn.close()

        return exists

    ############################################################

    def get_libraries(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            name,

            path,

            media_count

        FROM libraries

        ORDER BY name

        """)

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def add_media(self, media):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR IGNORE INTO media(

            filename,

            path,

            extension,

            media_type,

            filesize,

            sha256

        )

        VALUES(?,?,?,?,?,?)

        """,

        (

            media["filename"],

            media["path"],

            media["extension"],

            media["type"],

            media["size"],

            media["sha256"]

        ))

        inserted = cur.rowcount > 0

        conn.commit()

        conn.close()

        return inserted

    ############################################################

    def get_media_by_path(self, path):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            filename,

            path,

            sha256

        FROM media

        WHERE path=?

        """,

        (

            path,

        ))

        row = cur.fetchone()

        conn.close()

        return row

    ############################################################

    def get_media_by_sha256(self, sha256):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            filename,

            path,

            sha256

        FROM media

        WHERE sha256=?

        """,

        (

            sha256,

        ))

        row = cur.fetchone()

        conn.close()

        return row

    ############################################################

    def media_identity_sets(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            path,

            sha256

        FROM media

        """)

        paths = set()
        hashes = set()

        for path, sha256 in cur.fetchall():

            if path:
                paths.add(path)

            if sha256:
                hashes.add(sha256)

        conn.close()

        return paths, hashes

    ############################################################

    def get_media(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            filename,

            path,

            media_type

        FROM media

        ORDER BY filename

        """)

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def get_media_by_ids(self, media_ids):

        if not media_ids:
            return []

        conn = self.connection()

        cur = conn.cursor()

        placeholders = ",".join("?" for _ in media_ids)

        cur.execute(f"""

        SELECT

            id,

            filename,

            path,

            media_type

        FROM media

        WHERE id IN ({placeholders})

        ORDER BY filename

        """,

        tuple(media_ids))

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def get_media_page(self, limit, offset=0):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            filename,

            path,

            media_type

        FROM media

        ORDER BY filename

        LIMIT ? OFFSET ?

        """,

        (

            limit,

            offset

        ))

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def media_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM media")

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def get_media_under_path(self, folder_path):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            filename,

            path,

            media_type

        FROM media

        WHERE path LIKE ?

        ORDER BY filename

        """,

        (

            f"{folder_path}%",

        ))

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def media_under_path_count(self, folder_path):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(*)

        FROM media

        WHERE path LIKE ?
        AND media_type='image'

        """,

        (

            f"{folder_path}%",

        ))

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def get_media_under_path_page(self, folder_path, limit, offset=0):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            filename,

            path,

            media_type

        FROM media

        WHERE path LIKE ?
        AND media_type='image'

        ORDER BY filename

        LIMIT ? OFFSET ?

        """,

        (

            f"{folder_path}%",

            limit,

            offset

        ))

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def get_image_media(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            filename,

            path,

            media_type

        FROM media

        WHERE media_type='image'

        ORDER BY filename

        """)

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def image_media_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM media WHERE media_type='image'"
        )

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def get_image_media_page(self, limit, offset=0):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            id,

            filename,

            path,

            media_type

        FROM media

        WHERE media_type='image'

        ORDER BY filename

        LIMIT ? OFFSET ?

        """,

        (

            limit,

            offset

        ))

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def analyzed_media_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM ai_analysis")

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def media_intelligence_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM media_intelligence")

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def media_needing_analysis_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(*)

        FROM media

        LEFT JOIN ai_analysis
        ON ai_analysis.media_id = media.id

        WHERE media.media_type='image'
        AND ai_analysis.media_id IS NULL

        """)

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def media_needing_intelligence_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(*)

        FROM ai_analysis

        LEFT JOIN media_intelligence
        ON media_intelligence.media_id = ai_analysis.media_id

        WHERE media_intelligence.media_id IS NULL
        AND (
            ai_analysis.failure_reason IS NULL OR
            ai_analysis.failure_reason=''
        )

        """)

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def ai_metrics(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            COUNT(
                CASE
                    WHEN failure_reason IS NULL OR failure_reason=''
                    THEN 1
                END
            ),

            AVG(
                CASE
                    WHEN failure_reason IS NULL OR failure_reason=''
                    THEN analysis_duration
                END
            ),

            MAX(last_analyzed)

        FROM ai_analysis

        """)

        row = cur.fetchone()

        conn.close()

        return {
            "total_analyzed": row[0] or 0,
            "average_analysis_time": row[1] or 0,
            "last_analyzed": row[2] or ""
        }

    ############################################################

    def analysis_exists(self, media_id):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(

            "SELECT media_id FROM ai_analysis WHERE media_id=?",

            (media_id,)

        )

        exists = cur.fetchone() is not None

        conn.close()

        return exists

    ############################################################

    def get_ai_analysis(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM ai_analysis

        WHERE media_id=?

        """,

        (media_id,))

        row = cur.fetchone()

        conn.close()

        if row is None:
            return None

        return self._analysis_from_row(row)

    ############################################################

    def save_ai_analysis(self, media_id, analysis):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR REPLACE INTO ai_analysis(

            media_id,

            description,

            scene_type,

            activity,

            people_count,

            apparatus,

            equipment,

            keywords,

            community_score,

            recruitment_score,

            education_score,

            technical_score,

            overall_score,

            facebook_caption,

            instagram_caption,

            analyzed_at,

            model,

            analysis_duration,

            provider,

            retry_count,

            failure_reason,

            last_analyzed

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?,?,?,?,?,CURRENT_TIMESTAMP)

        """,

        (

            media_id,

            analysis.get("description"),

            analysis.get("scene_type"),

            analysis.get("activity"),

            self._to_int(analysis.get("people_count")),

            self._to_json(analysis.get("apparatus")),

            self._to_json(analysis.get("equipment")),

            self._to_json(analysis.get("keywords")),

            self._to_int(analysis.get("community_score")),

            self._to_int(analysis.get("recruitment_score")),

            self._to_int(analysis.get("education_score")),

            self._to_int(analysis.get("technical_score")),

            self._to_int(analysis.get("overall_score")),

            analysis.get("facebook_caption"),

            analysis.get("instagram_caption"),

            analysis.get("model"),

            self._to_float(analysis.get("analysis_duration")),

            analysis.get("provider"),

            self._to_int(analysis.get("retry_count")),

            analysis.get("failure_reason")

        ))

        conn.commit()

        conn.close()

    ############################################################

    def save_ai_failure(self, media_id, failure):

        existing = self.get_ai_analysis(media_id)

        if existing and not existing.get("failure_reason"):
            logger.error(
                "AI failure preserved existing analysis media_id=%s provider=%s reason=%s",
                media_id,
                failure.get("provider"),
                failure.get("failure_reason")
            )
            return

        analysis = existing or {
            "description": "",
            "scene_type": "",
            "activity": "",
            "people_count": 0,
            "apparatus": [],
            "equipment": [],
            "keywords": [],
            "community_score": 0,
            "recruitment_score": 0,
            "education_score": 0,
            "technical_score": 0,
            "overall_score": 0,
            "facebook_caption": "",
            "instagram_caption": "",
            "model": failure.get("model")
        }

        analysis["analysis_duration"] = failure.get("analysis_duration")
        analysis["provider"] = failure.get("provider")
        analysis["retry_count"] = failure.get("retry_count")
        analysis["failure_reason"] = failure.get("failure_reason")
        analysis["model"] = failure.get("model")

        self.save_ai_analysis(
            media_id,
            analysis
        )

    ############################################################

    def clear_mock_analysis(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        DELETE FROM media_intelligence

        WHERE source_model LIKE 'mock%'
        OR media_id IN (
            SELECT media_id
            FROM ai_analysis
            WHERE provider='mock'
            OR model LIKE 'mock%'
            OR description LIKE 'MOCK TEST ANALYSIS%'
        )

        """)

        intelligence_deleted = cur.rowcount

        cur.execute("""

        DELETE FROM ai_analysis

        WHERE provider='mock'
        OR model LIKE 'mock%'
        OR description LIKE 'MOCK TEST ANALYSIS%'

        """)

        analysis_deleted = cur.rowcount

        conn.commit()

        conn.close()

        logger.info(
            "Cleared mock analysis rows analysis=%s intelligence=%s",
            analysis_deleted,
            intelligence_deleted
        )

        return {
            "analysis_deleted": analysis_deleted,
            "intelligence_deleted": intelligence_deleted
        }

    ############################################################

    def save_media_intelligence(self, media_id, intelligence):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR REPLACE INTO media_intelligence(

            media_id,

            normalized_scene,

            incident_type,

            primary_activity,

            apparatus_tags,

            equipment_tags,

            ppe_tags,

            people_tags,

            content_tags,

            content_themes,

            recommended_uses,

            search_text,

            intelligence_score,

            generated_at,

            source_model

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?)

        """,

        (

            media_id,

            intelligence.get("normalized_scene"),

            intelligence.get("incident_type"),

            intelligence.get("primary_activity"),

            self._to_json(intelligence.get("apparatus_tags")),

            self._to_json(intelligence.get("equipment_tags")),

            self._to_json(intelligence.get("ppe_tags")),

            self._to_json(intelligence.get("people_tags")),

            self._to_json(intelligence.get("content_tags")),

            self._to_json(intelligence.get("content_themes")),

            self._to_json(intelligence.get("recommended_uses")),

            intelligence.get("search_text"),

            self._to_int(intelligence.get("intelligence_score")),

            intelligence.get("source_model")

        ))

        conn.commit()

        conn.close()

    ############################################################

    def get_media_intelligence(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM media_intelligence

        WHERE media_id=?

        """,

        (media_id,))

        row = cur.fetchone()

        conn.close()

        if row is None:
            return None

        return self._intelligence_from_row(row)

    ############################################################

    def media_intelligence_exists(self, media_id):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(

            "SELECT media_id FROM media_intelligence WHERE media_id=?",

            (media_id,)

        )

        exists = cur.fetchone() is not None

        conn.close()

        return exists

    ############################################################

    def get_media_needing_intelligence(self, limit=None):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        sql = """

        SELECT ai_analysis.*

        FROM ai_analysis

        LEFT JOIN media_intelligence
        ON media_intelligence.media_id = ai_analysis.media_id

        WHERE media_intelligence.media_id IS NULL
        AND (
            ai_analysis.failure_reason IS NULL OR
            ai_analysis.failure_reason=''
        )

        ORDER BY ai_analysis.last_analyzed DESC

        """

        params = ()

        if limit is not None:
            sql += " LIMIT ?"
            params = (self._to_int(limit),)

        cur.execute(sql, params)

        rows = cur.fetchall()

        conn.close()

        return [
            self._analysis_from_row(row)
            for row in rows
        ]

    ############################################################

    def search_intelligence(self, query, limit=100):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        pattern = f"%{query}%"

        cur.execute("""

        SELECT *

        FROM media_intelligence

        WHERE search_text LIKE ?
        OR content_tags LIKE ?
        OR content_themes LIKE ?
        OR recommended_uses LIKE ?

        ORDER BY intelligence_score DESC

        LIMIT ?

        """,

        (
            pattern,
            pattern,
            pattern,
            pattern,
            self._to_int(limit)
        ))

        rows = cur.fetchall()

        conn.close()

        return [
            self._intelligence_from_row(row)
            for row in rows
        ]

    ############################################################

    def get_media_by_incident_type(self, incident_type, limit=100):

        return self._media_by_intelligence_field(
            "incident_type",
            incident_type,
            limit
        )

    ############################################################

    def get_media_by_recommended_use(self, recommended_use, limit=100):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT

            media.id,

            media.filename,

            media.path,

            media.media_type

        FROM media

        JOIN media_intelligence
        ON media_intelligence.media_id = media.id

        WHERE media_intelligence.recommended_uses LIKE ?

        ORDER BY media.filename

        LIMIT ?

        """,

        (
            f"%{recommended_use}%",
            self._to_int(limit)
        ))

        rows = cur.fetchall()

        conn.close()

        return [
            (
                row["id"],
                row["filename"],
                row["path"],
                row["media_type"]
            )
            for row in rows
        ]

    ############################################################

    def intelligence_filter_counts(self, filters=None):

        filters = filters or {}

        return {
            "incident_type": self._intelligence_scalar_counts(
                "incident_type",
                filters
            ),
            "apparatus_tags": self._intelligence_json_counts(
                "apparatus_tags",
                filters
            ),
            "equipment_tags": self._intelligence_json_counts(
                "equipment_tags",
                filters
            ),
            "primary_activity": self._intelligence_scalar_counts(
                "primary_activity",
                filters
            ),
            "recommended_uses": self._intelligence_json_counts(
                "recommended_uses",
                filters
            ),
            "content_themes": self._intelligence_json_counts(
                "content_themes",
                filters
            ),
            "content_tags": self._intelligence_json_counts(
                "content_tags",
                filters
            )
        }

    ############################################################

    def intelligence_media_count(self, filters=None):

        where, params = self._intelligence_where(filters or {})

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(f"""

        SELECT COUNT(*)

        FROM media

        JOIN media_intelligence
        ON media_intelligence.media_id = media.id

        {where}

        """,

        params)

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def get_intelligence_media_page(
        self,
        filters=None,
        sort_by="filename",
        limit=200,
        offset=0
    ):

        where, params = self._intelligence_where(filters or {})
        order_by = self._intelligence_order_by(sort_by)

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(f"""

        SELECT

            media.id,

            media.filename,

            media.path,

            media.media_type

        FROM media

        JOIN media_intelligence
        ON media_intelligence.media_id = media.id

        {where}

        ORDER BY {order_by}

        LIMIT ? OFFSET ?

        """,

        params + [
            limit,
            offset
        ])

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def content_director_candidates(self, limit=500):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT

            media.id AS result_media_id,

            media.filename,

            media.path,

            media.media_type,

            media_intelligence.*,

            ai_analysis.community_score,

            ai_analysis.recruitment_score,

            ai_analysis.education_score,

            ai_analysis.technical_score,

            ai_analysis.overall_score

        FROM media

        JOIN media_intelligence
        ON media_intelligence.media_id = media.id

        LEFT JOIN ai_analysis
        ON ai_analysis.media_id = media.id

        ORDER BY
            media_intelligence.intelligence_score DESC,
            media.filename ASC

        LIMIT ?

        """,

        (
            self._to_int(limit),
        ))

        rows = cur.fetchall()

        conn.close()

        candidates = []

        for row in rows:

            intelligence = self._intelligence_from_row(row)
            intelligence.update(
                {
                    "media_id": row["result_media_id"],
                    "filename": row["filename"],
                    "path": row["path"],
                    "media_type": row["media_type"],
                    "community_score": row["community_score"] or 0,
                    "recruitment_score": row["recruitment_score"] or 0,
                    "education_score": row["education_score"] or 0,
                    "technical_score": row["technical_score"] or 0,
                    "overall_score": row["overall_score"] or 0
                }
            )
            candidates.append(intelligence)

        return candidates

    ############################################################

    def _intelligence_scalar_counts(self, field, filters):

        section_filters = dict(filters or {})
        section_filters.pop(field, None)
        where, params = self._intelligence_where(section_filters)

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(f"""

        SELECT

            media_intelligence.{field},

            COUNT(*)

        FROM media_intelligence

        JOIN media
        ON media.id = media_intelligence.media_id

        {where}

        GROUP BY media_intelligence.{field}

        HAVING media_intelligence.{field} IS NOT NULL
        AND media_intelligence.{field} != ''

        ORDER BY COUNT(*) DESC, media_intelligence.{field}

        """,

        params)

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def _intelligence_json_counts(self, field, filters):

        section_filters = dict(filters or {})
        section_filters.pop(field, None)
        where, params = self._intelligence_where(section_filters)

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(f"""

        SELECT

            json_each.value,

            COUNT(DISTINCT media_intelligence.media_id)

        FROM media_intelligence

        JOIN media
        ON media.id = media_intelligence.media_id

        JOIN json_each(media_intelligence.{field})

        {where}

        GROUP BY json_each.value

        HAVING json_each.value IS NOT NULL
        AND json_each.value != ''

        ORDER BY COUNT(DISTINCT media_intelligence.media_id) DESC,
        json_each.value

        """,

        params)

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def _intelligence_where(self, filters):

        clauses = []
        params = []

        list_fields = {
            "apparatus_tags",
            "equipment_tags",
            "ppe_tags",
            "people_tags",
            "content_tags",
            "content_themes",
            "recommended_uses"
        }

        scalar_fields = {
            "normalized_scene",
            "incident_type",
            "primary_activity"
        }

        for field, values in (filters or {}).items():

            values = [
                value
                for value in values
                if value
            ]

            if not values:
                continue

            placeholders = ",".join("?" for _ in values)

            if field in scalar_fields:
                clauses.append(
                    f"media_intelligence.{field} IN ({placeholders})"
                )
                params.extend(values)

            elif field in list_fields:
                clauses.append(f"""
                EXISTS (
                    SELECT 1
                    FROM json_each(media_intelligence.{field})
                    WHERE json_each.value IN ({placeholders})
                )
                """)
                params.extend(values)

        if not clauses:
            return "", []

        return (
            "WHERE " + " AND ".join(clauses),
            params
        )

    ############################################################

    def _intelligence_order_by(self, sort_by):

        sort_options = {
            "filename": "media.filename ASC",
            "date": "media.date_added DESC",
            "intelligence_score": (
                "media_intelligence.intelligence_score DESC, "
                "media.filename ASC"
            ),
            "newest": "media.date_added DESC",
            "oldest": "media.date_added ASC"
        }

        return sort_options.get(
            sort_by,
            sort_options["filename"]
        )

    ############################################################

    def _media_by_intelligence_field(self, field, value, limit):

        if field not in (
            "normalized_scene",
            "incident_type",
            "primary_activity"
        ):
            raise ValueError("Unsupported intelligence field")

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute(f"""

        SELECT

            media.id,

            media.filename,

            media.path,

            media.media_type

        FROM media

        JOIN media_intelligence
        ON media_intelligence.media_id = media.id

        WHERE media_intelligence.{field}=?

        ORDER BY media.filename

        LIMIT ?

        """,

        (
            value,
            self._to_int(limit)
        ))

        rows = cur.fetchall()

        conn.close()

        return [
            (
                row["id"],
                row["filename"],
                row["path"],
                row["media_type"]
            )
            for row in rows
        ]

    ############################################################

    def _analysis_from_row(self, row):

        return {
            "media_id": row["media_id"],
            "description": row["description"] or "",
            "scene_type": row["scene_type"] or "",
            "activity": row["activity"] or "",
            "people_count": row["people_count"] or 0,
            "apparatus": self._from_json(row["apparatus"]),
            "equipment": self._from_json(row["equipment"]),
            "keywords": self._from_json(row["keywords"]),
            "community_score": row["community_score"] or 0,
            "recruitment_score": row["recruitment_score"] or 0,
            "education_score": row["education_score"] or 0,
            "technical_score": row["technical_score"] or 0,
            "overall_score": row["overall_score"] or 0,
            "facebook_caption": row["facebook_caption"] or "",
            "instagram_caption": row["instagram_caption"] or "",
            "analyzed_at": row["analyzed_at"],
            "model": row["model"] or "",
            "analysis_duration": row["analysis_duration"] or 0,
            "provider": row["provider"] or "",
            "retry_count": row["retry_count"] or 0,
            "failure_reason": row["failure_reason"] or "",
            "last_analyzed": row["last_analyzed"] or ""
        }

    ############################################################

    def _intelligence_from_row(self, row):

        return {
            "media_id": row["media_id"],
            "normalized_scene": row["normalized_scene"] or "",
            "incident_type": row["incident_type"] or "",
            "primary_activity": row["primary_activity"] or "",
            "apparatus_tags": self._from_json(row["apparatus_tags"]),
            "equipment_tags": self._from_json(row["equipment_tags"]),
            "ppe_tags": self._from_json(row["ppe_tags"]),
            "people_tags": self._from_json(row["people_tags"]),
            "content_tags": self._from_json(row["content_tags"]),
            "content_themes": self._from_json(row["content_themes"]),
            "recommended_uses": self._from_json(row["recommended_uses"]),
            "search_text": row["search_text"] or "",
            "intelligence_score": row["intelligence_score"] or 0,
            "generated_at": row["generated_at"] or "",
            "source_model": row["source_model"] or ""
        }

    ############################################################

    def _to_json(self, value):

        if value is None:
            value = []

        return json.dumps(value)

    ############################################################

    def _from_json(self, value):

        if not value:
            return []

        try:
            return json.loads(value)
        except Exception:
            return [value]

    ############################################################

    def _to_int(self, value):

        try:
            return int(value)
        except Exception:
            return 0

    ############################################################

    def _to_float(self, value):

        try:
            return float(value)
        except Exception:
            return 0.0

    ############################################################

    def _ensure_ai_analysis_columns(self, cur):

        cur.execute("PRAGMA table_info(ai_analysis)")

        columns = {
            row[1]
            for row in cur.fetchall()
        }

        additions = {
            "analysis_duration": "REAL DEFAULT 0",
            "provider": "TEXT",
            "retry_count": "INTEGER DEFAULT 0",
            "failure_reason": "TEXT",
            "last_analyzed": "TIMESTAMP"
        }

        for name, definition in additions.items():

            if name in columns:
                continue

            cur.execute(
                f"ALTER TABLE ai_analysis ADD COLUMN {name} {definition}"
            )

            logger.info(
                "Added ai_analysis column %s",
                name
            )

    ############################################################

    def _ensure_media_intelligence_columns(self, cur):

        cur.execute("PRAGMA table_info(media_intelligence)")

        columns = {
            row[1]
            for row in cur.fetchall()
        }

        additions = {
            "source_model": "TEXT"
        }

        for name, definition in additions.items():

            if name in columns:
                continue

            cur.execute(
                f"ALTER TABLE media_intelligence ADD COLUMN {name} {definition}"
            )

            logger.info(
                "Added media_intelligence column %s",
                name
            )

    ############################################################

    def _ensure_indexes(self, cur):

        indexes = (
            "CREATE INDEX IF NOT EXISTS idx_media_filename ON media(filename)",
            "CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type)",
            "CREATE INDEX IF NOT EXISTS idx_media_path ON media(path)",
            "CREATE INDEX IF NOT EXISTS idx_ai_model ON ai_analysis(model)",
            "CREATE INDEX IF NOT EXISTS idx_ai_provider ON ai_analysis(provider)",
            "CREATE INDEX IF NOT EXISTS idx_ai_last_analyzed ON ai_analysis(last_analyzed)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_media ON media_intelligence(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_scene ON media_intelligence(normalized_scene)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_incident ON media_intelligence(incident_type)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_activity ON media_intelligence(primary_activity)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_score ON media_intelligence(intelligence_score)"
        )

        for statement in indexes:
            cur.execute(statement)
