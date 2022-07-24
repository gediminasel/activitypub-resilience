from typing import List

FETCH_RETRY_TIMERS: List[float] = [
    min(10 * (5**i), 3600 * 24) for i in range(56)
]  # sum([min(10 * (5 ** i), 3600*24) for i in range(56)]) / 3600 / 24 = 50 days
"""
List of sleep periods.
N-th element determines how long to sleep after n-th fetch failure.
"""

ACTOR_TYPES = ["Person", "Application", "Group", "Service"]
COLLECTION_TYPES = [
    "OrderedCollection",
    "Collection",
    "OrderedCollectionPage",
    "CollectionPage",
]

COMMIT_AFTER_EVERY_OP: bool = False

INFINITY_TIME = 10 * 365 * 3600 * 24

TRACE_LOG: bool = False
if TRACE_LOG:
    TRACE_LOG_FILE = open("out/logs/lookup.perf.log", "w", encoding="utf-8")


def log_trace(symbol: str, *args) -> None:
    print(symbol, *args, file=TRACE_LOG_FILE)
