import json
from typing import Any, Dict


class Config:
    """
    Crawler and lookup server configuration.
    Must be set before server or crawler is started and must NOT be modified while they are running.
    Configuration can be modified between runs.
    """

    debug: bool = False
    """Run in debug mode: local queries and HTTP uris are allowed."""

    web_port: int = 8880
    """Port on which to start lookup server"""

    web_host: str = "localhost"
    """Host of the web server"""

    archive_notes: bool = False
    """If true, server stores every received note in the database"""

    archive_collections: bool = False
    """
    If true, server stores every received collection
    and collection page in the database
    """

    parallel_fetches: int = 100
    """How many parallel requests to make"""

    domain_request_period: float = 2
    """Minimum time between two requests to the same domain"""

    check_for_internet_access: float = 10
    """
    How often to check if Internet connection is working,
    negative if don't check at all
    """

    prob_choose_from_domains: float = 0.6
    """Probability that scheduler will choose urls based on domains (not from random queue)."""

    scheduler_chunk: int = 1000
    """How many elements to fetch from the database queue to in-memory in one query"""

    max_in_queue_per_domain: int = 5
    """Maximum number of elements in in-memory queue per domain"""

    domain_chunk: int = 100
    """
    How many different domains to fetch from the database queue
    to in-memory in one batch based on domains.
    """

    choose_from_domain_queue: int = 5
    """How many elements to fetch from the database queue by domain to in-memory in one query"""

    max_queue_size: int = 10000
    """Maximum in-memory queue size"""

    min_update_period: int = 3600 * 24
    """Minimum time between object updates in seconds"""

    max_update_period: int = 3600 * 24 * 10
    """Maximum time between object updates in seconds"""

    @staticmethod
    def load(filename):
        with open(filename, "r") as f:
            data: Dict[str, Any] = json.load(f)
        properties = {
            "debug": bool,
            "web_port": int,
            "web_host": str,
            "archive_notes": bool,
            "archive_collections": bool,
            "parallel_fetches": int,
            "domain_request_period": float,
            "check_for_internet_access": float,
            "prob_choose_from_domains": float,
            "scheduler_chunk": int,
            "max_in_queue_per_domain": int,
            "domain_chunk": int,
            "choose_from_domain_queue": int,
            "max_queue_size": int,
            "min_update_period": int,
            "max_update_period": int,
        }
        unknown_props = set(data.keys() - properties.keys())
        if len(unknown_props) > 0:
            raise ValueError(
                "Unknown lookup config properties: " + " ".join(unknown_props)
            )

        for prop, constr in properties.items():
            if prop in data:
                setattr(Config, prop, constr(data[prop]))
