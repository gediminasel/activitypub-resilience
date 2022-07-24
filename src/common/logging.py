import time


class EventCounter:
    def __init__(self):
        self.counts: dict = {}
        self.total_counts: dict = {}
        self.last_flush: float = 0
        self.reset_total()

    def reset_total(self) -> None:
        self.counts: dict = {}
        self.total_counts: dict = {}
        self.last_flush: float = time.time()

    def on_event(self, typ: str) -> None:
        self.total_counts[typ] = self.total_counts.get(typ, 0) + 1
        self.counts[typ] = self.counts.get(typ, 0) + 1

    def get_stats(self) -> dict:
        stats = dict(self.counts)
        last_flush = self.last_flush
        stats["time"] = time.time()
        stats["period"] = stats["time"] - last_flush
        return stats

    def get_total_stats(self) -> dict:
        return self.total_counts

    def reset_stats(self) -> dict:
        stats = self.get_stats()
        self.last_flush = stats["time"]
        self.counts = {}
        return stats
