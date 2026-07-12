from core.app_context import context
from services.logging_service import LoggingService


logger = LoggingService.get_logger("content")


class CommunicationHistoryService:

    def __init__(self, database=None):

        self.db = database or context.database

    ############################################################

    def effective_memory(self, limit=500):

        return self.db.effective_communication_memory(limit=limit)

    ############################################################

    def memory_posts(self, limit=500):

        rows = self.effective_memory(limit=limit)

        return [
            self._post_shape(row)
            for row in rows
        ]

    ############################################################

    def topic_history(self, topic, limit=25):

        topic = self._token(topic)
        rows = [
            row
            for row in self.effective_memory(limit=limit * 4)
            if topic in {
                self._token(value)
                for value in row.get("topics", [])
            }
        ][:limit]

        return {
            "topic": topic,
            "count": len(rows),
            "last_posted": max(
                (
                    row.get("original_date", "")
                    for row in rows
                ),
                default=""
            ),
            "communications": rows
        }

    ############################################################

    def topic_frequency(self, limit=50):

        return self.db.communication_memory_topic_summary(limit=limit)

    ############################################################

    def campaign_history(self, campaign, limit=25):

        key = self._token(campaign)
        rows = [
            row
            for row in self.effective_memory(limit=limit * 4)
            if key in {
                self._token(value)
                for value in row.get("campaigns", [])
            }
        ][:limit]

        return {
            "campaign": campaign,
            "count": len(rows),
            "last_posted": max(
                (
                    row.get("original_date", "")
                    for row in rows
                ),
                default=""
            ),
            "communications": rows
        }

    ############################################################

    def program_history(self, program, limit=25):

        key = self._token(program)
        rows = [
            row
            for row in self.effective_memory(limit=limit * 4)
            if key in {
                self._token(value)
                for value in row.get("programs", [])
            }
        ][:limit]

        return {
            "program": program,
            "count": len(rows),
            "last_posted": max(
                (
                    row.get("original_date", "")
                    for row in rows
                ),
                default=""
            ),
            "communications": rows
        }

    ############################################################

    def memory_statistics(self):

        summary = self.db.communication_memory_engine_summary()
        topics = self.topic_frequency(limit=10)

        return {
            **summary,
            "top_topics": topics,
            "memory_available": summary.get("records", 0) > 0,
            "limitations": [] if summary.get("records", 0) else [
                "No normalized communication history has been imported yet."
            ]
        }

    ############################################################

    def _post_shape(self, row):

        return {
            "id": row.get("communication_id"),
            "platform": "",
            "post_date": row.get("original_date", "")[:10],
            "post_time": row.get("original_date", "")[11:19],
            "headline": row.get("title", ""),
            "caption": row.get("original_text", ""),
            "cta": "",
            "hashtags": [],
            "media_ids": [],
            "campaign": ", ".join(row.get("campaigns") or []),
            "writing_style": row.get("editorial_angle", ""),
            "opportunity_type": row.get("category", ""),
            "season": ", ".join(row.get("seasonal_relevance") or []),
            "context": row.get("communication_purpose", ""),
            "source": row.get("source_type", ""),
            "topics": row.get("topics", []),
            "programs": row.get("programs", []),
            "campaigns": row.get("campaigns", []),
            "confidence_score": row.get("confidence_score", 0)
        }

    def _token(self, value):

        return str(value or "").strip().lower().replace(" ", "_")
