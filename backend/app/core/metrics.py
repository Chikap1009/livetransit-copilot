"""Prometheus metric definitions shared across services.

Each process imports this and updates the metrics it cares about. Counters only go
up; gauges go up/down; histograms capture distributions (for p50/p99).
"""
from prometheus_client import Counter, Gauge, Histogram

# --- Poller ---
POLLS = Counter("lt_poller_polls_total", "Feed polls attempted")
POLL_FAILURES = Counter("lt_poller_poll_failures_total", "Feed polls that failed")
POSITIONS_PUBLISHED = Counter("lt_poller_positions_published_total", "Positions published")
FEED_TS = Gauge("lt_poller_last_feed_timestamp_seconds", "Unix ts of newest vehicle in last poll")

# --- Processor ---
MESSAGES = Counter("lt_processor_messages_total", "Stream messages processed")
BATCHES = Counter("lt_processor_batches_total", "Stream read batches processed")

# --- API ---
WS_CLIENTS = Gauge("lt_api_ws_clients", "Connected WebSocket clients")
REQ_LATENCY = Histogram("lt_api_request_seconds", "HTTP request latency", ["method", "route"])

METRICS_PORT_POLLER = 9101
METRICS_PORT_PROCESSOR = 9102
