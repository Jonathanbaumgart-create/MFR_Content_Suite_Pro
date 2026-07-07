import sqlite3
from pathlib import Path


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

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM ai_analysis

        WHERE media_id=?

        """,

        (media_id,))

        row = cur.fetchone()

        conn.close()

        return row

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

            model

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        """,

        (

            media_id,

            analysis.get("description"),

            analysis.get("scene_type"),

            analysis.get("activity"),

            analysis.get("people_count"),

            analysis.get("apparatus"),

            analysis.get("equipment"),

            analysis.get("keywords"),

            analysis.get("community_score"),

            analysis.get("recruitment_score"),

            analysis.get("education_score"),

            analysis.get("technical_score"),

            analysis.get("overall_score"),

            analysis.get("model")

        ))

        conn.commit()

        conn.close()