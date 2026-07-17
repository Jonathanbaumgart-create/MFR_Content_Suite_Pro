import json
import sqlite3


class CommunicationLearningRepository:

    def __init__(self, database):

        self.database = database

    ############################################################

    def create_import_run(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_learning_import_runs(
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
        import_run_id = cur.lastrowid
        conn.commit()
        conn.close()
        return import_run_id

    def update_import_run(self, import_run_id, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE communication_learning_import_runs
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
            "SELECT learning_id FROM communication_learning_records WHERE content_hash=?",
            (record.get("content_hash", ""),)
        )
        existing = cur.fetchone()

        if existing:
            conn.close()
            return {
                "learning_id": existing[0],
                "inserted": False
            }

        cur.execute("""
        INSERT INTO communication_learning_records(
            platform,
            post_id,
            communication_id,
            package_id,
            media_package_id,
            campaign,
            program,
            topic,
            publication_date,
            publication_time,
            imported_from,
            import_run_id,
            metrics_json,
            derived_metrics_json,
            linked_media_json,
            linked_context_json,
            source_type,
            raw_record_json,
            content_hash,
            reviewed,
            review_status,
            anomaly,
            exclude_from_learning,
            boosted_post,
            seasonal,
            reviewer_notes,
            created_at,
            updated_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            record.get("platform", ""),
            record.get("post_id", ""),
            self._to_int(record.get("communication_id")),
            record.get("package_id", ""),
            record.get("media_package_id", ""),
            record.get("campaign", ""),
            record.get("program", ""),
            record.get("topic", ""),
            record.get("publication_date", ""),
            record.get("publication_time", ""),
            record.get("imported_from", ""),
            self._to_int(record.get("import_run_id")),
            self._to_json(record.get("metrics", {})),
            self._to_json(record.get("derived_metrics", {})),
            self._to_json(record.get("linked_media", [])),
            self._to_json(record.get("linked_context", {})),
            record.get("source_type", ""),
            self._to_json(record.get("raw_record", {})),
            record.get("content_hash", ""),
            1 if record.get("reviewed") else 0,
            record.get("review_status", "unreviewed"),
            1 if record.get("anomaly") else 0,
            1 if record.get("exclude_from_learning") else 0,
            1 if record.get("boosted_post") else 0,
            1 if record.get("seasonal") else 0,
            record.get("reviewer_notes", ""),
            record.get("created_at", ""),
            record.get("updated_at", "")
        ))
        learning_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {
            "learning_id": learning_id,
            "inserted": True
        }

    ############################################################

    def records(self, filters=None, limit=500):

        filters = filters or {}
        clauses = ["1=1"]
        params = []

        for key, column in (
            ("platform", "platform"),
            ("campaign", "campaign"),
            ("topic", "topic"),
            ("review_status", "review_status")
        ):
            value = str(filters.get(key) or "").strip()
            if value:
                clauses.append(f"{column}=?")
                params.append(value)

        if not filters.get("include_excluded"):
            clauses.append("exclude_from_learning=0")

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""
            SELECT *
            FROM communication_learning_records
            WHERE {' AND '.join(clauses)}
            ORDER BY publication_date DESC, learning_id DESC
            LIMIT ?
            """,
            params + [self._to_int(limit)]
        ).fetchall()
        conn.close()
        return [self._record_from_row(row) for row in rows]

    def save_profile(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_learning_profiles(
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
        """,
        (
            item.get("profile_type", ""),
            item.get("profile_key", ""),
            item.get("version", ""),
            item.get("generated_at", ""),
            self._to_int(item.get("sample_count")),
            self._to_int(item.get("confidence")),
            self._to_json(item.get("profile", {})),
            self._to_json(item.get("source_summary", {}))
        ))
        profile_id = cur.lastrowid
        conn.commit()
        conn.close()
        return profile_id

    def save_summary(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_learning_summary(
            version,
            generated_at,
            sample_count,
            summary_json,
            confidence
        )
        VALUES(?,?,?,?,?)
        """,
        (
            item.get("version", ""),
            item.get("generated_at", ""),
            self._to_int(item.get("sample_count")),
            self._to_json(item.get("summary", {})),
            self._to_int(item.get("confidence"))
        ))
        summary_id = cur.lastrowid
        conn.commit()
        conn.close()
        return summary_id

    def latest_summary(self):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT *
            FROM communication_learning_summary
            ORDER BY summary_id DESC
            LIMIT 1
        """).fetchone()
        conn.close()

        if not row:
            return {}

        return {
            "summary_id": row["summary_id"],
            "version": row["version"],
            "generated_at": row["generated_at"],
            "sample_count": row["sample_count"],
            "confidence": row["confidence"],
            "summary": self._from_json(row["summary_json"])
        }

    ############################################################

    def review_record(self, learning_id, updates):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE communication_learning_records
        SET reviewed=1,
            review_status=?,
            anomaly=?,
            exclude_from_learning=?,
            boosted_post=?,
            seasonal=?,
            reviewer_notes=?,
            updated_at=?
        WHERE learning_id=?
        """,
        (
            updates.get("review_status", "reviewed"),
            1 if updates.get("anomaly") else 0,
            1 if updates.get("exclude_from_learning") else 0,
            1 if updates.get("boosted_post") else 0,
            1 if updates.get("seasonal") else 0,
            updates.get("reviewer_notes", ""),
            updates.get("updated_at", ""),
            self._to_int(learning_id)
        ))
        conn.commit()
        conn.close()

    def save_experiment(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_experiments(
            hypothesis,
            expected_outcome,
            actual_outcome,
            lesson_learned,
            target_platform,
            target_campaign,
            topic,
            experiment_type,
            test_date,
            status,
            created_at,
            updated_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            item.get("hypothesis", ""),
            item.get("expected_outcome", ""),
            item.get("actual_outcome", ""),
            item.get("lesson_learned", ""),
            item.get("target_platform", ""),
            item.get("target_campaign", ""),
            item.get("topic", ""),
            item.get("experiment_type", ""),
            item.get("test_date", ""),
            item.get("status", "planned"),
            item.get("created_at", ""),
            item.get("updated_at", "")
        ))
        experiment_id = cur.lastrowid
        conn.commit()
        conn.close()
        return experiment_id

    def experiments(self, limit=25):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT *
            FROM communication_experiments
            ORDER BY experiment_id DESC
            LIMIT ?
        """, (self._to_int(limit),)).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    ############################################################

    def _record_from_row(self, row):

        result = dict(row)
        result["metrics"] = self._from_json(row["metrics_json"])
        result["derived_metrics"] = self._from_json(row["derived_metrics_json"])
        result["linked_media"] = self._from_json(row["linked_media_json"])
        result["linked_context"] = self._from_json(row["linked_context_json"])
        result["raw_record"] = self._from_json(row["raw_record_json"])
        return result

    def _to_json(self, value):

        return json.dumps(value if value is not None else {})

    def _from_json(self, value):

        if not value:
            return {}

        try:
            return json.loads(value)
        except Exception:
            return {}

    def _to_int(self, value):

        try:
            return int(value or 0)
        except Exception:
            return 0
