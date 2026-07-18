import sqlite3
from pathlib import Path
import json
import re
from datetime import datetime, time, timedelta, timezone

from database.analysis_queue_repository import AnalysisQueueRepository
from database.analysis_queue_schema import (
    analysis_queue_indexes,
    create_analysis_queue_tables
)
from database.benchmark_repository import BenchmarkRepository
from database.benchmark_schema import (
    benchmark_indexes,
    create_benchmark_tables
)
from database.communication_repository import CommunicationRepository
from database.communication_learning_repository import CommunicationLearningRepository
from database.communication_learning_schema import (
    communication_learning_indexes,
    create_communication_learning_tables
)
from database.communication_schema import (
    communication_indexes,
    create_communication_tables
)
from services.logging_service import LoggingService
from services.time_service import TimeService


logger = LoggingService.get_logger("database")


class DatabaseManager:

    def __init__(self):

        Path("database").mkdir(exist_ok=True)

        self.db = Path("database") / "mfr_content.db"
        self._analysis_queue_repo = None
        self._benchmark_repo = None
        self._communication_repo = None
        self._communication_learning_repo = None

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

            first_seen_at TEXT,

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
,
            failure_category TEXT,

            raw_response TEXT,

            parse_status TEXT,

            parse_warnings TEXT,

            confidence REAL DEFAULT 0,

            people TEXT,

            activities TEXT,

            setting TEXT,

            indoor_outdoor TEXT,

            safety_concerns TEXT,

            public_use_risks TEXT,

            visible_text TEXT,

            uncertain_observations TEXT,

            structured_field_completeness REAL DEFAULT 0,

            request_metadata TEXT,

            preprocessing_metadata TEXT,

            provider_attempts TEXT,

            provider_response_excerpt TEXT,

            provider_status_code INTEGER,

            prompt_version TEXT,

            analysis_version TEXT,

            quality_state TEXT,

            trust_state TEXT,

            review_status TEXT,

            quality_warnings TEXT,

            media_context TEXT,

            reviewed_at TEXT,

            reviewer_notes TEXT

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS video_intelligence(

            media_id INTEGER PRIMARY KEY,

            duration_seconds REAL DEFAULT 0,

            analyzed_frame_count INTEGER DEFAULT 0,

            frame_timestamps TEXT,

            people_observed TEXT,

            apparatus_observed TEXT,

            equipment_observed TEXT,

            activities_observed TEXT,

            settings_observed TEXT,

            visible_text TEXT,

            uncertain_observations TEXT,

            likely_content_category TEXT,

            confidence REAL DEFAULT 0,

            review_state TEXT,

            provider TEXT,

            model TEXT,

            analysis_version TEXT,

            raw_frame_outputs TEXT,

            video_summary TEXT,

            primary_activity TEXT,

            secondary_activity TEXT,

            estimated_scene_count INTEGER DEFAULT 0,

            representative_frames TEXT,

            identified_ppe TEXT,

            training_evolution TEXT,

            incident_category TEXT,

            program TEXT,

            campaign TEXT,

            community_event TEXT,

            estimated_audience TEXT,

            communications_themes TEXT,

            story_potential INTEGER DEFAULT 0,

            education_score INTEGER DEFAULT 0,

            recruitment_score INTEGER DEFAULT 0,

            community_score INTEGER DEFAULT 0,

            operations_score INTEGER DEFAULT 0,

            reel_potential INTEGER DEFAULT 0,

            reel_explanation TEXT,

            clip_recommendations TEXT,

            cover_recommendation TEXT,

            story_category TEXT,

            trust_state TEXT,

            explanation TEXT,

            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS analysis_review_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            media_id INTEGER,

            analysis_saved_at TEXT,

            decision TEXT,

            trust_state TEXT,

            review_status TEXT,

            reviewer TEXT,

            corrections_json TEXT,

            notes TEXT,

            created_at TEXT

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS ai_analysis_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            media_id INTEGER,

            provider TEXT,

            model TEXT,

            failure_reason TEXT,

            analysis_json TEXT,

            saved_at TEXT

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
        # Filesystem Intelligence
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS filesystem_intelligence(

            media_id INTEGER PRIMARY KEY,

            media_root TEXT,

            relative_path TEXT,

            folder_hierarchy TEXT,

            root_category TEXT,

            parent_category TEXT,

            subcategory TEXT,

            folder_keywords TEXT,

            normalized_tags TEXT,

            apparatus_identifier TEXT,

            apparatus_name TEXT,

            apparatus_resolved INTEGER DEFAULT 0,

            incident_category TEXT,

            incident_type TEXT,

            training_category TEXT,

            training_type TEXT,

            drill_type TEXT,

            live_burn_context INTEGER DEFAULT 0,

            public_education_program TEXT,

            campaign TEXT,

            community_event TEXT,

            station TEXT,

            recruit_class INTEGER DEFAULT 0,

            mutual_aid_context INTEGER DEFAULT 0,

            year TEXT,

            month INTEGER DEFAULT 0,

            season TEXT,

            location_context TEXT,

            filesystem_confidence INTEGER DEFAULT 0,

            matching_rule TEXT,

            source_folders TEXT,

            conflict_state TEXT,

            conflict_details TEXT,

            enrichment_version TEXT,

            last_derived_at TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        ########################################################
        # Fire Service Intelligence
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS fire_service_intelligence(

            media_id INTEGER PRIMARY KEY,

            firefighter_count INTEGER,

            civilian_count INTEGER,

            officer_presence INTEGER,

            children_present INTEGER,

            group_size TEXT,

            personnel TEXT,

            ppe TEXT,

            equipment TEXT,

            apparatus TEXT,

            incident_classification TEXT,

            operational_activity TEXT,

            communications_uses TEXT,

            reasoning TEXT,

            operational_context TEXT,

            operational_skills TEXT,

            communications_intent TEXT,

            operational_confidence INTEGER,

            reasoning_evidence TEXT,

            operational_reasoning TEXT,

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
        # Communication Package History / Asset Actions
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS communication_package_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            package_id TEXT,

            recommendation_id TEXT,

            story_title TEXT,

            package_version TEXT,

            package_json TEXT,

            created_at TEXT

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS communication_package_asset_actions(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            package_id TEXT,

            media_id INTEGER,

            action TEXT,

            reason TEXT,

            previous_role TEXT,

            new_role TEXT,

            previous_media_id INTEGER DEFAULT 0,

            source TEXT,

            created_at TEXT

        )

        """)

        ########################################################
        # Home / Morning Brief Sessions
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS home_sessions(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            started_at TEXT,

            completed_at TEXT,

            status TEXT,

            duration_seconds REAL DEFAULT 0,

            summary_json TEXT,

            metrics_json TEXT

        )

        """)

        ########################################################
        # Decision Explainability / Audit Trail
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS decision_audit_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            decision_id TEXT,

            decision_type TEXT,

            subject_type TEXT,

            subject_id TEXT,

            headline TEXT,

            decision_score REAL DEFAULT 0,

            confidence_score REAL DEFAULT 0,

            trust_label TEXT,

            rank INTEGER DEFAULT 0,

            snapshot_json TEXT,

            generated_at TEXT,

            explanation_version TEXT

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
        # Human Feedback Intelligence
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS media_corrections(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            media_id INTEGER,

            field_name TEXT,

            original_value TEXT,

            corrected_value TEXT,

            correction_source TEXT,

            confidence_before INTEGER DEFAULT 0,

            confidence_after INTEGER DEFAULT 100,

            notes TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            active INTEGER DEFAULT 1

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS correction_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            correction_id INTEGER,

            media_id INTEGER,

            field_name TEXT,

            previous_value TEXT,

            new_value TEXT,

            correction_source TEXT,

            action TEXT,

            notes TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS correction_patterns(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            field_name TEXT,

            original_value TEXT,

            corrected_value TEXT,

            occurrence_count INTEGER DEFAULT 1,

            confidence INTEGER DEFAULT 50,

            example_media_ids TEXT,

            notes TEXT,

            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            active INTEGER DEFAULT 1,

            UNIQUE(field_name, original_value, corrected_value)

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
        # Knowledge Graph
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS entity_types(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE,

            description TEXT,

            active INTEGER DEFAULT 1

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS knowledge_categories(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE,

            description TEXT,

            active INTEGER DEFAULT 1

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS knowledge_sources(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE,

            source_type TEXT,

            path TEXT,

            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            confidence INTEGER DEFAULT 80,

            active INTEGER DEFAULT 1

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS entities(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            type TEXT,

            description TEXT,

            aliases TEXT,

            confidence INTEGER DEFAULT 80,

            active INTEGER DEFAULT 1,

            source TEXT,

            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(name, type)

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS entity_aliases(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            entity_id INTEGER,

            alias TEXT,

            normalized_alias TEXT,

            confidence INTEGER DEFAULT 80,

            active INTEGER DEFAULT 1,

            UNIQUE(entity_id, normalized_alias)

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS entity_relationships(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            source_entity_id INTEGER,

            target_entity_id INTEGER,

            relationship_type TEXT,

            description TEXT,

            confidence INTEGER DEFAULT 80,

            active INTEGER DEFAULT 1,

            source TEXT,

            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(source_entity_id, target_entity_id, relationship_type)

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

        cur.execute("""

        CREATE TABLE IF NOT EXISTS communications_intelligence_profiles(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            profile_type TEXT,

            profile_key TEXT,

            version TEXT,

            generated_at TEXT,

            sample_count INTEGER DEFAULT 0,

            confidence INTEGER DEFAULT 0,

            profile_json TEXT,

            source_summary_json TEXT

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS communication_edit_learning(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            platform TEXT,

            original_text TEXT,

            final_text TEXT,

            change_summary_json TEXT,

            source TEXT,

            approved INTEGER DEFAULT 1,

            created_at TEXT

        )

        """)

        create_analysis_queue_tables(cur)
        create_communication_tables(cur)
        create_benchmark_tables(cur)
        create_communication_learning_tables(cur)

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

        ########################################################
        # Editorial Strategies
        ########################################################

        cur.execute("""

        CREATE TABLE IF NOT EXISTS editorial_strategies(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            media_id INTEGER,

            strategy_id TEXT,

            strategy_type TEXT,

            title TEXT,

            objective TEXT,

            audience TEXT,

            core_message TEXT,

            reasoning TEXT,

            confidence INTEGER DEFAULT 0,

            communications_score INTEGER DEFAULT 0,

            recommended_platforms TEXT,

            posting_window TEXT,

            recommended_media TEXT,

            caption_direction TEXT,

            CTA TEXT,

            risks TEXT,

            limitations TEXT,

            supporting_evidence TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            selected INTEGER DEFAULT 0,

            dismissed INTEGER DEFAULT 0,

            UNIQUE(media_id, strategy_id)

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS editorial_comparisons(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            media_id INTEGER,

            recommended_strategy_id TEXT,

            runner_up_strategy_id TEXT,

            comparison_summary TEXT,

            tradeoffs TEXT,

            why_not_others TEXT,

            debate_summary TEXT,

            confidence INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

        """)

        self._ensure_media_columns(cur)
        self._ensure_analysis_session_columns(cur)
        self._ensure_analysis_queue_columns(cur)
        self._ensure_ai_analysis_columns(cur)
        self._ensure_media_intelligence_columns(cur)
        self._ensure_video_intelligence_columns(cur)
        self._ensure_fire_service_intelligence_columns(cur)
        self._ensure_knowledge_columns(cur)
        self._ensure_communication_columns(cur)
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

        first_seen_at = (
            media.get("first_seen_at") or
            media.get("discovered_at") or
            media.get("imported_at") or
            TimeService.utc_now_iso()
        )

        cur.execute("""

        INSERT OR IGNORE INTO media(

            filename,

            path,

            extension,

            media_type,

            filesize,

            sha256,

            first_seen_at,

            date_added,

            file_created_at,

            file_modified_at,

            capture_time,

            capture_time_source,

            duration_seconds,

            width,

            height,

            frame_rate,

            orientation,

            codec,

            thumbnail_status

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        """,

        (

            media["filename"],

            media["path"],

            media["extension"],

            media["type"],

            media["size"],

            media["sha256"],

            first_seen_at,

            first_seen_at,

            media.get("file_created_at", ""),

            media.get("file_modified_at", ""),

            media.get("capture_time", ""),

            media.get("capture_time_source", ""),

            self._to_float(media.get("duration_seconds")),

            self._to_int(media.get("width")),

            self._to_int(media.get("height")),

            self._to_float(media.get("frame_rate")),

            media.get("orientation", ""),

            media.get("codec", ""),

            media.get("thumbnail_status", "")

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

    def get_media_details(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM media
        WHERE id=?
        """, (self._to_int(media_id),))
        row = cur.fetchone()
        conn.close()

        if row is None:
            return None

        return {
            "id": row["id"],
            "filename": row["filename"] or "",
            "path": row["path"] or "",
            "extension": row["extension"] or "",
            "media_type": row["media_type"] or "",
            "filesize": row["filesize"] or 0,
            "first_seen_at": row["first_seen_at"] or row["date_added"] or "",
            "date_added": row["first_seen_at"] or row["date_added"] or "",
            "legacy_date_added": row["date_added"] or "",
            "file_created_at": row["file_created_at"] or "",
            "file_modified_at": row["file_modified_at"] or "",
            "capture_time": row["capture_time"] or "",
            "capture_time_source": row["capture_time_source"] or "",
            "duration_seconds": row["duration_seconds"] or 0,
            "width": row["width"] or 0,
            "height": row["height"] or 0,
            "frame_rate": row["frame_rate"] or 0,
            "orientation": row["orientation"] or "",
            "codec": row["codec"] or "",
            "thumbnail_status": row["thumbnail_status"] or ""
        }

    ############################################################

    def update_media_video_metadata(self, media_id, metadata):

        conn = self.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE media
        SET
            duration_seconds=?,
            width=?,
            height=?,
            frame_rate=?,
            orientation=?,
            codec=?,
            capture_time=?,
            capture_time_source=?,
            thumbnail_status=?
        WHERE id=?
        """,
        (
            self._to_float(metadata.get("duration")),
            self._to_int(metadata.get("width")),
            self._to_int(metadata.get("height")),
            self._to_float(metadata.get("frame_rate")),
            metadata.get("orientation", ""),
            metadata.get("codec", ""),
            metadata.get("capture_time", ""),
            (
                "video_metadata"
                if metadata.get("capture_time")
                else ""
            ),
            metadata.get("thumbnail_status", ""),
            self._to_int(media_id)
        ))
        conn.commit()
        conn.close()

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

    def get_media_page(self, limit, offset=0, filter_key="all", sort_key="filename_az"):

        conn = self.connection()
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        where, params, order_by = self._gallery_filter_clause(
            filter_key,
            sort_key=sort_key
        )

        cur.execute(f"""

        SELECT

            media.id,

            media.filename,

            media.path,

            media.media_type,

            media.duration_seconds,

            COALESCE(media.first_seen_at, media.date_added) AS date_added,

            media.capture_time,

            ai_analysis.provider,

            ai_analysis.model,

            ai_analysis.failure_reason,
            ai_analysis.failure_category,

            ai_analysis.trust_state,

            ai_analysis.review_status,

            ai_analysis.quality_state,

            media_intelligence.media_id AS intelligence_media_id,

            filesystem_intelligence.root_category AS filesystem_category,

            filesystem_intelligence.subcategory AS filesystem_subcategory,

            filesystem_intelligence.conflict_state AS filesystem_conflict,

            media_corrections.id AS correction_id,

            latest_queue.state AS queue_state,
            latest_queue.session_status AS queue_session_status

        FROM media

        LEFT JOIN ai_analysis
        ON ai_analysis.media_id=media.id

        LEFT JOIN media_intelligence
        ON media_intelligence.media_id=media.id

        LEFT JOIN filesystem_intelligence
        ON filesystem_intelligence.media_id=media.id

        LEFT JOIN video_intelligence
        ON video_intelligence.media_id=media.id

        LEFT JOIN (
            SELECT media_id, MIN(id) AS id
            FROM media_corrections
            WHERE active=1
            GROUP BY media_id
        ) media_corrections
        ON media_corrections.media_id=media.id

        LEFT JOIN (
            SELECT q1.media_id, q1.state, s.status AS session_status
            FROM analysis_queue q1
            LEFT JOIN analysis_sessions s
            ON s.session_id=q1.session_id
            INNER JOIN (
                SELECT media_id, MAX(queue_id) AS queue_id
                FROM analysis_queue
                GROUP BY media_id
            ) latest
            ON latest.queue_id=q1.queue_id
        ) latest_queue
        ON latest_queue.media_id=media.id

        {where}

        ORDER BY {order_by}

        LIMIT ? OFFSET ?

        """,

        tuple(params + [
            limit,

            offset
        ]))

        rows = [
            (
                row["id"],
                row["filename"],
                row["path"],
                row["media_type"],
                self._media_analysis_status_from_row(row),
                row["duration_seconds"] or 0,
                row["date_added"] or "",
                row["capture_time"] or "",
                self._filesystem_badge_from_row(row)
            )
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def _media_analysis_status_from_row(self, row):

        queue_state = row["queue_state"] or ""
        session_status = row["queue_session_status"] or ""

        if (
            session_status in ("Recoverable", "Interrupted")
            and queue_state in ("Waiting", "Queued", "Analyzing", "Retry Pending")
        ):
            return "Interrupted"

        if queue_state in (
            "Waiting",
            "Queued",
            "Retry Pending"
        ):
            return "Queued"

        if queue_state == "Analyzing":
            return "Analyzing"

        if (
            row["media_type"] == "video"
            and row["failure_category"] == "unsupported_provider"
        ):
            return "Unsupported Provider"

        if row["failure_reason"]:
            return "Failed"

        provider = row["provider"] or ""
        model = row["model"] or ""
        trust_state = row["trust_state"] or ""
        review_status = row["review_status"] or ""

        if provider == "mock" or model.startswith("mock"):
            return "Mock/Test Data"

        if provider:
            if trust_state == "rejected_real" or review_status == "rejected":
                return "Real - Rejected"

            if row["correction_id"]:
                return "Real - Corrected"

            if trust_state == "corrected_real" or review_status == "corrected":
                return "Real - Corrected"

            if trust_state == "approved_real" or review_status == "approved":
                return "Real - Approved"

            if trust_state == "unreviewed_real" or review_status == "review_required":
                return "Real - Review Required"

            if row["intelligence_media_id"]:
                return "Real - Review Required"

            return "Real - Review Required"

        return "Not analyzed"

    ############################################################

    def _filesystem_badge_from_row(self, row):

        conflict = row["filesystem_conflict"] or ""

        if conflict == "conflict":
            return "Folder Conflict"

        category = row["filesystem_category"] or ""
        subcategory = row["filesystem_subcategory"] or ""

        if not category or category == "unknown":
            return ""

        if subcategory and subcategory != "unknown":
            return f"{category}: {subcategory}"

        return category

    ############################################################

    def media_count(self, filter_key="all"):

        conn = self.connection()

        cur = conn.cursor()
        where, params, _order_by = self._gallery_filter_clause(filter_key)

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM media
            LEFT JOIN ai_analysis
            ON ai_analysis.media_id=media.id
            LEFT JOIN media_intelligence
            ON media_intelligence.media_id=media.id
            LEFT JOIN filesystem_intelligence
            ON filesystem_intelligence.media_id=media.id
            LEFT JOIN video_intelligence
            ON video_intelligence.media_id=media.id
            {self._gallery_correction_join()}
            {self._gallery_queue_join()}
            {where}
            """,
            tuple(params)
        )

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def media_count_for_selection(self, filter_key="all", media_type=None):

        conn = self.connection()

        cur = conn.cursor()
        where, params, _order_by = self._gallery_filter_clause(filter_key)
        clauses = []

        if where:
            clauses.append(where.replace("WHERE ", "", 1))

        if media_type:
            clauses.append("media.media_type=?")
            params.append(str(media_type))

        final_where = (
            "WHERE " + " AND ".join(clauses)
            if clauses
            else ""
        )

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM media
            LEFT JOIN ai_analysis
            ON ai_analysis.media_id=media.id
            LEFT JOIN media_intelligence
            ON media_intelligence.media_id=media.id
            LEFT JOIN filesystem_intelligence
            ON filesystem_intelligence.media_id=media.id
            LEFT JOIN video_intelligence
            ON video_intelligence.media_id=media.id
            {self._gallery_correction_join()}
            {self._gallery_queue_join()}
            {final_where}
            """,
            tuple(params)
        )

        count = cur.fetchone()[0]

        conn.close()

        return count

    ############################################################

    def get_media_ids_for_selection(
        self,
        filter_key="all",
        media_type=None,
        limit=10000
    ):

        conn = self.connection()
        cur = conn.cursor()
        where, params, order_by = self._gallery_filter_clause(filter_key)
        clauses = []

        if where:
            clauses.append(where.replace("WHERE ", "", 1))

        if media_type:
            clauses.append("media.media_type=?")
            params.append(str(media_type))

        final_where = (
            "WHERE " + " AND ".join(clauses)
            if clauses
            else ""
        )

        cur.execute(
            f"""
            SELECT media.id
            FROM media
            LEFT JOIN ai_analysis
            ON ai_analysis.media_id=media.id
            LEFT JOIN media_intelligence
            ON media_intelligence.media_id=media.id
            LEFT JOIN filesystem_intelligence
            ON filesystem_intelligence.media_id=media.id
            LEFT JOIN video_intelligence
            ON video_intelligence.media_id=media.id
            {self._gallery_correction_join()}
            {self._gallery_queue_join()}
            {final_where}
            ORDER BY {order_by}
            LIMIT ?
            """,
            tuple(params + [self._to_int(limit)])
        )

        ids = [
            row[0]
            for row in cur.fetchall()
        ]

        conn.close()

        return ids

    ############################################################

    def analysis_selection_preview(
        self,
        media_ids,
        force=False,
        retry_failed=False
    ):

        ids = [
            self._to_int(media_id)
            for media_id in media_ids
            if self._to_int(media_id)
        ]

        if not ids:
            return {
                "selected_count": 0,
                "photo_count": 0,
                "video_count": 0,
                "genuinely_unanalyzed_count": 0,
                "completed_real_analysis_count": 0,
                "mock_only_count": 0,
                "failed_count": 0,
                "retryable_failed_count": 0,
                "video_metadata_only_count": 0,
                "queueable_ids": [],
                "skipped_ids": [],
                "force_reanalysis": bool(force),
                "retry_failed": bool(retry_failed)
            }

        placeholders = ",".join("?" for _ in ids)
        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT
                media.id,
                media.media_type,
                ai_analysis.provider,
                ai_analysis.model,
                ai_analysis.failure_reason,
                ai_analysis.trust_state,
                ai_analysis.review_status,
                video_intelligence.media_id AS video_intelligence_id
            FROM media
            LEFT JOIN ai_analysis
            ON ai_analysis.media_id=media.id
            LEFT JOIN video_intelligence
            ON video_intelligence.media_id=media.id
            WHERE media.id IN ({placeholders})
            """,
            tuple(ids)
        )
        rows = cur.fetchall()
        conn.close()

        by_id = {
            row["id"]: row
            for row in rows
        }
        counts = {
            "selected_count": len(ids),
            "photo_count": 0,
            "video_count": 0,
            "genuinely_unanalyzed_count": 0,
            "completed_real_analysis_count": 0,
            "mock_only_count": 0,
            "failed_count": 0,
            "retryable_failed_count": 0,
            "video_metadata_only_count": 0,
            "queueable_ids": [],
            "skipped_ids": [],
            "force_reanalysis": bool(force),
            "retry_failed": bool(retry_failed)
        }

        for media_id in ids:
            row = by_id.get(media_id)

            if not row:
                counts["skipped_ids"].append(media_id)
                continue

            media_type = row["media_type"] or ""

            if media_type == "video":
                counts["video_count"] += 1
            else:
                counts["photo_count"] += 1

            provider = row["provider"] or ""
            model = row["model"] or ""
            failure = row["failure_reason"] or ""
            trust_state = row["trust_state"] or ""
            review_status = row["review_status"] or ""
            is_mock = (
                provider == "mock" or
                str(model).startswith("mock")
            )
            is_real = (
                bool(provider) and
                provider != "mock" and
                not str(model).startswith("mock") and
                not failure
            )
            is_failed = bool(failure)
            is_completed_real = is_real
            is_protected_real = (
                trust_state in ("approved_real", "corrected_real") or
                review_status in ("approved", "corrected")
            )

            if is_completed_real:
                counts["completed_real_analysis_count"] += 1

            if is_mock and not is_completed_real:
                counts["mock_only_count"] += 1

            if is_failed and not is_completed_real:
                counts["failed_count"] += 1
                counts["retryable_failed_count"] += 1

            if media_type == "video" and row["video_intelligence_id"] and not is_completed_real:
                counts["video_metadata_only_count"] += 1

            if not provider and not row["video_intelligence_id"]:
                counts["genuinely_unanalyzed_count"] += 1

            should_queue = False

            if force and is_completed_real and not is_protected_real:
                should_queue = True
            elif is_failed and retry_failed:
                should_queue = True
            elif not is_completed_real and not is_failed:
                should_queue = True

            if is_protected_real and not force:
                should_queue = False

            if should_queue:
                counts["queueable_ids"].append(media_id)
            else:
                counts["skipped_ids"].append(media_id)

        return counts

    ############################################################

    def _gallery_filter_clause(self, filter_key, sort_key="filename_az"):

        filter_key = str(filter_key or "all").lower()
        sort_key = str(sort_key or "filename_az").lower()
        clauses = []
        params = []
        order_by = self._gallery_order_by(sort_key)
        added_expr = self._media_added_timestamp_expr()
        real_completed = self._gallery_real_completed_clause()
        not_real_completed = f"NOT ({real_completed})"
        failed_clause = """
            (
                ai_analysis.failure_reason IS NOT NULL
                AND ai_analysis.failure_reason!=''
                AND NOT (
                    ai_analysis.provider IS NOT NULL
                    AND ai_analysis.provider!=''
                    AND ai_analysis.provider!='mock'
                    AND ai_analysis.model NOT LIKE 'mock%'
                    AND (ai_analysis.failure_reason IS NULL OR ai_analysis.failure_reason='')
                )
            )
        """

        if filter_key == "photos":
            clauses.append("media.media_type='image'")

        elif filter_key == "videos":
            clauses.append("media.media_type='video'")

        elif filter_key == "highest_reel_potential":
            clauses.append("media.media_type='video'")
            clauses.append("video_intelligence.reel_potential > 0")
            order_by = "video_intelligence.reel_potential DESC, media.id DESC"

        elif filter_key == "training_videos":
            clauses.append("media.media_type='video'")
            clauses.append(
                """
                (
                    video_intelligence.story_category='Training'
                    OR video_intelligence.primary_activity LIKE '%training%'
                    OR filesystem_intelligence.root_category='Training'
                )
                """
            )

        elif filter_key == "incident_videos":
            clauses.append("media.media_type='video'")
            clauses.append(
                """
                (
                    video_intelligence.story_category IN ('Incident', 'Operations')
                    OR video_intelligence.incident_category NOT IN ('', 'unknown')
                    OR filesystem_intelligence.root_category='Incidents'
                )
                """
            )

        elif filter_key == "community_videos":
            clauses.append("media.media_type='video'")
            clauses.append(
                """
                (
                    video_intelligence.story_category='Community'
                    OR video_intelligence.community_event!=''
                    OR filesystem_intelligence.root_category='Community'
                )
                """
            )

        elif filter_key == "recruitment_videos":
            clauses.append("media.media_type='video'")
            clauses.append(
                """
                (
                    video_intelligence.recruitment_score >= 60
                    OR video_intelligence.story_category='Recruitment'
                )
                """
            )

        elif filter_key == "reviewed_videos":
            clauses.append("media.media_type='video'")
            clauses.append(
                """
                (
                    video_intelligence.review_state IN ('approved', 'corrected')
                    OR ai_analysis.review_status IN ('approved', 'corrected')
                )
                """
            )

        elif filter_key == "unreviewed_videos":
            clauses.append("media.media_type='video'")
            clauses.append(
                """
                (
                    (
                        video_intelligence.review_state IS NULL
                        OR video_intelligence.review_state=''
                        OR video_intelligence.review_state='review_required'
                    )
                    AND (
                        ai_analysis.review_status IS NULL
                        OR ai_analysis.review_status=''
                        OR ai_analysis.review_status='review_required'
                    )
                )
                """
            )

        elif filter_key == "filesystem_training":
            clauses.append("filesystem_intelligence.root_category='Training'")

        elif filter_key == "filesystem_incidents":
            clauses.append("filesystem_intelligence.root_category='Incidents'")

        elif filter_key == "filesystem_apparatus":
            clauses.append("filesystem_intelligence.root_category='Apparatus'")

        elif filter_key == "filesystem_programs":
            clauses.append("filesystem_intelligence.root_category='Programs'")

        elif filter_key == "filesystem_campaigns":
            clauses.append("filesystem_intelligence.root_category='Campaigns'")

        elif filter_key == "filesystem_community":
            clauses.append("filesystem_intelligence.root_category='Community'")

        elif filter_key == "filesystem_conflicts":
            clauses.append("filesystem_intelligence.conflict_state='conflict'")

        elif filter_key == "has_filesystem_intelligence":
            clauses.append("filesystem_intelligence.media_id IS NOT NULL")

        elif filter_key == "missing_filesystem_intelligence":
            clauses.append("filesystem_intelligence.media_id IS NULL")

        elif filter_key in ("new_today", "added_today"):
            start, end = self._local_day_utc_bounds()
            clauses.append(
                f"""
                datetime({added_expr}) >= datetime(?)
                AND datetime({added_expr}) < datetime(?)
                """
            )
            params.extend([start, end])
            if sort_key == "filename_az":
                order_by = f"{added_expr} DESC, media.id DESC"

        elif filter_key == "captured_today":
            start, end = self._local_day_utc_bounds()
            capture_expr = self._media_timestamp_expr("media.capture_time")
            clauses.append(
                f"""
                datetime({capture_expr}) >= datetime(?)
                AND datetime({capture_expr}) < datetime(?)
                """
            )
            params.extend([start, end])
            if sort_key == "filename_az":
                order_by = f"{capture_expr} DESC, media.id DESC"

        elif filter_key == "last_7_days":
            clauses.append(
                f"datetime({added_expr}) >= datetime('now', '-7 days')"
            )
            if sort_key == "filename_az":
                order_by = f"{added_expr} DESC, media.id DESC"

        elif filter_key == "last_30_days":
            clauses.append(
                f"datetime({added_expr}) >= datetime('now', '-30 days')"
            )
            if sort_key == "filename_az":
                order_by = f"{added_expr} DESC, media.id DESC"

        elif filter_key == "last_12_months":
            clauses.append(
                f"datetime({added_expr}) >= datetime('now', '-365 days')"
            )
            if sort_key == "filename_az":
                order_by = f"{added_expr} DESC, media.id DESC"

        elif filter_key in ("unanalyzed", "not_analyzed"):
            clauses.append(not_real_completed)

        elif filter_key == "analyzed":
            clauses.append(real_completed)

        elif filter_key == "real_analysis":
            clauses.append(real_completed)

        elif filter_key == "review_required":
            clauses.append(
                f"""
                (
                    {real_completed}
                    AND (
                    ai_analysis.review_status='review_required'
                    OR ai_analysis.trust_state='unreviewed_real'
                    OR (
                        ai_analysis.review_status IS NULL
                        OR ai_analysis.review_status=''
                    )
                    )
                )
                """
            )

        elif filter_key == "approved":
            clauses.append(
                f"""
                (
                    {real_completed}
                    AND (
                    ai_analysis.review_status='approved'
                    OR ai_analysis.trust_state='approved_real'
                    )
                )
                """
            )

        elif filter_key == "corrected":
            clauses.append(
                f"""
                (
                    {real_completed}
                    AND (
                        ai_analysis.review_status='corrected'
                        OR ai_analysis.trust_state='corrected_real'
                        OR media_corrections.id IS NOT NULL
                    )
                )
                """
            )

        elif filter_key == "rejected":
            clauses.append(
                f"""
                (
                    {real_completed}
                    AND (
                        ai_analysis.review_status='rejected'
                        OR ai_analysis.trust_state='rejected_real'
                    )
                )
                """
            )

        elif filter_key == "failed":
            clauses.append(failed_clause)

        elif filter_key in ("mock", "mock_test_data"):
            clauses.append(
                """
                (
                    ai_analysis.media_id IS NOT NULL
                    AND (
                        ai_analysis.provider='mock'
                        OR ai_analysis.model LIKE 'mock%'
                        OR ai_analysis.description LIKE 'MOCK TEST ANALYSIS%'
                    )
                )
                """
            )

        elif filter_key == "photos_not_analyzed":
            clauses.append("media.media_type='image'")
            clauses.append(not_real_completed)

        elif filter_key == "videos_not_analyzed":
            clauses.append("media.media_type='video'")
            clauses.append(
                f"""
                (
                    {not_real_completed}
                    AND video_intelligence.media_id IS NULL
                )
                """
            )

        where = ""

        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        return where, params, order_by

    ############################################################

    def _gallery_real_completed_clause(self):

        return """
            (
                ai_analysis.media_id IS NOT NULL
                AND ai_analysis.provider IS NOT NULL
                AND ai_analysis.provider!=''
                AND ai_analysis.provider!='mock'
                AND ai_analysis.model NOT LIKE 'mock%'
                AND (ai_analysis.failure_reason IS NULL OR ai_analysis.failure_reason='')
            )
        """

    ############################################################

    def _gallery_correction_join(self):

        return """
            LEFT JOIN (
                SELECT media_id, MIN(id) AS id
                FROM media_corrections
                WHERE active=1
                GROUP BY media_id
            ) media_corrections
            ON media_corrections.media_id=media.id
        """

    ############################################################

    def _gallery_queue_join(self):

        return """
            LEFT JOIN (
                SELECT q1.media_id, q1.state, s.status AS session_status
                FROM analysis_queue q1
                LEFT JOIN analysis_sessions s
                ON s.session_id=q1.session_id
                INNER JOIN (
                    SELECT media_id, MAX(queue_id) AS queue_id
                    FROM analysis_queue
                    GROUP BY media_id
                ) latest
                ON latest.queue_id=q1.queue_id
            ) latest_queue
            ON latest_queue.media_id=media.id
        """

    ############################################################

    def _gallery_order_by(self, sort_key):

        added_expr = self._media_added_timestamp_expr()
        capture_expr = self._media_timestamp_expr("media.capture_time")
        analysis_expr = self._media_timestamp_expr("ai_analysis.last_analyzed")
        not_analyzed = self._gallery_real_completed_clause()

        options = {
            "added_newest": f"{added_expr} DESC, media.id DESC",
            "added_oldest": f"{added_expr} ASC, media.id ASC",
            "capture_newest": f"{capture_expr} DESC, media.id DESC",
            "capture_oldest": f"{capture_expr} ASC, media.id ASC",
            "analysis_newest": f"{analysis_expr} DESC, media.id DESC",
            "analysis_oldest": f"{analysis_expr} ASC, media.id ASC",
            "not_analyzed_first": f"CASE WHEN NOT ({not_analyzed}) THEN 0 ELSE 1 END, media.id DESC",
            "review_required_first": "CASE WHEN ai_analysis.review_status='review_required' OR ai_analysis.trust_state='unreviewed_real' THEN 0 ELSE 1 END, media.id DESC",
            "corrected_first": "CASE WHEN ai_analysis.review_status='corrected' OR ai_analysis.trust_state='corrected_real' OR media_corrections.id IS NOT NULL THEN 0 ELSE 1 END, media.id DESC",
            "failed_first": "CASE WHEN ai_analysis.failure_reason IS NOT NULL AND ai_analysis.failure_reason!='' THEN 0 ELSE 1 END, media.id DESC",
            "filename_za": "media.filename COLLATE NOCASE DESC, media.id DESC",
            "filename_az": "media.filename COLLATE NOCASE ASC, media.id ASC"
        }

        return options.get(sort_key, options["filename_az"])

    ############################################################

    def _local_day_utc_bounds(self, date_value=None):

        local_zone = TimeService.local_timezone()
        local_now = TimeService.to_local(
            TimeService.utc_now_iso()
        )
        day = date_value or local_now.date()
        local_start = datetime.combine(
            day,
            time.min,
            tzinfo=local_zone
        )
        local_end = local_start + timedelta(days=1)
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)

        return (
            utc_start.strftime("%Y-%m-%d %H:%M:%S"),
            utc_end.strftime("%Y-%m-%d %H:%M:%S")
        )

    ############################################################

    def _media_added_timestamp_expr(self):

        return self._media_timestamp_expr(
            "COALESCE(media.first_seen_at, media.date_added)"
        )

    ############################################################

    def _media_timestamp_expr(self, field):

        return (
            "REPLACE(REPLACE(REPLACE("
            f"{field}, "
            "'T', ' '), '+00:00', ''), ' UTC', '')"
        )

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

        now = TimeService.utc_now_iso()

        self._save_ai_analysis_history(
            cur,
            media_id,
            analysis,
            now
        )

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

            last_analyzed,

            raw_response,

            parse_status,

            parse_warnings,

            confidence,

            people,

            activities,

            setting,

            indoor_outdoor,

            safety_concerns,

            public_use_risks,

            structured_field_completeness
,
            failure_category,

            visible_text,

            uncertain_observations,

            request_metadata,

            preprocessing_metadata,

            provider_attempts,

            provider_response_excerpt,

            provider_status_code,

            prompt_version,

            analysis_version,

            quality_state,

            trust_state,

            review_status,

            quality_warnings,

            media_context,

            reviewed_at,

            reviewer_notes

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

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

            now,

            analysis.get("model"),

            self._to_float(analysis.get("analysis_duration")),

            analysis.get("provider"),

            self._to_int(analysis.get("retry_count")),

            analysis.get("failure_reason"),

            now,

            analysis.get("raw_response"),

            analysis.get("parse_status"),

            self._to_json(analysis.get("parse_warnings")),

            self._to_float(analysis.get("confidence")),

            self._to_json(analysis.get("people")),

            self._to_json(analysis.get("activities")),

            analysis.get("setting"),

            analysis.get("indoor_outdoor"),

            self._to_json(analysis.get("safety_concerns")),

            self._to_json(analysis.get("public_use_risks")),

            self._to_float(analysis.get("structured_field_completeness"))
,
            analysis.get("failure_category"),

            self._to_json(analysis.get("visible_text")),

            self._to_json(analysis.get("uncertain_observations")),

            self._to_json(analysis.get("request_metadata")),

            self._to_json(analysis.get("preprocessing_metadata")),

            self._to_json(analysis.get("provider_attempts")),

            analysis.get("provider_response_excerpt"),

            self._to_int(analysis.get("provider_status_code")),

            analysis.get("prompt_version"),

            analysis.get("analysis_version"),

            analysis.get("quality_state"),

            analysis.get("trust_state"),

            analysis.get("review_status"),

            self._to_json(analysis.get("quality_warnings")),

            analysis.get("media_context"),

            analysis.get("reviewed_at"),

            analysis.get("reviewer_notes")

        ))

        conn.commit()

        conn.close()

    ############################################################

    def _save_ai_analysis_history(self, cur, media_id, analysis, saved_at):

        cur.execute("""

        INSERT INTO ai_analysis_history(

            media_id,

            provider,

            model,

            failure_reason,

            analysis_json,

            saved_at

        )

        VALUES(?,?,?,?,?,?)

        """,

        (

            media_id,

            analysis.get("provider"),

            analysis.get("model"),

            analysis.get("failure_reason"),

            self._to_json(analysis),

            saved_at

        ))

    ############################################################

    def save_ai_failure(self, media_id, failure):

        existing = self.get_ai_analysis(media_id)

        if existing and not existing.get("failure_reason"):
            now = TimeService.utc_now_iso()
            conn = self.connection()
            cur = conn.cursor()
            self._save_ai_analysis_history(
                cur,
                media_id,
                {
                    "description": "",
                    "provider": failure.get("provider"),
                    "model": failure.get("model"),
                    "failure_reason": failure.get("failure_reason"),
                    "analysis_duration": failure.get("analysis_duration"),
                    "retry_count": failure.get("retry_count"),
                    "raw_response": failure.get("raw_response"),
                    "parse_status": failure.get("parse_status"),
                    "parse_warnings": failure.get("parse_warnings"),
                    "confidence": failure.get("confidence"),
                    "people": failure.get("people"),
                    "activities": failure.get("activities"),
                    "setting": failure.get("setting"),
                    "indoor_outdoor": failure.get("indoor_outdoor"),
                    "safety_concerns": failure.get("safety_concerns"),
                    "public_use_risks": failure.get("public_use_risks"),
                    "structured_field_completeness": failure.get(
                        "structured_field_completeness"
                    ),
                    "failure_category": failure.get("failure_category"),
                    "request_metadata": failure.get("request_metadata"),
                    "preprocessing_metadata": failure.get(
                        "preprocessing_metadata"
                    ),
                    "provider_attempts": failure.get("provider_attempts"),
                    "provider_response_excerpt": failure.get(
                        "provider_response_excerpt"
                    ),
                    "provider_status_code": failure.get(
                        "provider_status_code"
                    ),
                    "quality_state": failure.get("quality_state"),
                    "trust_state": failure.get("trust_state"),
                    "review_status": failure.get("review_status")
                },
                now
            )
            conn.commit()
            conn.close()
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
        analysis["failure_category"] = failure.get("failure_category")
        analysis["model"] = failure.get("model")

        for key in (
            "raw_response",
            "parse_status",
            "parse_warnings",
            "confidence",
            "people",
            "activities",
            "setting",
            "indoor_outdoor",
            "safety_concerns",
            "public_use_risks",
            "structured_field_completeness",
            "request_metadata",
            "preprocessing_metadata",
            "provider_attempts",
            "provider_response_excerpt",
            "provider_status_code",
            "quality_state",
            "trust_state",
            "review_status",
            "quality_warnings",
            "media_context"
        ):
            if key in failure:
                analysis[key] = failure.get(key)

        self.save_ai_analysis(
            media_id,
            analysis
        )

    ############################################################

    def analysis_review_queue(self, limit=50):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT
            media.id AS media_id,
            media.filename,
            media.path,
            ai_analysis.provider,
            ai_analysis.model,
            ai_analysis.parse_status,
            ai_analysis.confidence,
            ai_analysis.quality_state,
            ai_analysis.trust_state,
            ai_analysis.review_status,
            ai_analysis.quality_warnings,
            ai_analysis.raw_response,
            ai_analysis.last_analyzed
        FROM ai_analysis
        JOIN media
        ON media.id=ai_analysis.media_id
        WHERE ai_analysis.provider!='mock'
        AND (
            ai_analysis.review_status IS NULL
            OR ai_analysis.review_status=''
            OR ai_analysis.review_status IN ('review_required', 'reanalyze_requested')
            OR ai_analysis.trust_state='unreviewed_real'
        )
        ORDER BY ai_analysis.last_analyzed DESC
        LIMIT ?
        """, (self._to_int(limit),))
        rows = [
            {
                "media_id": row["media_id"],
                "filename": row["filename"] or "",
                "path": row["path"] or "",
                "provider": row["provider"] or "",
                "model": row["model"] or "",
                "parse_status": row["parse_status"] or "",
                "confidence": row["confidence"] or 0,
                "quality_state": row["quality_state"] or "",
                "trust_state": row["trust_state"] or "",
                "review_status": row["review_status"] or "",
                "quality_warnings": self._from_json(row["quality_warnings"]),
                "raw_response": row["raw_response"] or "",
                "last_analyzed": row["last_analyzed"] or ""
            }
            for row in cur.fetchall()
        ]
        conn.close()

        return rows

    ############################################################

    def get_priority_media_rows(
        self,
        limit=1000,
        since_days=None,
        include_photos=True,
        include_videos=True,
        only_unanalyzed=True,
        include_failed=False,
        force=False
    ):

        media_types = []

        if include_photos:
            media_types.append("image")

        if include_videos:
            media_types.append("video")

        if not media_types:
            return []

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in media_types)
        clauses = [
            f"media.media_type IN ({placeholders})"
        ]
        params = list(media_types)

        if since_days is not None:
            added_expr = self._media_added_timestamp_expr()
            capture_expr = self._media_timestamp_expr("media.capture_time")
            clauses.append(
                f"""
                (
                    datetime({added_expr}) >= datetime('now', ?)
                    OR datetime({capture_expr}) >= datetime('now', ?)
                )
                """
            )
            window = f"-{int(since_days)} days"
            params.extend([window, window])

        if only_unanalyzed:
            clauses.append(
                """
                (
                    ai_analysis.media_id IS NULL
                    OR ai_analysis.failure_reason IS NOT NULL
                    AND ai_analysis.failure_reason!=''
                )
                """
            )

        if not include_failed:
            clauses.append(
                """
                (
                    ai_analysis.failure_reason IS NULL
                    OR ai_analysis.failure_reason=''
                )
                """
            )

        if not force:
            clauses.append(
                """
                (
                    ai_analysis.trust_state IS NULL
                    OR ai_analysis.trust_state=''
                    OR ai_analysis.trust_state NOT IN ('approved_real', 'corrected_real')
                )
                """
            )

        sql = f"""
        SELECT
            media.id,
            media.filename,
            media.path,
            media.media_type,
            COALESCE(media.first_seen_at, media.date_added) AS date_added,
            media.date_added AS legacy_date_added,
            media.first_seen_at,
            media.file_created_at,
            media.file_modified_at,
            media.capture_time,
            media.capture_time_source,
            media.duration_seconds,
            media.width,
            media.height,
            media.frame_rate,
            media.orientation,
            media.codec,
            media.thumbnail_status,
            ai_analysis.provider,
            ai_analysis.model,
            ai_analysis.failure_reason,
            ai_analysis.trust_state,
            ai_analysis.review_status
        FROM media
        LEFT JOIN ai_analysis
        ON ai_analysis.media_id=media.id
        WHERE {' AND '.join(clauses)}
        ORDER BY
            COALESCE(
                media.capture_time,
                media.first_seen_at,
                media.date_added,
                media.file_modified_at,
                media.file_created_at
            ) DESC,
            media.id DESC
        LIMIT ?
        """
        params.append(self._to_int(limit))
        cur.execute(sql, tuple(params))
        rows = [
            dict(row)
            for row in cur.fetchall()
        ]
        conn.close()

        return rows

    ############################################################

    def recent_media_counts(self, since_days=None):

        conn = self.connection()
        cur = conn.cursor()
        clauses = []
        params = []

        if since_days is not None:
            added_expr = self._media_added_timestamp_expr()
            capture_expr = self._media_timestamp_expr("media.capture_time")
            clauses.append(
                f"""
                (
                    datetime({added_expr}) >= datetime('now', ?)
                    OR datetime({capture_expr}) >= datetime('now', ?)
                )
                """
            )
            window = f"-{int(since_days)} days"
            params.extend([window, window])

        where = (
            "WHERE " + " AND ".join(clauses)
            if clauses
            else ""
        )
        cur.execute(f"""
        SELECT
            COUNT(*),
            SUM(CASE WHEN media.media_type='image' THEN 1 ELSE 0 END),
            SUM(CASE WHEN media.media_type='video' THEN 1 ELSE 0 END),
            SUM(CASE WHEN ai_analysis.media_id IS NULL THEN 1 ELSE 0 END),
            SUM(CASE WHEN ai_analysis.review_status='review_required' OR ai_analysis.trust_state='unreviewed_real' THEN 1 ELSE 0 END),
            SUM(CASE WHEN ai_analysis.review_status='approved' OR ai_analysis.trust_state='approved_real' THEN 1 ELSE 0 END),
            SUM(CASE WHEN ai_analysis.review_status='corrected' OR ai_analysis.trust_state='corrected_real' THEN 1 ELSE 0 END),
            SUM(CASE WHEN ai_analysis.failure_reason IS NOT NULL AND ai_analysis.failure_reason!='' THEN 1 ELSE 0 END)
        FROM media
        LEFT JOIN ai_analysis
        ON ai_analysis.media_id=media.id
        {where}
        """, tuple(params))
        row = cur.fetchone() or (0, 0, 0, 0, 0, 0, 0, 0)
        conn.close()

        return {
            "total": row[0] or 0,
            "photos": row[1] or 0,
            "videos": row[2] or 0,
            "unanalyzed": row[3] or 0,
            "review_required": row[4] or 0,
            "approved": row[5] or 0,
            "corrected": row[6] or 0,
            "failed": row[7] or 0
        }

    ############################################################

    def analysis_review_metrics(self):

        conn = self.connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT trust_state, review_status, COUNT(*)
        FROM ai_analysis
        WHERE provider IS NOT NULL
        AND provider!=''
        GROUP BY trust_state, review_status
        """)
        counts = {}

        for trust_state, review_status, count in cur.fetchall():
            key = trust_state or review_status or "unreviewed_real"
            counts[key] = counts.get(key, 0) + count

        conn.close()

        approved = counts.get("approved_real", 0)
        corrected = counts.get("corrected_real", 0)
        rejected = counts.get("rejected_real", 0)
        failed = counts.get("failed", 0)
        mock = counts.get("mock", 0)
        unreviewed = counts.get("unreviewed_real", 0)
        total_real = approved + corrected + rejected + failed + unreviewed
        reviewed = approved + corrected + rejected

        return {
            "review_unreviewed": unreviewed,
            "review_approved": approved,
            "review_corrected": corrected,
            "review_rejected": rejected,
            "review_failed": failed,
            "review_mock": mock,
            "review_completion_percentage": (
                round((reviewed / total_real) * 100, 1)
                if total_real else 0
            )
        }

    ############################################################

    def analysis_review_eligible_ids(self, media_ids):

        ids = [
            self._to_int(media_id)
            for media_id in media_ids or []
            if self._to_int(media_id)
        ]

        if not ids:
            return []

        placeholders = ",".join("?" for _ in ids)
        conn = self.connection()
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT media.id
            FROM media
            JOIN ai_analysis
            ON ai_analysis.media_id=media.id
            WHERE media.id IN ({placeholders})
            AND ai_analysis.provider IS NOT NULL
            AND ai_analysis.provider!=''
            AND ai_analysis.provider!='mock'
            AND (
                ai_analysis.model IS NULL OR
                ai_analysis.model NOT LIKE 'mock%'
            )
            AND (
                ai_analysis.failure_reason IS NULL OR
                ai_analysis.failure_reason=''
            )
            AND (
                ai_analysis.review_status='review_required' OR
                (
                    (
                        ai_analysis.review_status IS NULL OR
                        ai_analysis.review_status=''
                    )
                    AND ai_analysis.trust_state='unreviewed_real'
                )
            )
            """,
            tuple(ids)
        )
        eligible = {
            row[0]
            for row in cur.fetchall()
        }
        conn.close()

        return [
            media_id
            for media_id in ids
            if media_id in eligible
        ]

    ############################################################

    def record_analysis_review(
        self,
        media_id,
        decision,
        trust_state,
        review_status,
        reviewer="Jonathan",
        corrections=None,
        notes=""
    ):

        now = TimeService.utc_now_iso()
        existing = self.get_ai_analysis(media_id) or {}
        conn = self.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO analysis_review_history(
            media_id,
            analysis_saved_at,
            decision,
            trust_state,
            review_status,
            reviewer,
            corrections_json,
            notes,
            created_at
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            media_id,
            existing.get("last_analyzed") or existing.get("analyzed_at", ""),
            decision,
            trust_state,
            review_status,
            reviewer,
            self._to_json(corrections or {}),
            notes,
            now
        ))
        cur.execute("""
        UPDATE ai_analysis
        SET trust_state=?,
            review_status=?,
            reviewed_at=?,
            reviewer_notes=?
        WHERE media_id=?
        """,
        (
            trust_state,
            review_status,
            now,
            notes,
            media_id
        ))
        conn.commit()
        conn.close()

        return self.get_ai_analysis(media_id)

    ############################################################

    def analysis_review_history(self, media_id, limit=50):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM analysis_review_history
        WHERE media_id=?
        ORDER BY id DESC
        LIMIT ?
        """, (media_id, self._to_int(limit)))
        rows = [
            {
                "id": row["id"],
                "media_id": row["media_id"],
                "analysis_saved_at": row["analysis_saved_at"] or "",
                "decision": row["decision"] or "",
                "trust_state": row["trust_state"] or "",
                "review_status": row["review_status"] or "",
                "reviewer": row["reviewer"] or "",
                "corrections": self._from_json(row["corrections_json"]),
                "notes": row["notes"] or "",
                "created_at": row["created_at"] or ""
            }
            for row in cur.fetchall()
        ]
        conn.close()

        return rows

    ############################################################

    def legacy_mock_analysis_summary(self):

        conn = self.connection()
        cur = conn.cursor()

        mock_where = self._mock_analysis_where()

        cur.execute(f"""

        SELECT COUNT(*)

        FROM ai_analysis

        WHERE {mock_where}

        """)

        analysis_count = cur.fetchone()[0] or 0

        counts = {
            "media_count": analysis_count,
            "analysis_rows": analysis_count
        }

        for key, table in (
            ("media_intelligence_rows", "media_intelligence"),
            ("fire_service_rows", "fire_service_intelligence"),
            ("editorial_strategy_rows", "editorial_strategies"),
            ("editorial_comparison_rows", "editorial_comparisons")
        ):
            cur.execute(f"""

            SELECT COUNT(*)

            FROM {table}

            WHERE media_id IN (
                SELECT media_id
                FROM ai_analysis
                WHERE {mock_where}
            )

            """)

            counts[key] = cur.fetchone()[0] or 0

        conn.close()

        return counts

    ############################################################

    def clear_mock_analysis(self):

        conn = self.connection()

        cur = conn.cursor()
        mock_where = self._mock_analysis_where()
        summary = self.legacy_mock_analysis_summary()

        cur.execute("""

        CREATE TEMP TABLE IF NOT EXISTS mock_cleanup_media(
            media_id INTEGER PRIMARY KEY
        )

        """)

        cur.execute("DELETE FROM mock_cleanup_media")

        cur.execute(f"""

        INSERT OR IGNORE INTO mock_cleanup_media(media_id)

        SELECT media_id

        FROM ai_analysis

        WHERE {mock_where}

        """)

        cur.execute("""

        DELETE FROM editorial_comparisons

        WHERE media_id IN (
            SELECT media_id
            FROM mock_cleanup_media
        )

        """)

        editorial_comparisons_deleted = cur.rowcount

        cur.execute("""

        DELETE FROM editorial_strategies

        WHERE media_id IN (
            SELECT media_id
            FROM mock_cleanup_media
        )

        """)

        editorial_strategies_deleted = cur.rowcount

        cur.execute("""

        DELETE FROM fire_service_intelligence

        WHERE media_id IN (
            SELECT media_id
            FROM mock_cleanup_media
        )

        """)

        fire_service_deleted = cur.rowcount

        cur.execute("""

        DELETE FROM media_intelligence

        WHERE media_id IN (
            SELECT media_id
            FROM mock_cleanup_media
        )

        """)

        intelligence_deleted = cur.rowcount

        cur.execute("""

        DELETE FROM ai_analysis

        WHERE media_id IN (
            SELECT media_id
            FROM mock_cleanup_media
        )

        """)

        analysis_deleted = cur.rowcount

        conn.commit()

        conn.close()

        logger.info(
            (
                "Cleared mock analysis rows analysis=%s intelligence=%s "
                "fire_service=%s editorial_strategies=%s editorial_comparisons=%s"
            ),
            analysis_deleted,
            intelligence_deleted,
            fire_service_deleted,
            editorial_strategies_deleted,
            editorial_comparisons_deleted
        )

        return {
            **summary,
            "analysis_deleted": analysis_deleted,
            "intelligence_deleted": intelligence_deleted,
            "fire_service_deleted": fire_service_deleted,
            "editorial_strategies_deleted": editorial_strategies_deleted,
            "editorial_comparisons_deleted": editorial_comparisons_deleted
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

        intelligence = self._intelligence_from_row(row)
        intelligence["fire_service_intelligence"] = (
            self.get_fire_service_intelligence(media_id)
        )

        return intelligence

    ############################################################

    def save_filesystem_intelligence(self, media_id, intelligence):

        conn = self.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO filesystem_intelligence(
            media_id,
            media_root,
            relative_path,
            folder_hierarchy,
            root_category,
            parent_category,
            subcategory,
            folder_keywords,
            normalized_tags,
            apparatus_identifier,
            apparatus_name,
            apparatus_resolved,
            incident_category,
            incident_type,
            training_category,
            training_type,
            drill_type,
            live_burn_context,
            public_education_program,
            campaign,
            community_event,
            station,
            recruit_class,
            mutual_aid_context,
            year,
            month,
            season,
            location_context,
            filesystem_confidence,
            matching_rule,
            source_folders,
            conflict_state,
            conflict_details,
            enrichment_version,
            last_derived_at,
            updated_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
        """, (
            media_id,
            intelligence.get("media_root", ""),
            intelligence.get("relative_path", ""),
            self._to_json(intelligence.get("folder_hierarchy")),
            intelligence.get("root_category", ""),
            intelligence.get("parent_category", ""),
            intelligence.get("subcategory", ""),
            self._to_json(intelligence.get("folder_keywords")),
            self._to_json(intelligence.get("normalized_tags")),
            intelligence.get("apparatus_identifier", ""),
            intelligence.get("apparatus_name", ""),
            self._to_int(intelligence.get("apparatus_resolved")),
            intelligence.get("incident_category", ""),
            intelligence.get("incident_type", ""),
            intelligence.get("training_category", ""),
            intelligence.get("training_type", ""),
            intelligence.get("drill_type", ""),
            self._to_int(intelligence.get("live_burn_context")),
            intelligence.get("public_education_program", ""),
            intelligence.get("campaign", ""),
            intelligence.get("community_event", ""),
            intelligence.get("station", ""),
            self._to_int(intelligence.get("recruit_class")),
            self._to_int(intelligence.get("mutual_aid_context")),
            intelligence.get("year", ""),
            self._to_int(intelligence.get("month")),
            intelligence.get("season", ""),
            intelligence.get("location_context", ""),
            self._to_int(intelligence.get("filesystem_confidence")),
            intelligence.get("matching_rule", ""),
            self._to_json(intelligence.get("source_folders")),
            intelligence.get("conflict_state", ""),
            self._to_json(intelligence.get("conflict_details")),
            intelligence.get("enrichment_version", ""),
            intelligence.get("last_derived_at", "")
        ))
        conn.commit()
        conn.close()

    ############################################################

    def get_filesystem_intelligence(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM filesystem_intelligence
            WHERE media_id=?
            """,
            (self._to_int(media_id),)
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return self._filesystem_intelligence_from_row(row)

    ############################################################

    def filesystem_intelligence_for_media_ids(self, media_ids):

        ids = [
            self._to_int(media_id)
            for media_id in media_ids
            if self._to_int(media_id)
        ]

        if not ids:
            return {}

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in ids)
        cur.execute(
            f"""
            SELECT *
            FROM filesystem_intelligence
            WHERE media_id IN ({placeholders})
            """,
            tuple(ids)
        )
        rows = cur.fetchall()
        conn.close()

        return {
            row["media_id"]: self._filesystem_intelligence_from_row(row)
            for row in rows
        }

    ############################################################

    def get_media_needing_filesystem_intelligence(
        self,
        rules_version,
        limit=500
    ):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                media.id,
                media.filename,
                media.path,
                media.media_type,
                media_intelligence.normalized_scene,
                media_intelligence.incident_type,
                media_intelligence.primary_activity
            FROM media
            LEFT JOIN filesystem_intelligence
            ON filesystem_intelligence.media_id=media.id
            LEFT JOIN media_intelligence
            ON media_intelligence.media_id=media.id
            WHERE
                filesystem_intelligence.media_id IS NULL
                OR filesystem_intelligence.enrichment_version!=?
                OR filesystem_intelligence.relative_path=''
            ORDER BY media.id
            LIMIT ?
            """,
            (
                str(rules_version or ""),
                self._to_int(limit) or 500
            )
        )
        rows = cur.fetchall()
        conn.close()

        return rows

    ############################################################

    def filesystem_knowledge_map(self, limit=100):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COALESCE(NULLIF(root_category, ''), 'unknown') AS category,
                COALESCE(NULLIF(subcategory, ''), 'unknown') AS subcategory,
                COUNT(*) AS media_count,
                SUM(CASE WHEN media.media_type='image' THEN 1 ELSE 0 END) AS photo_count,
                SUM(CASE WHEN media.media_type='video' THEN 1 ELSE 0 END) AS video_count,
                SUM(CASE WHEN ai_analysis.media_id IS NOT NULL THEN 1 ELSE 0 END) AS analyzed_count,
                SUM(CASE WHEN ai_analysis.media_id IS NULL THEN 1 ELSE 0 END) AS not_analyzed_count,
                SUM(CASE WHEN ai_analysis.review_status IN ('approved', 'corrected') THEN 1 ELSE 0 END) AS reviewed_count,
                SUM(CASE WHEN filesystem_intelligence.conflict_state='conflict' THEN 1 ELSE 0 END) AS conflict_count
            FROM filesystem_intelligence
            JOIN media
            ON media.id=filesystem_intelligence.media_id
            LEFT JOIN ai_analysis
            ON ai_analysis.media_id=media.id
            GROUP BY category, subcategory
            ORDER BY category, media_count DESC, subcategory
            LIMIT ?
            """,
            (self._to_int(limit) or 100,)
        )
        rows = [
            dict(row)
            for row in cur.fetchall()
        ]
        conn.close()

        return rows

    ############################################################

    def filesystem_intelligence_summary(self):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN conflict_state='conflict' THEN 1 ELSE 0 END) AS conflicts,
                SUM(CASE WHEN filesystem_confidence>=70 THEN 1 ELSE 0 END) AS confident,
                SUM(CASE WHEN media.media_type='video' THEN 1 ELSE 0 END) AS videos
            FROM filesystem_intelligence
            JOIN media
            ON media.id=filesystem_intelligence.media_id
        """)
        row = cur.fetchone()
        conn.close()

        return dict(row) if row else {
            "total": 0,
            "conflicts": 0,
            "confident": 0,
            "videos": 0
        }

    ############################################################

    def save_fire_service_intelligence(self, media_id, intelligence):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        INSERT OR REPLACE INTO fire_service_intelligence(

            media_id,

            firefighter_count,

            civilian_count,

            officer_presence,

            children_present,

            group_size,

            personnel,

            ppe,

            equipment,

            apparatus,

            incident_classification,

            operational_activity,

            communications_uses,

            reasoning,

            operational_context,

            operational_skills,

            communications_intent,

            operational_confidence,

            reasoning_evidence,

            operational_reasoning,

            generated_at,

            source_model

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?)

        """,

        (
            self._to_int(media_id),
            self._to_int(intelligence.get("firefighter_count")),
            self._to_int(intelligence.get("civilian_count")),
            1 if intelligence.get("officer_presence") else 0,
            1 if intelligence.get("children_present") else 0,
            intelligence.get("group_size", ""),
            self._to_json(intelligence.get("personnel")),
            self._to_json(intelligence.get("ppe")),
            self._to_json(intelligence.get("equipment")),
            self._to_json(intelligence.get("apparatus")),
            intelligence.get("incident_classification", ""),
            intelligence.get("operational_activity", ""),
            self._to_json(intelligence.get("communications_uses")),
            self._to_json(intelligence.get("reasoning")),
            intelligence.get("operational_context", ""),
            self._to_json(intelligence.get("operational_skills")),
            self._to_json(intelligence.get("communications_intent")),
            self._to_int(intelligence.get("operational_confidence")),
            self._to_json(intelligence.get("reasoning_evidence")),
            self._to_json(intelligence.get("operational_reasoning")),
            intelligence.get("source_model", "")
        ))

        conn.commit()
        conn.close()

    ############################################################

    def get_fire_service_intelligence(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM fire_service_intelligence

        WHERE media_id=?

        """,

        (self._to_int(media_id),))

        row = cur.fetchone()

        conn.close()

        if row is None:
            return None

        return self._fire_service_intelligence_from_row(row)

    ############################################################

    def fire_service_intelligence_count(self):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM fire_service_intelligence")

        count = cur.fetchone()[0]

        conn.close()

        return count or 0

    ############################################################

    def save_video_intelligence(self, media_id, intelligence):

        conn = self.connection()
        cur = conn.cursor()
        cur.execute("""

        INSERT OR REPLACE INTO video_intelligence(

            media_id,
            duration_seconds,
            analyzed_frame_count,
            frame_timestamps,
            people_observed,
            apparatus_observed,
            equipment_observed,
            activities_observed,
            settings_observed,
            visible_text,
            uncertain_observations,
            likely_content_category,
            confidence,
            review_state,
            provider,
            model,
            analysis_version,
            raw_frame_outputs,
            video_summary,
            primary_activity,
            secondary_activity,
            estimated_scene_count,
            representative_frames,
            identified_ppe,
            training_evolution,
            incident_category,
            program,
            campaign,
            community_event,
            estimated_audience,
            communications_themes,
            story_potential,
            education_score,
            recruitment_score,
            community_score,
            operations_score,
            reel_potential,
            reel_explanation,
            clip_recommendations,
            cover_recommendation,
            story_category,
            trust_state,
            explanation,
            generated_at

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        """,
        (
            self._to_int(media_id),
            self._to_float(intelligence.get("duration_seconds")),
            self._to_int(intelligence.get("analyzed_frame_count")),
            self._to_json(intelligence.get("frame_timestamps")),
            self._to_json(intelligence.get("people_observed")),
            self._to_json(intelligence.get("apparatus_observed")),
            self._to_json(intelligence.get("equipment_observed")),
            self._to_json(intelligence.get("activities_observed")),
            self._to_json(intelligence.get("settings_observed")),
            self._to_json(intelligence.get("visible_text")),
            self._to_json(intelligence.get("uncertain_observations")),
            intelligence.get("likely_content_category", ""),
            self._to_float(intelligence.get("confidence")),
            intelligence.get("review_state", ""),
            intelligence.get("provider", ""),
            intelligence.get("model", ""),
            intelligence.get("analysis_version", ""),
            self._to_json(intelligence.get("raw_frame_outputs")),
            intelligence.get("video_summary", ""),
            intelligence.get("primary_activity", ""),
            intelligence.get("secondary_activity", ""),
            self._to_int(intelligence.get("estimated_scene_count")),
            self._to_json(intelligence.get("representative_frames")),
            self._to_json(intelligence.get("identified_ppe")),
            intelligence.get("training_evolution", ""),
            intelligence.get("incident_category", ""),
            intelligence.get("program", ""),
            intelligence.get("campaign", ""),
            intelligence.get("community_event", ""),
            self._to_json(intelligence.get("estimated_audience")),
            self._to_json(intelligence.get("communications_themes")),
            self._to_int(intelligence.get("story_potential")),
            self._to_int(intelligence.get("education_score")),
            self._to_int(intelligence.get("recruitment_score")),
            self._to_int(intelligence.get("community_score")),
            self._to_int(intelligence.get("operations_score")),
            self._to_int(intelligence.get("reel_potential")),
            intelligence.get("reel_explanation", ""),
            self._to_json(intelligence.get("clip_recommendations")),
            self._to_json(intelligence.get("cover_recommendation")),
            intelligence.get("story_category", ""),
            intelligence.get("trust_state", ""),
            intelligence.get("explanation", ""),
            TimeService.utc_now_iso()
        ))
        conn.commit()
        conn.close()

    ############################################################

    def get_video_intelligence(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM video_intelligence
        WHERE media_id=?
        """, (self._to_int(media_id),))
        row = cur.fetchone()
        conn.close()

        if row is None:
            return None

        return {
            "media_id": row["media_id"],
            "duration_seconds": row["duration_seconds"] or 0,
            "analyzed_frame_count": row["analyzed_frame_count"] or 0,
            "frame_timestamps": self._from_json(row["frame_timestamps"]),
            "people_observed": self._from_json(row["people_observed"]),
            "apparatus_observed": self._from_json(row["apparatus_observed"]),
            "equipment_observed": self._from_json(row["equipment_observed"]),
            "activities_observed": self._from_json(row["activities_observed"]),
            "settings_observed": self._from_json(row["settings_observed"]),
            "visible_text": self._from_json(row["visible_text"]),
            "uncertain_observations": self._from_json(row["uncertain_observations"]),
            "likely_content_category": row["likely_content_category"] or "",
            "confidence": row["confidence"] or 0,
            "review_state": row["review_state"] or "",
            "provider": row["provider"] or "",
            "model": row["model"] or "",
            "analysis_version": row["analysis_version"] or "",
            "raw_frame_outputs": self._from_json(row["raw_frame_outputs"]),
            "video_summary": row["video_summary"] or "",
            "primary_activity": row["primary_activity"] or "",
            "secondary_activity": row["secondary_activity"] or "",
            "estimated_scene_count": row["estimated_scene_count"] or 0,
            "representative_frames": self._from_json(row["representative_frames"]),
            "identified_ppe": self._from_json(row["identified_ppe"]),
            "training_evolution": row["training_evolution"] or "",
            "incident_category": row["incident_category"] or "",
            "program": row["program"] or "",
            "campaign": row["campaign"] or "",
            "community_event": row["community_event"] or "",
            "estimated_audience": self._from_json(row["estimated_audience"]),
            "communications_themes": self._from_json(row["communications_themes"]),
            "story_potential": row["story_potential"] or 0,
            "education_score": row["education_score"] or 0,
            "recruitment_score": row["recruitment_score"] or 0,
            "community_score": row["community_score"] or 0,
            "operations_score": row["operations_score"] or 0,
            "reel_potential": row["reel_potential"] or 0,
            "reel_explanation": row["reel_explanation"] or "",
            "clip_recommendations": self._from_json(row["clip_recommendations"]),
            "cover_recommendation": self._from_json(row["cover_recommendation"]),
            "story_category": row["story_category"] or "",
            "trust_state": row["trust_state"] or "",
            "explanation": row["explanation"] or "",
            "generated_at": row["generated_at"] or ""
        }

    ############################################################

    def video_intelligence_count(self):

        conn = self.connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM video_intelligence")
        count = cur.fetchone()[0] or 0
        conn.close()

        return count

    ############################################################

    def fire_service_unknown_count(self):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(*)

        FROM fire_service_intelligence

        WHERE incident_classification='unknown'
        OR operational_activity='unknown'

        """)

        count = cur.fetchone()[0]

        conn.close()

        return count or 0

    ############################################################

    def fire_service_top_values(self, field, limit=5):

        allowed = {
            "incident_classification",
            "operational_activity",
            "operational_context"
        }

        if field not in allowed:
            return []

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(f"""

        SELECT {field} AS name, COUNT(*) AS count

        FROM fire_service_intelligence

        WHERE {field} IS NOT NULL
        AND {field} != ''

        GROUP BY {field}

        ORDER BY count DESC, {field}

        LIMIT ?

        """,

        (self._to_int(limit),))

        rows = [
            {
                "name": row["name"],
                "count": row["count"] or 0
            }
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def fire_service_top_communications_uses(self, limit=5):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT json_each.value AS name,
               COUNT(DISTINCT fire_service_intelligence.media_id) AS count

        FROM fire_service_intelligence,
             json_each(fire_service_intelligence.communications_uses)

        WHERE json_each.value IS NOT NULL
        AND json_each.value != ''

        GROUP BY json_each.value

        ORDER BY count DESC, json_each.value

        LIMIT ?

        """,

        (self._to_int(limit),))

        rows = [
            {
                "name": row["name"],
                "count": row["count"] or 0
            }
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def fire_service_top_operational_contexts(self, limit=5):

        return self.fire_service_top_values(
            "operational_context",
            limit=limit
        )

    ############################################################

    def fire_service_top_operational_skills(self, limit=5):

        return self._fire_service_json_counts(
            "operational_skills",
            limit=limit
        )

    ############################################################

    def fire_service_intent_count(self, intent):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(DISTINCT fire_service_intelligence.media_id)

        FROM fire_service_intelligence,
             json_each(fire_service_intelligence.communications_intent)

        WHERE json_each.value=?

        """,

        (intent,))

        count = cur.fetchone()[0]

        conn.close()

        return count or 0

    ############################################################

    def fire_service_context_count(self, context):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(*)

        FROM fire_service_intelligence

        WHERE operational_context=?

        """,

        (context,))

        count = cur.fetchone()[0]

        conn.close()

        return count or 0

    ############################################################

    def _fire_service_json_counts(self, field, limit=5):

        allowed = {
            "communications_uses",
            "communications_intent",
            "operational_skills"
        }

        if field not in allowed:
            return []

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(f"""

        SELECT json_each.value AS name,
               COUNT(DISTINCT fire_service_intelligence.media_id) AS count

        FROM fire_service_intelligence,
             json_each(fire_service_intelligence.{field})

        WHERE json_each.value IS NOT NULL
        AND json_each.value != ''

        GROUP BY json_each.value

        ORDER BY count DESC, json_each.value

        LIMIT ?

        """,

        (self._to_int(limit),))

        rows = [
            {
                "name": row["name"],
                "count": row["count"] or 0
            }
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

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
            ),
            "editorial_strategy": self._editorial_strategy_counts(filters),
            "review_status": self._intelligence_review_counts(filters)
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

            filesystem_intelligence.root_category AS fs_root_category,

            filesystem_intelligence.subcategory AS fs_subcategory,

            filesystem_intelligence.normalized_tags AS fs_normalized_tags,

            filesystem_intelligence.apparatus_identifier AS fs_apparatus_identifier,

            filesystem_intelligence.apparatus_name AS fs_apparatus_name,

            filesystem_intelligence.incident_type AS fs_incident_type,

            filesystem_intelligence.training_type AS fs_training_type,

            filesystem_intelligence.public_education_program AS fs_program,

            filesystem_intelligence.campaign AS fs_campaign,

            filesystem_intelligence.community_event AS fs_community_event,

            filesystem_intelligence.filesystem_confidence AS fs_confidence,

            filesystem_intelligence.conflict_state AS fs_conflict_state,

            ai_analysis.community_score,

            ai_analysis.description AS analysis_description,

            ai_analysis.recruitment_score,

            ai_analysis.education_score,

            ai_analysis.technical_score,

            ai_analysis.overall_score,

            ai_analysis.provider,

            ai_analysis.model,

            ai_analysis.trust_state,

            ai_analysis.review_status,

            ai_analysis.quality_state

        FROM media

        JOIN media_intelligence
        ON media_intelligence.media_id = media.id

        LEFT JOIN filesystem_intelligence
        ON filesystem_intelligence.media_id = media.id

        LEFT JOIN ai_analysis
        ON ai_analysis.media_id = media.id

        WHERE (
            ai_analysis.failure_reason IS NULL
            OR ai_analysis.failure_reason=''
        )
        AND (
            ai_analysis.trust_state IS NULL
            OR ai_analysis.trust_state=''
            OR ai_analysis.trust_state NOT IN ('rejected_real', 'failed')
        )

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
                    "description": row["analysis_description"] or "",
                    "effective_description": row["analysis_description"] or "",
                    "community_score": row["community_score"] or 0,
                    "recruitment_score": row["recruitment_score"] or 0,
                    "education_score": row["education_score"] or 0,
                    "technical_score": row["technical_score"] or 0,
                    "overall_score": row["overall_score"] or 0,
                    "provider": row["provider"] or "",
                    "model": row["model"] or "",
                    "trust_state": row["trust_state"] or "",
                    "review_status": row["review_status"] or "",
                    "quality_state": row["quality_state"] or "",
                    "filesystem_intelligence": {
                        "root_category": row["fs_root_category"] or "",
                        "subcategory": row["fs_subcategory"] or "",
                        "normalized_tags": self._from_json(row["fs_normalized_tags"]),
                        "apparatus_identifier": row["fs_apparatus_identifier"] or "",
                        "apparatus_name": row["fs_apparatus_name"] or "",
                        "incident_type": row["fs_incident_type"] or "",
                        "training_type": row["fs_training_type"] or "",
                        "public_education_program": row["fs_program"] or "",
                        "campaign": row["fs_campaign"] or "",
                        "community_event": row["fs_community_event"] or "",
                        "filesystem_confidence": row["fs_confidence"] or 0,
                        "conflict_state": row["fs_conflict_state"] or ""
                    }
                }
            )
            candidates.append(intelligence)

        return candidates

    ############################################################

    def communications_officer_metrics(self, since_utc=None):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        since = since_utc or "1970-01-01T00:00:00+00:00"

        added_expr = self._media_added_timestamp_expr()

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM media
            WHERE datetime({added_expr}) >= datetime(?)
            """,
            (since,)
        )
        new_media = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT COUNT(*)
        FROM ai_analysis
        WHERE datetime(REPLACE(REPLACE(last_analyzed, 'T', ' '), '+00:00', '')) >= datetime(?)
        """, (since,))
        analyzed_since = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT COUNT(*)
        FROM ai_analysis
        WHERE provider!='mock'
        AND (
            review_status IS NULL
            OR review_status=''
            OR review_status IN ('review_required', 'reanalyze_requested')
            OR trust_state='unreviewed_real'
        )
        """)
        review_queue = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT COUNT(*)
        FROM ai_analysis
        WHERE review_status='approved'
        OR trust_state='approved_real'
        """)
        approved = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT COUNT(*)
        FROM ai_analysis
        WHERE review_status='corrected'
        OR trust_state='corrected_real'
        """)
        corrected = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT COUNT(*)
        FROM ai_analysis
        WHERE failure_reason IS NOT NULL
        AND failure_reason!=''
        """)
        failed = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT COUNT(*)
        FROM media
        LEFT JOIN ai_analysis
        ON ai_analysis.media_id=media.id
        WHERE media.media_type='video'
        AND ai_analysis.provider IS NOT NULL
        AND ai_analysis.provider!='mock'
        AND (
            ai_analysis.review_status IS NULL
            OR ai_analysis.review_status=''
            OR ai_analysis.review_status IN ('review_required', 'reanalyze_requested')
            OR ai_analysis.trust_state='unreviewed_real'
        )
        """)
        videos_awaiting_review = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM social_posts")
        memory_posts = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM communication_records")
        communication_records = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM communication_deliveries")
        communication_deliveries = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT MAX(post_date)
        FROM social_posts
        WHERE post_date IS NOT NULL
        AND post_date!=''
        """)
        latest_post = cur.fetchone()[0] or ""

        if not latest_post:
            cur.execute("""
            SELECT MAX(published_at)
            FROM communication_deliveries
            WHERE published_at IS NOT NULL
            AND published_at!=''
            """)
            latest_post = cur.fetchone()[0] or ""

        cur.execute("""
        SELECT MIN(original_date), MAX(original_date)
        FROM communication_records
        WHERE original_date IS NOT NULL
        AND original_date!=''
        """)
        first_last = cur.fetchone()
        first_communication = first_last[0] if first_last else ""
        latest_communication = first_last[1] if first_last else ""

        cur.execute("""
        SELECT COUNT(*)
        FROM communication_deliveries
        WHERE engagement_metrics IS NOT NULL
        AND engagement_metrics!=''
        AND engagement_metrics!='{}'
        """)
        engagement_available = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM recommendation_history")
        recommendation_history = cur.fetchone()[0] or 0

        conn.close()

        return {
            "new_media_since": new_media,
            "media_analyzed_since": analyzed_since,
            "review_queue_size": review_queue,
            "approved_media_count": approved,
            "corrected_media_count": corrected,
            "failed_analysis_count": failed,
            "videos_awaiting_review": videos_awaiting_review,
            "communications_memory_posts": memory_posts,
            "communications_memory_latest_post": latest_post,
            "recommendation_history_count": recommendation_history
        }

    ############################################################

    def create_home_session(self, started_at=None):

        started_at = started_at or TimeService.utc_now_iso()
        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO home_sessions(
            started_at,
            status
        )
        VALUES(?,?)
        """, (
            started_at,
            "running"
        ))

        session_id = cur.lastrowid
        conn.commit()
        conn.close()

        return session_id

    ############################################################

    def complete_home_session(
        self,
        session_id,
        status="completed",
        completed_at=None,
        duration_seconds=0,
        summary=None,
        metrics=None
    ):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""
        UPDATE home_sessions
        SET completed_at=?,
            status=?,
            duration_seconds=?,
            summary_json=?,
            metrics_json=?
        WHERE id=?
        """, (
            completed_at or TimeService.utc_now_iso(),
            status,
            self._to_float(duration_seconds),
            self._to_json(summary or {}),
            self._to_json(metrics or {}),
            self._to_int(session_id)
        ))

        conn.commit()
        conn.close()

    ############################################################

    def latest_completed_home_session(self, before_session_id=None):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        params = []
        where = """
        WHERE status='completed'
        AND completed_at IS NOT NULL
        AND completed_at!=''
        """

        if before_session_id:
            where += " AND id < ?"
            params.append(self._to_int(before_session_id))

        cur.execute(f"""
        SELECT *
        FROM home_sessions
        {where}
        ORDER BY datetime(REPLACE(REPLACE(completed_at, 'T', ' '), '+00:00', '')) DESC,
                 id DESC
        LIMIT 1
        """, tuple(params))

        row = cur.fetchone()
        conn.close()

        if not row:
            return {}

        return {
            "id": row["id"],
            "started_at": row["started_at"] or "",
            "completed_at": row["completed_at"] or "",
            "status": row["status"] or "",
            "duration_seconds": row["duration_seconds"] or 0,
            "summary": self._from_json(row["summary_json"]),
            "metrics": self._from_json(row["metrics_json"])
        }

    ############################################################

    def media_analyzed_count_since(self, since_utc=None):

        since = since_utc or "1970-01-01T00:00:00+00:00"
        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""
        SELECT COUNT(*)
        FROM ai_analysis
        WHERE datetime(REPLACE(REPLACE(last_analyzed, 'T', ' '), '+00:00', '')) >= datetime(?)
        """, (since,))

        count = cur.fetchone()[0] or 0
        conn.close()

        return count

    ############################################################

    def communications_memory_metrics(self):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM social_posts")
        memory_posts = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM communication_records")
        communication_records = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM communication_deliveries")
        communication_deliveries = cur.fetchone()[0] or 0

        cur.execute("""
        SELECT MAX(post_date)
        FROM social_posts
        WHERE post_date IS NOT NULL
        AND post_date!=''
        """)
        latest_post = cur.fetchone()[0] or ""

        if not latest_post:
            cur.execute("""
            SELECT MAX(published_at)
            FROM communication_deliveries
            WHERE published_at IS NOT NULL
            AND published_at!=''
            """)
            latest_post = cur.fetchone()[0] or ""

        cur.execute("""
        SELECT MIN(original_date), MAX(original_date)
        FROM communication_records
        WHERE original_date IS NOT NULL
        AND original_date!=''
        """)
        first_last = cur.fetchone()
        first_communication = first_last[0] if first_last else ""
        latest_communication = first_last[1] if first_last else ""

        cur.execute("""
        SELECT COUNT(*)
        FROM communication_deliveries
        WHERE engagement_metrics IS NOT NULL
        AND engagement_metrics!=''
        AND engagement_metrics!='{}'
        """)
        engagement_available = cur.fetchone()[0] or ""

        cur.execute("SELECT COUNT(*) FROM recommendation_history")
        recommendation_history = cur.fetchone()[0] or 0

        conn.close()

        return {
            "communications_memory_posts": memory_posts + communication_records,
            "communications_memory_legacy_posts": memory_posts,
            "historical_communications_imported": communication_records,
            "communication_deliveries": communication_deliveries,
            "communications_memory_latest_post": latest_post,
            "communications_memory_first_post": first_communication,
            "communications_memory_latest_communication": latest_communication,
            "communications_memory_engagement_records": engagement_available,
            "recommendation_history_count": recommendation_history
        }

    ############################################################

    def media_added_count_between(self, start_utc, end_utc):

        conn = self.connection()
        cur = conn.cursor()
        added_expr = self._media_added_timestamp_expr()

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM media
            WHERE datetime({added_expr}) >= datetime(?)
            AND datetime({added_expr}) < datetime(?)
            """,
            (
                start_utc,
                end_utc
            )
        )

        count = cur.fetchone()[0] or 0
        conn.close()

        return count

    ############################################################

    def communications_officer_assets(self, media_ids, limit=25):

        ids = [
            self._to_int(media_id)
            for media_id in media_ids[:int(limit or 25)]
            if self._to_int(media_id)
        ]

        if not ids:
            return []

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in ids)

        cur.execute(f"""
        SELECT
            media.id AS result_media_id,
            media.filename,
            media.path,
            media.media_type,
            media_intelligence.*,
            filesystem_intelligence.root_category AS fs_root_category,
            filesystem_intelligence.subcategory AS fs_subcategory,
            filesystem_intelligence.normalized_tags AS fs_normalized_tags,
            filesystem_intelligence.apparatus_identifier AS fs_apparatus_identifier,
            filesystem_intelligence.apparatus_name AS fs_apparatus_name,
            filesystem_intelligence.incident_type AS fs_incident_type,
            filesystem_intelligence.training_type AS fs_training_type,
            filesystem_intelligence.public_education_program AS fs_program,
            filesystem_intelligence.campaign AS fs_campaign,
            filesystem_intelligence.community_event AS fs_community_event,
            filesystem_intelligence.filesystem_confidence AS fs_confidence,
            filesystem_intelligence.conflict_state AS fs_conflict_state,
            ai_analysis.trust_state,
            ai_analysis.review_status,
            ai_analysis.failure_reason,
            ai_analysis.description AS analysis_description,
            ai_analysis.provider,
            ai_analysis.model
        FROM media
        JOIN media_intelligence
        ON media_intelligence.media_id=media.id
        LEFT JOIN filesystem_intelligence
        ON filesystem_intelligence.media_id=media.id
        LEFT JOIN ai_analysis
        ON ai_analysis.media_id=media.id
        WHERE media.id IN ({placeholders})
        """, tuple(ids))

        rows = cur.fetchall()
        conn.close()

        by_id = {}

        for row in rows:
            asset = self._intelligence_from_row(row)
            asset.update({
                "media_id": row["result_media_id"],
                "filename": row["filename"] or "",
                "path": row["path"] or "",
                "media_type": row["media_type"] or "",
                "trust_state": row["trust_state"] or "",
                "review_status": row["review_status"] or "",
                "failure_reason": row["failure_reason"] or "",
                "description": row["analysis_description"] or "",
                "effective_description": row["analysis_description"] or "",
                "provider": row["provider"] or "",
                "model": row["model"] or ""
            })
            asset["filesystem_intelligence"] = {
                "root_category": row["fs_root_category"] or "",
                "subcategory": row["fs_subcategory"] or "",
                "normalized_tags": self._from_json(row["fs_normalized_tags"]),
                "apparatus_identifier": row["fs_apparatus_identifier"] or "",
                "apparatus_name": row["fs_apparatus_name"] or "",
                "incident_type": row["fs_incident_type"] or "",
                "training_type": row["fs_training_type"] or "",
                "public_education_program": row["fs_program"] or "",
                "campaign": row["fs_campaign"] or "",
                "community_event": row["fs_community_event"] or "",
                "filesystem_confidence": row["fs_confidence"] or 0,
                "conflict_state": row["fs_conflict_state"] or ""
            }
            by_id[asset["media_id"]] = asset

        return [
            by_id[media_id]
            for media_id in ids
            if media_id in by_id
        ]

    ############################################################

    def operational_activity_candidate_rows(self, since_days=30, limit=300):

        limit = max(1, min(self._to_int(limit) or 300, 1000))
        since_days = max(1, min(self._to_int(since_days) or 30, 365))
        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        added_expr = self._media_added_timestamp_expr()
        capture_expr = self._media_timestamp_expr("media.capture_time")
        analyzed_expr = self._media_timestamp_expr("ai_analysis.last_analyzed")
        window = f"-{since_days} days"

        cur.execute(f"""
        SELECT
            media.id AS media_id,
            media.filename,
            media.path,
            media.media_type,
            media.extension,
            media.first_seen_at,
            media.date_added,
            media.capture_time,
            media.capture_time_source,
            media.duration_seconds,
            media.width,
            media.height,
            ai_analysis.provider,
            ai_analysis.model,
            ai_analysis.failure_reason,
            ai_analysis.trust_state,
            ai_analysis.review_status,
            ai_analysis.quality_state,
            ai_analysis.confidence,
            ai_analysis.last_analyzed,
            ai_analysis.description AS analysis_description
        FROM media
        LEFT JOIN ai_analysis
        ON ai_analysis.media_id=media.id
        WHERE
            datetime({capture_expr}) >= datetime('now', ?)
            OR datetime({added_expr}) >= datetime('now', ?)
            OR datetime({analyzed_expr}) >= datetime('now', ?)
        ORDER BY
            COALESCE(
                media.capture_time,
                media.first_seen_at,
                media.date_added,
                ai_analysis.last_analyzed
            ) DESC,
            media.id DESC
        LIMIT ?
        """, (window, window, window, limit))

        rows = [
            dict(row)
            for row in cur.fetchall()
        ]
        conn.close()

        return rows

    ############################################################

    def media_package_asset_rows(self, media_ids, limit=50):

        ids = [
            self._to_int(media_id)
            for media_id in media_ids[:int(limit or 50)]
            if self._to_int(media_id)
        ]

        if not ids:
            return []

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in ids)

        cur.execute(f"""
        SELECT
            media.id AS media_id,
            media.filename,
            media.path,
            media.media_type,
            media.sha256,
            media.first_seen_at,
            media.date_added,
            media.capture_time,
            media.duration_seconds,
            media.width,
            media.height,
            media.orientation,
            ai_analysis.trust_state,
            ai_analysis.review_status,
            ai_analysis.failure_reason,
            ai_analysis.provider,
            ai_analysis.model,
            video_intelligence.reel_potential,
            video_intelligence.story_potential,
            video_intelligence.clip_recommendations,
            video_intelligence.cover_recommendation,
            video_intelligence.story_category,
            video_intelligence.communications_themes
        FROM media
        LEFT JOIN ai_analysis
        ON ai_analysis.media_id=media.id
        LEFT JOIN video_intelligence
        ON video_intelligence.media_id=media.id
        WHERE media.id IN ({placeholders})
        """, tuple(ids))

        rows = cur.fetchall()
        conn.close()
        by_id = {}

        for row in rows:
            by_id[row["media_id"]] = {
                "media_id": row["media_id"],
                "filename": row["filename"] or "",
                "path": row["path"] or "",
                "media_type": row["media_type"] or "",
                "sha256": row["sha256"] or "",
                "first_seen_at": row["first_seen_at"] or "",
                "date_added": row["date_added"] or "",
                "capture_time": row["capture_time"] or "",
                "duration_seconds": row["duration_seconds"] or 0,
                "width": row["width"] or 0,
                "height": row["height"] or 0,
                "orientation": row["orientation"] or "",
                "trust_state": row["trust_state"] or "",
                "review_status": row["review_status"] or "",
                "failure_reason": row["failure_reason"] or "",
                "provider": row["provider"] or "",
                "model": row["model"] or "",
                "reel_potential": row["reel_potential"] or 0,
                "story_potential": row["story_potential"] or 0,
                "clip_recommendations": self._from_json(
                    row["clip_recommendations"]
                ),
                "cover_recommendation": self._from_json(
                    row["cover_recommendation"]
                ),
                "video_story_category": row["story_category"] or "",
                "video_communications_themes": self._from_json(
                    row["communications_themes"]
                )
            }

        return [
            by_id[media_id]
            for media_id in ids
            if media_id in by_id
        ]

    ############################################################

    def save_communication_package_history(self, package):

        package = package or {}
        conn = self.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_package_history(
            package_id,
            recommendation_id,
            story_title,
            package_version,
            package_json,
            created_at
        )
        VALUES(?,?,?,?,?,?)
        """, (
            package.get("package_id", ""),
            package.get("recommendation_id", ""),
            package.get("story_title") or package.get("headline", ""),
            package.get("version", ""),
            self._to_json(package),
            package.get("generated_at") or TimeService.utc_now_iso()
        ))
        row_id = cur.lastrowid
        conn.commit()
        conn.close()
        return row_id

    ############################################################

    def communication_package_history(
        self,
        package_id=None,
        recommendation_id=None,
        limit=20
    ):

        clauses = []
        params = []

        if package_id:
            clauses.append("package_id=?")
            params.append(package_id)

        if recommendation_id:
            clauses.append("recommendation_id=?")
            params.append(recommendation_id)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT *
            FROM communication_package_history
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            tuple(params + [self._to_int(limit) or 20])
        )
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "package_id": row["package_id"] or "",
                "recommendation_id": row["recommendation_id"] or "",
                "story_title": row["story_title"] or "",
                "package_version": row["package_version"] or "",
                "package": self._from_json(row["package_json"]),
                "created_at": row["created_at"] or ""
            }
            for row in rows
        ]

    ############################################################

    def save_communication_package_asset_action(self, action):

        action = action or {}
        conn = self.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_package_asset_actions(
            package_id,
            media_id,
            action,
            reason,
            previous_role,
            new_role,
            previous_media_id,
            source,
            created_at
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            action.get("package_id", ""),
            self._to_int(action.get("media_id")),
            action.get("action", ""),
            action.get("reason", ""),
            action.get("previous_role", ""),
            action.get("new_role", ""),
            self._to_int(action.get("previous_media_id")),
            action.get("source", "Jonathan"),
            action.get("created_at") or TimeService.utc_now_iso()
        ))
        row_id = cur.lastrowid
        conn.commit()
        conn.close()
        return row_id

    ############################################################

    def communication_package_asset_actions(self, package_id, limit=50):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM communication_package_asset_actions
        WHERE package_id=?
        ORDER BY id DESC
        LIMIT ?
        """, (
            package_id,
            self._to_int(limit) or 50
        ))
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "package_id": row["package_id"] or "",
                "media_id": row["media_id"] or 0,
                "action": row["action"] or "",
                "reason": row["reason"] or "",
                "previous_role": row["previous_role"] or "",
                "new_role": row["new_role"] or "",
                "previous_media_id": row["previous_media_id"] or 0,
                "source": row["source"] or "",
                "created_at": row["created_at"] or ""
            }
            for row in rows
        ]

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

    def save_decision_audit_snapshot(self, snapshot):

        snapshot = snapshot or {}
        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO decision_audit_history(

            decision_id,

            decision_type,

            subject_type,

            subject_id,

            headline,

            decision_score,

            confidence_score,

            trust_label,

            rank,

            snapshot_json,

            generated_at,

            explanation_version

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)

        """,

        (
            snapshot.get("decision_id", ""),
            snapshot.get("decision_type", ""),
            snapshot.get("subject_type", ""),
            str(snapshot.get("subject_id", "")),
            snapshot.get("headline", ""),
            self._to_float(snapshot.get("decision_score")),
            self._to_float(snapshot.get("confidence_score")),
            snapshot.get("trust_label", ""),
            self._to_int(snapshot.get("rank")),
            self._to_json(snapshot),
            snapshot.get("generated_at") or TimeService.utc_now_iso(),
            snapshot.get("explanation_version", "")
        ))

        conn.commit()

        conn.close()

    ############################################################

    def recent_decision_audit_snapshots(
        self,
        decision_id=None,
        decision_type=None,
        subject_id=None,
        limit=10
    ):

        clauses = []
        params = []

        if decision_id:
            clauses.append("decision_id=?")
            params.append(decision_id)

        if decision_type:
            clauses.append("decision_type=?")
            params.append(decision_type)

        if subject_id:
            clauses.append("subject_id=?")
            params.append(str(subject_id))

        where = ""

        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT *
            FROM decision_audit_history
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            tuple(params + [self._to_int(limit) or 10])
        )
        rows = cur.fetchall()
        conn.close()

        result = []

        for row in rows:
            result.append({
                "id": row["id"],
                "decision_id": row["decision_id"] or "",
                "decision_type": row["decision_type"] or "",
                "subject_type": row["subject_type"] or "",
                "subject_id": row["subject_id"] or "",
                "headline": row["headline"] or "",
                "decision_score": row["decision_score"] or 0,
                "confidence_score": row["confidence_score"] or 0,
                "trust_label": row["trust_label"] or "",
                "rank": row["rank"] or 0,
                "snapshot": self._from_json(row["snapshot_json"]),
                "generated_at": row["generated_at"] or "",
                "explanation_version": row["explanation_version"] or ""
            })

        return result

    ############################################################

    def prune_decision_audit_history(self, keep_latest=5000):

        conn = self.connection()

        cur = conn.cursor()

        cur.execute("""

        DELETE FROM decision_audit_history
        WHERE id NOT IN (
            SELECT id
            FROM decision_audit_history
            ORDER BY id DESC
            LIMIT ?
        )

        """,

        (
            self._to_int(keep_latest) or 5000,
        ))

        conn.commit()

        conn.close()

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

    def save_editorial_strategy(self, media_id, strategy):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        INSERT INTO editorial_strategies(

            media_id,
            strategy_id,
            strategy_type,
            title,
            objective,
            audience,
            core_message,
            reasoning,
            confidence,
            communications_score,
            recommended_platforms,
            posting_window,
            recommended_media,
            caption_direction,
            CTA,
            risks,
            limitations,
            supporting_evidence,
            selected,
            dismissed

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        ON CONFLICT(media_id, strategy_id) DO UPDATE SET
            strategy_type=excluded.strategy_type,
            title=excluded.title,
            objective=excluded.objective,
            audience=excluded.audience,
            core_message=excluded.core_message,
            reasoning=excluded.reasoning,
            confidence=excluded.confidence,
            communications_score=excluded.communications_score,
            recommended_platforms=excluded.recommended_platforms,
            posting_window=excluded.posting_window,
            recommended_media=excluded.recommended_media,
            caption_direction=excluded.caption_direction,
            CTA=excluded.CTA,
            risks=excluded.risks,
            limitations=excluded.limitations,
            supporting_evidence=excluded.supporting_evidence,
            created_at=CURRENT_TIMESTAMP

        """,

        (
            self._to_int(media_id),
            strategy.get("strategy_id", ""),
            strategy.get("strategy_type", ""),
            strategy.get("title", ""),
            strategy.get("objective", ""),
            strategy.get("target_audience", strategy.get("audience", "")),
            strategy.get("core_message", ""),
            self._to_json(strategy.get("reasoning")),
            self._to_int(strategy.get("confidence")),
            self._to_int(strategy.get("communications_score")),
            self._to_json(strategy.get("recommended_platforms")),
            strategy.get("recommended_posting_window", strategy.get("posting_window", "")),
            self._to_json(strategy.get("recommended_media")),
            strategy.get("caption_direction", ""),
            strategy.get("call_to_action", strategy.get("CTA", "")),
            self._to_json(strategy.get("risks")),
            self._to_json(strategy.get("limitations")),
            self._to_json(strategy.get("supporting_evidence")),
            self._to_int(strategy.get("selected")),
            self._to_int(strategy.get("dismissed"))
        ))

        strategy_id = cur.lastrowid
        conn.commit()
        conn.close()

        return strategy_id

    ############################################################

    def save_editorial_strategies(self, media_id, strategies):

        ids = []

        for strategy in strategies or []:
            ids.append(
                self.save_editorial_strategy(
                    media_id,
                    strategy
                )
            )

        return ids

    ############################################################

    def editorial_strategies_for_media(self, media_id, limit=10):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM editorial_strategies

        WHERE media_id=?

        ORDER BY confidence DESC,
                 communications_score DESC,
                 created_at DESC

        LIMIT ?

        """,

        (
            self._to_int(media_id),
            self._to_int(limit)
        ))

        rows = cur.fetchall()
        conn.close()

        return [
            self._editorial_strategy_from_row(row)
            for row in rows
        ]

    ############################################################

    def latest_editorial_comparison(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM editorial_comparisons

        WHERE media_id=?

        ORDER BY created_at DESC, id DESC

        LIMIT 1

        """,

        (
            self._to_int(media_id),
        ))

        row = cur.fetchone()
        conn.close()

        if row is None:
            return None

        return self._editorial_comparison_from_row(row)

    ############################################################

    def save_editorial_comparison(self, media_id, comparison):

        conn = self.connection()
        cur = conn.cursor()

        recommended = comparison.get("recommended_strategy") or {}
        runner_up = comparison.get("runner_up") or {}

        cur.execute("""

        INSERT INTO editorial_comparisons(

            media_id,
            recommended_strategy_id,
            runner_up_strategy_id,
            comparison_summary,
            tradeoffs,
            why_not_others,
            debate_summary,
            confidence

        )

        VALUES(?,?,?,?,?,?,?,?)

        """,

        (
            self._to_int(media_id),
            recommended.get("strategy_id", ""),
            runner_up.get("strategy_id", ""),
            comparison.get("comparison_summary", ""),
            self._to_json(comparison.get("tradeoffs")),
            self._to_json(comparison.get("why_not_others")),
            comparison.get("debate_summary", ""),
            self._to_int(comparison.get("confidence"))
        ))

        comparison_id = cur.lastrowid
        conn.commit()
        conn.close()

        return comparison_id

    ############################################################

    def mark_editorial_strategy(
        self,
        media_id,
        strategy_id,
        selected=None,
        dismissed=None
    ):

        updates = []
        params = []

        if selected is not None:
            updates.append("selected=?")
            params.append(self._to_int(selected))

        if dismissed is not None:
            updates.append("dismissed=?")
            params.append(self._to_int(dismissed))

        if not updates:
            return

        params.extend(
            [
                self._to_int(media_id),
                strategy_id
            ]
        )

        conn = self.connection()
        cur = conn.cursor()

        cur.execute(f"""

        UPDATE editorial_strategies

        SET {", ".join(updates)}

        WHERE media_id=?
        AND strategy_id=?

        """,

        params)

        conn.commit()
        conn.close()

    ############################################################

    def editorial_metrics(self):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(DISTINCT media_id) AS count

        FROM editorial_strategies

        """)

        media_with = cur.fetchone()["count"] or 0

        cur.execute("""

        SELECT COUNT(*) AS count

        FROM editorial_strategies

        WHERE selected=1

        """)

        selected = cur.fetchone()["count"] or 0

        cur.execute("""

        SELECT COUNT(*) AS count

        FROM editorial_strategies

        WHERE dismissed=1

        """)

        dismissed = cur.fetchone()["count"] or 0

        cur.execute("""

        SELECT strategy_type AS name, COUNT(*) AS count

        FROM editorial_strategies

        WHERE selected=1

        GROUP BY strategy_type

        ORDER BY COUNT(*) DESC, strategy_type

        LIMIT 5

        """)

        selected_types = [
            {
                "name": row["name"] or "",
                "count": row["count"] or 0
            }
            for row in cur.fetchall()
        ]

        cur.execute("""

        SELECT strategy_type AS name, COUNT(*) AS count

        FROM editorial_strategies

        WHERE dismissed=1

        GROUP BY strategy_type

        ORDER BY COUNT(*) DESC, strategy_type

        LIMIT 5

        """)

        dismissed_types = [
            {
                "name": row["name"] or "",
                "count": row["count"] or 0
            }
            for row in cur.fetchall()
        ]

        cur.execute("""

        SELECT COUNT(*)

        FROM media_intelligence

        WHERE NOT EXISTS (
            SELECT 1
            FROM editorial_strategies
            WHERE editorial_strategies.media_id=media_intelligence.media_id
        )

        """)

        missing = cur.fetchone()[0] or 0
        total_actions = selected + dismissed

        conn.close()

        return {
            "media_with_editorial_strategies": media_with,
            "most_selected_strategy_types": selected_types,
            "most_dismissed_strategy_types": dismissed_types,
            "strategy_acceptance_rate": self._rate(selected, total_actions),
            "media_missing_editorial_strategy": missing,
            "editorial_readiness": (
                "Ready"
                if missing == 0 and media_with
                else f"{media_with} media prepared"
            )
        }

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

    def save_media_correction(self, correction):

        media_id = self._to_int(correction.get("media_id"))
        field_name = correction.get("field_name", "")
        original_value = self._to_json(correction.get("original_value"))
        corrected_value = self._to_json(correction.get("corrected_value"))
        source = correction.get("correction_source", "Jonathan")
        notes = correction.get("notes", "")

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        SELECT id, corrected_value

        FROM media_corrections

        WHERE media_id=?
        AND field_name=?
        AND active=1

        ORDER BY updated_at DESC, id DESC

        LIMIT 1

        """,

        (
            media_id,
            field_name
        ))

        existing = cur.fetchone()
        previous_value = existing[1] if existing else original_value

        if existing:
            correction_id = existing[0]
            cur.execute("""

            UPDATE media_corrections

            SET
                original_value=?,
                corrected_value=?,
                correction_source=?,
                confidence_before=?,
                confidence_after=?,
                notes=?,
                updated_at=CURRENT_TIMESTAMP,
                active=1

            WHERE id=?

            """,

            (
                original_value,
                corrected_value,
                source,
                self._to_int(correction.get("confidence_before")),
                self._to_int(correction.get("confidence_after", 100)),
                notes,
                correction_id
            ))
            action = "updated"

        else:
            cur.execute("""

            INSERT INTO media_corrections(

                media_id,

                field_name,

                original_value,

                corrected_value,

                correction_source,

                confidence_before,

                confidence_after,

                notes,

                active

            )

            VALUES(?,?,?,?,?,?,?,?,1)

            """,

            (
                media_id,
                field_name,
                original_value,
                corrected_value,
                source,
                self._to_int(correction.get("confidence_before")),
                self._to_int(correction.get("confidence_after", 100)),
                notes
            ))
            correction_id = cur.lastrowid
            action = "created"

        cur.execute("""

        INSERT INTO correction_history(

            correction_id,

            media_id,

            field_name,

            previous_value,

            new_value,

            correction_source,

            action,

            notes

        )

        VALUES(?,?,?,?,?,?,?,?)

        """,

        (
            correction_id,
            media_id,
            field_name,
            previous_value,
            corrected_value,
            source,
            action,
            notes
        ))

        conn.commit()
        conn.close()

        return correction_id

    ############################################################

    def deactivate_media_correction(
        self,
        media_id,
        field_name,
        source="Jonathan",
        notes=""
    ):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        SELECT id, corrected_value

        FROM media_corrections

        WHERE media_id=?
        AND field_name=?
        AND active=1

        ORDER BY updated_at DESC, id DESC

        LIMIT 1

        """,

        (
            self._to_int(media_id),
            field_name
        ))

        row = cur.fetchone()

        if not row:
            conn.close()
            return False

        correction_id, previous = row

        cur.execute("""

        UPDATE media_corrections

        SET active=0,
            correction_source=?,
            notes=?,
            updated_at=CURRENT_TIMESTAMP

        WHERE id=?

        """,

        (
            source,
            notes,
            correction_id
        ))

        cur.execute("""

        INSERT INTO correction_history(

            correction_id,

            media_id,

            field_name,

            previous_value,

            new_value,

            correction_source,

            action,

            notes

        )

        VALUES(?,?,?,?,?,?,?,?)

        """,

        (
            correction_id,
            self._to_int(media_id),
            field_name,
            previous,
            "",
            source,
            "reset",
            notes
        ))

        conn.commit()
        conn.close()

        return True

    ############################################################

    def active_media_corrections(self, media_id):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM media_corrections

        WHERE media_id=?
        AND active=1

        ORDER BY updated_at DESC, id DESC

        """,

        (self._to_int(media_id),))

        rows = [
            self._media_correction_from_row(row)
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def active_media_corrections_for_media_ids(self, media_ids):

        media_ids = [
            self._to_int(media_id)
            for media_id in media_ids
            if self._to_int(media_id)
        ]

        if not media_ids:
            return {}

        placeholders = ",".join("?" for _ in media_ids)
        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(f"""

        SELECT *

        FROM media_corrections

        WHERE active=1
        AND media_id IN ({placeholders})

        ORDER BY media_id, updated_at DESC, id DESC

        """,

        tuple(media_ids))

        grouped = {}

        for row in cur.fetchall():
            correction = self._media_correction_from_row(row)
            grouped.setdefault(
                correction["media_id"],
                []
            ).append(correction)

        conn.close()

        return grouped

    ############################################################

    def fire_service_intelligence_for_media_ids(self, media_ids):

        media_ids = [
            self._to_int(media_id)
            for media_id in media_ids
            if self._to_int(media_id)
        ]

        if not media_ids:
            return {}

        placeholders = ",".join("?" for _ in media_ids)
        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(f"""

        SELECT *

        FROM fire_service_intelligence

        WHERE media_id IN ({placeholders})

        """,

        tuple(media_ids))

        rows = {
            row["media_id"]: self._fire_service_intelligence_from_row(row)
            for row in cur.fetchall()
        }

        conn.close()

        return rows

    ############################################################

    def correction_history_for_media(self, media_id, limit=50):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM correction_history

        WHERE media_id=?

        ORDER BY created_at DESC, id DESC

        LIMIT ?

        """,

        (
            self._to_int(media_id),
            self._to_int(limit)
        ))

        rows = [
            self._correction_history_from_row(row)
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def update_correction_pattern(self, pattern):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        INSERT INTO correction_patterns(

            field_name,

            original_value,

            corrected_value,

            occurrence_count,

            confidence,

            example_media_ids,

            notes,

            active

        )

        VALUES(?,?,?,?,?,?,?,1)

        ON CONFLICT(field_name, original_value, corrected_value)
        DO UPDATE SET
            occurrence_count=excluded.occurrence_count,
            confidence=excluded.confidence,
            example_media_ids=excluded.example_media_ids,
            notes=excluded.notes,
            last_seen=CURRENT_TIMESTAMP,
            active=1

        """,

        (
            pattern.get("field_name", ""),
            self._to_json(pattern.get("original_value")),
            self._to_json(pattern.get("corrected_value")),
            self._to_int(pattern.get("occurrence_count")),
            self._to_int(pattern.get("confidence")),
            self._to_json(pattern.get("example_media_ids")),
            pattern.get("notes", "")
        ))

        conn.commit()
        conn.close()

    ############################################################

    def correction_patterns(self, limit=50):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM correction_patterns

        WHERE active=1

        ORDER BY occurrence_count DESC, last_seen DESC

        LIMIT ?

        """,

        (self._to_int(limit),))

        rows = [
            self._correction_pattern_from_row(row)
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def correction_pattern_candidates(self, field_name, original_value, corrected_value):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        SELECT media_id

        FROM media_corrections

        WHERE field_name=?
        AND original_value=?
        AND corrected_value=?

        ORDER BY updated_at DESC, id DESC

        LIMIT 20

        """,

        (
            field_name,
            self._to_json(original_value),
            self._to_json(corrected_value)
        ))

        rows = [
            row[0]
            for row in cur.fetchall()
            if row[0]
        ]

        conn.close()

        return rows

    ############################################################

    def human_feedback_metrics(self):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        SELECT COUNT(DISTINCT media_id)

        FROM media_corrections

        WHERE active=1

        """)
        corrected_media = cur.fetchone()[0] or 0

        cur.execute("""

        SELECT COUNT(*)

        FROM media_corrections

        WHERE active=1

        """)
        active_corrections = cur.fetchone()[0] or 0

        cur.execute("""

        SELECT field_name, COUNT(*)

        FROM media_corrections

        WHERE active=1

        GROUP BY field_name

        ORDER BY COUNT(*) DESC, field_name

        LIMIT 8

        """)
        fields = [
            {
                "name": row[0],
                "count": row[1] or 0
            }
            for row in cur.fetchall()
        ]

        cur.execute("""

        SELECT COUNT(*)

        FROM correction_patterns

        WHERE active=1

        """)
        patterns = cur.fetchone()[0] or 0

        conn.close()

        return {
            "corrected_media_count": corrected_media,
            "active_corrections": active_corrections,
            "most_corrected_fields": fields,
            "correction_patterns_found": patterns
        }

    ############################################################

    def similar_media_for_correction(self, media_id, terms, limit=12):

        terms = [
            str(term or "").strip()
            for term in terms or []
            if str(term or "").strip()
        ][:8]

        if not terms:
            return []

        clauses = []
        params = []

        for term in terms:
            pattern = f"%{term}%"
            clauses.append("""
            (
                media_intelligence.search_text LIKE ?
                OR media_intelligence.content_tags LIKE ?
                OR media_intelligence.content_themes LIKE ?
                OR media_intelligence.recommended_uses LIKE ?
            )
            """)
            params.extend(
                (
                    pattern,
                    pattern,
                    pattern,
                    pattern
                )
            )

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(f"""

        SELECT
            media.id,
            media.filename,
            media.path,
            media.media_type,
            media_intelligence.intelligence_score

        FROM media

        JOIN media_intelligence
        ON media_intelligence.media_id = media.id

        WHERE media.id != ?
        AND (
            {" OR ".join(clauses)}
        )

        ORDER BY media_intelligence.intelligence_score DESC, media.filename ASC

        LIMIT ?

        """,

        [self._to_int(media_id)] + params + [self._to_int(limit)])

        rows = [
            {
                "id": row["id"],
                "filename": row["filename"],
                "path": row["path"],
                "media_type": row["media_type"],
                "intelligence_score": row["intelligence_score"] or 0
            }
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

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

    def ensure_knowledge_graph_defaults(self, entity_types, categories):

        conn = self.connection()
        cur = conn.cursor()

        for name in entity_types or []:
            cur.execute("""

            INSERT OR IGNORE INTO entity_types(

                name,

                active

            )

            VALUES(?,1)

            """,

            (name,))

        for name in categories or []:
            cur.execute("""

            INSERT OR IGNORE INTO knowledge_categories(

                name,

                active

            )

            VALUES(?,1)

            """,

            (name,))

        conn.commit()
        conn.close()

    ############################################################

    def save_graph_entity(self, entity):

        conn = self.connection()
        cur = conn.cursor()

        aliases = entity.get("aliases") or []
        name = entity.get("name", "")
        entity_type = entity.get("type", "")

        cur.execute("""

        INSERT INTO entities(

            name,

            type,

            description,

            aliases,

            confidence,

            active,

            source,

            updated

        )

        VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)

        ON CONFLICT(name, type) DO UPDATE SET
            description=excluded.description,
            aliases=excluded.aliases,
            confidence=excluded.confidence,
            active=excluded.active,
            source=excluded.source,
            updated=CURRENT_TIMESTAMP

        """,

        (
            name,
            entity_type,
            entity.get("description", ""),
            self._to_json(aliases),
            self._to_int(entity.get("confidence")),
            1 if entity.get("active", True) else 0,
            entity.get("source", "")
        ))

        cur.execute("""

        SELECT id

        FROM entities

        WHERE name=?
        AND type=?

        """,

        (
            name,
            entity_type
        ))

        entity_id = cur.fetchone()[0]

        values = [name] + list(aliases)

        for alias in values:
            normalized = self._graph_token(alias)

            if not normalized:
                continue

            cur.execute("""

            INSERT INTO entity_aliases(

                entity_id,

                alias,

                normalized_alias,

                confidence,

                active

            )

            VALUES(?,?,?,?,1)

            ON CONFLICT(entity_id, normalized_alias) DO UPDATE SET
                alias=excluded.alias,
                confidence=excluded.confidence,
                active=1

            """,

            (
                entity_id,
                alias,
                normalized,
                self._to_int(entity.get("confidence"))
            ))

        conn.commit()
        conn.close()

        return entity_id

    ############################################################

    def save_graph_relationship(self, relationship):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""

        INSERT INTO entity_relationships(

            source_entity_id,

            target_entity_id,

            relationship_type,

            description,

            confidence,

            active,

            source,

            updated

        )

        VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)

        ON CONFLICT(source_entity_id, target_entity_id, relationship_type)
        DO UPDATE SET
            description=excluded.description,
            confidence=excluded.confidence,
            active=excluded.active,
            source=excluded.source,
            updated=CURRENT_TIMESTAMP

        """,

        (
            self._to_int(relationship.get("source_entity_id")),
            self._to_int(relationship.get("target_entity_id")),
            relationship.get("relationship_type", ""),
            relationship.get("description", ""),
            self._to_int(relationship.get("confidence")),
            1 if relationship.get("active", True) else 0,
            relationship.get("source", "")
        ))

        relationship_id = cur.lastrowid

        if not relationship_id:
            cur.execute("""

            SELECT id

            FROM entity_relationships

            WHERE source_entity_id=?
            AND target_entity_id=?
            AND relationship_type=?

            """,

            (
                self._to_int(relationship.get("source_entity_id")),
                self._to_int(relationship.get("target_entity_id")),
                relationship.get("relationship_type", "")
            ))

            row = cur.fetchone()
            relationship_id = row[0] if row else None

        conn.commit()
        conn.close()

        return relationship_id

    ############################################################

    def graph_entity_by_name_or_alias(self, value):

        token = self._graph_token(value)

        if not token:
            return None

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT entities.*

        FROM entities

        LEFT JOIN entity_aliases
        ON entity_aliases.entity_id = entities.id

        WHERE entities.active=1
        AND (
            lower(entities.name)=?
            OR replace(lower(entities.name), ' ', '_')=?
            OR entity_aliases.normalized_alias=?
        )

        ORDER BY entities.confidence DESC, entities.name

        LIMIT 1

        """,

        (
            str(value or "").strip().lower(),
            token,
            token
        ))

        row = cur.fetchone()
        conn.close()

        if row is None:
            return None

        return self._graph_entity_from_row(row)

    ############################################################

    def search_graph_entities(self, query="", limit=25):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        pattern = f"%{str(query or '').strip()}%"
        token_pattern = f"%{self._graph_token(query)}%"

        cur.execute("""

        SELECT DISTINCT entities.*

        FROM entities

        LEFT JOIN entity_aliases
        ON entity_aliases.entity_id = entities.id

        WHERE entities.active=1
        AND (
            ?=''
            OR entities.name LIKE ?
            OR entities.type LIKE ?
            OR entities.description LIKE ?
            OR entity_aliases.alias LIKE ?
            OR entity_aliases.normalized_alias LIKE ?
        )

        ORDER BY entities.type, entities.name

        LIMIT ?

        """,

        (
            str(query or "").strip(),
            pattern,
            pattern,
            pattern,
            pattern,
            token_pattern,
            self._to_int(limit)
        ))

        rows = cur.fetchall()
        conn.close()

        return [
            self._graph_entity_from_row(row)
            for row in rows
        ]

    ############################################################

    def graph_related_entities(self, entity_id, depth=1, limit=50):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        rows = []
        frontier = {self._to_int(entity_id)}
        visited = set(frontier)
        max_depth = max(
            1,
            min(3, self._to_int(depth))
        )

        for current_depth in range(max_depth):

            if not frontier:
                break

            placeholders = ",".join("?" for _ in frontier)
            cur.execute(f"""

            SELECT
                entity_relationships.*,
                source.name AS source_name,
                source.type AS source_type,
                target.name AS target_name,
                target.type AS target_type

            FROM entity_relationships

            JOIN entities AS source
            ON source.id = entity_relationships.source_entity_id

            JOIN entities AS target
            ON target.id = entity_relationships.target_entity_id

            WHERE entity_relationships.active=1
            AND (
                entity_relationships.source_entity_id IN ({placeholders})
                OR entity_relationships.target_entity_id IN ({placeholders})
            )

            ORDER BY entity_relationships.confidence DESC, target.name

            """,

            tuple(frontier) + tuple(frontier))

            next_frontier = set()

            for row in cur.fetchall():
                source_id = row["source_entity_id"]
                target_id = row["target_entity_id"]

                if source_id in frontier:
                    related_id = target_id
                    name = row["target_name"]
                    entity_type = row["target_type"]
                else:
                    related_id = source_id
                    name = row["source_name"]
                    entity_type = row["source_type"]

                rows.append(
                    {
                        "id": related_id,
                        "name": name,
                        "type": entity_type,
                        "relationship": row["relationship_type"],
                        "confidence": row["confidence"] or 0,
                        "reason": row["description"] or "",
                        "depth": current_depth + 1
                    }
                )

                if related_id not in visited:
                    visited.add(related_id)
                    next_frontier.add(related_id)

                if len(rows) >= self._to_int(limit):
                    break

            if len(rows) >= self._to_int(limit):
                break

            frontier = next_frontier

        conn.close()

        unique = []
        seen = set()

        for row in rows:
            key = (
                row["id"],
                row["relationship"]
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(row)

        return unique[:self._to_int(limit)]

    ############################################################

    def graph_relationships(self, limit=50):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT
            entity_relationships.*,
            source.name AS source_name,
            source.type AS source_type,
            target.name AS target_name,
            target.type AS target_type

        FROM entity_relationships

        JOIN entities AS source
        ON source.id = entity_relationships.source_entity_id

        JOIN entities AS target
        ON target.id = entity_relationships.target_entity_id

        WHERE entity_relationships.active=1

        ORDER BY entity_relationships.updated DESC, entity_relationships.id DESC

        LIMIT ?

        """,

        (self._to_int(limit),))

        rows = [
            self._graph_relationship_from_row(row)
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def graph_top_entity_types(self, limit=8):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT type AS name, COUNT(*) AS count

        FROM entities

        WHERE active=1

        GROUP BY type

        ORDER BY count DESC, type

        LIMIT ?

        """,

        (self._to_int(limit),))

        rows = [
            {
                "name": row["name"],
                "count": row["count"] or 0
            }
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def graph_recent_entities(self, limit=8):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM entities

        WHERE active=1

        ORDER BY updated DESC, id DESC

        LIMIT ?

        """,

        (self._to_int(limit),))

        rows = [
            self._graph_entity_from_row(row)
            for row in cur.fetchall()
        ]

        conn.close()

        return rows

    ############################################################

    def knowledge_graph_health(self):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM entities WHERE active=1")
        entities = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM entity_relationships WHERE active=1")
        relationships = cur.fetchone()[0] or 0

        cur.execute("""

        SELECT COUNT(*)

        FROM entities

        WHERE active=1
        AND (
            confidence < 50
            OR type IS NULL
            OR type=''
        )

        """)
        unknown = cur.fetchone()[0] or 0

        cur.execute("""

        SELECT COUNT(*)

        FROM entities

        WHERE active=1
        AND id NOT IN (
            SELECT source_entity_id FROM entity_relationships WHERE active=1
            UNION
            SELECT target_entity_id FROM entity_relationships WHERE active=1
        )

        """)
        unused = cur.fetchone()[0] or 0

        conn.close()

        completeness = 0

        if entities:
            linked = max(
                0,
                entities - unused
            )
            completeness = int(
                (linked / entities) * 100
            )

        return {
            "entities": entities,
            "relationships": relationships,
            "unknown_entities": unknown,
            "unused_entities": unused,
            "graph_completeness": completeness
        }

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

    def save_communications_intelligence_profile(self, profile):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO communications_intelligence_profiles(
            profile_type,
            profile_key,
            version,
            generated_at,
            sample_count,
            confidence,
            profile_json,
            source_summary_json
        )
        VALUES(?,?,?,?,?,?,?,?)
        """, (
            profile.get("profile_type", "department"),
            profile.get("profile_key", "morden_fire_rescue"),
            profile.get("version", ""),
            profile.get("generated_at", TimeService.utc_now_iso()),
            self._to_int(profile.get("sample_count")),
            self._to_int(profile.get("confidence")),
            self._to_json(profile.get("profile", {})),
            self._to_json(profile.get("source_summary", {}))
        ))

        profile_id = cur.lastrowid
        conn.commit()
        conn.close()

        return profile_id

    ############################################################

    def latest_communications_intelligence_profile(
        self,
        profile_type="department",
        profile_key="morden_fire_rescue"
    ):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
        SELECT *
        FROM communications_intelligence_profiles
        WHERE profile_type=?
        AND profile_key=?
        ORDER BY datetime(REPLACE(REPLACE(generated_at, 'T', ' '), '+00:00', '')) DESC,
                 id DESC
        LIMIT 1
        """, (
            profile_type,
            profile_key
        ))

        row = cur.fetchone()
        conn.close()

        if not row:
            return {}

        return {
            "id": row["id"],
            "profile_type": row["profile_type"] or "",
            "profile_key": row["profile_key"] or "",
            "version": row["version"] or "",
            "generated_at": row["generated_at"] or "",
            "sample_count": row["sample_count"] or 0,
            "confidence": row["confidence"] or 0,
            "profile": self._from_json(row["profile_json"]),
            "source_summary": self._from_json(row["source_summary_json"])
        }

    ############################################################

    def save_communication_edit_learning(self, edit):

        conn = self.connection()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO communication_edit_learning(
            platform,
            original_text,
            final_text,
            change_summary_json,
            source,
            approved,
            created_at
        )
        VALUES(?,?,?,?,?,?,?)
        """, (
            edit.get("platform", ""),
            edit.get("original_text", ""),
            edit.get("final_text", ""),
            self._to_json(edit.get("change_summary", {})),
            edit.get("source", ""),
            self._to_int(edit.get("approved", 1)),
            edit.get("created_at", TimeService.utc_now_iso())
        ))

        edit_id = cur.lastrowid
        conn.commit()
        conn.close()

        return edit_id

    ############################################################

    def communication_edit_learning_samples(self, limit=500):

        conn = self.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
        SELECT *
        FROM communication_edit_learning
        WHERE approved=1
        ORDER BY datetime(REPLACE(REPLACE(created_at, 'T', ' '), '+00:00', '')) DESC,
                 id DESC
        LIMIT ?
        """, (self._to_int(limit),))

        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "platform": row["platform"] or "",
                "original_text": row["original_text"] or "",
                "final_text": row["final_text"] or "",
                "change_summary": self._from_json(row["change_summary_json"]),
                "source": row["source"] or "",
                "approved": row["approved"] or 0,
                "created_at": row["created_at"] or ""
            }
            for row in rows
        ]

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

    def _analysis_queue_repository(self):

        if self._analysis_queue_repo is None:
            self._analysis_queue_repo = AnalysisQueueRepository(self)

        return self._analysis_queue_repo

    ############################################################

    def create_analysis_session(
        self,
        scope,
        provider,
        model,
        total_items=0,
        settings=None
    ):

        return self._analysis_queue_repository().create_session(
            scope,
            provider,
            model,
            total_items,
            settings
        )

    def enqueue_analysis_items(
        self,
        session_id,
        media_items,
        provider,
        model,
        force=False
    ):

        return self._analysis_queue_repository().enqueue_items(
            session_id,
            media_items,
            provider,
            model,
            force=force
        )

    def next_analysis_queue_batch(self, session_id, limit):

        return self._analysis_queue_repository().next_batch(session_id, limit)

    def mark_analysis_queue_analyzing(self, queue_id):

        return self._analysis_queue_repository().mark_analyzing(queue_id)

    def mark_analysis_queue_completed(
        self,
        queue_id,
        duration=0,
        provider_latency=0,
        db_write_duration=0
    ):

        return self._analysis_queue_repository().mark_completed(
            queue_id,
            duration=duration,
            provider_latency=provider_latency,
            db_write_duration=db_write_duration
        )

    def mark_analysis_queue_skipped(self, queue_id, reason):

        return self._analysis_queue_repository().mark_skipped(queue_id, reason)

    def mark_analysis_queue_failed(
        self,
        queue_id,
        category,
        reason,
        duration=0
    ):

        return self._analysis_queue_repository().mark_failed(
            queue_id,
            category,
            reason,
            duration=duration
        )

    def retry_failed_analysis_items(self, session_id=None):

        return self._analysis_queue_repository().retry_failed(session_id)

    def cancel_analysis_session(self, session_id, reason="Canceled by user"):

        return self._analysis_queue_repository().cancel_session(
            session_id,
            reason
        )

    def reset_stale_analysis_items(self, session_id=None):

        return self._analysis_queue_repository().reset_stale_analyzing(
            session_id
        )

    def mark_analysis_worker_started(
        self,
        session_id,
        worker_id,
        process_id=None,
        thread_id=None,
        status="Active"
    ):

        return self._analysis_queue_repository().mark_worker_started(
            session_id,
            worker_id,
            process_id=process_id,
            thread_id=thread_id,
            status=status
        )

    def heartbeat_analysis_session(self, session_id, worker_status="Active"):

        return self._analysis_queue_repository().heartbeat_session(
            session_id,
            worker_status=worker_status
        )

    def mark_analysis_worker_stopped(
        self,
        session_id,
        worker_status,
        reason=""
    ):

        return self._analysis_queue_repository().mark_worker_stopped(
            session_id,
            worker_status,
            reason=reason
        )

    def mark_analysis_session_recoverable(self, session_id, reason):

        return self._analysis_queue_repository().mark_session_recoverable(
            session_id,
            reason
        )

    def pause_analysis_session(self, session_id, reason="Paused"):

        return self._analysis_queue_repository().pause_session(
            session_id,
            reason=reason
        )

    def increment_analysis_session_resume_count(self, session_id):

        return self._analysis_queue_repository().increment_resume_count(
            session_id
        )

    def update_analysis_session(self, session_id, **fields):

        return self._analysis_queue_repository().update_session(
            session_id,
            **fields
        )

    def refresh_analysis_session_counts(self, session_id):

        return self._analysis_queue_repository().refresh_session_counts(
            session_id
        )

    def analysis_session_summary(self, session_id=None):

        return self._analysis_queue_repository().session_summary(session_id)

    def incomplete_analysis_sessions(self):

        return self._analysis_queue_repository().incomplete_sessions()

    def latest_incomplete_analysis_session(self):

        return self._analysis_queue_repository().latest_incomplete_session()

    def analysis_queue_counts(self, session_id=None):

        return self._analysis_queue_repository().queue_counts(session_id)

    def media_analysis_statuses(self, media_ids):

        return self._analysis_queue_repository().media_statuses(media_ids)

    ############################################################

    def _communication_repository(self):

        if self._communication_repo is None:
            self._communication_repo = CommunicationRepository(self)

        return self._communication_repo

    ############################################################

    def _benchmark_repository(self):

        if self._benchmark_repo is None:
            self._benchmark_repo = BenchmarkRepository(self)

        return self._benchmark_repo

    ############################################################

    def _communication_learning_repository(self):

        if self._communication_learning_repo is None:
            self._communication_learning_repo = CommunicationLearningRepository(self)

        return self._communication_learning_repo

    ############################################################

    def create_communication_learning_import_run(self, item):

        return self._communication_learning_repository().create_import_run(item)

    def update_communication_learning_import_run(self, import_run_id, item):

        return self._communication_learning_repository().update_import_run(
            import_run_id,
            item
        )

    def save_communication_learning_record(self, record):

        return self._communication_learning_repository().save_record(record)

    def communication_learning_records(self, filters=None, limit=500):

        return self._communication_learning_repository().records(
            filters=filters,
            limit=limit
        )

    def save_communication_learning_profile(self, item):

        return self._communication_learning_repository().save_profile(item)

    def save_communication_learning_summary(self, item):

        return self._communication_learning_repository().save_summary(item)

    def latest_communication_learning_summary(self):

        return self._communication_learning_repository().latest_summary()

    def review_communication_learning_record(self, learning_id, updates):

        return self._communication_learning_repository().review_record(
            learning_id,
            updates
        )

    def save_communication_experiment(self, item):

        return self._communication_learning_repository().save_experiment(item)

    def communication_experiments(self, limit=25):

        return self._communication_learning_repository().experiments(limit)

    ############################################################

    def save_benchmark_department(self, item):

        return self._benchmark_repository().save_department(item)

    def create_benchmark_import_run(self, item):

        return self._benchmark_repository().create_import_run(item)

    def update_benchmark_import_run(self, import_run_id, item):

        return self._benchmark_repository().update_import_run(
            import_run_id,
            item
        )

    def save_benchmark_record(self, record):

        return self._benchmark_repository().save_record(record)

    def save_benchmark_pattern(self, pattern):

        return self._benchmark_repository().save_pattern(pattern)

    def benchmark_records(self, filters=None, limit=100, offset=0):

        return self._benchmark_repository().records(
            filters=filters,
            limit=limit,
            offset=offset
        )

    def benchmark_patterns(self, filters=None, limit=50):

        return self._benchmark_repository().patterns(
            filters=filters,
            limit=limit
        )

    def benchmark_insights(self):

        return self._benchmark_repository().insights()

    def review_benchmark_pattern(self, pattern_id, updates):

        return self._benchmark_repository().review_pattern(
            pattern_id,
            updates
        )

    def save_benchmark_experiment(self, item):

        return self._benchmark_repository().save_experiment(item)

    def rollback_benchmark_import_run(self, import_run_id):

        return self._benchmark_repository().rollback_import_run(import_run_id)

    ############################################################

    def save_communication_record(self, record):

        return self._communication_repository().save_communication_record(record)

    def save_communication_delivery(self, delivery):

        return self._communication_repository().save_communication_delivery(delivery)

    def save_communication_intelligence(self, intelligence):

        return self._communication_repository().save_communication_intelligence(intelligence)

    def save_communication_correction(self, correction):

        return self._communication_repository().save_communication_correction(correction)

    def clear_communication_correction(self, communication_id, field_name):

        return self._communication_repository().clear_communication_correction(
            communication_id,
            field_name
        )

    def save_communication_campaign(self, campaign):

        return self._communication_repository().save_communication_campaign(campaign)

    def save_communication_program(self, program):

        return self._communication_repository().save_communication_program(program)

    def link_communication_campaign(self, communication_id, campaign_id, evidence="", confidence=0):

        return self._communication_repository().link_communication_campaign(
            communication_id,
            campaign_id,
            evidence,
            confidence
        )

    def link_communication_program(self, communication_id, program_id, evidence="", confidence=0):

        return self._communication_repository().link_communication_program(
            communication_id,
            program_id,
            evidence,
            confidence
        )

    def link_communication_topic(self, communication_id, topic, evidence="", confidence=0):

        return self._communication_repository().link_communication_topic(
            communication_id,
            topic,
            evidence,
            confidence
        )

    def save_communication_outcome(self, outcome):

        return self._communication_repository().save_communication_outcome(outcome)

    def save_communication_import_run(self, summary):

        return self._communication_repository().save_communication_import_run(summary)

    def create_communication_import_run(self, summary):

        return self._communication_repository().create_communication_import_run(summary)

    def update_communication_import_run(self, import_run_id, summary):

        return self._communication_repository().update_communication_import_run(
            import_run_id,
            summary
        )

    def save_communication_import_item(self, item):

        return self._communication_repository().save_communication_import_item(item)

    def save_communication_duplicate_review(self, item):

        return self._communication_repository().save_communication_duplicate_review(item)

    def save_communication_media_reference(self, item):

        return self._communication_repository().save_communication_media_reference(item)

    def communication_duplicate_candidate(
        self,
        normalized_text,
        date_prefix,
        source_identifier="",
        platform_post_id=""
    ):

        return self._communication_repository().communication_duplicate_candidate(
            normalized_text,
            date_prefix,
            source_identifier,
            platform_post_id
        )

    def communication_has_delivery_platform(self, communication_id, platform):

        return self._communication_repository().communication_has_delivery_platform(
            communication_id,
            platform
        )

    def rollback_communication_import_run(self, import_run_id):

        return self._communication_repository().rollback_communication_import_run(
            import_run_id
        )

    def update_communication_intelligence_review(self, communication_id, updates):

        return self._communication_repository().update_communication_intelligence_review(
            communication_id,
            updates
        )

    def communication_records(self, limit=100, search_text=""):

        return self._communication_repository().communication_records(limit, search_text)

    def communication_deliveries(self, communication_id=None, limit=100):

        return self._communication_repository().communication_deliveries(
            communication_id,
            limit
        )

    def communication_campaigns(self, limit=100):

        return self._communication_repository().communication_campaigns(limit)

    def communication_programs(self, limit=100):

        return self._communication_repository().communication_programs(limit)

    def communication_import_runs(self, limit=20):

        return self._communication_repository().communication_import_runs(limit)

    def effective_communication_intelligence(self, communication_id):

        return self._communication_repository().effective_communication_intelligence(
            communication_id
        )

    def effective_communication_memory(self, limit=500):

        return self._communication_repository().effective_communication_memory(limit)

    def effective_communication_memory_between(self, start_date, end_date, limit=250):

        return self._communication_repository().effective_communication_memory_between(
            start_date,
            end_date,
            limit
        )

    def communication_memory_topic_summary(self, limit=50):

        return self._communication_repository().communication_memory_topic_summary(limit)

    def communication_memory_engine_summary(self):

        return self._communication_repository().communication_memory_engine_summary()

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

    def _intelligence_review_counts(self, filters):

        section_filters = dict(filters or {})
        section_filters.pop("review_status", None)
        where, params = self._intelligence_where(section_filters)

        conn = self.connection()
        cur = conn.cursor()

        statuses = (
            (
                "human_corrected",
                "EXISTS (SELECT 1 FROM media_corrections WHERE media_corrections.media_id=media.id AND media_corrections.active=1)"
            ),
            (
                "needs_review",
                "media_intelligence.intelligence_score < 50 OR fire_service_intelligence.operational_confidence < 50"
            ),
            (
                "low_confidence",
                "media_intelligence.intelligence_score < 65 OR fire_service_intelligence.operational_confidence < 65"
            )
        )
        rows = []

        for status, clause in statuses:
            extra_where = where
            extra_params = list(params)

            if extra_where:
                extra_where += f" AND ({clause})"
            else:
                extra_where = f"WHERE ({clause})"

            cur.execute(f"""

            SELECT COUNT(DISTINCT media.id)

            FROM media

            JOIN media_intelligence
            ON media.id = media_intelligence.media_id

            LEFT JOIN fire_service_intelligence
            ON fire_service_intelligence.media_id = media.id

            {extra_where}

            """,

            extra_params)

            count = cur.fetchone()[0] or 0

            if count:
                rows.append(
                    (
                        status,
                        count
                    )
                )

        conn.close()

        return rows

    ############################################################

    def _editorial_strategy_counts(self, filters):

        section_filters = dict(filters or {})
        section_filters.pop("editorial_strategy", None)
        where, params = self._intelligence_where(section_filters)

        conn = self.connection()
        cur = conn.cursor()

        cur.execute(f"""

        SELECT
            editorial_strategies.strategy_type,
            COUNT(DISTINCT media.id)

        FROM media

        JOIN media_intelligence
        ON media.id = media_intelligence.media_id

        JOIN editorial_strategies
        ON editorial_strategies.media_id = media.id

        {where}

        GROUP BY editorial_strategies.strategy_type

        HAVING editorial_strategies.strategy_type IS NOT NULL
        AND editorial_strategies.strategy_type != ''

        ORDER BY COUNT(DISTINCT media.id) DESC,
                 editorial_strategies.strategy_type

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

            elif field == "review_status":
                review_clauses = []

                if "human_corrected" in values:
                    review_clauses.append("""
                    EXISTS (
                        SELECT 1
                        FROM media_corrections
                        WHERE media_corrections.media_id=media.id
                        AND media_corrections.active=1
                    )
                    """)

                if "needs_review" in values:
                    review_clauses.append("""
                    (
                        media_intelligence.intelligence_score < 50
                        OR EXISTS (
                            SELECT 1
                            FROM fire_service_intelligence
                            WHERE fire_service_intelligence.media_id=media.id
                            AND fire_service_intelligence.operational_confidence < 50
                        )
                    )
                    """)

                if "low_confidence" in values:
                    review_clauses.append("""
                    (
                        media_intelligence.intelligence_score < 65
                        OR EXISTS (
                            SELECT 1
                            FROM fire_service_intelligence
                            WHERE fire_service_intelligence.media_id=media.id
                            AND fire_service_intelligence.operational_confidence < 65
                        )
                    )
                    """)

                if review_clauses:
                    clauses.append(
                        "(" + " OR ".join(review_clauses) + ")"
                    )

            elif field == "editorial_strategy":
                clauses.append(f"""
                EXISTS (
                    SELECT 1
                    FROM editorial_strategies
                    WHERE editorial_strategies.media_id=media.id
                    AND editorial_strategies.strategy_type IN ({placeholders})
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
            "correction_count": (
                "(SELECT COUNT(*) FROM media_corrections "
                "WHERE media_corrections.media_id=media.id "
                "AND media_corrections.active=1) DESC, "
                "media.filename ASC"
            ),
            "editorial_confidence": (
                "(SELECT MAX(confidence) FROM editorial_strategies "
                "WHERE editorial_strategies.media_id=media.id) DESC, "
                "media.filename ASC"
            ),
            "strategy_count": (
                "(SELECT COUNT(*) FROM editorial_strategies "
                "WHERE editorial_strategies.media_id=media.id) DESC, "
                "media.filename ASC"
            ),
            "top_editorial_strategy": (
                "(SELECT strategy_type FROM editorial_strategies "
                "WHERE editorial_strategies.media_id=media.id "
                "ORDER BY confidence DESC LIMIT 1) ASC, "
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
            "last_analyzed": row["last_analyzed"] or "",
            "raw_response": row["raw_response"] or "",
            "parse_status": row["parse_status"] or "",
            "parse_warnings": self._from_json(row["parse_warnings"]),
            "confidence": row["confidence"] or 0,
            "people": self._from_json(row["people"]),
            "activities": self._from_json(row["activities"]),
            "setting": row["setting"] or "",
            "indoor_outdoor": row["indoor_outdoor"] or "",
            "safety_concerns": self._from_json(row["safety_concerns"]),
            "public_use_risks": self._from_json(row["public_use_risks"]),
            "visible_text": self._from_json(row["visible_text"]),
            "uncertain_observations": self._from_json(
                row["uncertain_observations"]
            ),
            "structured_field_completeness": (
                row["structured_field_completeness"] or 0
            ),
            "failure_category": row["failure_category"] or "",
            "request_metadata": self._from_json(row["request_metadata"]),
            "preprocessing_metadata": self._from_json(
                row["preprocessing_metadata"]
            ),
            "provider_attempts": self._from_json(row["provider_attempts"]),
            "provider_response_excerpt": row["provider_response_excerpt"] or "",
            "provider_status_code": row["provider_status_code"] or 0,
            "prompt_version": row["prompt_version"] or "",
            "analysis_version": row["analysis_version"] or "",
            "quality_state": row["quality_state"] or "",
            "trust_state": row["trust_state"] or "",
            "review_status": row["review_status"] or "",
            "quality_warnings": self._from_json(row["quality_warnings"]),
            "media_context": row["media_context"] or "",
            "reviewed_at": row["reviewed_at"] or "",
            "reviewer_notes": row["reviewer_notes"] or ""
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

    def _fire_service_intelligence_from_row(self, row):

        return {
            "media_id": row["media_id"],
            "firefighter_count": row["firefighter_count"] or 0,
            "civilian_count": row["civilian_count"] or 0,
            "officer_presence": bool(row["officer_presence"]),
            "children_present": bool(row["children_present"]),
            "group_size": row["group_size"] or "",
            "personnel": self._from_json(row["personnel"]),
            "ppe": self._from_json(row["ppe"]),
            "equipment": self._from_json(row["equipment"]),
            "apparatus": self._from_json(row["apparatus"]),
            "incident_classification": row["incident_classification"] or "",
            "operational_activity": row["operational_activity"] or "",
            "communications_uses": self._from_json(row["communications_uses"]),
            "reasoning": self._from_json(row["reasoning"]),
            "operational_context": row["operational_context"] or "",
            "operational_skills": self._from_json(row["operational_skills"]),
            "communications_intent": self._from_json(row["communications_intent"]),
            "operational_confidence": row["operational_confidence"] or 0,
            "reasoning_evidence": self._from_json(row["reasoning_evidence"]),
            "operational_reasoning": self._from_json(row["operational_reasoning"]),
            "generated_at": row["generated_at"] or "",
            "source_model": row["source_model"] or ""
        }

    ############################################################

    def _filesystem_intelligence_from_row(self, row):

        return {
            "media_id": row["media_id"],
            "media_root": row["media_root"] or "",
            "relative_path": row["relative_path"] or "",
            "folder_hierarchy": self._from_json(row["folder_hierarchy"]),
            "root_category": row["root_category"] or "",
            "parent_category": row["parent_category"] or "",
            "subcategory": row["subcategory"] or "",
            "folder_keywords": self._from_json(row["folder_keywords"]),
            "normalized_tags": self._from_json(row["normalized_tags"]),
            "apparatus_identifier": row["apparatus_identifier"] or "",
            "apparatus_name": row["apparatus_name"] or "",
            "apparatus_resolved": bool(row["apparatus_resolved"]),
            "incident_category": row["incident_category"] or "",
            "incident_type": row["incident_type"] or "",
            "training_category": row["training_category"] or "",
            "training_type": row["training_type"] or "",
            "drill_type": row["drill_type"] or "",
            "live_burn_context": bool(row["live_burn_context"]),
            "public_education_program": row["public_education_program"] or "",
            "campaign": row["campaign"] or "",
            "community_event": row["community_event"] or "",
            "station": row["station"] or "",
            "recruit_class": bool(row["recruit_class"]),
            "mutual_aid_context": bool(row["mutual_aid_context"]),
            "year": row["year"] or "",
            "month": row["month"] or 0,
            "season": row["season"] or "",
            "location_context": row["location_context"] or "",
            "filesystem_confidence": row["filesystem_confidence"] or 0,
            "matching_rule": row["matching_rule"] or "",
            "source_folders": self._from_json(row["source_folders"]),
            "conflict_state": row["conflict_state"] or "",
            "conflict_details": self._from_json(row["conflict_details"]),
            "enrichment_version": row["enrichment_version"] or "",
            "last_derived_at": row["last_derived_at"] or "",
            "created_at": row["created_at"] or "",
            "updated_at": row["updated_at"] or ""
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

    def _graph_entity_from_row(self, row):

        return {
            "id": row["id"],
            "name": row["name"] or "",
            "type": row["type"] or "",
            "description": row["description"] or "",
            "aliases": self._from_json(row["aliases"]),
            "confidence": row["confidence"] or 0,
            "active": bool(row["active"]),
            "source": row["source"] or "",
            "created": row["created"] or "",
            "updated": row["updated"] or ""
        }

    ############################################################

    def _graph_relationship_from_row(self, row):

        return {
            "id": row["id"],
            "source_entity_id": row["source_entity_id"],
            "source_name": row["source_name"] or "",
            "source_type": row["source_type"] or "",
            "target_entity_id": row["target_entity_id"],
            "target_name": row["target_name"] or "",
            "target_type": row["target_type"] or "",
            "relationship_type": row["relationship_type"] or "",
            "description": row["description"] or "",
            "confidence": row["confidence"] or 0,
            "active": bool(row["active"]),
            "source": row["source"] or "",
            "created": row["created"] or "",
            "updated": row["updated"] or ""
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

    def _media_correction_from_row(self, row):

        return {
            "id": row["id"],
            "media_id": row["media_id"],
            "field_name": row["field_name"] or "",
            "original_value": self._from_json(row["original_value"]),
            "corrected_value": self._from_json(row["corrected_value"]),
            "correction_source": row["correction_source"] or "",
            "confidence_before": row["confidence_before"] or 0,
            "confidence_after": row["confidence_after"] or 0,
            "notes": row["notes"] or "",
            "created_at": row["created_at"] or "",
            "updated_at": row["updated_at"] or "",
            "active": bool(row["active"])
        }

    ############################################################

    def _correction_history_from_row(self, row):

        return {
            "id": row["id"],
            "correction_id": row["correction_id"],
            "media_id": row["media_id"],
            "field_name": row["field_name"] or "",
            "previous_value": self._from_json(row["previous_value"]),
            "new_value": self._from_json(row["new_value"]),
            "correction_source": row["correction_source"] or "",
            "action": row["action"] or "",
            "notes": row["notes"] or "",
            "created_at": row["created_at"] or ""
        }

    ############################################################

    def _correction_pattern_from_row(self, row):

        return {
            "id": row["id"],
            "field_name": row["field_name"] or "",
            "original_value": self._from_json(row["original_value"]),
            "corrected_value": self._from_json(row["corrected_value"]),
            "occurrence_count": row["occurrence_count"] or 0,
            "confidence": row["confidence"] or 0,
            "example_media_ids": self._from_json(row["example_media_ids"]),
            "notes": row["notes"] or "",
            "first_seen": row["first_seen"] or "",
            "last_seen": row["last_seen"] or "",
            "active": bool(row["active"])
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

    def _editorial_strategy_from_row(self, row):

        return {
            "id": row["id"],
            "media_id": row["media_id"],
            "strategy_id": row["strategy_id"] or "",
            "strategy_type": row["strategy_type"] or "",
            "title": row["title"] or "",
            "objective": row["objective"] or "",
            "target_audience": row["audience"] or "",
            "core_message": row["core_message"] or "",
            "reasoning": self._from_json(row["reasoning"]),
            "confidence": row["confidence"] or 0,
            "communications_score": row["communications_score"] or 0,
            "recommended_platforms": self._from_json(row["recommended_platforms"]),
            "recommended_posting_window": row["posting_window"] or "",
            "recommended_media": self._from_json(row["recommended_media"]),
            "caption_direction": row["caption_direction"] or "",
            "call_to_action": row["CTA"] or "",
            "risks": self._from_json(row["risks"]),
            "limitations": self._from_json(row["limitations"]),
            "supporting_evidence": self._from_json(row["supporting_evidence"]),
            "created_at": row["created_at"] or "",
            "selected": bool(row["selected"]),
            "dismissed": bool(row["dismissed"])
        }

    ############################################################

    def _editorial_comparison_from_row(self, row):

        return {
            "id": row["id"],
            "media_id": row["media_id"],
            "recommended_strategy_id": row["recommended_strategy_id"] or "",
            "runner_up_strategy_id": row["runner_up_strategy_id"] or "",
            "comparison_summary": row["comparison_summary"] or "",
            "tradeoffs": self._from_json(row["tradeoffs"]),
            "why_not_others": self._from_json(row["why_not_others"]),
            "debate_summary": row["debate_summary"] or "",
            "confidence": row["confidence"] or 0,
            "created_at": row["created_at"] or ""
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

    def _mock_analysis_where(self):

        return """
        (
            failure_reason IS NULL OR failure_reason=''
        )
        AND (
            provider='mock'
            OR model LIKE 'mock%'
            OR description LIKE 'MOCK TEST ANALYSIS%'
        )
        """

    ############################################################

    def _to_int(self, value):

        if isinstance(value, str):
            match = re.search(r"-?\d+", value)

            if match:
                value = match.group(0)

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

    def _rate(self, value, total):

        if total <= 0:
            return 0

        return round((value / total) * 100, 1)

    ############################################################

    def _graph_token(self, value):

        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value)

        return value.strip("_")

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

    def _ensure_media_columns(self, cur):

        cur.execute("PRAGMA table_info(media)")

        columns = {
            row[1]
            for row in cur.fetchall()
        }

        additions = {
            "file_created_at": "TEXT",
            "file_modified_at": "TEXT",
            "first_seen_at": "TEXT",
            "capture_time": "TEXT",
            "capture_time_source": "TEXT",
            "duration_seconds": "REAL DEFAULT 0",
            "width": "INTEGER DEFAULT 0",
            "height": "INTEGER DEFAULT 0",
            "frame_rate": "REAL DEFAULT 0",
            "orientation": "TEXT",
            "codec": "TEXT",
            "thumbnail_status": "TEXT"
        }

        for name, definition in additions.items():

            if name in columns:
                continue

            cur.execute(
                f"ALTER TABLE media ADD COLUMN {name} {definition}"
            )

            logger.info(
                "Added media column %s",
                name
            )

        cur.execute("""
        UPDATE media
        SET first_seen_at=date_added
        WHERE
            (first_seen_at IS NULL OR first_seen_at='')
            AND date_added IS NOT NULL
            AND date_added!=''
        """)

    ############################################################

    def _ensure_analysis_queue_columns(self, cur):

        cur.execute("PRAGMA table_info(analysis_queue)")

        columns = {
            row[1]
            for row in cur.fetchall()
        }

        additions = {
            "priority_reason": "TEXT"
        }

        for name, definition in additions.items():

            if name in columns:
                continue

            cur.execute(
                f"ALTER TABLE analysis_queue ADD COLUMN {name} {definition}"
            )

            logger.info(
                "Added analysis_queue column %s",
                name
            )

    ############################################################

    def _ensure_analysis_session_columns(self, cur):

        cur.execute("PRAGMA table_info(analysis_sessions)")

        columns = {
            row[1]
            for row in cur.fetchall()
        }

        additions = {
            "worker_id": "TEXT",
            "worker_process_id": "INTEGER",
            "worker_thread_id": "TEXT",
            "worker_status": "TEXT",
            "worker_started_at": "TEXT",
            "worker_heartbeat_at": "TEXT",
            "worker_stopped_at": "TEXT",
            "worker_stop_reason": "TEXT",
            "last_progress_at": "TEXT",
            "resume_count": "INTEGER DEFAULT 0"
        }

        for name, definition in additions.items():

            if name in columns:
                continue

            cur.execute(
                f"ALTER TABLE analysis_sessions ADD COLUMN {name} {definition}"
            )

            logger.info(
                "Added analysis_sessions column %s",
                name
            )

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
            "last_analyzed": "TIMESTAMP",
            "raw_response": "TEXT",
            "parse_status": "TEXT",
            "parse_warnings": "TEXT",
            "confidence": "REAL DEFAULT 0",
            "people": "TEXT",
            "activities": "TEXT",
            "setting": "TEXT",
            "indoor_outdoor": "TEXT",
            "safety_concerns": "TEXT",
            "public_use_risks": "TEXT",
            "visible_text": "TEXT",
            "uncertain_observations": "TEXT",
            "structured_field_completeness": "REAL DEFAULT 0",
            "failure_category": "TEXT",
            "request_metadata": "TEXT",
            "preprocessing_metadata": "TEXT",
            "provider_attempts": "TEXT",
            "provider_response_excerpt": "TEXT",
            "provider_status_code": "INTEGER",
            "prompt_version": "TEXT",
            "analysis_version": "TEXT",
            "quality_state": "TEXT",
            "trust_state": "TEXT",
            "review_status": "TEXT",
            "quality_warnings": "TEXT",
            "media_context": "TEXT",
            "reviewed_at": "TEXT",
            "reviewer_notes": "TEXT"
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

    def _ensure_video_intelligence_columns(self, cur):

        cur.execute("PRAGMA table_info(video_intelligence)")

        columns = {
            row[1]
            for row in cur.fetchall()
        }

        additions = {
            "video_summary": "TEXT",
            "primary_activity": "TEXT",
            "secondary_activity": "TEXT",
            "estimated_scene_count": "INTEGER DEFAULT 0",
            "representative_frames": "TEXT",
            "identified_ppe": "TEXT",
            "training_evolution": "TEXT",
            "incident_category": "TEXT",
            "program": "TEXT",
            "campaign": "TEXT",
            "community_event": "TEXT",
            "estimated_audience": "TEXT",
            "communications_themes": "TEXT",
            "story_potential": "INTEGER DEFAULT 0",
            "education_score": "INTEGER DEFAULT 0",
            "recruitment_score": "INTEGER DEFAULT 0",
            "community_score": "INTEGER DEFAULT 0",
            "operations_score": "INTEGER DEFAULT 0",
            "reel_potential": "INTEGER DEFAULT 0",
            "reel_explanation": "TEXT",
            "clip_recommendations": "TEXT",
            "cover_recommendation": "TEXT",
            "story_category": "TEXT",
            "trust_state": "TEXT",
            "explanation": "TEXT"
        }

        for name, definition in additions.items():

            if name in columns:
                continue

            cur.execute(
                f"ALTER TABLE video_intelligence ADD COLUMN {name} {definition}"
            )

            logger.info(
                "Added video_intelligence column %s",
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

    def _ensure_fire_service_intelligence_columns(self, cur):

        cur.execute("PRAGMA table_info(fire_service_intelligence)")

        columns = {
            row[1]
            for row in cur.fetchall()
        }

        additions = {
            "operational_context": "TEXT",
            "operational_skills": "TEXT",
            "communications_intent": "TEXT",
            "operational_confidence": "INTEGER",
            "reasoning_evidence": "TEXT",
            "operational_reasoning": "TEXT"
        }

        for name, definition in additions.items():

            if name in columns:
                continue

            cur.execute(
                f"ALTER TABLE fire_service_intelligence ADD COLUMN {name} {definition}"
            )

            logger.info(
                "Added fire_service_intelligence column %s",
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

    def _ensure_communication_columns(self, cur):

        additions = {
            "communication_records": {
                "original_date_text": "TEXT",
                "normalized_date_utc": "TEXT",
                "source_file": "TEXT",
                "import_run_id": "INTEGER DEFAULT 0",
                "raw_record_json": "TEXT",
                "raw_engagement_json": "TEXT",
                "attachment_references_json": "TEXT",
                "original_platform": "TEXT",
                "import_status": "TEXT DEFAULT 'active'"
            },
            "communication_deliveries": {
                "source_file": "TEXT",
                "import_run_id": "INTEGER DEFAULT 0",
                "attachment_references_json": "TEXT",
                "media_matches_json": "TEXT",
                "match_confidence": "INTEGER DEFAULT 0",
                "original_platform": "TEXT"
            },
            "communication_editorial_intelligence": {
                "review_status": "TEXT DEFAULT 'needs_review'",
                "reviewer_notes": "TEXT",
                "reviewed_at": "TEXT"
            }
        }

        for table, columns_to_add in additions.items():
            cur.execute(f"PRAGMA table_info({table})")
            columns = {
                row[1]
                for row in cur.fetchall()
            }

            for name, definition in columns_to_add.items():
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

        cur.executescript("""
        CREATE TABLE IF NOT EXISTS communication_import_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_run_id INTEGER,
            communication_id INTEGER,
            delivery_id INTEGER,
            action TEXT,
            reason TEXT,
            details_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS communication_duplicate_reviews(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_run_id INTEGER,
            candidate_hash TEXT,
            incoming_summary TEXT,
            existing_communication_id INTEGER DEFAULT 0,
            duplicate_type TEXT,
            confidence INTEGER DEFAULT 0,
            reason TEXT,
            status TEXT DEFAULT 'needs_review',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS communication_media_references(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_run_id INTEGER,
            communication_id INTEGER,
            delivery_id INTEGER,
            reference_text TEXT,
            source_relative_path TEXT,
            matched_media_id INTEGER DEFAULT 0,
            match_confidence INTEGER DEFAULT 0,
            match_reason TEXT,
            status TEXT DEFAULT 'unmatched',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

    ############################################################

    def _ensure_indexes(self, cur):

        indexes = (
            "CREATE INDEX IF NOT EXISTS idx_media_filename ON media(filename)",
            "CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type)",
            "CREATE INDEX IF NOT EXISTS idx_media_path ON media(path)",
            "CREATE INDEX IF NOT EXISTS idx_media_first_seen ON media(first_seen_at)",
            "CREATE INDEX IF NOT EXISTS idx_media_date_added ON media(date_added)",
            "CREATE INDEX IF NOT EXISTS idx_media_capture_time ON media(capture_time)",
            "CREATE INDEX IF NOT EXISTS idx_media_file_modified ON media(file_modified_at)",
            "CREATE INDEX IF NOT EXISTS idx_video_intelligence_media ON video_intelligence(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_video_intelligence_review ON video_intelligence(review_state)",
            "CREATE INDEX IF NOT EXISTS idx_video_intelligence_reel ON video_intelligence(reel_potential)",
            "CREATE INDEX IF NOT EXISTS idx_video_intelligence_story ON video_intelligence(story_category)",
            "CREATE INDEX IF NOT EXISTS idx_ai_model ON ai_analysis(model)",
            "CREATE INDEX IF NOT EXISTS idx_ai_provider ON ai_analysis(provider)",
            "CREATE INDEX IF NOT EXISTS idx_ai_last_analyzed ON ai_analysis(last_analyzed)",
            "CREATE INDEX IF NOT EXISTS idx_ai_trust_state ON ai_analysis(trust_state)",
            "CREATE INDEX IF NOT EXISTS idx_ai_review_status ON ai_analysis(review_status)",
            "CREATE INDEX IF NOT EXISTS idx_ai_quality_state ON ai_analysis(quality_state)",
            "CREATE INDEX IF NOT EXISTS idx_ai_history_media ON ai_analysis_history(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_ai_history_saved ON ai_analysis_history(saved_at)",
            "CREATE INDEX IF NOT EXISTS idx_ai_history_provider ON ai_analysis_history(provider)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_review_media ON analysis_review_history(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_analysis_review_created ON analysis_review_history(created_at)",
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
            "CREATE INDEX IF NOT EXISTS idx_filesystem_media ON filesystem_intelligence(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_category ON filesystem_intelligence(root_category)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_subcategory ON filesystem_intelligence(subcategory)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_apparatus ON filesystem_intelligence(apparatus_identifier)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_incident ON filesystem_intelligence(incident_type)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_training ON filesystem_intelligence(training_type)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_program ON filesystem_intelligence(public_education_program)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_campaign ON filesystem_intelligence(campaign)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_conflict ON filesystem_intelligence(conflict_state)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_confidence ON filesystem_intelligence(filesystem_confidence)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_version ON filesystem_intelligence(enrichment_version)",
            "CREATE INDEX IF NOT EXISTS idx_filesystem_tags ON filesystem_intelligence(normalized_tags)",
            "CREATE INDEX IF NOT EXISTS idx_fire_service_media ON fire_service_intelligence(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_fire_service_incident ON fire_service_intelligence(incident_classification)",
            "CREATE INDEX IF NOT EXISTS idx_fire_service_activity ON fire_service_intelligence(operational_activity)",
            "CREATE INDEX IF NOT EXISTS idx_fire_service_group ON fire_service_intelligence(group_size)",
            "CREATE INDEX IF NOT EXISTS idx_fire_service_context ON fire_service_intelligence(operational_context)",
            "CREATE INDEX IF NOT EXISTS idx_fire_service_confidence ON fire_service_intelligence(operational_confidence)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_history_media ON recommendation_history(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_history_date ON recommendation_history(recommendation_date)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_history_opportunity ON recommendation_history(opportunity)",
            "CREATE INDEX IF NOT EXISTS idx_comm_package_history_package ON communication_package_history(package_id)",
            "CREATE INDEX IF NOT EXISTS idx_comm_package_history_recommendation ON communication_package_history(recommendation_id)",
            "CREATE INDEX IF NOT EXISTS idx_comm_package_history_created ON communication_package_history(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_comm_package_actions_package ON communication_package_asset_actions(package_id)",
            "CREATE INDEX IF NOT EXISTS idx_comm_package_actions_media ON communication_package_asset_actions(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_home_sessions_status ON home_sessions(status)",
            "CREATE INDEX IF NOT EXISTS idx_home_sessions_completed ON home_sessions(completed_at)",
            "CREATE INDEX IF NOT EXISTS idx_home_sessions_started ON home_sessions(started_at)",
            "CREATE INDEX IF NOT EXISTS idx_decision_audit_decision ON decision_audit_history(decision_id)",
            "CREATE INDEX IF NOT EXISTS idx_decision_audit_type_subject ON decision_audit_history(decision_type, subject_id)",
            "CREATE INDEX IF NOT EXISTS idx_decision_audit_generated ON decision_audit_history(generated_at)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_rec ON recommendation_feedback(recommendation_id)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_media ON recommendation_feedback(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_type ON recommendation_feedback(feedback_type)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_opportunity ON recommendation_feedback(opportunity_type)",
            "CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_created ON recommendation_feedback(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_media_corrections_media ON media_corrections(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_corrections_field ON media_corrections(field_name)",
            "CREATE INDEX IF NOT EXISTS idx_media_corrections_active ON media_corrections(active)",
            "CREATE INDEX IF NOT EXISTS idx_correction_history_media ON correction_history(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_correction_history_field ON correction_history(field_name)",
            "CREATE INDEX IF NOT EXISTS idx_correction_patterns_field ON correction_patterns(field_name)",
            "CREATE INDEX IF NOT EXISTS idx_correction_patterns_active ON correction_patterns(active)",
            "CREATE INDEX IF NOT EXISTS idx_apparatus_name ON apparatus(name)",
            "CREATE INDEX IF NOT EXISTS idx_programs_name ON programs(name)",
            "CREATE INDEX IF NOT EXISTS idx_annual_events_name ON annual_events(name)",
            "CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name)",
            "CREATE INDEX IF NOT EXISTS idx_response_area_name ON response_area(name)",
            "CREATE INDEX IF NOT EXISTS idx_community_partners_name ON community_partners(name)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_sha ON knowledge_documents(sha256)",
            "CREATE INDEX IF NOT EXISTS idx_entity_types_name ON entity_types(name)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_categories_name ON knowledge_categories(name)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_sources_name ON knowledge_sources(name)",
            "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",
            "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)",
            "CREATE INDEX IF NOT EXISTS idx_entities_active ON entities(active)",
            "CREATE INDEX IF NOT EXISTS idx_entity_aliases_alias ON entity_aliases(normalized_alias)",
            "CREATE INDEX IF NOT EXISTS idx_entity_aliases_entity ON entity_aliases(entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_entity_relationships_source ON entity_relationships(source_entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_entity_relationships_target ON entity_relationships(target_entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_entity_relationships_type ON entity_relationships(relationship_type)",
            "CREATE INDEX IF NOT EXISTS idx_content_templates_style ON content_templates(writing_style)",
            "CREATE INDEX IF NOT EXISTS idx_content_templates_platform ON content_templates(platform)",
            "CREATE INDEX IF NOT EXISTS idx_content_templates_active ON content_templates(active)",
            "CREATE INDEX IF NOT EXISTS idx_editorial_strategies_media ON editorial_strategies(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_editorial_strategies_type ON editorial_strategies(strategy_type)",
            "CREATE INDEX IF NOT EXISTS idx_editorial_strategies_confidence ON editorial_strategies(confidence)",
            "CREATE INDEX IF NOT EXISTS idx_editorial_strategies_selected ON editorial_strategies(selected)",
            "CREATE INDEX IF NOT EXISTS idx_editorial_strategies_dismissed ON editorial_strategies(dismissed)",
            "CREATE INDEX IF NOT EXISTS idx_editorial_comparisons_media ON editorial_comparisons(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON social_posts(platform)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_date ON social_posts(post_date)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_campaign ON social_posts(campaign)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_caption_hash ON social_posts(caption_hash)",
            "CREATE INDEX IF NOT EXISTS idx_social_posts_opportunity ON social_posts(opportunity_type)",
            "CREATE INDEX IF NOT EXISTS idx_media_usage_media ON media_usage(media_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_usage_post ON media_usage(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_usage_used_at ON media_usage(used_at)",
            "CREATE INDEX IF NOT EXISTS idx_writing_patterns_post ON writing_patterns(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_comm_intel_profile_key ON communications_intelligence_profiles(profile_type, profile_key)",
            "CREATE INDEX IF NOT EXISTS idx_comm_intel_profile_generated ON communications_intelligence_profiles(generated_at)",
            "CREATE INDEX IF NOT EXISTS idx_comm_edit_learning_platform ON communication_edit_learning(platform)",
            "CREATE INDEX IF NOT EXISTS idx_comm_edit_learning_created ON communication_edit_learning(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_hashtags_tag ON hashtags(tag)",
            "CREATE INDEX IF NOT EXISTS idx_hashtags_use_count ON hashtags(use_count)",
        ) + analysis_queue_indexes() + communication_indexes() + benchmark_indexes() + communication_learning_indexes()

        for statement in indexes:
            cur.execute(statement)
