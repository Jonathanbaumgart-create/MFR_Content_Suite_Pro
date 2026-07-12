def create_communication_tables(cur):

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS communication_records(
        communication_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        original_text TEXT,
        summary TEXT,
        original_date TEXT,
        source_type TEXT,
        source_identifier TEXT,
        imported_from TEXT,
        imported_at TEXT,
        content_hash TEXT UNIQUE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS communication_deliveries(
        delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
        communication_id INTEGER,
        platform TEXT,
        published_at TEXT,
        platform_post_id TEXT,
        permalink TEXT,
        delivery_text TEXT,
        media_count INTEGER DEFAULT 0,
        photo_count INTEGER DEFAULT 0,
        video_count INTEGER DEFAULT 0,
        engagement_metrics TEXT,
        imported_at TEXT,
        delivery_hash TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS communication_editorial_intelligence(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        communication_id INTEGER,
        primary_story TEXT,
        editorial_angle TEXT,
        communication_purpose TEXT,
        category TEXT,
        intended_audiences TEXT,
        topics TEXT,
        programs TEXT,
        campaigns TEXT,
        seasonal_relevance TEXT,
        educational_value INTEGER DEFAULT 0,
        recruitment_value INTEGER DEFAULT 0,
        preparedness_value INTEGER DEFAULT 0,
        operational_value INTEGER DEFAULT 0,
        community_trust_value INTEGER DEFAULT 0,
        historical_value INTEGER DEFAULT 0,
        human_interest_value INTEGER DEFAULT 0,
        evergreen_value INTEGER DEFAULT 0,
        confidence_score INTEGER DEFAULT 0,
        source_signals TEXT,
        analysis_version TEXT,
        generated_at TEXT,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS communication_intelligence_corrections(
        correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        communication_id INTEGER,
        field_name TEXT,
        original_value TEXT,
        corrected_value TEXT,
        correction_source TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS communication_campaigns(
        campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        description TEXT,
        active_years TEXT,
        recurring_months TEXT,
        goals TEXT,
        audiences TEXT,
        associated_program_ids TEXT,
        editorial_angles TEXT,
        topics TEXT,
        partner_organizations TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS communication_programs(
        program_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        description TEXT,
        typical_audiences TEXT,
        typical_topics TEXT,
        associated_campaign_ids TEXT,
        associated_partner_ids TEXT,
        seasonal_pattern TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS communication_campaign_links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        communication_id INTEGER,
        campaign_id INTEGER,
        evidence TEXT,
        confidence INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(communication_id, campaign_id)
    );

    CREATE TABLE IF NOT EXISTS communication_program_links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        communication_id INTEGER,
        program_id INTEGER,
        evidence TEXT,
        confidence INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(communication_id, program_id)
    );

    CREATE TABLE IF NOT EXISTS communication_topic_links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        communication_id INTEGER,
        topic TEXT,
        evidence TEXT,
        confidence INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(communication_id, topic)
    );

    CREATE TABLE IF NOT EXISTS communication_outcomes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        communication_id INTEGER,
        engagement_assessment TEXT,
        educational_strength INTEGER DEFAULT 0,
        recruitment_strength INTEGER DEFAULT 0,
        community_trust_strength INTEGER DEFAULT 0,
        preparedness_strength INTEGER DEFAULT 0,
        historical_value INTEGER DEFAULT 0,
        evergreen_status TEXT,
        recommended_repeat_interval_days INTEGER DEFAULT 0,
        should_repeat INTEGER DEFAULT 0,
        editorial_success_notes TEXT,
        confidence_score INTEGER DEFAULT 0,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS communication_import_runs(
        import_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT,
        source_name TEXT,
        started_at TEXT,
        completed_at TEXT,
        records_processed INTEGER DEFAULT 0,
        records_inserted INTEGER DEFAULT 0,
        deliveries_inserted INTEGER DEFAULT 0,
        duplicates_skipped INTEGER DEFAULT 0,
        records_failed INTEGER DEFAULT 0,
        campaigns_detected TEXT,
        programs_detected TEXT,
        topics_extracted TEXT,
        warnings TEXT,
        status TEXT,
        duration_seconds REAL DEFAULT 0
    );
    """)


def communication_indexes():

    return (
        "CREATE INDEX IF NOT EXISTS idx_comm_records_date ON communication_records(original_date)",
        "CREATE INDEX IF NOT EXISTS idx_comm_records_hash ON communication_records(content_hash)",
        "CREATE INDEX IF NOT EXISTS idx_comm_records_source ON communication_records(source_identifier)",
        "CREATE INDEX IF NOT EXISTS idx_comm_deliveries_comm ON communication_deliveries(communication_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_deliveries_platform ON communication_deliveries(platform)",
        "CREATE INDEX IF NOT EXISTS idx_comm_deliveries_published ON communication_deliveries(published_at)",
        "CREATE INDEX IF NOT EXISTS idx_comm_deliveries_post_id ON communication_deliveries(platform_post_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_editorial_comm ON communication_editorial_intelligence(communication_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_editorial_category ON communication_editorial_intelligence(category)",
        "CREATE INDEX IF NOT EXISTS idx_comm_editorial_angle ON communication_editorial_intelligence(editorial_angle)",
        "CREATE INDEX IF NOT EXISTS idx_comm_editorial_active ON communication_editorial_intelligence(active)",
        "CREATE INDEX IF NOT EXISTS idx_comm_corrections_comm ON communication_intelligence_corrections(communication_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_corrections_active ON communication_intelligence_corrections(active)",
        "CREATE INDEX IF NOT EXISTS idx_comm_campaigns_name ON communication_campaigns(name)",
        "CREATE INDEX IF NOT EXISTS idx_comm_programs_name ON communication_programs(name)",
        "CREATE INDEX IF NOT EXISTS idx_comm_campaign_links_comm ON communication_campaign_links(communication_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_campaign_links_campaign ON communication_campaign_links(campaign_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_program_links_comm ON communication_program_links(communication_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_program_links_program ON communication_program_links(program_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_topic_links_topic ON communication_topic_links(topic)",
        "CREATE INDEX IF NOT EXISTS idx_comm_topic_links_comm ON communication_topic_links(communication_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_outcomes_comm ON communication_outcomes(communication_id)",
        "CREATE INDEX IF NOT EXISTS idx_comm_import_runs_started ON communication_import_runs(started_at)"
    )
