import sqlite3


class CommunicationRepository:

    def __init__(self, database):

        self.database = database

    ############################################################

    def save_communication_record(self, record):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT communication_id FROM communication_records WHERE content_hash=?",
            (
                record.get("content_hash", ""),
            )
        )
        existing = cur.fetchone()

        if existing:
            conn.close()

            return {
                "communication_id": existing[0],
                "inserted": False
            }

        cur.execute("""
        INSERT INTO communication_records(
            title,
            original_text,
            summary,
            original_date,
            original_date_text,
            normalized_date_utc,
            source_type,
            source_identifier,
            imported_from,
            source_file,
            import_run_id,
            raw_record_json,
            raw_engagement_json,
            attachment_references_json,
            original_platform,
            import_status,
            imported_at,
            content_hash,
            notes
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            record.get("title", ""),
            record.get("original_text", ""),
            record.get("summary", ""),
            record.get("original_date", ""),
            record.get("original_date_text", ""),
            record.get("normalized_date_utc", record.get("original_date", "")),
            record.get("source_type", ""),
            record.get("source_identifier", ""),
            record.get("imported_from", ""),
            record.get("source_file", record.get("imported_from", "")),
            self._to_int(record.get("import_run_id")),
            self._to_json(record.get("raw_record", {})),
            self._to_json(record.get("raw_engagement", {})),
            self._to_json(record.get("attachment_references", [])),
            record.get("original_platform", ""),
            record.get("import_status", "active"),
            record.get("imported_at", ""),
            record.get("content_hash", ""),
            record.get("notes", "")
        ))

        communication_id = cur.lastrowid
        conn.commit()
        conn.close()

        return {
            "communication_id": communication_id,
            "inserted": True
        }

    ############################################################

    def save_communication_delivery(self, delivery):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT OR IGNORE INTO communication_deliveries(
            communication_id,
            platform,
            published_at,
            platform_post_id,
            permalink,
            delivery_text,
            media_count,
            photo_count,
            video_count,
            engagement_metrics,
            source_file,
            import_run_id,
            attachment_references_json,
            media_matches_json,
            match_confidence,
            original_platform,
            imported_at,
            delivery_hash
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            self._to_int(delivery.get("communication_id")),
            delivery.get("platform", ""),
            delivery.get("published_at", ""),
            delivery.get("platform_post_id", ""),
            delivery.get("permalink", ""),
            delivery.get("delivery_text", ""),
            self._to_int(delivery.get("media_count")),
            self._to_int(delivery.get("photo_count")),
            self._to_int(delivery.get("video_count")),
            self._to_json(delivery.get("engagement_metrics") or {}),
            delivery.get("source_file", ""),
            self._to_int(delivery.get("import_run_id")),
            self._to_json(delivery.get("attachment_references", [])),
            self._to_json(delivery.get("media_matches", [])),
            self._to_int(delivery.get("match_confidence")),
            delivery.get("original_platform", delivery.get("platform", "")),
            delivery.get("imported_at", ""),
            delivery.get("delivery_hash", "")
        ))

        inserted = cur.rowcount > 0
        delivery_id = cur.lastrowid if inserted else None
        conn.commit()
        conn.close()

        return {
            "delivery_id": delivery_id,
            "inserted": inserted
        }

    ############################################################

    def save_communication_intelligence(self, intelligence):

        communication_id = self._to_int(
            intelligence.get("communication_id")
        )
        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE communication_editorial_intelligence
        SET active=0
        WHERE communication_id=?
        """,
        (
            communication_id,
        ))
        cur.execute("""
        INSERT INTO communication_editorial_intelligence(
            communication_id,
            primary_story,
            editorial_angle,
            communication_purpose,
            category,
            intended_audiences,
            topics,
            programs,
            campaigns,
            seasonal_relevance,
            educational_value,
            recruitment_value,
            preparedness_value,
            operational_value,
            community_trust_value,
            historical_value,
            human_interest_value,
            evergreen_value,
            confidence_score,
            source_signals,
            analysis_version,
            generated_at,
            active
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
        """,
        (
            communication_id,
            intelligence.get("primary_story", ""),
            intelligence.get("editorial_angle", ""),
            intelligence.get("communication_purpose", ""),
            intelligence.get("category", ""),
            self._to_json(intelligence.get("intended_audiences", [])),
            self._to_json(intelligence.get("topics", [])),
            self._to_json(intelligence.get("programs", [])),
            self._to_json(intelligence.get("campaigns", [])),
            self._to_json(intelligence.get("seasonal_relevance", [])),
            self._to_int(intelligence.get("educational_value")),
            self._to_int(intelligence.get("recruitment_value")),
            self._to_int(intelligence.get("preparedness_value")),
            self._to_int(intelligence.get("operational_value")),
            self._to_int(intelligence.get("community_trust_value")),
            self._to_int(intelligence.get("historical_value")),
            self._to_int(intelligence.get("human_interest_value")),
            self._to_int(intelligence.get("evergreen_value")),
            self._to_int(intelligence.get("confidence_score")),
            self._to_json(intelligence.get("source_signals", [])),
            intelligence.get("analysis_version", ""),
            intelligence.get("generated_at", "")
        ))

        intelligence_id = cur.lastrowid
        conn.commit()
        conn.close()

        return intelligence_id

    ############################################################

    def save_communication_correction(self, correction):

        communication_id = self._to_int(correction.get("communication_id"))
        field_name = correction.get("field_name", "")
        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE communication_intelligence_corrections
        SET active=0,
            updated_at=CURRENT_TIMESTAMP
        WHERE communication_id=?
        AND field_name=?
        AND active=1
        """,
        (
            communication_id,
            field_name
        ))
        cur.execute("""
        INSERT INTO communication_intelligence_corrections(
            communication_id,
            field_name,
            original_value,
            corrected_value,
            correction_source,
            notes,
            active
        )
        VALUES(?,?,?,?,?,?,1)
        """,
        (
            communication_id,
            field_name,
            self._to_json(correction.get("original_value")),
            self._to_json(correction.get("corrected_value")),
            correction.get("correction_source", "Jonathan"),
            correction.get("notes", "")
        ))

        correction_id = cur.lastrowid
        conn.commit()
        conn.close()

        return correction_id

    ############################################################

    def clear_communication_correction(self, communication_id, field_name):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE communication_intelligence_corrections
        SET active=0,
            updated_at=CURRENT_TIMESTAMP
        WHERE communication_id=?
        AND field_name=?
        AND active=1
        """,
        (
            self._to_int(communication_id),
            field_name
        ))
        changed = cur.rowcount
        conn.commit()
        conn.close()

        return changed

    ############################################################

    def save_communication_campaign(self, campaign):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_campaigns(
            name,
            description,
            active_years,
            recurring_months,
            goals,
            audiences,
            associated_program_ids,
            editorial_angles,
            topics,
            partner_organizations,
            status
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET
            description=COALESCE(NULLIF(excluded.description, ''), description),
            active_years=excluded.active_years,
            recurring_months=excluded.recurring_months,
            goals=excluded.goals,
            audiences=excluded.audiences,
            associated_program_ids=excluded.associated_program_ids,
            editorial_angles=excluded.editorial_angles,
            topics=excluded.topics,
            partner_organizations=excluded.partner_organizations,
            status=excluded.status,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            campaign.get("name", ""),
            campaign.get("description", ""),
            self._to_json(campaign.get("active_years", [])),
            self._to_json(campaign.get("recurring_months", [])),
            self._to_json(campaign.get("goals", [])),
            self._to_json(campaign.get("audiences", [])),
            self._to_json(campaign.get("associated_program_ids", [])),
            self._to_json(campaign.get("editorial_angles", [])),
            self._to_json(campaign.get("topics", [])),
            self._to_json(campaign.get("partner_organizations", [])),
            campaign.get("status", "active")
        ))

        campaign_id = cur.lastrowid
        cur.execute(
            "SELECT campaign_id FROM communication_campaigns WHERE name=?",
            (
                campaign.get("name", ""),
            )
        )
        row = cur.fetchone()
        campaign_id = row[0] if row else campaign_id
        conn.commit()
        conn.close()

        return campaign_id

    ############################################################

    def save_communication_program(self, program):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_programs(
            name,
            description,
            typical_audiences,
            typical_topics,
            associated_campaign_ids,
            associated_partner_ids,
            seasonal_pattern,
            status
        )
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(name) DO UPDATE SET
            description=COALESCE(NULLIF(excluded.description, ''), description),
            typical_audiences=excluded.typical_audiences,
            typical_topics=excluded.typical_topics,
            associated_campaign_ids=excluded.associated_campaign_ids,
            associated_partner_ids=excluded.associated_partner_ids,
            seasonal_pattern=excluded.seasonal_pattern,
            status=excluded.status,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            program.get("name", ""),
            program.get("description", ""),
            self._to_json(program.get("typical_audiences", [])),
            self._to_json(program.get("typical_topics", [])),
            self._to_json(program.get("associated_campaign_ids", [])),
            self._to_json(program.get("associated_partner_ids", [])),
            program.get("seasonal_pattern", ""),
            program.get("status", "active")
        ))

        program_id = cur.lastrowid
        cur.execute(
            "SELECT program_id FROM communication_programs WHERE name=?",
            (
                program.get("name", ""),
            )
        )
        row = cur.fetchone()
        program_id = row[0] if row else program_id
        conn.commit()
        conn.close()

        return program_id

    ############################################################

    def link_communication_campaign(self, communication_id, campaign_id, evidence="", confidence=0):

        self._link(
            "communication_campaign_links",
            "campaign_id",
            communication_id,
            campaign_id,
            evidence,
            confidence
        )

    def link_communication_program(self, communication_id, program_id, evidence="", confidence=0):

        self._link(
            "communication_program_links",
            "program_id",
            communication_id,
            program_id,
            evidence,
            confidence
        )

    def link_communication_topic(self, communication_id, topic, evidence="", confidence=0):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT OR IGNORE INTO communication_topic_links(
            communication_id,
            topic,
            evidence,
            confidence
        )
        VALUES(?,?,?,?)
        """,
        (
            self._to_int(communication_id),
            topic,
            evidence,
            self._to_int(confidence)
        ))
        conn.commit()
        conn.close()

    ############################################################

    def save_communication_outcome(self, outcome):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_outcomes(
            communication_id,
            engagement_assessment,
            educational_strength,
            recruitment_strength,
            community_trust_strength,
            preparedness_strength,
            historical_value,
            evergreen_status,
            recommended_repeat_interval_days,
            should_repeat,
            editorial_success_notes,
            confidence_score,
            source
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            self._to_int(outcome.get("communication_id")),
            outcome.get("engagement_assessment", ""),
            self._to_int(outcome.get("educational_strength")),
            self._to_int(outcome.get("recruitment_strength")),
            self._to_int(outcome.get("community_trust_strength")),
            self._to_int(outcome.get("preparedness_strength")),
            self._to_int(outcome.get("historical_value")),
            outcome.get("evergreen_status", ""),
            self._to_int(outcome.get("recommended_repeat_interval_days")),
            self._to_int(outcome.get("should_repeat")),
            outcome.get("editorial_success_notes", ""),
            self._to_int(outcome.get("confidence_score")),
            outcome.get("source", "")
        ))

        outcome_id = cur.lastrowid
        conn.commit()
        conn.close()

        return outcome_id

    ############################################################

    def save_communication_import_run(self, summary):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_import_runs(
            source_type,
            source_name,
            started_at,
            completed_at,
            records_processed,
            records_inserted,
            deliveries_inserted,
            duplicates_skipped,
            records_failed,
            campaigns_detected,
            programs_detected,
            topics_extracted,
            warnings,
            status,
            duration_seconds
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            summary.get("source_type", ""),
            summary.get("source_name", ""),
            summary.get("started_at", ""),
            summary.get("completed_at", ""),
            self._to_int(summary.get("records_processed")),
            self._to_int(summary.get("records_inserted")),
            self._to_int(summary.get("deliveries_inserted")),
            self._to_int(summary.get("duplicates_skipped")),
            self._to_int(summary.get("records_failed")),
            self._to_json(self._json_list(summary.get("campaigns_detected", []))),
            self._to_json(self._json_list(summary.get("programs_detected", []))),
            self._to_json(self._json_list(summary.get("topics_extracted", []))),
            self._to_json(summary.get("warnings", [])),
            summary.get("status", ""),
            float(summary.get("duration_seconds") or 0)
        ))

        import_run_id = cur.lastrowid
        conn.commit()
        conn.close()

        return import_run_id

    def create_communication_import_run(self, summary):

        return self.save_communication_import_run(
            {
                **summary,
                "completed_at": summary.get("completed_at", ""),
                "records_processed": summary.get("records_processed", 0),
                "records_inserted": summary.get("records_inserted", 0),
                "deliveries_inserted": summary.get("deliveries_inserted", 0),
                "duplicates_skipped": summary.get("duplicates_skipped", 0),
                "records_failed": summary.get("records_failed", 0),
                "campaigns_detected": summary.get("campaigns_detected", []),
                "programs_detected": summary.get("programs_detected", []),
                "topics_extracted": summary.get("topics_extracted", []),
                "warnings": summary.get("warnings", []),
                "status": summary.get("status", "running"),
                "duration_seconds": summary.get("duration_seconds", 0)
            }
        )

    def update_communication_import_run(self, import_run_id, summary):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE communication_import_runs
        SET completed_at=?,
            records_processed=?,
            records_inserted=?,
            deliveries_inserted=?,
            duplicates_skipped=?,
            records_failed=?,
            campaigns_detected=?,
            programs_detected=?,
            topics_extracted=?,
            warnings=?,
            status=?,
            duration_seconds=?
        WHERE import_run_id=?
        """,
        (
            summary.get("completed_at", ""),
            self._to_int(summary.get("records_processed")),
            self._to_int(summary.get("records_inserted")),
            self._to_int(summary.get("deliveries_inserted")),
            self._to_int(summary.get("duplicates_skipped")),
            self._to_int(summary.get("records_failed")),
            self._to_json(self._json_list(summary.get("campaigns_detected", []))),
            self._to_json(self._json_list(summary.get("programs_detected", []))),
            self._to_json(self._json_list(summary.get("topics_extracted", []))),
            self._to_json(summary.get("warnings", [])),
            summary.get("status", ""),
            float(summary.get("duration_seconds") or 0),
            self._to_int(import_run_id)
        ))
        conn.commit()
        conn.close()

    def save_communication_import_item(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_import_items(
            import_run_id,
            communication_id,
            delivery_id,
            action,
            reason,
            details_json
        )
        VALUES(?,?,?,?,?,?)
        """,
        (
            self._to_int(item.get("import_run_id")),
            self._to_int(item.get("communication_id")),
            self._to_int(item.get("delivery_id")),
            item.get("action", ""),
            item.get("reason", ""),
            self._to_json(item.get("details", {}))
        ))
        item_id = cur.lastrowid
        conn.commit()
        conn.close()

        return item_id

    def save_communication_duplicate_review(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_duplicate_reviews(
            import_run_id,
            candidate_hash,
            incoming_summary,
            existing_communication_id,
            duplicate_type,
            confidence,
            reason,
            status
        )
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            self._to_int(item.get("import_run_id")),
            item.get("candidate_hash", ""),
            item.get("incoming_summary", ""),
            self._to_int(item.get("existing_communication_id")),
            item.get("duplicate_type", ""),
            self._to_int(item.get("confidence")),
            item.get("reason", ""),
            item.get("status", "needs_review")
        ))
        review_id = cur.lastrowid
        conn.commit()
        conn.close()

        return review_id

    def save_communication_media_reference(self, item):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO communication_media_references(
            import_run_id,
            communication_id,
            delivery_id,
            reference_text,
            source_relative_path,
            matched_media_id,
            match_confidence,
            match_reason,
            status
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            self._to_int(item.get("import_run_id")),
            self._to_int(item.get("communication_id")),
            self._to_int(item.get("delivery_id")),
            item.get("reference_text", ""),
            item.get("source_relative_path", ""),
            self._to_int(item.get("matched_media_id")),
            self._to_int(item.get("match_confidence")),
            item.get("match_reason", ""),
            item.get("status", "unmatched")
        ))
        reference_id = cur.lastrowid
        conn.commit()
        conn.close()

        return reference_id

    def communication_duplicate_candidate(self, normalized_text, date_prefix, source_identifier="", platform_post_id=""):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        result = {}

        if source_identifier:
            cur.execute("""
            SELECT communication_id, title, source_identifier
            FROM communication_records
            WHERE source_identifier=?
            LIMIT 1
            """, (source_identifier,))
            row = cur.fetchone()

            if row:
                result = {
                    "duplicate_type": "source_identifier",
                    "communication_id": row["communication_id"],
                    "confidence": 100,
                    "reason": "Exact source identifier already exists."
                }

        if not result and platform_post_id:
            cur.execute("""
            SELECT communication_id
            FROM communication_deliveries
            WHERE platform_post_id=?
            LIMIT 1
            """, (platform_post_id,))
            row = cur.fetchone()

            if row:
                result = {
                    "duplicate_type": "platform_post_id",
                    "communication_id": row["communication_id"],
                    "confidence": 100,
                    "reason": "Exact platform post ID already exists."
                }

        if not result and normalized_text:
            cur.execute("""
            SELECT communication_id, original_text, original_date
            FROM communication_records
            WHERE substr(original_date, 1, 10)=?
            ORDER BY communication_id DESC
            LIMIT 100
            """, (date_prefix,))
            rows = cur.fetchall()

            incoming_compact = self._compact(normalized_text)
            incoming_plain = self._plain(normalized_text)

            for row in rows:
                existing_plain = self._plain(row["original_text"] or "")
                existing_compact = self._compact(row["original_text"] or "")

                if incoming_plain == existing_plain:
                    result = {
                        "duplicate_type": "normalized_text_date",
                        "communication_id": row["communication_id"],
                        "confidence": 98,
                        "reason": "Exact normalized text and date already exist."
                    }
                    break

                if incoming_compact == existing_compact:
                    result = {
                        "duplicate_type": "punctuation_or_whitespace",
                        "communication_id": row["communication_id"],
                        "confidence": 92,
                        "reason": "Only punctuation or whitespace differs."
                    }
                    break

                similarity = self._similarity(
                    incoming_plain,
                    existing_plain
                )

                if similarity >= 0.55:
                    result = {
                        "duplicate_type": "probable_text_date",
                        "communication_id": row["communication_id"],
                        "confidence": 80,
                        "reason": "Similar text on the same date requires review."
                    }
                    break

        conn.close()

        return result

    def communication_has_delivery_platform(self, communication_id, platform):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT COUNT(*)
        FROM communication_deliveries
        WHERE communication_id=?
        AND lower(platform)=lower(?)
        """,
        (
            self._to_int(communication_id),
            platform or ""
        ))
        count = cur.fetchone()[0] or 0
        conn.close()

        return count > 0

    def rollback_communication_import_run(self, import_run_id):

        import_run_id = self._to_int(import_run_id)
        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT communication_id FROM communication_records WHERE import_run_id=?",
            (import_run_id,)
        )
        communication_ids = [
            row[0]
            for row in cur.fetchall()
        ]

        if not communication_ids:
            conn.close()
            return {
                "import_run_id": import_run_id,
                "communications_removed": 0,
                "deliveries_removed": 0,
                "status": "nothing_to_rollback"
            }

        placeholders = ",".join("?" for _value in communication_ids)
        params = tuple(communication_ids)
        removed = {}

        for table in (
            "communication_media_references",
            "communication_intelligence_corrections",
            "communication_editorial_intelligence",
            "communication_campaign_links",
            "communication_program_links",
            "communication_topic_links",
            "communication_outcomes"
        ):
            cur.execute(
                f"DELETE FROM {table} WHERE communication_id IN ({placeholders})",
                params
            )
            removed[table] = cur.rowcount

        cur.execute("""
        DELETE FROM communication_campaigns
        WHERE campaign_id NOT IN (
            SELECT DISTINCT campaign_id
            FROM communication_campaign_links
        )
        """)
        removed["orphan_communication_campaigns"] = cur.rowcount

        cur.execute("""
        DELETE FROM communication_programs
        WHERE program_id NOT IN (
            SELECT DISTINCT program_id
            FROM communication_program_links
        )
        """)
        removed["orphan_communication_programs"] = cur.rowcount

        cur.execute(
            "DELETE FROM communication_deliveries WHERE import_run_id=?",
            (import_run_id,)
        )
        deliveries_removed = cur.rowcount
        cur.execute(
            "DELETE FROM communication_records WHERE import_run_id=?",
            (import_run_id,)
        )
        communications_removed = cur.rowcount
        cur.execute(
            "DELETE FROM communication_import_items WHERE import_run_id=?",
            (import_run_id,)
        )
        cur.execute(
            "DELETE FROM communication_duplicate_reviews WHERE import_run_id=?",
            (import_run_id,)
        )
        cur.execute("""
        UPDATE communication_import_runs
        SET status='rolled_back'
        WHERE import_run_id=?
        """, (import_run_id,))
        conn.commit()
        conn.close()

        return {
            "import_run_id": import_run_id,
            "communications_removed": communications_removed,
            "deliveries_removed": deliveries_removed,
            "details": removed,
            "status": "rolled_back"
        }

    def update_communication_intelligence_review(self, communication_id, updates):

        conn = self.database.connection()
        cur = conn.cursor()
        fields = []
        values = []

        for field in (
            "review_status",
            "reviewer_notes",
            "reviewed_at"
        ):
            if field not in updates:
                continue

            fields.append(f"{field}=?")
            values.append(updates.get(field, ""))

        if fields:
            values.append(self._to_int(communication_id))
            cur.execute(
                f"""
                UPDATE communication_editorial_intelligence
                SET {', '.join(fields)}
                WHERE communication_id=?
                AND active=1
                """,
                tuple(values)
            )

        conn.commit()
        conn.close()

    ############################################################

    def communication_records(self, limit=100, search_text=""):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        sql = """
        SELECT *
        FROM communication_records
        """
        params = []

        if search_text:
            sql += """
            WHERE title LIKE ?
            OR original_text LIKE ?
            OR summary LIKE ?
            """
            pattern = f"%{search_text}%"
            params.extend((pattern, pattern, pattern))

        sql += """
        ORDER BY original_date DESC, communication_id DESC
        LIMIT ?
        """
        params.append(self._to_int(limit) or 100)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        conn.close()

        return [
            self._communication_record_from_row(row)
            for row in rows
        ]

    def communication_deliveries(self, communication_id=None, limit=100):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        sql = """
        SELECT *
        FROM communication_deliveries
        """
        params = []

        if communication_id:
            sql += " WHERE communication_id=?"
            params.append(self._to_int(communication_id))

        sql += """
        ORDER BY published_at DESC, delivery_id DESC
        LIMIT ?
        """
        params.append(self._to_int(limit) or 100)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        conn.close()

        return [
            self._communication_delivery_from_row(row)
            for row in rows
        ]

    def communication_campaigns(self, limit=100):

        return self._all(
            "communication_campaigns",
            "name",
            limit,
            self._communication_campaign_from_row
        )

    def communication_programs(self, limit=100):

        return self._all(
            "communication_programs",
            "name",
            limit,
            self._communication_program_from_row
        )

    def communication_import_runs(self, limit=20):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM communication_import_runs
        ORDER BY import_run_id DESC
        LIMIT ?
        """,
        (
            self._to_int(limit) or 20,
        ))
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "import_run_id": row["import_run_id"],
                "source_type": row["source_type"] or "",
                "source_name": row["source_name"] or "",
                "records_processed": row["records_processed"] or 0,
                "records_inserted": row["records_inserted"] or 0,
                "deliveries_inserted": row["deliveries_inserted"] or 0,
                "duplicates_skipped": row["duplicates_skipped"] or 0,
                "records_failed": row["records_failed"] or 0,
                "campaigns_detected": self._from_json(row["campaigns_detected"]),
                "programs_detected": self._from_json(row["programs_detected"]),
                "topics_extracted": self._from_json(row["topics_extracted"]),
                "warnings": self._from_json(row["warnings"]),
                "status": row["status"] or "",
                "duration_seconds": row["duration_seconds"] or 0
            }
            for row in rows
        ]

    ############################################################

    def effective_communication_intelligence(self, communication_id):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM communication_records WHERE communication_id=?",
            (
                self._to_int(communication_id),
            )
        )
        record = cur.fetchone()

        if not record:
            conn.close()
            return {}

        cur.execute("""
        SELECT *
        FROM communication_editorial_intelligence
        WHERE communication_id=?
        AND active=1
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            self._to_int(communication_id),
        ))
        intelligence = cur.fetchone()
        cur.execute("""
        SELECT *
        FROM communication_intelligence_corrections
        WHERE communication_id=?
        AND active=1
        ORDER BY correction_id
        """,
        (
            self._to_int(communication_id),
        ))
        corrections = cur.fetchall()
        cur.execute("""
        SELECT *
        FROM communication_deliveries
        WHERE communication_id=?
        ORDER BY published_at DESC, delivery_id DESC
        """,
        (
            self._to_int(communication_id),
        ))
        deliveries = cur.fetchall()
        conn.close()

        return self._effective_communication_from_rows(
            record,
            intelligence,
            corrections,
            deliveries
        )

    def effective_communication_memory(self, limit=500):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM communication_records
        ORDER BY original_date DESC, communication_id DESC
        LIMIT ?
        """,
        (
            self._to_int(limit) or 500,
        ))
        record_rows = cur.fetchall()
        communication_ids = [
            row["communication_id"]
            for row in record_rows
        ]

        if not communication_ids:
            conn.close()
            return []

        placeholders = ",".join("?" for _value in communication_ids)
        cur.execute(f"""
        SELECT *
        FROM communication_editorial_intelligence
        WHERE active=1
        AND communication_id IN ({placeholders})
        ORDER BY id DESC
        """,
        tuple(communication_ids))
        intelligence_rows = cur.fetchall()
        cur.execute(f"""
        SELECT *
        FROM communication_intelligence_corrections
        WHERE active=1
        AND communication_id IN ({placeholders})
        ORDER BY correction_id
        """,
        tuple(communication_ids))
        correction_rows = cur.fetchall()
        cur.execute(f"""
        SELECT *
        FROM communication_deliveries
        WHERE communication_id IN ({placeholders})
        ORDER BY published_at DESC, delivery_id DESC
        """,
        tuple(communication_ids))
        delivery_rows = cur.fetchall()
        conn.close()

        intelligence_by_id = {}

        for row in intelligence_rows:
            communication_id = row["communication_id"]

            if communication_id not in intelligence_by_id:
                intelligence_by_id[communication_id] = row

        corrections_by_id = {}

        for row in correction_rows:
            corrections_by_id.setdefault(
                row["communication_id"],
                []
            ).append(row)

        deliveries_by_id = {}

        for row in delivery_rows:
            deliveries_by_id.setdefault(
                row["communication_id"],
                []
            ).append(row)

        return [
            self._effective_communication_from_rows(
                record,
                intelligence_by_id.get(record["communication_id"]),
                corrections_by_id.get(record["communication_id"], []),
                deliveries_by_id.get(record["communication_id"], [])
            )
            for record in record_rows
        ]

    ############################################################

    def effective_communication_memory_between(self, start_date, end_date, limit=250):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM communication_records
        WHERE import_status='active'
        AND COALESCE(normalized_date_utc, original_date) >= ?
        AND COALESCE(normalized_date_utc, original_date) < ?
        ORDER BY original_date DESC, communication_id DESC
        LIMIT ?
        """,
        (
            start_date,
            end_date,
            self._to_int(limit) or 250,
        ))
        record_rows = cur.fetchall()
        communication_ids = [
            row["communication_id"]
            for row in record_rows
        ]

        if not communication_ids:
            conn.close()
            return []

        placeholders = ",".join("?" for _value in communication_ids)
        cur.execute(f"""
        SELECT *
        FROM communication_editorial_intelligence
        WHERE active=1
        AND communication_id IN ({placeholders})
        ORDER BY id DESC
        """,
        tuple(communication_ids))
        intelligence_rows = cur.fetchall()
        cur.execute(f"""
        SELECT *
        FROM communication_intelligence_corrections
        WHERE active=1
        AND communication_id IN ({placeholders})
        ORDER BY correction_id
        """,
        tuple(communication_ids))
        correction_rows = cur.fetchall()
        cur.execute(f"""
        SELECT *
        FROM communication_deliveries
        WHERE communication_id IN ({placeholders})
        ORDER BY published_at DESC, delivery_id DESC
        """,
        tuple(communication_ids))
        delivery_rows = cur.fetchall()
        conn.close()

        intelligence_by_id = {}
        for row in intelligence_rows:
            communication_id = row["communication_id"]
            if communication_id not in intelligence_by_id:
                intelligence_by_id[communication_id] = row

        corrections_by_id = {}
        for row in correction_rows:
            corrections_by_id.setdefault(
                row["communication_id"],
                []
            ).append(row)

        deliveries_by_id = {}
        for row in delivery_rows:
            deliveries_by_id.setdefault(
                row["communication_id"],
                []
            ).append(row)

        return [
            self._effective_communication_from_rows(
                record,
                intelligence_by_id.get(record["communication_id"]),
                corrections_by_id.get(record["communication_id"], []),
                deliveries_by_id.get(record["communication_id"], [])
            )
            for record in record_rows
        ]

    ############################################################

    def communication_memory_topic_summary(self, limit=50):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT topic, COUNT(*), MAX(r.original_date)
        FROM communication_topic_links t
        JOIN communication_records r
            ON r.communication_id=t.communication_id
        GROUP BY topic
        ORDER BY COUNT(*) DESC, topic
        LIMIT ?
        """,
        (
            self._to_int(limit) or 50,
        ))
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "topic": row[0],
                "count": row[1] or 0,
                "last_posted": row[2] or ""
            }
            for row in rows
        ]

    def communication_memory_engine_summary(self):

        conn = self.database.connection()
        cur = conn.cursor()
        tables = (
            ("communication_records", "records"),
            ("communication_deliveries", "deliveries"),
            ("communication_campaigns", "campaigns"),
            ("communication_programs", "programs"),
            ("communication_topic_links", "topics"),
            ("communication_import_runs", "import_runs")
        )
        counts = {}

        for table, key in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[key] = cur.fetchone()[0]

        conn.close()

        return counts

    ############################################################

    def _link(self, table, target_column, communication_id, target_id, evidence, confidence):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute(f"""
        INSERT OR IGNORE INTO {table}(
            communication_id,
            {target_column},
            evidence,
            confidence
        )
        VALUES(?,?,?,?)
        """,
        (
            self._to_int(communication_id),
            self._to_int(target_id),
            evidence,
            self._to_int(confidence)
        ))
        conn.commit()
        conn.close()

    def _all(self, table, order_by, limit, mapper):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"""
        SELECT *
        FROM {table}
        ORDER BY {order_by}
        LIMIT ?
        """,
        (
            self._to_int(limit) or 100,
        ))
        rows = cur.fetchall()
        conn.close()

        return [
            mapper(row)
            for row in rows
        ]

    ############################################################

    def _communication_record_from_row(self, row):

        return {
            "communication_id": row["communication_id"],
            "title": row["title"] or "",
            "original_text": row["original_text"] or "",
            "summary": row["summary"] or "",
            "original_date": row["original_date"] or "",
            "source_type": row["source_type"] or "",
            "source_identifier": row["source_identifier"] or "",
            "imported_from": row["imported_from"] or "",
            "imported_at": row["imported_at"] or "",
            "content_hash": row["content_hash"] or "",
            "notes": row["notes"] or "",
            "created_at": row["created_at"] or ""
        }

    def _communication_delivery_from_row(self, row):

        return {
            "delivery_id": row["delivery_id"],
            "communication_id": row["communication_id"] or 0,
            "platform": row["platform"] or "",
            "published_at": row["published_at"] or "",
            "platform_post_id": row["platform_post_id"] or "",
            "permalink": row["permalink"] or "",
            "delivery_text": row["delivery_text"] or "",
            "media_count": row["media_count"] or 0,
            "photo_count": row["photo_count"] or 0,
            "video_count": row["video_count"] or 0,
            "engagement_metrics": self._from_json(row["engagement_metrics"]),
            "imported_at": row["imported_at"] or "",
            "delivery_hash": row["delivery_hash"] or ""
        }

    def _communication_intelligence_from_row(self, row):

        return {
            "communication_id": row["communication_id"] or 0,
            "primary_story": row["primary_story"] or "",
            "editorial_angle": row["editorial_angle"] or "",
            "communication_purpose": row["communication_purpose"] or "",
            "category": row["category"] or "",
            "intended_audiences": self._from_json(row["intended_audiences"]),
            "topics": self._from_json(row["topics"]),
            "programs": self._from_json(row["programs"]),
            "campaigns": self._from_json(row["campaigns"]),
            "seasonal_relevance": self._from_json(row["seasonal_relevance"]),
            "educational_value": row["educational_value"] or 0,
            "recruitment_value": row["recruitment_value"] or 0,
            "preparedness_value": row["preparedness_value"] or 0,
            "operational_value": row["operational_value"] or 0,
            "community_trust_value": row["community_trust_value"] or 0,
            "historical_value": row["historical_value"] or 0,
            "human_interest_value": row["human_interest_value"] or 0,
            "evergreen_value": row["evergreen_value"] or 0,
            "confidence_score": row["confidence_score"] or 0,
            "source_signals": self._from_json(row["source_signals"]),
            "analysis_version": row["analysis_version"] or "",
            "generated_at": row["generated_at"] or ""
        }

    def _effective_communication_from_rows(self, record, intelligence=None, corrections=None, deliveries=None):

        effective = self._communication_record_from_row(record)
        effective["source_layer"] = "raw"
        effective["deliveries"] = [
            self._communication_delivery_from_row(delivery)
            for delivery in deliveries or []
        ]

        if intelligence:
            effective.update(
                self._communication_intelligence_from_row(intelligence)
            )
            effective["source_layer"] = "automated_intelligence"
        else:
            effective.update(
                {
                    "primary_story": effective.get("summary", ""),
                    "editorial_angle": "",
                    "communication_purpose": "",
                    "category": "",
                    "intended_audiences": [],
                    "topics": [],
                    "programs": [],
                    "campaigns": [],
                    "seasonal_relevance": [],
                    "confidence_score": 0
                }
            )

        correction_rows = []

        for correction in corrections or []:
            field = correction["field_name"]
            effective[field] = self._from_json(correction["corrected_value"])
            effective["source_layer"] = "human_corrected"
            correction_rows.append(
                {
                    "field_name": field,
                    "original_value": self._from_json(correction["original_value"]),
                    "corrected_value": self._from_json(correction["corrected_value"]),
                    "correction_source": correction["correction_source"] or "",
                    "notes": correction["notes"] or "",
                    "created_at": correction["created_at"] or ""
                }
            )

        effective["corrections"] = correction_rows

        return effective

    def _communication_campaign_from_row(self, row):

        return {
            "campaign_id": row["campaign_id"],
            "name": row["name"] or "",
            "description": row["description"] or "",
            "active_years": self._from_json(row["active_years"]),
            "recurring_months": self._from_json(row["recurring_months"]),
            "goals": self._from_json(row["goals"]),
            "audiences": self._from_json(row["audiences"]),
            "associated_program_ids": self._from_json(row["associated_program_ids"]),
            "editorial_angles": self._from_json(row["editorial_angles"]),
            "topics": self._from_json(row["topics"]),
            "partner_organizations": self._from_json(row["partner_organizations"]),
            "status": row["status"] or "",
            "created_at": row["created_at"] or "",
            "updated_at": row["updated_at"] or ""
        }

    def _communication_program_from_row(self, row):

        return {
            "program_id": row["program_id"],
            "name": row["name"] or "",
            "description": row["description"] or "",
            "typical_audiences": self._from_json(row["typical_audiences"]),
            "typical_topics": self._from_json(row["typical_topics"]),
            "associated_campaign_ids": self._from_json(row["associated_campaign_ids"]),
            "associated_partner_ids": self._from_json(row["associated_partner_ids"]),
            "seasonal_pattern": row["seasonal_pattern"] or "",
            "status": row["status"] or "",
            "created_at": row["created_at"] or "",
            "updated_at": row["updated_at"] or ""
        }

    ############################################################

    def _to_json(self, value):

        return self.database._to_json(value)

    def _from_json(self, value):

        return self.database._from_json(value)

    def _to_int(self, value):

        return self.database._to_int(value)

    def _json_list(self, value):

        if isinstance(value, set):
            return sorted(value)

        return value

    def _plain(self, value):

        return " ".join(str(value or "").lower().split())

    def _compact(self, value):

        return "".join(
            character
            for character in self._plain(value)
            if character.isalnum()
        )

    def _similarity(self, left, right):

        left_words = set(str(left or "").split())
        right_words = set(str(right or "").split())

        if not left_words or not right_words:
            return 0

        return len(left_words & right_words) / len(left_words | right_words)
