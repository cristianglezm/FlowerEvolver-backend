import base64
import json
import threading
import structlog
from ..metrics import KAFKA_MESSAGES_PRODUCED_TOTAL

logger = structlog.get_logger(__name__)

_producer = None
_thread = None
_RETRY_DELAY_SECONDS = 5
_SEND_TIMEOUT_SECONDS = 2


def _connect(app):
    global _producer
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    servers = app.config['KAFKA_BOOTSTRAP_SERVERS']
    while _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_block_ms=_SEND_TIMEOUT_SECONDS * 1000,
            )
            logger.info("kafka_producer_initialized", bootstrap_servers=servers)
        except KafkaError as e:
            logger.warning("kafka_producer_unavailable", error=str(e), retry_in=_RETRY_DELAY_SECONDS)
            threading.Event().wait(_RETRY_DELAY_SECONDS)


def init_producer(app):
    global _thread
    if not app.config['KAFKA_ENABLED']:
        logger.info("kafka_producer_disabled")
        return None
    _thread = threading.Thread(target=_connect, args=(app,), daemon=True, name='kafka-producer')
    _thread.start()
    return _thread


def get_producer():
    return _producer


def request_description(app, request_id, image_path):
    if _producer is None:
        return
    topic = app.config['KAFKA_REQUEST_TOPIC']
    try:
        with open(image_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('ascii')
        _producer.send(topic, {'request_id': request_id, 'image_base64': image_base64})
        _producer.flush(timeout=_SEND_TIMEOUT_SECONDS)
        KAFKA_MESSAGES_PRODUCED_TOTAL.labels(topic=topic, status='success').inc()
        logger.info("kafka_description_requested", request_id=request_id, topic=topic)
    except Exception as e:
        KAFKA_MESSAGES_PRODUCED_TOTAL.labels(topic=topic, status='failure').inc()
        logger.error("kafka_produce_failed", request_id=request_id, error=str(e))
