def create_benchmark_tables(cur):

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS benchmark_departments(
        department_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        region TEXT,
        country TEXT,
        notes TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS benchmark_import_runs(
        import_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT,
        source_file TEXT,
        started_at TEXT,
        completed_at TEXT,
        records_processed INTEGER DEFAULT 0,
        records_inserted INTEGER DEFAULT 0,
        duplicates_skipped INTEGER DEFAULT 0,
        invalid_records INTEGER DEFAULT 0,
        warnings_json TEXT,
        status TEXT,
        duration_seconds REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS benchmark_records(
        benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_id INTEGER,
        source_department TEXT,
        source_platform TEXT,
        source_date_text TEXT,
        source_date_utc TEXT,
        source_url TEXT,
        source_identifier TEXT,
        source_file TEXT,
        import_run_id INTEGER DEFAULT 0,
        headline TEXT,
        original_text TEXT,
        normalized_analysis_json TEXT,
        media_type TEXT,
        photo_count INTEGER DEFAULT 0,
        video_count INTEGER DEFAULT 0,
        reel_indicator INTEGER DEFAULT 0,
        duration_seconds REAL DEFAULT 0,
        raw_engagement_json TEXT,
        engagement_available INTEGER DEFAULT 0,
        engagement_status TEXT,
        engagement_indicator REAL DEFAULT 0,
        hashtags_json TEXT,
        cta TEXT,
        campaign TEXT,
        topic TEXT,
        audience TEXT,
        editorial_angle TEXT,
        raw_metadata_json TEXT,
        reviewed INTEGER DEFAULT 0,
        review_status TEXT DEFAULT 'unreviewed',
        applicability TEXT,
        copyright_status TEXT,
        content_hash TEXT UNIQUE,
        imported_at TEXT,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS benchmark_patterns(
        pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_key TEXT,
        pattern_type TEXT,
        title TEXT,
        description TEXT,
        source_department TEXT,
        source_platform TEXT,
        topic TEXT,
        editorial_angle TEXT,
        media_type TEXT,
        reel_pattern INTEGER DEFAULT 0,
        evidence_count INTEGER DEFAULT 0,
        benchmark_ids_json TEXT,
        engagement_basis TEXT,
        applicability TEXT,
        applicability_reason TEXT,
        adaptation_notes TEXT,
        limitations TEXT,
        human_status TEXT DEFAULT 'unreviewed',
        reviewer_notes TEXT,
        saved_for_testing INTEGER DEFAULT 0,
        linked_mfr_campaign TEXT,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS benchmark_experiments(
        experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pattern_id INTEGER,
        mfr_adaptation TEXT,
        target_platform TEXT,
        target_campaign TEXT,
        test_date TEXT,
        expected_outcome TEXT,
        actual_outcome TEXT,
        lesson_learned TEXT,
        status TEXT DEFAULT 'planned',
        created_at TEXT,
        updated_at TEXT
    );
    """)


def benchmark_indexes():

    return (
        "CREATE INDEX IF NOT EXISTS idx_benchmark_dept_name ON benchmark_departments(name)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_dept ON benchmark_records(department_id)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_platform ON benchmark_records(source_platform)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_date ON benchmark_records(source_date_utc)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_media ON benchmark_records(media_type)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_topic ON benchmark_records(topic)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_campaign ON benchmark_records(campaign)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_angle ON benchmark_records(editorial_angle)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_reel ON benchmark_records(reel_indicator)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_review ON benchmark_records(review_status)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_applicability ON benchmark_records(applicability)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_import ON benchmark_records(import_run_id)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_records_hash ON benchmark_records(content_hash)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_patterns_type ON benchmark_patterns(pattern_type)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_patterns_topic ON benchmark_patterns(topic)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_patterns_app ON benchmark_patterns(applicability)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_patterns_status ON benchmark_patterns(human_status)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_experiments_pattern ON benchmark_experiments(pattern_id)"
    )
