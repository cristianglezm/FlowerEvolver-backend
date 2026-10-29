from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests made.",
    ["endpoint", "method", "status_code"]
)

HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    "http_request_latency_seconds",
    "Latency of HTTP requests.",
    ["endpoint", "method"]
)

FLOWER_EVOLVER_INVOCATIONS_TOTAL = Counter(
    "flower_evolver_invocations_total",
    "Total number of FlowerEvolver binary invocations.",
    ["operation", "status"]
)

KAFKA_MESSAGES_PRODUCED_TOTAL = Counter(
    "kafka_messages_produced_total",
    "Total number of Kafka messages produced by the app.",
    ["topic", "status"]
)

KAFKA_MESSAGES_PROCESSED_TOTAL = Counter(
    "kafka_messages_processed_total",
    "Total number of Kafka messages processed by the consumer.",
    ["topic", "status"]
)

KAFKA_MESSAGE_PROCESSING_TIME_SECONDS = Histogram(
    "kafka_message_processing_time_seconds",
    "Time taken to process a single Kafka message.",
    ["topic"]
)
