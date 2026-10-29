import base64
import json
import structlog
from ..metrics import KAFKA_MESSAGES_PRODUCED_TOTAL

logger = structlog.get_logger(__name__)

_producer = None


def init_producer(app):
    global _producer
    if not app.config['KAFKA_ENABLED']:
        logger.info("kafka_producer_disabled")
        return None
    from kafka import KafkaProducer
    _producer = KafkaProducer(
        bootstrap_servers=app.config['KAFKA_BOOTSTRAP_SERVERS'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    )
    logger.info("kafka_producer_initialized", bootstrap_servers=app.config['KAFKA_BOOTSTRAP_SERVERS'])
    return _producer


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
        _producer.flush()
        KAFKA_MESSAGES_PRODUCED_TOTAL.labels(topic=topic, status='success').inc()
        logger.info("kafka_description_requested", request_id=request_id, topic=topic)
    except Exception as e:
        KAFKA_MESSAGES_PRODUCED_TOTAL.labels(topic=topic, status='failure').inc()
        logger.error("kafka_produce_failed", request_id=request_id, error=str(e))
