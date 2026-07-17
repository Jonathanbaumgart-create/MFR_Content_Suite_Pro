def create_communication_learning_tables(cur):

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS communication_learning_records(
        learning_id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT,
        post_id TEXT,
        communication_id INTEGER DEFAULT 0,
        package_id TEXT,
        media_package_id TEXT,
        campaign TEXT,
        program TEXT,
        topic TEXT,
        publication_date TEXT,
        publication_time TEXT,
        imported_from TEXT,
        import_run_id INTEGER DEFAULT 0,
        metrics_json TEXT,
        derived_metrics_json TEXT,
        linked_media_json TEXT,
        linked_context_json TEXT,
        source_type TEXT,
        raw_record_json TEXT,
        content_hash TEXT UNIQUE,
        reviewed INTEGER DEFAULT 0,
        review_status TEXT DEFAULT 'unreviewed',
        anomaly INTEGER DEFAULT 0,
        exclude_from_learning INTEGER DEFAULT 0,
        boosted_post INTEGER DEFAULT 0,
        seasonal INTEGER DEFAULT 0,
        reviewer_notes TEXT,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS communication_learning_profiles(
        profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_type TEXT,
        profile_key TEXT,
        version TEXT,
        generated_at TEXT,
        sample_count INTEGER DEFAULT 0,
        confidence INTEGER DEFAULT 0,
        profile_json TEXT,
        source_summary_json TEXT
    );

    CREATE TABLE IF NOT EXISTS communication_learning_summary(
        summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT,
        generated_at TEXT,
        sample_count INTEGER DEFAULT 0,
        summary_json TEXT,
        confidence INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS communication_performance_metrics(
        metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
        learning_id INTEGER,
        metric_name TEXT,
        metric_value REAL DEFAULT 0,
        confidence INTEGER DEFAULT 0,
        limitations TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS communication_learning_import_runs(
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

    CREATE TABLE IF NOT EXISTS communication_experiments(
        experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        hypothesis TEXT,
        expected_outcome TEXT,
        actual_outcome TEXT,
        lesson_learned TEXT,
        target_platform TEXT,
        target_campaign TEXT,
        topic TEXT,
        experiment_type TEXT,
        test_date TEXT,
        status TEXT DEFAULT 'planned',
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS communication_learning_versions(
        version_id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT,
        description TEXT,
        created_at TEXT
    );
    """)


def communication_learning_indexes():

    return (
        "CREATE INDEX IF NOT EXISTS idx_learning_records_platform ON communication_learning_records(platform)",
        "CREATE INDEX IF NOT EXISTS idx_learning_records_post ON communication_learning_records(post_id)",
        "CREATE INDEX IF NOT EXISTS idx_learning_records_comm ON communication_learning_records(communication_id)",
        "CREATE INDEX IF NOT EXISTS idx_learning_records_package ON communication_learning_records(package_id)",
        "CREATE INDEX IF NOT EXISTS idx_learning_records_campaign ON communication_learning_records(campaign)",
        "CREATE INDEX IF NOT EXISTS idx_learning_records_topic ON communication_learning_records(topic)",
        "CREATE INDEX IF NOT EXISTS idx_learning_records_date ON communication_learning_records(publication_date)",
        "CREATE INDEX IF NOT EXISTS idx_learning_records_import ON communication_learning_records(import_run_id)",
        "CREATE INDEX IF NOT EXISTS idx_learning_records_hash ON communication_learning_records(content_hash)",
        "CREATE INDEX IF NOT EXISTS idx_learning_profiles_key ON communication_learning_profiles(profile_type, profile_key)",
        "CREATE INDEX IF NOT EXISTS idx_learning_profiles_generated ON communication_learning_profiles(generated_at)",
        "CREATE INDEX IF NOT EXISTS idx_learning_summary_generated ON communication_learning_summary(generated_at)",
        "CREATE INDEX IF NOT EXISTS idx_learning_metrics_record ON communication_performance_metrics(learning_id)",
        "CREATE INDEX IF NOT EXISTS idx_learning_metrics_name ON communication_performance_metrics(metric_name)",
        "CREATE INDEX IF NOT EXISTS idx_learning_import_started ON communication_learning_import_runs(started_at)",
        "CREATE INDEX IF NOT EXISTS idx_learning_experiments_topic ON communication_experiments(topic)",
        "CREATE INDEX IF NOT EXISTS idx_learning_experiments_status ON communication_experiments(status)"
    )
