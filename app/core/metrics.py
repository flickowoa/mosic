from prometheus_client import Counter, Histogram

TOTAL_API_REQUESTS = Counter(
    "mosic_api_requests_total",
    "Total API requests received",
    ["method"],
)

REQUEST_LATENCY = Histogram(
    "mosic_request_latency_seconds",
    "Latency per request in seconds",
    ["method", "path"],
)

STREAMS_BY_CLIP = Counter(
    "mosic_streams_total",
    "Stream requests per clip",
    ["song_id", "title"],
)
