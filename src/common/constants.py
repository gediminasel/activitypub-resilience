from typing import List

AS_JSON_CONTENT_TYPE: str = (
    'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
)

ACTIVITY_JSON_CONTENT_TYPE: str = "application/activity+json"

ACCEPTABLE_CONTENT_TYPES: str = f"{ACTIVITY_JSON_CONTENT_TYPE}, {AS_JSON_CONTENT_TYPE}"

JSON_CONTENT_TYPE: str = "application/json"
HTML_CONTENT_TYPE: str = "text/html"

WEBFINGER_CONTENT_TYPE: str = "application/jrd+json, application/json"

HOST_META_CONTENT_TYPE: str = "application/xrd+xml, application/xml, text/xml"

HIGHLY_RELIABLE_SITES: List[str] = [
    "https://www.google.com/",
    "https://www.cloudflare.com/",
]
"""Used to check if Internet connection is working"""

INF_TIME_CONST: float = 1e16
"""Used to schedule events infinitely far in the future"""
