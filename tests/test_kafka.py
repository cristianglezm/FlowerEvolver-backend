import base64
import threading
import time
from types import SimpleNamespace
from app import create_app
from app.background import kafka_producer, kafka_consumer
from app.repositories import description_repository


def test_init_producer_connects_in_background(monkeypatch):
    release = threading.Event()

    class SlowProducer:
        def __init__(self, **kwargs):
            release.wait(5)

    monkeypatch.setattr('kafka.KafkaProducer', SlowProducer)
    monkeypatch.setattr(kafka_producer, '_producer', None)
    app = SimpleNamespace(config={'KAFKA_ENABLED': True, 'KAFKA_BOOTSTRAP_SERVERS': 'kafka:9092'})
    start = time.time()
    thread = kafka_producer.init_producer(app)
    assert time.time() - start < 1
    assert kafka_producer.get_producer() is None
    release.set()
    thread.join(2)
    assert isinstance(kafka_producer.get_producer(), SlowProducer)


def test_init_producer_disabled_does_not_start_anything():
    app = SimpleNamespace(config={'KAFKA_ENABLED': False})
    assert kafka_producer.init_producer(app) is None


def test_request_description_payload_matches_describe_service(monkeypatch, tmp_path):
    sent = []

    class FakeProducer:
        def send(self, topic, value):
            sent.append((topic, value))

        def flush(self, timeout=None):
            pass

    monkeypatch.setattr(kafka_producer, '_producer', FakeProducer())
    image = tmp_path / '1.png'
    image.write_bytes(b'png-bytes')
    app = SimpleNamespace(config={'KAFKA_REQUEST_TOPIC': 'descRequests'})
    kafka_producer.request_description(app, 1, image)
    assert sent == [('descRequests', {'request_id': 1, 'image_base64': base64.b64encode(b'png-bytes').decode()})]


def test_request_description_is_a_noop_without_producer(monkeypatch, tmp_path):
    monkeypatch.setattr(kafka_producer, '_producer', None)
    app = SimpleNamespace(config={'KAFKA_REQUEST_TOPIC': 'descRequests'})
    kafka_producer.request_description(app, 1, tmp_path / 'missing.png')


def test_consumer_stores_a_description_once():
    app = create_app()
    request_id = 987654
    with app.app_context():
        kafka_consumer._handle_message(app, 'descResponses', {'request_id': request_id, 'description': 'first'})
        kafka_consumer._handle_message(app, 'descResponses', {'request_id': request_id, 'description': 'second'})
        stored = description_repository.get_by_id(request_id)
        assert stored.description == 'first'
        from app import db
        db.session.delete(stored)
        db.session.commit()


def test_consumer_ignores_messages_missing_fields():
    app = create_app()
    with app.app_context():
        kafka_consumer._handle_message(app, 'descResponses', {'request_id': 987655})
        kafka_consumer._handle_message(app, 'descResponses', {'description': 'no id'})
        assert description_repository.get_by_id(987655) is None
