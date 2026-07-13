from core.app_context import context
from services.logging_service import LoggingService


logger = LoggingService.get_logger("ai")


class AnalysisReviewService:

    APPROVE = "approve"
    CORRECT = "correct"
    REJECT = "reject"
    REANALYZE = "reanalyze"

    def __init__(self, database=None):

        self.db = database or context.database

    ############################################################

    def queue(self, limit=50):

        return self.db.analysis_review_queue(limit=limit)

    ############################################################

    def metrics(self):

        return self.db.analysis_review_metrics()

    ############################################################

    def approve(self, media_id, reviewer="Jonathan", notes=""):

        return self.record_decision(
            media_id,
            self.APPROVE,
            reviewer=reviewer,
            notes=notes
        )

    ############################################################

    def correct(self, media_id, corrections, reviewer="Jonathan", notes=""):

        return self.record_decision(
            media_id,
            self.CORRECT,
            corrections=corrections,
            reviewer=reviewer,
            notes=notes
        )

    ############################################################

    def reject(self, media_id, reviewer="Jonathan", notes=""):

        return self.record_decision(
            media_id,
            self.REJECT,
            reviewer=reviewer,
            notes=notes
        )

    ############################################################

    def request_reanalysis(self, media_id, reviewer="Jonathan", notes=""):

        return self.record_decision(
            media_id,
            self.REANALYZE,
            reviewer=reviewer,
            notes=notes
        )

    ############################################################

    def record_decision(
        self,
        media_id,
        decision,
        corrections=None,
        reviewer="Jonathan",
        notes=""
    ):

        if decision not in {
            self.APPROVE,
            self.CORRECT,
            self.REJECT,
            self.REANALYZE
        }:
            raise ValueError("Unsupported review decision")

        trust_state = {
            self.APPROVE: "approved_real",
            self.CORRECT: "corrected_real",
            self.REJECT: "rejected_real",
            self.REANALYZE: "unreviewed_real"
        }[decision]

        review_status = {
            self.APPROVE: "approved",
            self.CORRECT: "corrected",
            self.REJECT: "rejected",
            self.REANALYZE: "reanalyze_requested"
        }[decision]

        result = self.db.record_analysis_review(
            media_id,
            decision=decision,
            trust_state=trust_state,
            review_status=review_status,
            reviewer=reviewer,
            corrections=corrections or {},
            notes=notes
        )

        logger.info(
            "Analysis review decision media_id=%s decision=%s trust_state=%s",
            media_id,
            decision,
            trust_state
        )

        return result
