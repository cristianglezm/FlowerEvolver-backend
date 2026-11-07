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
    "Total number of FlowerEvolver library invocations.",
    ["operation", "status"]
)

FLOWER_EVOLVER_INVOCATION_DURATION_SECONDS = Histogram(
    "flower_evolver_invocation_duration_seconds",
    "Time taken by a single FlowerEvolver library invocation.",
    ["operation"]
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

FLOWERS_GENERATED_TOTAL = Counter(
    "flowers_generated_total",
    "Flowers successfully made, by kind: create, share, mutation or reproduction.",
    ["kind"]
)

FLOWER_LIMIT_REACHED_TOTAL = Counter(
    "flower_limit_reached_total",
    "Requests refused because the daily flower limit was reached, by kind.",
    ["kind"]
)


def init_metric_labels(config):
    """Create every known label combination so each series exists at 0 from the first scrape.

    A labelled series only exists after its first increment, so Prometheus would see it already at its
    final value and rate()/increase() would miss the first events (the dashboards would show 0 for them).
    """
    for kind in ("create", "share", "mutation", "reproduction"):
        FLOWERS_GENERATED_TOTAL.labels(kind=kind)
    for kind in ("create", "mutation", "reproduction"):
        FLOWER_LIMIT_REACHED_TOTAL.labels(kind=kind)
    for operation in ("make", "draw", "mutate", "reproduce"):
        FLOWER_EVOLVER_INVOCATION_DURATION_SECONDS.labels(operation=operation)
        for status in ("success", "failure"):
            FLOWER_EVOLVER_INVOCATIONS_TOTAL.labels(operation=operation, status=status)
    for status in ("success", "failure"):
        KAFKA_MESSAGES_PRODUCED_TOTAL.labels(topic=config['KAFKA_REQUEST_TOPIC'], status=status)
        KAFKA_MESSAGES_PROCESSED_TOTAL.labels(topic=config['KAFKA_RESPONSE_TOPIC'], status=status)
    KAFKA_MESSAGE_PROCESSING_TIME_SECONDS.labels(topic=config['KAFKA_RESPONSE_TOPIC'])
