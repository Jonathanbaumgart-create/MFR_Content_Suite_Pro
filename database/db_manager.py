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

        self._ensure_ai_analysis_columns(cur)
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

    def analyzed_media_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM ai_analysis")

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

    def _ensure_indexes(self, cur):

        indexes = (
            "CREATE INDEX IF NOT EXISTS idx_media_filename ON media(filename)",
            "CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type)",
            "CREATE INDEX IF NOT EXISTS idx_media_path ON media(path)",
            "CREATE INDEX IF NOT EXISTS idx_ai_model ON ai_analysis(model)",
            "CREATE INDEX IF NOT EXISTS idx_ai_provider ON ai_analysis(provider)",
            "CREATE INDEX IF NOT EXISTS idx_ai_last_analyzed ON ai_analysis(last_analyzed)"
        )

        for statement in indexes:
            cur.execute(statement)
