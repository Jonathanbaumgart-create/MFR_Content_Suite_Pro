import sqlite3
from pathlib import Path
import json


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

        conn.commit()

        conn.close()

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

    def media_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM media")

        count = cur.fetchone()[0]

        conn.close()

        return count

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

            model

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?)

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

            analysis.get("model")

        ))

        conn.commit()

        conn.close()

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
            "model": row["model"] or ""
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
