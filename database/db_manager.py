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

            communications_score INTEGER,

            storytelling_score INTEGER,

            community_engagement_score INTEGER,

            educational_value_score INTEGER,

            recruitment_value_score INTEGER,

            recognition_value_score INTEGER,

            emergency_response_value_score INTEGER,

            public_education_value_score INTEGER,

            seasonal_relevance_score INTEGER,

            visual_impact_score INTEGER,

            trust_building_score INTEGER,

            emotional_impact_score INTEGER,

            communications_category_scores TEXT,

            platform_suitability TEXT,

            evergreen_score INTEGER,

            time_sensitive_score INTEGER,

            historical_importance_score INTEGER,

            uniqueness_score INTEGER,

            posting_frequency_risk INTEGER,

            suggested_campaigns TEXT,

            suggested_audience TEXT,

            suggested_platform TEXT,

            suggested_time_of_year TEXT,

            communications_reasoning TEXT,

            communications_scored_at TIMESTAMP,

            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            source_model TEXT

        )

        """)

        ########################################################
        # Recommendation History
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS recommendation_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            media_id INTEGER,

            recommendation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            reason TEXT,

            opportunity TEXT,

            score REAL,

            platform TEXT

        )

        """)

        ########################################################
        # Recommendation Feedback
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS recommendation_feedback(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            recommendation_id TEXT,

            media_id INTEGER,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            feedback_type TEXT,

            accepted INTEGER DEFAULT 0,

            dismissed INTEGER DEFAULT 0,

            opened INTEGER DEFAULT 0,

            regenerated INTEGER DEFAULT 0,

            notes TEXT,

            confidence REAL,

            opportunity_type TEXT

        )

        """)

        ########################################################
        # Department Knowledge
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS department_profile(

            key TEXT PRIMARY KEY,

            value TEXT

        )

        """)

        for table in (
            "apparatus",
            "programs",
            "annual_events",
            "locations",
            "response_area",
            "community_partners"
        ):
            cur.execute(f"""

            CREATE TABLE IF NOT EXISTS {table}(

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                category TEXT,

                description TEXT,

                tags TEXT,

                active_months TEXT,

                inactive_months TEXT,

                season TEXT,

                event_date TEXT,

                campaign_window TEXT,

                audience TEXT,

                school_year_program INTEGER DEFAULT 0,

                notes TEXT,

                active INTEGER DEFAULT 1

            )

            """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS knowledge_documents(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            path TEXT,

            filename TEXT,

            sha256 TEXT UNIQUE,

            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            summary TEXT

        )

        """)

        ########################################################
        # Communications Memory
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS platforms(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE,

            active INTEGER DEFAULT 1

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS campaigns(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE,

            description TEXT,

            season TEXT,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS social_posts(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            platform TEXT,

            post_date TEXT,

            post_time TEXT,

            headline TEXT,

            caption TEXT,

            cta TEXT,

            hashtags TEXT,

            emojis TEXT,

            media_ids TEXT,

            campaign TEXT,

            writing_style TEXT,

            opportunity_type TEXT,

            season TEXT,

            context TEXT,

            source TEXT,

            imported INTEGER DEFAULT 0,

            generated INTEGER DEFAULT 0,

            manually_created INTEGER DEFAULT 0,

            caption_hash TEXT UNIQUE,

            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS media_usage(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            media_id INTEGER,

            post_id INTEGER,

            platform TEXT,

            used_at TEXT,

            campaign TEXT

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS writing_patterns(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            post_id INTEGER,

            opening_hook TEXT,

            caption_length INTEGER DEFAULT 0,

            emoji_count INTEGER DEFAULT 0,

            hashtag_count INTEGER DEFAULT 0,

            writing_tone TEXT,

            cta TEXT,

            question_asked INTEGER DEFAULT 0,

            storytelling INTEGER DEFAULT 0,

            educational INTEGER DEFAULT 0,

            recognition INTEGER DEFAULT 0,

            recruitment INTEGER DEFAULT 0,

            incident_recap INTEGER DEFAULT 0,

            community_engagement INTEGER DEFAULT 0,

            safety_message INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS hashtags(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            tag TEXT UNIQUE,

            use_count INTEGER DEFAULT 0,

            last_used TEXT

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS post_metrics(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            post_id INTEGER,

            likes INTEGER DEFAULT 0,

            comments INTEGER DEFAULT 0,

            shares INTEGER DEFAULT 0,

            reach INTEGER DEFAULT 0,

            engagement_rate REAL DEFAULT 0,

            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        ########################################################
        # Content Templates
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS content_templates(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            writing_style TEXT,

            platform TEXT,

            body TEXT,

            active INTEGER DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        self._ensure_ai_analysis_columns(cur)
        self._ensure_media_intelligence_columns(cur)
        self._ensure_knowledge_columns(cur)
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

    def last_provider_failure(self):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT media_id, provider, model, retry_count, failure_reason, last_analyzed

        FROM ai_analysis

        WHERE failure_reason IS NOT NULL
        AND failure_reason != ''

        ORDER BY last_analyzed DESC

        LIMIT 1

        """)

        row = cur.fetchone()

        conn.close()

        if row is None:
            return None

        return {
            "media_id": row["media_id"],
            "provider": row["provider"] or "",
            "model": row["model"] or "",
            "retry_count": row["retry_count"] or 0,
            "failure_reason": row["failure_reason"] or "",
            "last_analyzed": row["last_analyzed"] or ""
        }

    ############################################################

    def last_successful_analysis(self):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT media_id, provider, model, last_analyzed

        FROM ai_analysis

        WHERE failure_reason IS NULL
        OR failure_reason = ''

        ORDER BY last_analyzed DESC

        LIMIT 1

        """)

        row = cur.fetchone()

        conn.close()

        if row is None:
            return None

        return {
            "media_id": row["media_id"],
            "provider": row["provider"] or "",
            "model": row["model"] or "",
            "last_analyzed": row["last_analyzed"] or ""
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

    def save_communications_scores(self, media_id, scores):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        UPDATE media_intelligence

        SET
            communications_score=?,
            storytelling_score=?,
            community_engagement_score=?,
            educational_value_score=?,
            recruitment_value_score=?,
            recognition_value_score=?,
            emergency_response_value_score=?,
            public_education_value_score=?,
            seasonal_relevance_score=?,
            visual_impact_score=?,
            trust_building_score=?,
            emotional_impact_score=?,
            communications_category_scores=?,
            platform_suitability=?,
            evergreen_score=?,
            time_sensitive_score=?,
            historical_importance_score=?,
            uniqueness_score=?,
            posting_frequency_risk=?,
            suggested_campaigns=?,
            suggested_audience=?,
            suggested_platform=?,
            suggested_time_of_year=?,
            communications_reasoning=?,
            communications_scored_at=CURRENT_TIMESTAMP

        WHERE media_id=?

        """,

        (
            self._to_int(scores.get("communications_score")),
            self._to_int(scores.get("storytelling_score")),
            self._to_int(scores.get("community_engagement_score")),
            self._to_int(scores.get("educational_value_score")),
            self._to_int(scores.get("recruitment_value_score")),
            self._to_int(scores.get("recognition_value_score")),
            self._to_int(scores.get("emergency_response_value_score")),
            self._to_int(scores.get("public_education_value_score")),
            self._to_int(scores.get("seasonal_relevance_score")),
            self._to_int(scores.get("visual_impact_score")),
            self._to_int(scores.get("trust_building_score")),
            self._to_int(scores.get("emotional_impact_score")),
            self._to_json(scores.get("communications_category_scores")),
            self._to_json(scores.get("platform_suitability")),
            self._to_int(scores.get("evergreen_score")),
            self._to_int(scores.get("time_sensitive_score")),
            self._to_int(scores.get("historical_importance_score")),
            self._to_int(scores.get("uniqueness_score")),
            self._to_int(scores.get("posting_frequency_risk")),
            self._to_json(scores.get("suggested_campaigns")),
            self._to_json(scores.get("suggested_audience")),
            scores.get("suggested_platform", ""),
            scores.get("suggested_time_of_year", ""),
            self._to_json(scores.get("communications_reasoning")),
            self._to_int(media_id)
        ))

        conn.commit()
        conn.close()

    ############################################################

    def get_media_needing_communications_scores(self, limit=None):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        sql = """

        SELECT *

        FROM media_intelligence

        WHERE communications_score IS NULL

        ORDER BY intelligence_score DESC, media_id ASC

        """

        params = []

        if limit is not None:
            sql += " LIMIT ?"
            params.append(
                self._to_int(limit)
            )

        cur.execute(
            sql,
            params
        )

        rows = [
            self._intelligence_from_row(row)
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def media_missing_communications_scores_count(self):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(*)

        FROM media_intelligence

        WHERE communications_score IS NULL

        """)

        count = cur.fetchone()[0]
        conn.close()

        return count

    ############################################################

    def communications_score_summary(self):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT
            COUNT(*) AS scored_count,
            AVG(communications_score) AS average_score

        FROM media_intelligence

        WHERE communications_score IS NOT NULL

        """)

        summary = cur.fetchone()

        cur.execute("""

        SELECT
            media_intelligence.media_id,
            media.filename,
            media.path,
            media_intelligence.communications_score

        FROM media_intelligence

        JOIN media
        ON media.id = media_intelligence.media_id

        WHERE media_intelligence.communications_score IS NOT NULL

        ORDER BY media_intelligence.communications_score DESC,
                 media.filename ASC

        LIMIT 5

        """)

        highest = [
            {
                "media_id": row["media_id"],
                "filename": row["filename"] or "",
                "path": row["path"] or "",
                "communications_score": row["communications_score"] or 0
            }
            for row in cur.fetchall()
        ]

        conn.close()

        return {
            "scored_count": summary["scored_count"] or 0,
            "average_score": round(summary["average_score"] or 0, 1),
            "highest_scoring_media": highest,
            "missing_count": self.media_missing_communications_scores_count()
        }

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
            media_intelligence.communications_score DESC,
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

    def save_recommendation_history(self, recommendation):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO recommendation_history(

            media_id,

            reason,

            opportunity,

            score,

            platform

        )

        VALUES(?,?,?,?,?)

        """,

        (
            self._to_int(recommendation.get("media_id")),
            recommendation.get("reason", ""),
            recommendation.get("opportunity", ""),
            self._to_float(recommendation.get("score")),
            recommendation.get("platform", "")
        ))

        conn.commit()

        conn.close()

    ############################################################

    def recent_recommended_media_ids(self, days=30, limit=500):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT DISTINCT media_id

        FROM recommendation_history

        WHERE media_id IS NOT NULL
        AND recommendation_date >= datetime('now', ?)

        ORDER BY recommendation_date DESC

        LIMIT ?

        """,

        (
            f"-{self._to_int(days)} days",
            self._to_int(limit)
        ))

        rows = cur.fetchall()

        conn.close()

        return {
            row[0]
            for row in rows
            if row[0]
        }

    ############################################################

    def recommendation_counts(self, days=90):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            opportunity,

            COUNT(*)

        FROM recommendation_history

        WHERE recommendation_date >= datetime('now', ?)

        GROUP BY opportunity

        ORDER BY COUNT(*) DESC, opportunity

        """,

        (
            f"-{self._to_int(days)} days",
        ))

        rows = cur.fetchall()

        conn.close()

        return rows

    ############################################################

    def recommendation_history_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM recommendation_history")

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def save_recommendation_feedback(self, feedback):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO recommendation_feedback(

            recommendation_id,

            media_id,

            feedback_type,

            accepted,

            dismissed,

            opened,

            regenerated,

            notes,

            confidence,

            opportunity_type

        )

        VALUES(?,?,?,?,?,?,?,?,?,?)

        """,

        (
            feedback.get("recommendation_id", ""),
            self._to_int(feedback.get("media_id")) or None,
            feedback.get("feedback_type", ""),
            self._to_int(feedback.get("accepted")),
            self._to_int(feedback.get("dismissed")),
            self._to_int(feedback.get("opened")),
            self._to_int(feedback.get("regenerated")),
            feedback.get("notes", ""),
            self._to_float(feedback.get("confidence")),
            feedback.get("opportunity_type", "")
        ))

        feedback_id = cur.lastrowid

        conn.commit()

        conn.close()

        return feedback_id

    ############################################################

    def recommendation_feedback_rows(self, limit=1000):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM recommendation_feedback

        ORDER BY created_at DESC, id DESC

        LIMIT ?

        """,

        (
            self._to_int(limit),
        ))

        rows = cur.fetchall()

        conn.close()

        return [
            self._recommendation_feedback_from_row(row)
            for row in rows
        ]

    ############################################################

    def recommendation_feedback_for_media(self, media_id, limit=200):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM recommendation_feedback

        WHERE media_id=?

        ORDER BY created_at DESC, id DESC

        LIMIT ?

        """,

        (
            self._to_int(media_id),
            self._to_int(limit)
        ))

        rows = cur.fetchall()

        conn.close()

        return [
            self._recommendation_feedback_from_row(row)
            for row in rows
        ]

    ############################################################

    def department_profile(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            key,

            value

        FROM department_profile

        ORDER BY key

        """)

        rows = cur.fetchall()

        conn.close()

        return {
            key: value or ""
            for key, value in rows
        }

    ############################################################

    def save_department_profile_value(self, key, value):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR REPLACE INTO department_profile(

            key,

            value

        )

        VALUES(?,?)

        """,

        (
            key,
            value
        ))

        conn.commit()

        conn.close()

    ############################################################

    def knowledge_items(self, table):

        table = self._knowledge_table(table)
        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute(f"""

        SELECT *

        FROM {table}

        ORDER BY active DESC, name ASC

        """)

        rows = cur.fetchall()

        conn.close()

        return [
            self._knowledge_item_from_row(row)
            for row in rows
        ]

    ############################################################

    def save_knowledge_item(self, table, item):

        table = self._knowledge_table(table)
        item_id = self._to_int(item.get("id"))
        values = (
            item.get("name", ""),
            item.get("category", ""),
            item.get("description", ""),
            self._to_json(item.get("tags")),
            self._to_json(item.get("active_months")),
            self._to_json(item.get("inactive_months")),
            item.get("season", ""),
            item.get("event_date", ""),
            item.get("campaign_window", ""),
            item.get("audience", ""),
            1 if item.get("school_year_program", False) else 0,
            item.get("notes", ""),
            1 if item.get("active", True) else 0
        )
        conn = self.connection()

        cur = conn.cursor()

        if item_id:
            cur.execute(f"""

            UPDATE {table}

            SET
                name=?,
                category=?,
                description=?,
                tags=?,
                active_months=?,
                inactive_months=?,
                season=?,
                event_date=?,
                campaign_window=?,
                audience=?,
                school_year_program=?,
                notes=?,
                active=?

            WHERE id=?

            """,

            values + (item_id,))

        else:
            cur.execute(f"""

            INSERT INTO {table}(

                name,

                category,

                description,

                tags,

                active_months,

                inactive_months,

                season,

                event_date,

                campaign_window,

                audience,

                school_year_program,

                notes,

                active

            )

            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)

            """,

            values)
            item_id = cur.lastrowid

        conn.commit()

        conn.close()

        return item_id

    ############################################################

    def delete_knowledge_item(self, table, item_id):

        table = self._knowledge_table(table)
        conn = self.connection()

        cur = conn.cursor()

        cur.execute(
            f"DELETE FROM {table} WHERE id=?",
            (
                self._to_int(item_id),
            )
        )

        conn.commit()

        conn.close()

    ############################################################

    def save_knowledge_document(self, document):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR IGNORE INTO knowledge_documents(

            path,

            filename,

            sha256,

            summary

        )

        VALUES(?,?,?,?)

        """,

        (
            document.get("path", ""),
            document.get("filename", ""),
            document.get("sha256", ""),
            self._to_json(document.get("summary", {}))
        ))

        inserted = cur.rowcount > 0

        conn.commit()

        conn.close()

        return inserted

    ############################################################

    def knowledge_document_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM knowledge_documents")

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def knowledge_document_exists(self, sha256):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM knowledge_documents WHERE sha256=?",
            (
                sha256,
            )
        )

        exists = cur.fetchone() is not None

        conn.close()

        return exists

    ############################################################

    def save_social_post(self, post):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR IGNORE INTO social_posts(

            platform,

            post_date,

            post_time,

            headline,

            caption,

            cta,

            hashtags,

            emojis,

            media_ids,

            campaign,

            writing_style,

            opportunity_type,

            season,

            context,

            source,

            imported,

            generated,

            manually_created,

            caption_hash

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        """,

        (
            post.get("platform", ""),
            post.get("post_date", ""),
            post.get("post_time", ""),
            post.get("headline", ""),
            post.get("caption", ""),
            post.get("cta", ""),
            self._to_json(post.get("hashtags", [])),
            self._to_json(post.get("emojis", [])),
            self._to_json(post.get("media_ids", [])),
            post.get("campaign", ""),
            post.get("writing_style", ""),
            post.get("opportunity_type", ""),
            post.get("season", ""),
            post.get("context", ""),
            post.get("source", ""),
            self._to_int(post.get("imported")),
            self._to_int(post.get("generated")),
            self._to_int(post.get("manually_created")),
            post.get("caption_hash", "")
        ))

        post_id = cur.lastrowid if cur.rowcount > 0 else None

        conn.commit()

        conn.close()

        return post_id

    ############################################################

    def social_post_exists(self, caption_hash):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM social_posts WHERE caption_hash=?",
            (
                caption_hash,
            )
        )

        row = cur.fetchone()

        conn.close()

        return row[0] if row else None

    ############################################################

    def social_caption_exists(self, caption):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM social_posts WHERE caption=? LIMIT 1",
            (
                caption,
            )
        )

        row = cur.fetchone()

        conn.close()

        return row[0] if row else None

    ############################################################

    def save_campaign(self, campaign):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR IGNORE INTO campaigns(

            name,

            description,

            season,

            active

        )

        VALUES(?,?,?,?)

        """,

        (
            campaign.get("name", ""),
            campaign.get("description", ""),
            campaign.get("season", ""),
            1 if campaign.get("active", True) else 0
        ))

        campaign_id = cur.lastrowid

        conn.commit()

        conn.close()

        return campaign_id

    ############################################################

    def save_platform(self, platform):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT OR IGNORE INTO platforms(

            name,

            active

        )

        VALUES(?,1)

        """,

        (
            platform,
        ))

        platform_id = cur.lastrowid

        conn.commit()

        conn.close()

        return platform_id

    ############################################################

    def save_media_usage(self, usage):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO media_usage(

            media_id,

            post_id,

            platform,

            used_at,

            campaign

        )

        VALUES(?,?,?,?,?)

        """,

        (
            self._to_int(usage.get("media_id")),
            self._to_int(usage.get("post_id")),
            usage.get("platform", ""),
            usage.get("used_at", ""),
            usage.get("campaign", "")
        ))

        usage_id = cur.lastrowid

        conn.commit()

        conn.close()

        return usage_id

    ############################################################

    def save_writing_pattern(self, pattern):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO writing_patterns(

            post_id,

            opening_hook,

            caption_length,

            emoji_count,

            hashtag_count,

            writing_tone,

            cta,

            question_asked,

            storytelling,

            educational,

            recognition,

            recruitment,

            incident_recap,

            community_engagement,

            safety_message

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        """,

        (
            self._to_int(pattern.get("post_id")),
            pattern.get("opening_hook", ""),
            self._to_int(pattern.get("caption_length")),
            self._to_int(pattern.get("emoji_count")),
            self._to_int(pattern.get("hashtag_count")),
            pattern.get("writing_tone", ""),
            pattern.get("cta", ""),
            self._to_int(pattern.get("question_asked")),
            self._to_int(pattern.get("storytelling")),
            self._to_int(pattern.get("educational")),
            self._to_int(pattern.get("recognition")),
            self._to_int(pattern.get("recruitment")),
            self._to_int(pattern.get("incident_recap")),
            self._to_int(pattern.get("community_engagement")),
            self._to_int(pattern.get("safety_message"))
        ))

        pattern_id = cur.lastrowid

        conn.commit()

        conn.close()

        return pattern_id

    ############################################################

    def save_hashtag_use(self, tag, used_at=""):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO hashtags(

            tag,

            use_count,

            last_used

        )

        VALUES(?,1,?)

        ON CONFLICT(tag) DO UPDATE SET
            use_count=use_count+1,
            last_used=excluded.last_used

        """,

        (
            tag,
            used_at
        ))

        conn.commit()

        conn.close()

    ############################################################

    def social_posts(self, limit=100, search_text=""):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        sql = """

        SELECT *

        FROM social_posts

        """
        params = []

        if search_text:
            sql += """

            WHERE caption LIKE ?
            OR headline LIKE ?
            OR campaign LIKE ?

            """
            pattern = f"%{search_text}%"
            params.extend(
                (
                    pattern,
                    pattern,
                    pattern
                )
            )

        sql += """

        ORDER BY post_date DESC, post_time DESC, id DESC

        LIMIT ?

        """
        params.append(
            self._to_int(limit)
        )

        cur.execute(
            sql,
            tuple(params)
        )

        rows = cur.fetchall()

        conn.close()

        return [
            self._social_post_from_row(row)
            for row in rows
        ]

    ############################################################

    def social_post_count(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM social_posts")

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def communication_memory_summary(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM social_posts")
        total_posts = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM campaigns")
        campaigns = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM platforms")
        platforms = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM media_usage")
        media_usage = cur.fetchone()[0]

        cur.execute("""

        SELECT tag, use_count

        FROM hashtags

        ORDER BY use_count DESC, tag

        LIMIT 10

        """)
        top_hashtags = cur.fetchall()

        cur.execute("""

        SELECT writing_style, COUNT(*)

        FROM social_posts

        WHERE writing_style IS NOT NULL
        AND writing_style != ''

        GROUP BY writing_style

        ORDER BY COUNT(*) DESC, writing_style

        LIMIT 10

        """)
        writing_styles = cur.fetchall()

        cur.execute("""

        SELECT platform, COUNT(*)

        FROM social_posts

        WHERE platform IS NOT NULL
        AND platform != ''

        GROUP BY platform

        ORDER BY COUNT(*) DESC, platform

        """)
        platform_counts = cur.fetchall()

        cur.execute("""

        SELECT campaign, COUNT(*)

        FROM social_posts

        WHERE campaign IS NOT NULL
        AND campaign != ''

        GROUP BY campaign

        ORDER BY COUNT(*) DESC, campaign

        LIMIT 10

        """)
        recent_campaigns = cur.fetchall()

        conn.close()

        return {
            "total_posts": total_posts,
            "campaigns": campaigns,
            "platforms": platforms,
            "media_usage": media_usage,
            "top_hashtags": top_hashtags,
            "writing_styles": writing_styles,
            "platform_counts": platform_counts,
            "recent_campaigns": recent_campaigns
        }

    ############################################################

    def writing_pattern_statistics(self):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            AVG(caption_length),
            AVG(hashtag_count),
            AVG(emoji_count),
            AVG(CASE WHEN question_asked THEN 1.0 ELSE 0 END),
            AVG(CASE WHEN storytelling THEN 1.0 ELSE 0 END),
            AVG(CASE WHEN educational THEN 1.0 ELSE 0 END),
            AVG(CASE WHEN recognition THEN 1.0 ELSE 0 END),
            AVG(CASE WHEN recruitment THEN 1.0 ELSE 0 END),
            AVG(CASE WHEN incident_recap THEN 1.0 ELSE 0 END),
            AVG(CASE WHEN community_engagement THEN 1.0 ELSE 0 END),
            AVG(CASE WHEN safety_message THEN 1.0 ELSE 0 END)

        FROM writing_patterns

        """)

        row = cur.fetchone()

        cur.execute("""

        SELECT opening_hook, COUNT(*)

        FROM writing_patterns

        WHERE opening_hook IS NOT NULL
        AND opening_hook != ''

        GROUP BY opening_hook

        ORDER BY COUNT(*) DESC, opening_hook

        LIMIT 5

        """)
        openings = cur.fetchall()

        cur.execute("""

        SELECT cta, COUNT(*)

        FROM writing_patterns

        WHERE cta IS NOT NULL
        AND cta != ''

        GROUP BY cta

        ORDER BY COUNT(*) DESC, cta

        LIMIT 5

        """)
        ctas = cur.fetchall()

        conn.close()

        row = row or (0,) * 11

        return {
            "average_caption_length": row[0] or 0,
            "average_hashtags": row[1] or 0,
            "average_emojis": row[2] or 0,
            "question_rate": row[3] or 0,
            "storytelling_rate": row[4] or 0,
            "educational_rate": row[5] or 0,
            "recognition_rate": row[6] or 0,
            "recruitment_rate": row[7] or 0,
            "incident_recap_rate": row[8] or 0,
            "community_engagement_rate": row[9] or 0,
            "safety_message_rate": row[10] or 0,
            "common_openings": openings,
            "common_ctas": ctas
        }

    ############################################################

    def media_usage_summary(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM media_usage

        WHERE media_id=?

        ORDER BY used_at DESC

        """,

        (
            self._to_int(media_id),
        ))

        rows = cur.fetchall()

        conn.close()

        return [
            {
                "post_id": row["post_id"],
                "platform": row["platform"] or "",
                "used_at": row["used_at"] or "",
                "campaign": row["campaign"] or ""
            }
            for row in rows
        ]

    ############################################################

    def recently_used_social_media_ids(self, days=90):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT DISTINCT media_id

        FROM media_usage

        WHERE media_id IS NOT NULL
        AND used_at >= datetime('now', ?)

        """,

        (
            f"-{self._to_int(days)} days",
        ))

        rows = cur.fetchall()

        conn.close()

        return {
            row[0]
            for row in rows
            if row[0]
        }

    ############################################################

    def campaign_names(self, limit=20):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        SELECT name

        FROM campaigns

        ORDER BY name

        LIMIT ?

        """,

        (
            self._to_int(limit),
        ))

        rows = cur.fetchall()

        conn.close()

        return [
            row[0]
            for row in rows
        ]

    ############################################################

    def content_templates(self, writing_style=None, platform=None):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()

        sql = """

        SELECT *

        FROM content_templates

        WHERE active=1

        """
        params = []

        if writing_style:
            sql += " AND writing_style=?"
            params.append(writing_style)

        if platform:
            sql += " AND platform=?"
            params.append(platform)

        sql += " ORDER BY name"

        cur.execute(
            sql,
            tuple(params)
        )

        rows = cur.fetchall()

        conn.close()

        return [
            self._content_template_from_row(row)
            for row in rows
        ]

    ############################################################

    def save_content_template(self, template):

        template_id = self._to_int(
            template.get("id")
        )
        values = (
            template.get("name", ""),
            template.get("writing_style", ""),
            template.get("platform", ""),
            template.get("body", ""),
            1 if template.get("active", True) else 0
        )
        conn = self.connection()

        cur = conn.cursor()

        if template_id:
            cur.execute("""

            UPDATE content_templates

            SET
                name=?,
                writing_style=?,
                platform=?,
                body=?,
                active=?,
                updated_at=CURRENT_TIMESTAMP

            WHERE id=?

            """,

            values + (template_id,))

        else:
            cur.execute("""

            INSERT INTO content_templates(

                name,

                writing_style,

                platform,

                body,

                active

            )

            VALUES(?,?,?,?,?)

            """,

            values)
            template_id = cur.lastrowid

        conn.commit()

        conn.close()

        return template_id

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
            "communications_score": (
                "media_intelligence.communications_score DESC, "
                "media.filename ASC"
            ),
            "storytelling": (
                "media_intelligence.storytelling_score DESC, "
                "media.filename ASC"
            ),
            "educational": (
                "media_intelligence.educational_value_score DESC, "
                "media.filename ASC"
            ),
            "recruitment": (
                "media_intelligence.recruitment_value_score DESC, "
                "media.filename ASC"
            ),
            "community_engagement": (
                "media_intelligence.community_engagement_score DESC, "
                "media.filename ASC"
            ),
            "trust_building": (
                "media_intelligence.trust_building_score DESC, "
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
            "communications_score": row["communications_score"] or 0,
            "storytelling_score": row["storytelling_score"] or 0,
            "community_engagement_score": row["community_engagement_score"] or 0,
            "educational_value_score": row["educational_value_score"] or 0,
            "recruitment_value_score": row["recruitment_value_score"] or 0,
            "recognition_value_score": row["recognition_value_score"] or 0,
            "emergency_response_value_score": row["emergency_response_value_score"] or 0,
            "public_education_value_score": row["public_education_value_score"] or 0,
            "seasonal_relevance_score": row["seasonal_relevance_score"] or 0,
            "visual_impact_score": row["visual_impact_score"] or 0,
            "trust_building_score": row["trust_building_score"] or 0,
            "emotional_impact_score": row["emotional_impact_score"] or 0,
            "communications_category_scores": self._from_json(row["communications_category_scores"]),
            "platform_suitability": self._from_json(row["platform_suitability"]),
            "evergreen_score": row["evergreen_score"] or 0,
            "time_sensitive_score": row["time_sensitive_score"] or 0,
            "historical_importance_score": row["historical_importance_score"] or 0,
            "uniqueness_score": row["uniqueness_score"] or 0,
            "posting_frequency_risk": row["posting_frequency_risk"] or 0,
            "suggested_campaigns": self._from_json(row["suggested_campaigns"]),
            "suggested_audience": self._from_json(row["suggested_audience"]),
            "suggested_platform": row["suggested_platform"] or "",
            "suggested_time_of_year": row["suggested_time_of_year"] or "",
            "communications_reasoning": self._from_json(row["communications_reasoning"]),
            "communications_scored_at": row["communications_scored_at"] or "",
            "generated_at": row["generated_at"] or "",
            "source_model": row["source_model"] or ""
        }

    ############################################################

    def _knowledge_item_from_row(self, row):

        return {
            "id": row["id"],
            "name": row["name"] or "",
            "category": row["category"] or "",
            "description": row["description"] or "",
            "tags": self._from_json(row["tags"]),
            "active_months": self._from_json(row["active_months"]),
            "inactive_months": self._from_json(row["inactive_months"]),
            "season": row["season"] or "",
            "event_date": row["event_date"] or "",
            "campaign_window": row["campaign_window"] or "",
            "audience": row["audience"] or "",
            "school_year_program": bool(row["school_year_program"]),
            "notes": row["notes"] or "",
            "active": bool(row["active"])
        }

    ############################################################

    def _recommendation_feedback_from_row(self, row):

        return {
            "id": row["id"],
            "recommendation_id": row["recommendation_id"] or "",
            "media_id": row["media_id"],
            "created_at": row["created_at"] or "",
            "feedback_type": row["feedback_type"] or "",
            "accepted": bool(row["accepted"]),
            "dismissed": bool(row["dismissed"]),
            "opened": bool(row["opened"]),
            "regenerated": bool(row["regenerated"]),
            "notes": row["notes"] or "",
            "confidence": row["confidence"] or 0,
            "opportunity_type": row["opportunity_type"] or ""
        }

    ############################################################

    def _content_template_from_row(self, row):

        return {
            "id": row["id"],
            "name": row["name"] or "",
            "writing_style": row["writing_style"] or "",
            "platform": row["platform"] or "",
            "body": row["body"] or "",
            "active": bool(row["active"]),
            "created_at": row["created_at"] or "",
            "updated_at": row["updated_at"] or ""
        }

    ############################################################

    def _social_post_from_row(self, row):

        return {
            "id": row["id"],
            "platform": row["platform"] or "",
            "post_date": row["post_date"] or "",
            "post_time": row["post_time"] or "",
            "headline": row["headline"] or "",
            "caption": row["caption"] or "",
            "cta": row["cta"] or "",
            "hashtags": self._from_json(row["hashtags"]),
            "emojis": self._from_json(row["emojis"]),
            "media_ids": self._from_json(row["media_ids"]),
            "campaign": row["campaign"] or "",
            "writing_style": row["writing_style"] or "",
            "opportunity_type": row["opportunity_type"] or "",
            "season": row["season"] or "",
            "context": row["context"] or "",
            "source": row["source"] or "",
            "imported": bool(row["imported"]),
            "generated": bool(row["generated"]),
            "manually_created": bool(row["manually_created"]),
            "caption_hash": row["caption_hash"] or "",
            "imported_at": row["imported_at"] or ""
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

    def _knowledge_table(self, table):

        allowed = {
            "apparatus",
            "programs",
            "annual_events",
            "locations",
            "response_area",
            "community_partners"
        }

        if table not in allowed:
            raise ValueError("Unsupported knowledge table")

        return table

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
            "source_model": "TEXT",
            "communications_score": "INTEGER",
            "storytelling_score": "INTEGER",
            "community_engagement_score": "INTEGER",
            "educational_value_score": "INTEGER",
            "recruitment_value_score": "INTEGER",
            "recognition_value_score": "INTEGER",
            "emergency_response_value_score": "INTEGER",
            "public_education_value_score": "INTEGER",
            "seasonal_relevance_score": "INTEGER",
            "visual_impact_score": "INTEGER",
            "trust_building_score": "INTEGER",
            "emotional_impact_score": "INTEGER",
            "communications_category_scores": "TEXT",
            "platform_suitability": "TEXT",
            "evergreen_score": "INTEGER",
            "time_sensitive_score": "INTEGER",
            "historical_importance_score": "INTEGER",
            "uniqueness_score": "INTEGER",
            "posting_frequency_risk": "INTEGER",
            "suggested_campaigns": "TEXT",
            "suggested_audience": "TEXT",
            "suggested_platform": "TEXT",
            "suggested_time_of_year": "TEXT",
            "communications_reasoning": "TEXT",
            "communications_scored_at": "TIMESTAMP"
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

    def _ensure_knowledge_columns(self, cur):

        additions = {
            "active_months": "TEXT",
            "inactive_months": "TEXT",
            "season": "TEXT",
            "event_date": "TEXT",
            "campaign_window": "TEXT",
            "audience": "TEXT",
            "school_year_program": "INTEGER DEFAULT 0",
            "notes": "TEXT"
        }

        for table in (
            "apparatus",
            "programs",
            "annual_events",
            "locations",
            "response_area",
            "community_partners"
        ):
            cur.execute(f"PRAGMA table_info({table})")
            columns = {
                row[1]
                for row in cur.fetchall()
            }

            for name, definition in additions.items():

                if name in columns:
                    continue

                cur.execute(
                    f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
                )

                logger.info(
                    "Added %s column %s",
                    table,
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
            "CREATE INDEX IF NOT EXISTS idx_intelligence_score ON media_intelligence(intelligence_score)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_comm_score ON media_intelligence(communications_score)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_storytelling ON media_intelligence(storytelling_score)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_education_value ON media_intelligence(educational_value_score)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_recruitment_value ON media_intelligence(recruitment_value_score)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_community_engagement ON media_intelligence(community_engagement_score)",
            "CREATE INDEX IF NOT EXISTS idx_intelligence_trust ON media_intelligence(trust_building_score)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_history_media ON recommendation_history(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_history_date ON recommendation_history(recommendation_date)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_history_opportunity ON recommendation_history(opportunity)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_rec ON recommendation_feedback(recommendation_id)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_media ON recommendation_feedback(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_type ON recommendation_feedback(feedback_type)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_opportunity ON recommendation_feedback(opportunity_type)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_created ON recommendation_feedback(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_apparatus_name ON apparatus(name)",
            "CREATE INDEX IF NOT EXISTS idx_programs_name ON programs(name)",
            "CREATE INDEX IF NOT EXISTS idx_annual_events_name ON annual_events(name)",
            "CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name)",
            "CREATE INDEX IF NOT EXISTS idx_response_area_name ON response_area(name)",
            "CREATE INDEX IF NOT EXISTS idx_community_partners_name ON community_partners(name)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_sha ON knowledge_documents(sha256)",
            "CREATE INDEX IF NOT EXISTS idx_content_templates_style ON content_templates(writing_style)",
            "CREATE INDEX IF NOT EXISTS idx_content_templates_platform ON content_templates(platform)",
            "CREATE INDEX IF NOT EXISTS idx_content_templates_active ON content_templates(active)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts(platform)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_date ON social_posts(post_date)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_campaign ON social_posts(campaign)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_caption_hash ON social_posts(caption_hash)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_opportunity ON social_posts(opportunity_type)",
            "CREATE INDEX IF NOT EXISTS idx_media_usage_media ON media_usage(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_usage_post ON media_usage(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_usage_used_at ON media_usage(used_at)",
            "CREATE INDEX IF NOT EXISTS idx_writing_patterns_post ON writing_patterns(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_hashtags_tag ON hashtags(tag)",
            "CREATE INDEX IF NOT EXISTS idx_hashtags_use_count ON hashtags(use_count)"
        )

        for statement in indexes:
            cur.execute(statement)
