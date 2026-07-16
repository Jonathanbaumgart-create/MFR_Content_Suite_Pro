import json
import sqlite3


class BenchmarkRepository:

    def __init__(self, database):

        self.database = database

    ############################################################

    def save_department(self, item):

        name = str(item.get("name") or "").strip()

        if not name:
            return 0

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT OR IGNORE INTO benchmark_departments(
            name,
            region,
            country,
            notes,
            created_at,
            updated_at
        )
        VALUES(?,?,?,?,?,?)
        """,
        (
            name,
            item.get("region", ""),
            item.get("country", ""),
            item.get("notes", ""),
            item.get("created_at", ""),
            item.get("updated_at", "")
        ))
        cur.execute(
            "SELECT department_id FROM benchmark_departments WHERE name=?",
            (name,)
        )
        row = cur.fetchone()
        conn.commit()
        conn.close()

        return row[0] if row else 0

    ############################################################

    def create_import_run(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO benchmark_import_runs(
            source_type,
            source_file,
            started_at,
            warnings_json,
            status
        )
        VALUES(?,?,?,?,?)
        """,
        (
            item.get("source_type", ""),
            item.get("source_file", ""),
            item.get("started_at", ""),
            self._to_json(item.get("warnings", [])),
            item.get("status", "running")
        ))
        run_id = cur.lastrowid
        conn.commit()
        conn.close()
        return run_id

    def update_import_run(self, import_run_id, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE benchmark_import_runs
        SET completed_at=?,
            records_processed=?,
            records_inserted=?,
            duplicates_skipped=?,
            invalid_records=?,
            warnings_json=?,
            status=?,
            duration_seconds=?
        WHERE import_run_id=?
        """,
        (
            item.get("completed_at", ""),
            self._to_int(item.get("records_processed")),
            self._to_int(item.get("records_inserted")),
            self._to_int(item.get("duplicates_skipped")),
            self._to_int(item.get("invalid_records")),
            self._to_json(item.get("warnings", [])),
            item.get("status", ""),
            float(item.get("duration_seconds") or 0),
            self._to_int(import_run_id)
        ))
        conn.commit()
        conn.close()

    ############################################################

    def save_record(self, record):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT benchmark_id FROM benchmark_records WHERE content_hash=?",
            (record.get("content_hash", ""),)
        )
        existing = cur.fetchone()

        if existing:
            conn.close()
            return {
                "benchmark_id": existing[0],
                "inserted": False
            }

        cur.execute("""
        INSERT INTO benchmark_records(
            department_id,
            source_department,
            source_platform,
            source_date_text,
            source_date_utc,
            source_url,
            source_identifier,
            source_file,
            import_run_id,
            headline,
            original_text,
            normalized_analysis_json,
            media_type,
            photo_count,
            video_count,
            reel_indicator,
            duration_seconds,
            raw_engagement_json,
            engagement_available,
            engagement_status,
            engagement_indicator,
            hashtags_json,
            cta,
            campaign,
            topic,
            audience,
            editorial_angle,
            raw_metadata_json,
            reviewed,
            review_status,
            applicability,
            copyright_status,
            content_hash,
            imported_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            self._to_int(record.get("department_id")),
            record.get("source_department", ""),
            record.get("source_platform", ""),
            record.get("source_date_text", ""),
            record.get("source_date_utc", ""),
            record.get("source_url", ""),
            record.get("source_identifier", ""),
            record.get("source_file", ""),
            self._to_int(record.get("import_run_id")),
            record.get("headline", ""),
            record.get("original_text", ""),
            self._to_json(record.get("normalized_analysis", {})),
            record.get("media_type", ""),
            self._to_int(record.get("photo_count")),
            self._to_int(record.get("video_count")),
            1 if record.get("reel_indicator") else 0,
            float(record.get("duration_seconds") or 0),
            self._to_json(record.get("raw_engagement", {})),
            1 if record.get("engagement_available") else 0,
            record.get("engagement_status", ""),
            float(record.get("engagement_indicator") or 0),
            self._to_json(record.get("hashtags", [])),
            record.get("cta", ""),
            record.get("campaign", ""),
            record.get("topic", ""),
            record.get("audience", ""),
            record.get("editorial_angle", ""),
            self._to_json(record.get("raw_metadata", {})),
            1 if record.get("reviewed") else 0,
            record.get("review_status", "unreviewed"),
            record.get("applicability", ""),
            record.get("copyright_status", ""),
            record.get("content_hash", ""),
            record.get("imported_at", "")
        ))
        benchmark_id = cur.lastrowid
        conn.commit()
        conn.close()

        return {
            "benchmark_id": benchmark_id,
            "inserted": True
        }

    ############################################################

    def save_pattern(self, pattern):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO benchmark_patterns(
            pattern_key,
            pattern_type,
            title,
            description,
            source_department,
            source_platform,
            topic,
            editorial_angle,
            media_type,
            reel_pattern,
            evidence_count,
            benchmark_ids_json,
            engagement_basis,
            applicability,
            applicability_reason,
            adaptation_notes,
            limitations,
            human_status,
            reviewer_notes,
            saved_for_testing,
            linked_mfr_campaign,
            created_at,
            updated_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            pattern.get("pattern_key", ""),
            pattern.get("pattern_type", ""),
            pattern.get("title", ""),
            pattern.get("description", ""),
            pattern.get("source_department", ""),
            pattern.get("source_platform", ""),
            pattern.get("topic", ""),
            pattern.get("editorial_angle", ""),
            pattern.get("media_type", ""),
            1 if pattern.get("reel_pattern") else 0,
            self._to_int(pattern.get("evidence_count")),
            self._to_json(pattern.get("benchmark_ids", [])),
            pattern.get("engagement_basis", ""),
            pattern.get("applicability", ""),
            pattern.get("applicability_reason", ""),
            pattern.get("adaptation_notes", ""),
            pattern.get("limitations", ""),
            pattern.get("human_status", "unreviewed"),
            pattern.get("reviewer_notes", ""),
            1 if pattern.get("saved_for_testing") else 0,
            pattern.get("linked_mfr_campaign", ""),
            pattern.get("created_at", ""),
            pattern.get("updated_at", "")
        ))
        pattern_id = cur.lastrowid
        conn.commit()
        conn.close()
        return pattern_id

    ############################################################

    def records(self, filters=None, limit=100, offset=0):

        filters = filters or {}
        clauses = ["active=1"]
        params = []

        for key, column in (
            ("department", "source_department"),
            ("platform", "source_platform"),
            ("media_type", "media_type"),
            ("topic", "topic"),
            ("campaign", "campaign"),
            ("editorial_angle", "editorial_angle"),
            ("applicability", "applicability")
        ):
            value = str(filters.get(key) or "").strip()
            if value:
                clauses.append(f"{column}=?")
                params.append(value)

        if filters.get("reel"):
            clauses.append("reel_indicator=1")

        if filters.get("engagement_available"):
            clauses.append("engagement_available=1")

        if filters.get("reviewed"):
            clauses.append("reviewed=1")

        search = str(filters.get("search") or "").strip()
        if search:
            clauses.append("(original_text LIKE ? OR headline LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        sql = f"""
        SELECT *
        FROM benchmark_records
        WHERE {' AND '.join(clauses)}
        ORDER BY source_date_utc DESC, benchmark_id DESC
        LIMIT ? OFFSET ?
        """
        params.extend([
            self._to_int(limit),
            self._to_int(offset)
        ])
        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [self._record_from_row(row) for row in rows]

    def patterns(self, filters=None, limit=50):

        filters = filters or {}
        clauses = ["1=1"]
        params = []

        for key, column in (
            ("topic", "topic"),
            ("pattern_type", "pattern_type"),
            ("applicability", "applicability"),
            ("human_status", "human_status")
        ):
            value = str(filters.get(key) or "").strip()
            if value:
                clauses.append(f"{column}=?")
                params.append(value)

        if filters.get("reel"):
            clauses.append("reel_pattern=1")

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT *
            FROM benchmark_patterns
            WHERE {' AND '.join(clauses)}
            ORDER BY evidence_count DESC, pattern_id DESC
            LIMIT ?
            """,
            params + [self._to_int(limit)]
        ).fetchall()
        conn.close()
        return [self._pattern_from_row(row) for row in rows]

    def insights(self):

        conn = self.database.connection()
        cur = conn.cursor()

        def grouped(sql):
            return [
                {
                    "label": row[0] or "unknown",
                    "count": row[1]
                }
                for row in cur.execute(sql).fetchall()
            ]

        result = {
            "records": cur.execute(
                "SELECT COUNT(*) FROM benchmark_records WHERE active=1"
            ).fetchone()[0],
            "departments": cur.execute(
                "SELECT COUNT(DISTINCT source_department) FROM benchmark_records WHERE active=1"
            ).fetchone()[0],
            "platforms": grouped(
                "SELECT source_platform, COUNT(*) FROM benchmark_records WHERE active=1 GROUP BY source_platform ORDER BY COUNT(*) DESC LIMIT 8"
            ),
            "topics": grouped(
                "SELECT topic, COUNT(*) FROM benchmark_records WHERE active=1 GROUP BY topic ORDER BY COUNT(*) DESC LIMIT 8"
            ),
            "campaigns": grouped(
                "SELECT campaign, COUNT(*) FROM benchmark_records WHERE active=1 AND campaign!='' GROUP BY campaign ORDER BY COUNT(*) DESC LIMIT 8"
            ),
            "formats": grouped(
                "SELECT editorial_angle, COUNT(*) FROM benchmark_records WHERE active=1 GROUP BY editorial_angle ORDER BY COUNT(*) DESC LIMIT 8"
            ),
            "media_types": grouped(
                "SELECT media_type, COUNT(*) FROM benchmark_records WHERE active=1 GROUP BY media_type ORDER BY COUNT(*) DESC"
            ),
            "reel_records": cur.execute(
                "SELECT COUNT(*) FROM benchmark_records WHERE active=1 AND reel_indicator=1"
            ).fetchone()[0],
            "engagement_available": cur.execute(
                "SELECT COUNT(*) FROM benchmark_records WHERE active=1 AND engagement_available=1"
            ).fetchone()[0],
            "applicability": grouped(
                "SELECT applicability, COUNT(*) FROM benchmark_records WHERE active=1 GROUP BY applicability ORDER BY COUNT(*) DESC"
            ),
            "patterns": cur.execute(
                "SELECT COUNT(*) FROM benchmark_patterns"
            ).fetchone()[0]
        }
        conn.close()
        return result

    ############################################################

    def review_pattern(self, pattern_id, updates):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE benchmark_patterns
        SET human_status=?,
            applicability=?,
            reviewer_notes=?,
            adaptation_notes=?,
            saved_for_testing=?,
            linked_mfr_campaign=?,
            updated_at=?
        WHERE pattern_id=?
        """,
        (
            updates.get("human_status", "reviewed"),
            updates.get("applicability", ""),
            updates.get("reviewer_notes", ""),
            updates.get("adaptation_notes", ""),
            1 if updates.get("saved_for_testing") else 0,
            updates.get("linked_mfr_campaign", ""),
            updates.get("updated_at", ""),
            self._to_int(pattern_id)
        ))
        conn.commit()
        conn.close()

    def save_experiment(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO benchmark_experiments(
            pattern_id,
            mfr_adaptation,
            target_platform,
            target_campaign,
            test_date,
            expected_outcome,
            actual_outcome,
            lesson_learned,
            status,
            created_at,
            updated_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            self._to_int(item.get("pattern_id")),
            item.get("mfr_adaptation", ""),
            item.get("target_platform", ""),
            item.get("target_campaign", ""),
            item.get("test_date", ""),
            item.get("expected_outcome", ""),
            item.get("actual_outcome", ""),
            item.get("lesson_learned", ""),
            item.get("status", "planned"),
            item.get("created_at", ""),
            item.get("updated_at", "")
        ))
        experiment_id = cur.lastrowid
        conn.commit()
        conn.close()
        return experiment_id

    def rollback_import_run(self, import_run_id):

        import_run_id = self._to_int(import_run_id)
        conn = self.database.connection()
        cur = conn.cursor()
        count = cur.execute(
            "SELECT COUNT(*) FROM benchmark_records WHERE import_run_id=?",
            (import_run_id,)
        ).fetchone()[0]
        cur.execute(
            "DELETE FROM benchmark_records WHERE import_run_id=?",
            (import_run_id,)
        )
        cur.execute(
            "UPDATE benchmark_import_runs SET status='rolled_back' WHERE import_run_id=?",
            (import_run_id,)
        )
        conn.commit()
        conn.close()
        return count

    ############################################################

    def _record_from_row(self, row):

        return {
            key: row[key]
            for key in row.keys()
        } | {
            "normalized_analysis": self._from_json(row["normalized_analysis_json"]),
            "raw_engagement": self._from_json(row["raw_engagement_json"]),
            "hashtags": self._from_json(row["hashtags_json"]),
            "raw_metadata": self._from_json(row["raw_metadata_json"])
        }

    def _pattern_from_row(self, row):

        return {
            key: row[key]
            for key in row.keys()
        } | {
            "benchmark_ids": self._from_json(row["benchmark_ids_json"])
        }

    def _to_json(self, value):

        return json.dumps(value if value is not None else [])

    def _from_json(self, value):

        if not value:
            return [] if value == "" else {}

        try:
            return json.loads(value)
        except Exception:
            return {}

    def _to_int(self, value):

        try:
            return int(value or 0)
        except Exception:
            return 0
