import logging

from common.logging import EventCounter

LOGGER_NAME = "lookup_server"

logger: logging.Logger = logging.getLogger(LOGGER_NAME)


class LookupEventCounter(EventCounter):
    PAGE_FETCHED = "page_fetched"
    PAGE_FETCH_FAILED = "page_fetch_failed"
    PAGE_FETCH_TEMP_ERROR = "page_fetch_temporary_error"
    PAGE_REFETCHED = "page_refetched"
    PAGE_UPDATED = "page_updated"
    ACTOR_FOUND = "actor_found"
    OBJECT_FOUND = "object_found"
    GET_OBJECT_SERVED = "get_object_served"
    GET_OBJECT_NOT_FOUND = "get_object_not_found"
    NEW_URI_FOUND = "new_uri_found"
    ACTOR_PAGE_SERVED = "actor_page_served"
    ACTORS_TO_SIGN_SERVED = "actors_to_sign_server"
    ACTOR_SIGNED = "actor_signed"
    ACTOR_SIGN_FAILED = "actor_sign_failed"
    SCHEDULE_RANDOM = "schedule_random"
    SCHEDULE_RANDOM_FROM_DOMAIN = "schedule_random_from_domain"

    def __init__(self):
        super().__init__()
        self.all_time_fetched = 0
        self.queue_size = 0
        self.actor_count = 0


event_counter: LookupEventCounter = LookupEventCounter()
