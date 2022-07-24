import logging

from common.logging import EventCounter

LOGGER_NAME = "verifier"

logger: logging.Logger = logging.getLogger(LOGGER_NAME)


class VerifierEventCounter(EventCounter):
    ACTOR_FETCH_FAILED = "actor_fetch_failed"
    ACTOR_FETCH_TEMP_ERROR = "actor_fetch_temporary_error"
    ACTOR_FETCH_SKIPPED = "actor_fetch_skipped"
    ACTOR_INFO_MISMATCH = "actor_info_mismatch"
    ACTOR_SIGNED = "actor_signed"
    BATCH_SUBMITTED = "batch_submitted"
    BATCH_SUBMIT_FAILED = "batch_submit_failed"
    PAGE_FETCHED = "page_fetched"
    LONG_FETCH = "long_fetch"


event_counter = VerifierEventCounter()
