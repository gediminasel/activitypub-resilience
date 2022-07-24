import json
from typing import List


class Config:
    """
    Verifier configuration.
    Must be set before verifier is started and must NOT be modified afterwards.
    """

    web_port: int = 9123
    """Port on which to start verifier server"""

    web_host: str = "localhost"
    """Host of the web server"""

    actor_uri: str = "http://localhost:9123/actor"
    """Uri of verifier"""

    actor_name: str = "Simple verifier"
    """Name of verifier"""

    status_path: str = "/status"
    """Where to serve verifier status"""

    actor_key_path: str = "/actor"
    """Path where key should be served"""

    parallel_fetches: int = 100
    """How many parallel requests to make"""

    queue_size: int = 400
    """Maximum length of the queue"""

    domain_request_period: float = 1
    """Minimum time between two requests to the same domain"""

    request_timeout: float = 20
    """Maximum request time in total"""

    lookup_request_period: float = 0.25
    """Minimum time between two requests to the lookup server"""

    signature_batch_size: int = 50
    """Maximum number of signatures to include in one request"""

    signature_batch_timeout: float = 10
    """Maximum time in seconds to wait before sending an incomplete batch of signatures"""

    actor_retry_timers: List[float] = [60, 3600, 24 * 3600, 24 * 3600 * 20]
    """
    How often an actor fetch should be retried.
    """

    commit_after_every: bool = False
    """
    Should the database commit after every action
    """

    domain_retry_timers: List[float] = [
        2 * (5**i) for i in range(9)
    ]  # sum = 10 (5**9 - 1) / 2 = 56 days
    """
    List of sleep periods.
    N-th element determines how long to sleep after n-th fetch failure.
    """

    @staticmethod
    def load(filename):
        with open(filename, "r") as f:
            data = json.load(f)
        if "web_port" in data:
            Config.web_port = int(data["web_port"])
        if "web_host" in data:
            Config.web_host = str(data["web_host"])
        if "actor_uri" in data:
            Config.actor_uri = str(data["actor_uri"])
        if "actor_key_path" in data:
            Config.actor_key_path = bool(data["actor_key_path"])
        if "parallel_fetches" in data:
            Config.parallel_fetches = int(data["parallel_fetches"])
        if "queue_size" in data:
            Config.queue_size = int(data["queue_size"])
        if "domain_request_period" in data:
            Config.domain_request_period = float(data["domain_request_period"])
