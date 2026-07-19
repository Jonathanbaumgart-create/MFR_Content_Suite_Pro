import json
import sqlite3

from models.analysis_queue import (
    AnalysisQueueState,
    AnalysisSessionStatus
)
from services.time_service import TimeService


class AnalysisQueueRepository:

    def __init__(self, database):

        self.database = database

    ############################################################

    def create_session(self, scope, provider, model, total_items=0, settings=None):

        now = TimeService.utc_now_iso()
        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO analysis_sessions(
            status,
            scope,
            provider,
            model,
            settings_json,
            total_items,
            created_at,
            updated_at
        )
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            AnalysisSessionStatus.QUEUED,
            scope,
            provider,
            model,
            self._to_json(settings or {}),
            int(total_items or 0),
            now,
            now
        ))
        session_id = cur.lastrowid
        conn.commit()
        conn.close()

        return session_id

    ############################################################

    def enqueue_items(self, session_id, media_items, provider, model, force=False):

        if not media_items:
            return 0

        now = TimeService.utc_now_iso()
        inserted = 0
        conn = self.database.connection()
        cur = conn.cursor()

        for item in media_items:

            parsed = self._media_item(item)
            media_id = parsed["media_id"]
            filename = parsed["filename"]
            path = parsed["path"]
            media_type = parsed["media_type"]

            cur.execute("""
            INSERT OR IGNORE INTO analysis_queue(
                session_id,
                media_id,
                filename,
                path,
                media_type,
                state,
                priority,
                priority_reason,
                force,
                provider,
                model,
                queued_at,
                updated_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(session_id),
                int(media_id),
                filename,
                path,
                media_type,
                AnalysisQueueState.QUEUED,
                parsed["priority"],
                parsed["priority_reason"],
                1 if force else 0,
                provider,
                model,
                now,
                now
            ))
            inserted += cur.rowcount

        conn.commit()
        conn.close()
        self.refresh_session_counts(session_id)

        return inserted

    ############################################################

    def _media_item(self, item):

        if isinstance(item, dict):
            return {
                "media_id": item.get("media_id") or item.get("id"),
                "filename": item.get("filename", ""),
                "path": item.get("path", ""),
                "media_type": item.get("media_type", ""),
                "priority": int(item.get("priority_score") or item.get("priority") or 0),
                "priority_reason": item.get("priority_reason", "")
            }

        return {
            "media_id": item[0],
            "filename": item[1],
            "path": item[2],
            "media_type": item[3],
            "priority": 0,
            "priority_reason": ""
        }

    ############################################################

    def next_batch(self, session_id, limit):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM analysis_queue
        WHERE session_id=?
        AND state IN (?, ?, ?)
        ORDER BY priority DESC, queue_id
        LIMIT ?
        """,
        (
            int(session_id),
            AnalysisQueueState.WAITING,
            AnalysisQueueState.QUEUED,
            AnalysisQueueState.RETRY_PENDING,
            int(limit)
        ))
        rows = [
            dict(row)
            for row in cur.fetchall()
        ]
        conn.close()

        return rows

    ############################################################

    def mark_analyzing(self, queue_id):

        now = TimeService.utc_now_iso()
        self._update_item(
            queue_id,
            state=AnalysisQueueState.ANALYZING,
            started_at=now,
            updated_at=now
        )

    ############################################################

    def mark_completed(self, queue_id, duration=0, provider_latency=0, db_write_duration=0):

        now = TimeService.utc_now_iso()
        self._update_item(
            queue_id,
            state=AnalysisQueueState.COMPLETED,
            completed_at=now,
            updated_at=now,
            failure_category="",
            failure_reason="",
            analysis_duration=duration,
            provider_latency=provider_latency,
            db_write_duration=db_write_duration
        )

    ############################################################

    def mark_skipped(self, queue_id, reason):

        now = TimeService.utc_now_iso()
        self._update_item(
            queue_id,
            state=AnalysisQueueState.SKIPPED,
            completed_at=now,
            updated_at=now,
            failure_category="",
            failure_reason=reason
        )

    ############################################################

    def mark_failed(self, queue_id, category, reason, duration=0):

        now = TimeService.utc_now_iso()
        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE analysis_queue
        SET state=?,
            attempts=attempts + 1,
            failure_category=?,
            failure_reason=?,
            completed_at=?,
            updated_at=?,
            analysis_duration=?
        WHERE queue_id=?
        """,
        (
            AnalysisQueueState.FAILED,
            category,
            reason,
            now,
            now,
            float(duration or 0),
            int(queue_id)
        ))
        conn.commit()
        conn.close()

    ############################################################

    def retry_failed(self, session_id=None):

        now = TimeService.utc_now_iso()
        conn = self.database.connection()
        cur = conn.cursor()
        params = [AnalysisQueueState.RETRY_PENDING, now, AnalysisQueueState.FAILED]
        sql = """
        UPDATE analysis_queue
        SET state=?,
            updated_at=?,
            completed_at=NULL
        WHERE state=?
        """

        if session_id:
            sql += " AND session_id=?"
            params.append(int(session_id))

        cur.execute(sql, tuple(params))
        count = cur.rowcount
        conn.commit()
        conn.close()

        if session_id:
            self.update_session(
                session_id,
                status=AnalysisSessionStatus.QUEUED,
                finished_at=None,
                cancel_reason=""
            )
            self.refresh_session_counts(session_id)

        return count

    ############################################################

    def cancel_session(self, session_id, reason="Canceled by user"):

        now = TimeService.utc_now_iso()
        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE analysis_queue
        SET state=?,
            failure_reason=?,
            updated_at=?,
            completed_at=?
        WHERE session_id=?
        AND state IN (?, ?, ?)
        """,
        (
            AnalysisQueueState.CANCELED,
            reason,
            now,
            now,
            int(session_id),
            AnalysisQueueState.WAITING,
            AnalysisQueueState.QUEUED,
            AnalysisQueueState.RETRY_PENDING
        ))
        count = cur.rowcount
        conn.commit()
        conn.close()
        self.update_session(
            session_id,
            status=AnalysisSessionStatus.CANCELED,
            finished_at=now,
            cancel_reason=reason
        )
        self.refresh_session_counts(session_id)

        return count

    ############################################################

    def reset_stale_analyzing(self, session_id=None):

        now = TimeService.utc_now_iso()
        conn = self.database.connection()
        cur = conn.cursor()
        params = [
            AnalysisQueueState.RETRY_PENDING,
            now,
            "Reset after app restart",
            AnalysisQueueState.ANALYZING
        ]
        sql = """
        UPDATE analysis_queue
        SET state=?,
            updated_at=?,
            failure_reason=?
        WHERE state=?
        """

        if session_id:
            sql += " AND session_id=?"
            params.append(int(session_id))

        cur.execute(sql, tuple(params))
        count = cur.rowcount
        conn.commit()
        conn.close()

        return count

    ############################################################

    def active_media_type_counts(self, session_id):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT media_type, COUNT(*)
        FROM analysis_queue
        WHERE session_id=?
        AND state IN (?, ?, ?, ?)
        GROUP BY media_type
        """,
        (
            int(session_id),
            AnalysisQueueState.WAITING,
            AnalysisQueueState.QUEUED,
            AnalysisQueueState.ANALYZING,
            AnalysisQueueState.RETRY_PENDING
        ))
        counts = {
            row[0] or "": row[1]
            for row in cur.fetchall()
        }
        conn.close()

        return counts

    ############################################################

    def mark_worker_started(
        self,
        session_id,
        worker_id,
        process_id=None,
        thread_id=None,
        status="Active"
    ):

        now = TimeService.utc_now_iso()
        self.update_session(
            session_id,
            status=AnalysisSessionStatus.RUNNING,
            worker_id=worker_id,
            worker_process_id=process_id,
            worker_thread_id=thread_id,
            worker_status=status,
            worker_started_at=now,
            worker_heartbeat_at=now,
            worker_stopped_at="",
            worker_stop_reason="",
            last_progress_at=now,
            cancel_reason=""
        )

    ############################################################

    def heartbeat_session(self, session_id, worker_status="Active"):

        now = TimeService.utc_now_iso()
        self.update_session(
            session_id,
            worker_status=worker_status,
            worker_heartbeat_at=now,
            last_progress_at=now
        )

    ############################################################

    def mark_worker_stopped(
        self,
        session_id,
        worker_status,
        reason=""
    ):

        now = TimeService.utc_now_iso()
        self.update_session(
            session_id,
            worker_status=worker_status,
            worker_stopped_at=now,
            worker_stop_reason=reason,
            last_progress_at=now
        )

    ############################################################

    def mark_session_recoverable(self, session_id, reason):

        now = TimeService.utc_now_iso()
        self.update_session(
            session_id,
            status=AnalysisSessionStatus.RECOVERABLE,
            worker_status="stale",
            worker_stopped_at=now,
            worker_stop_reason=reason,
            last_progress_at=now,
            current_filename="",
            current_media_id=None,
            estimated_remaining_seconds=0
        )
        self.refresh_session_counts(session_id)

    ############################################################

    def pause_session(self, session_id, reason="Paused"):

        now = TimeService.utc_now_iso()
        self.update_session(
            session_id,
            status=AnalysisSessionStatus.PAUSED,
            worker_status="Paused",
            worker_stopped_at=now,
            worker_stop_reason=reason,
            last_progress_at=now,
            current_filename="",
            current_media_id=None,
            estimated_remaining_seconds=0,
            cancel_reason=reason
        )
        self.refresh_session_counts(session_id)

    ############################################################

    def increment_resume_count(self, session_id):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE analysis_sessions
        SET resume_count=COALESCE(resume_count, 0) + 1,
            updated_at=?
        WHERE session_id=?
        """,
        (
            TimeService.utc_now_iso(),
            int(session_id)
        ))
        conn.commit()
        conn.close()

    ############################################################

    def update_session(self, session_id, **fields):

        if not fields:
            return

        fields["updated_at"] = fields.get(
            "updated_at",
            TimeService.utc_now_iso()
        )
        names = []
        values = []

        for name, value in fields.items():
            names.append(f"{name}=?")
            values.append(value)

        values.append(int(session_id))
        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute(
            f"UPDATE analysis_sessions SET {', '.join(names)} WHERE session_id=?",
            tuple(values)
        )
        conn.commit()
        conn.close()

    ############################################################

    def refresh_session_counts(self, session_id):

        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT state, COUNT(*)
        FROM analysis_queue
        WHERE session_id=?
        GROUP BY state
        """,
        (
            int(session_id),
        ))
        counts = {
            row[0]: row[1]
            for row in cur.fetchall()
        }
        total = sum(counts.values())
        queued = (
            counts.get(AnalysisQueueState.WAITING, 0) +
            counts.get(AnalysisQueueState.QUEUED, 0) +
            counts.get(AnalysisQueueState.ANALYZING, 0) +
            counts.get(AnalysisQueueState.RETRY_PENDING, 0)
        )
        cur.execute("""
        UPDATE analysis_sessions
        SET total_items=?,
            queued_count=?,
            completed_count=?,
            failed_count=?,
            skipped_count=?,
            retry_pending_count=?,
            updated_at=?
        WHERE session_id=?
        """,
        (
            total,
            queued,
            counts.get(AnalysisQueueState.COMPLETED, 0),
            counts.get(AnalysisQueueState.FAILED, 0),
            counts.get(AnalysisQueueState.SKIPPED, 0),
            counts.get(AnalysisQueueState.RETRY_PENDING, 0),
            TimeService.utc_now_iso(),
            int(session_id)
        ))
        conn.commit()
        conn.close()

        return counts

    ############################################################

    def session_summary(self, session_id=None):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if session_id:
            cur.execute(
                "SELECT * FROM analysis_sessions WHERE session_id=?",
                (
                    int(session_id),
                )
            )
        else:
            cur.execute("""
            SELECT *
            FROM analysis_sessions
            ORDER BY session_id DESC
            LIMIT 1
            """)

        row = cur.fetchone()
        conn.close()

        if not row:
            return {}

        return dict(row)

    ############################################################

    def incomplete_sessions(self):

        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT *
        FROM analysis_sessions
        WHERE status IN (?, ?, ?, ?, ?, ?)
        ORDER BY session_id DESC
        """,
        (
            AnalysisSessionStatus.QUEUED,
            AnalysisSessionStatus.STARTING,
            AnalysisSessionStatus.RUNNING,
            AnalysisSessionStatus.PAUSED,
            AnalysisSessionStatus.RECOVERABLE,
            AnalysisSessionStatus.INTERRUPTED
        ))
        rows = [
            dict(row)
            for row in cur.fetchall()
        ]
        conn.close()

        return rows

    ############################################################

    def latest_incomplete_session(self):

        sessions = self.incomplete_sessions()
        return sessions[0] if sessions else None

    ############################################################

    def queue_counts(self, session_id=None):

        conn = self.database.connection()
        cur = conn.cursor()
        params = []
        sql = """
        SELECT state, COUNT(*)
        FROM analysis_queue
        """

        if session_id:
            sql += " WHERE session_id=?"
            params.append(int(session_id))

        sql += " GROUP BY state"
        cur.execute(sql, tuple(params))
        counts = {
            row[0]: row[1]
            for row in cur.fetchall()
        }
        conn.close()

        return counts

    ############################################################

    def media_statuses(self, media_ids):

        if not media_ids:
            return {}

        placeholders = ",".join("?" for _ in media_ids)
        conn = self.database.connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"""
        SELECT media.id AS media_id,
               ai_analysis.provider,
               ai_analysis.failure_reason,
               ai_analysis.model,
               ai_analysis.trust_state,
               ai_analysis.review_status,
               media_intelligence.media_id AS intelligence_media_id,
               media_corrections.id AS correction_id,
               latest_queue.state AS queue_state,
               latest_queue.session_status AS queue_session_status
        FROM media
        LEFT JOIN ai_analysis
        ON ai_analysis.media_id=media.id
        LEFT JOIN media_intelligence
        ON media_intelligence.media_id=media.id
        LEFT JOIN media_corrections
        ON media_corrections.media_id=media.id
        AND media_corrections.active=1
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
        WHERE media.id IN ({placeholders})
        """,
        tuple(media_ids))
        rows = [
            dict(row)
            for row in cur.fetchall()
        ]
        conn.close()

        return {
            row["media_id"]: self._status_from_row(row)
            for row in rows
        }

    ############################################################

    def _update_item(self, queue_id, **fields):

        names = []
        values = []

        for name, value in fields.items():
            names.append(f"{name}=?")
            values.append(value)

        values.append(int(queue_id))
        conn = self.database.connection()
        cur = conn.cursor()
        cur.execute(
            f"UPDATE analysis_queue SET {', '.join(names)} WHERE queue_id=?",
            tuple(values)
        )
        conn.commit()
        conn.close()

    ############################################################

    def _status_from_row(self, row):

        queue_state = row.get("queue_state") or ""
        session_status = row.get("queue_session_status") or ""

        if (
            session_status in (
                AnalysisSessionStatus.RECOVERABLE,
                AnalysisSessionStatus.INTERRUPTED
            )
            and queue_state in AnalysisQueueState.ACTIVE
        ):
            return "Interrupted"

        if queue_state in (
            AnalysisQueueState.QUEUED,
            AnalysisQueueState.WAITING,
            AnalysisQueueState.RETRY_PENDING
        ):
            return "Queued"

        if queue_state == AnalysisQueueState.ANALYZING:
            return "Analyzing"

        if row.get("failure_reason"):
            return "Failed"

        provider = row.get("provider") or ""
        model = row.get("model") or ""
        trust_state = row.get("trust_state") or ""
        review_status = row.get("review_status") or ""

        if provider == "mock" or model.startswith("mock"):
            return "Mock/Test Data"

        if provider:
            if trust_state == "rejected_real" or review_status == "rejected":
                return "Real - Rejected"

            if row.get("correction_id"):
                return "Real - Corrected"

            if trust_state == "corrected_real" or review_status == "corrected":
                return "Real - Corrected"

            if trust_state == "approved_real" or review_status == "approved":
                return "Real - Approved"

            if trust_state == "unreviewed_real" or review_status == "review_required":
                return "Real - Review Required"

            if row.get("intelligence_media_id"):
                return "Real - Review Required"

            return "Real - Review Required"

        return "Not analyzed"

    ############################################################

    def _to_json(self, value):

        return json.dumps(value)
