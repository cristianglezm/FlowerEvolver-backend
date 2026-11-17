import threading
from types import SimpleNamespace
import pytest
from app import create_app
from app.background import kafka_consumer, kafka_producer


class Producer:
    """What KafkaProducer looks like after it bootstrapped. kafka-python 3.x answers False to
    bootstrap_connected() once the bootstrap succeeded, the health check must not rely on it."""

    @staticmethod
    def bootstrap_connected():
        return False


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, KAFKA_ENABLED=True)
    return app


@pytest.fixture
def kafka(monkeypatch):
    """Sets the state of this worker's kafka producer and consumer."""
    running = threading.Event()
    thread = threading.Thread(target=running.wait, daemon=True)
    thread.start()

    def setup(producer=None, producer_error=None, consumer_connected=False, consumer_error=None,
              producer_thread=True, consumer_thread=True):
        monkeypatch.setattr(kafka_producer, '_producer', producer)
        monkeypatch.setattr(kafka_producer, '_last_error', producer_error)
        monkeypatch.setattr(kafka_producer, '_thread', thread if producer_thread else None)
        monkeypatch.setattr(kafka_consumer, '_thread', thread if consumer_thread else None)
        monkeypatch.setattr(kafka_consumer, '_last_error', consumer_error)
        if consumer_connected:
            kafka_consumer._connected.set()
        else:
            kafka_consumer._connected.clear()

    yield setup
    kafka_consumer._connected.clear()
    running.set()


def kafka_status(app):
    with app.app_context():
        from app.monitoring import _kafka_status
        return _kafka_status()


def test_kafka_not_configured_when_disabled(app):
    app.config['KAFKA_ENABLED'] = False
    assert kafka_status(app) == 'not_configured'


def test_kafka_ok_when_producer_and_consumer_are_connected(app, kafka):
    kafka(producer=Producer(), consumer_connected=True, producer_thread=False)
    assert kafka_status(app) == 'ok'


def test_kafka_is_connecting_while_the_producer_has_not_connected_yet(app, kafka):
    kafka(producer=None)
    assert kafka_status(app) == 'connecting'


def test_kafka_is_connecting_while_the_consumer_has_not_connected_yet(app, kafka):
    kafka(producer=Producer(), consumer_connected=False)
    assert kafka_status(app) == 'connecting'


def test_kafka_error_when_the_last_producer_attempt_failed(app, kafka):
    kafka(producer=None, producer_error='NoBrokersAvailable')
    assert kafka_status(app) == 'error'


def test_kafka_error_when_the_consumer_lost_the_connection(app, kafka):
    kafka(producer=Producer(), consumer_connected=False, consumer_error='broker went away')
    assert kafka_status(app) == 'error'


def test_kafka_error_when_the_consumer_thread_is_dead(app, kafka):
    kafka(producer=Producer(), consumer_connected=True, consumer_thread=False)
    assert kafka_status(app) == 'error'


def test_kafka_error_when_the_producer_thread_died_without_connecting(app, kafka):
    kafka(producer=None, producer_thread=False, consumer_connected=True)
    assert kafka_status(app) == 'error'


def test_health_is_200_when_everything_is_up(app, kafka):
    kafka(producer=Producer(), consumer_connected=True)
    response = app.test_client().get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'ok', 'components': {'database': 'ok', 'kafka': 'ok', 'redis': 'not_configured'}}


def test_health_is_503_and_degraded_while_kafka_connects(app, kafka):
    kafka(producer=None)
    response = app.test_client().get('/health')
    assert response.status_code == 503
    assert response.json['status'] == 'degraded'
    assert response.json['components']['kafka'] == 'connecting'


def test_health_reports_redis_ok_and_error(app, monkeypatch):
    app.config.update(KAFKA_ENABLED=False, REDIS_ENABLED=True)
    monkeypatch.setitem(app.extensions, 'redis_client', SimpleNamespace(ping=lambda: True))
    assert app.test_client().get('/health').json['components']['redis'] == 'ok'

    def broken():
        raise ConnectionError('redis is down')
    monkeypatch.setitem(app.extensions, 'redis_client', SimpleNamespace(ping=broken))
    response = app.test_client().get('/health')
    assert response.json['components']['redis'] == 'error'
    assert response.status_code == 503


def test_health_reports_database_error(app, monkeypatch):
    app.config['KAFKA_ENABLED'] = False

    def broken(*args, **kwargs):
        raise RuntimeError('db is down')
    from app import db
    monkeypatch.setattr(db.session, 'execute', broken)
    response = app.test_client().get('/health')
    assert response.json['components']['database'] == 'error'
    assert response.status_code == 503


def test_readyz_depends_on_the_database_only(app, kafka):
    kafka(producer=None, producer_error='kafka is down')
    assert app.test_client().get('/readyz').status_code == 200
    assert app.test_client().get('/healthz').status_code == 200
