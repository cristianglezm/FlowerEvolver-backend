import json
import threading
import structlog
from ..metrics import KAFKA_MESSAGES_PROCESSED_TOTAL, KAFKA_MESSAGE_PROCESSING_TIME_SECONDS
from ..repositories import description_repository

logger = structlog.get_logger(__name__)

_thread = None
_stop_event = threading.Event()
_RETRY_DELAY_SECONDS = 5


def _handle_message(app, topic, data):
    request_id = data.get('request_id')
    description = data.get('description')
    if not request_id or not description:
        logger.warning("kafka_message_missing_fields", topic=topic)
        return
    with KAFKA_MESSAGE_PROCESSING_TIME_SECONDS.labels(topic=topic).time():
        try:
            with app.app_context():
                if description_repository.get_by_id(request_id):
                    logger.info("kafka_description_already_exists", request_id=request_id)
                    return
                description_repository.create(request_id, description)
            KAFKA_MESSAGES_PROCESSED_TOTAL.labels(topic=topic, status='success').inc()
            logger.info("kafka_description_stored", request_id=request_id)
        except Exception as e:
            KAFKA_MESSAGES_PROCESSED_TOTAL.labels(topic=topic, status='failure').inc()
            logger.error("kafka_message_processing_failed", request_id=request_id, error=str(e))


def _consume_once(app):
    from kafka import KafkaConsumer
    topic = app.config['KAFKA_RESPONSE_TOPIC']
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=app.config['KAFKA_BOOTSTRAP_SERVERS'],
        group_id='flowerevolver-backend-descriptions',
        auto_offset_reset='earliest',
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        consumer_timeout_ms=1000,
    )
    logger.info("kafka_consumer_started", topic=topic)
    try:
        while not _stop_event.is_set():
            for message in consumer:
                _handle_message(app, topic, message.value)
                if _stop_event.is_set():
                    break
    finally:
        consumer.close()
        logger.info("kafka_consumer_stopped", topic=topic)


def _consume_loop(app):
    while not _stop_event.is_set():
        try:
            _consume_once(app)
        except Exception as e:
            logger.warning("kafka_consumer_connection_failed", error=str(e), retry_in=_RETRY_DELAY_SECONDS)
            _stop_event.wait(_RETRY_DELAY_SECONDS)


def start_consumer(app):
    global _thread
    if not app.config['KAFKA_ENABLED']:
        logger.info("kafka_consumer_disabled")
        return None
    _stop_event.clear()
    _thread = threading.Thread(target=_consume_loop, args=(app,), daemon=True, name='kafka-consumer')
    _thread.start()
    return _thread


def stop_consumer():
    _stop_event.set()


def is_alive():
    return _thread is not None and _thread.is_alive()
