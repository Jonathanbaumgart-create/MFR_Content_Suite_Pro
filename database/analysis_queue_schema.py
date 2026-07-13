def create_analysis_queue_tables(cur):

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS analysis_sessions(
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT,
        scope TEXT,
        provider TEXT,
        model TEXT,
        settings_json TEXT,
        total_items INTEGER DEFAULT 0,
        queued_count INTEGER DEFAULT 0,
        completed_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        skipped_count INTEGER DEFAULT 0,
        retry_pending_count INTEGER DEFAULT 0,
        current_media_id INTEGER,
        current_filename TEXT,
        started_at TEXT,
        finished_at TEXT,
        created_at TEXT,
        updated_at TEXT,
        elapsed_seconds REAL DEFAULT 0,
        average_seconds_per_item REAL DEFAULT 0,
        throughput_per_hour REAL DEFAULT 0,
        estimated_remaining_seconds REAL DEFAULT 0,
        cancel_reason TEXT
    );

    CREATE TABLE IF NOT EXISTS analysis_queue(
        queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        media_id INTEGER,
        filename TEXT,
        path TEXT,
        media_type TEXT,
        state TEXT,
        priority INTEGER DEFAULT 0,
        priority_reason TEXT,
        attempts INTEGER DEFAULT 0,
        force INTEGER DEFAULT 0,
        provider TEXT,
        model TEXT,
        failure_category TEXT,
        failure_reason TEXT,
        queued_at TEXT,
        started_at TEXT,
        completed_at TEXT,
        updated_at TEXT,
        analysis_duration REAL DEFAULT 0,
        provider_latency REAL DEFAULT 0,
        db_write_duration REAL DEFAULT 0,
        queue_wait_seconds REAL DEFAULT 0,
        UNIQUE(session_id, media_id)
    );
    """)


def analysis_queue_indexes():

    return (
        "CREATE INDEX IF NOT EXISTS idx_analysis_sessions_status ON analysis_sessions(status)",
        "CREATE INDEX IF NOT EXISTS idx_analysis_sessions_created ON analysis_sessions(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_analysis_sessions_provider ON analysis_sessions(provider)",
        "CREATE INDEX IF NOT EXISTS idx_analysis_queue_session ON analysis_queue(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_analysis_queue_media ON analysis_queue(media_id)",
        "CREATE INDEX IF NOT EXISTS idx_analysis_queue_state ON analysis_queue(state)",
        "CREATE INDEX IF NOT EXISTS idx_analysis_queue_updated ON analysis_queue(updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_analysis_queue_failure ON analysis_queue(failure_category)"
    )
