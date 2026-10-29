import os
import pytest
from flask import Flask, jsonify
from app.rate_limit import PerClientBucketFactory, register_rate_limiting
from pyrate_limiter import Duration, InMemoryBucket, Rate

TIMES = 3
REDIS_URL = os.getenv('TEST_REDIS_URL')


def make_app(redis_enabled=False):
    app = Flask(__name__)
    app.config.update(
        RATE_LIMIT_TIMES=TIMES,
        RATE_LIMIT_SECONDS=60,
        REDIS_ENABLED=redis_enabled,
        REDIS_URL=REDIS_URL or 'redis://localhost:6379',
    )
    register_rate_limiting(app)

    @app.route('/api/flowers')
    def flowers():
        return jsonify(ok=True)

    @app.route('/api/mutations')
    def mutations():
        return jsonify(ok=True)

    @app.route('/api/flowers/<int:flower_id>')
    def flower(flower_id):
        return jsonify(id=flower_id)

    @app.route('/healthz')
    def healthz():
        return jsonify(status='ok')

    return app


def get(client, path, ip='10.0.0.1'):
    return client.get(path, environ_base={'REMOTE_ADDR': ip})


@pytest.fixture(params=['memory', pytest.param('redis', marks=pytest.mark.skipif(
    not REDIS_URL, reason='set TEST_REDIS_URL to run the redis backend'))])
def client(request):
    app = make_app(redis_enabled=request.param == 'redis')
    if request.param == 'redis':
        app.extensions['redis_client'].flushdb()
    return app.test_client()


def test_requests_over_the_limit_get_429(client):
    for _ in range(TIMES):
        assert get(client, '/api/flowers').status_code == 200
    response = get(client, '/api/flowers')
    assert response.status_code == 429
    assert response.json == {'error': 'Too Many Requests'}


def test_one_client_does_not_use_up_the_limit_of_another(client):
    for _ in range(TIMES + 2):
        get(client, '/api/flowers', ip='10.0.0.1')
    assert get(client, '/api/flowers', ip='10.0.0.1').status_code == 429
    assert get(client, '/api/flowers', ip='10.0.0.2').status_code == 200


def test_limit_is_per_route(client):
    for _ in range(TIMES + 1):
        get(client, '/api/flowers')
    assert get(client, '/api/flowers').status_code == 429
    assert get(client, '/api/mutations').status_code == 200


def test_different_ids_of_the_same_route_share_the_limit(client):
    for flower_id in range(TIMES):
        assert get(client, f'/api/flowers/{flower_id}').status_code == 200
    assert get(client, '/api/flowers/99').status_code == 429


def test_paths_outside_api_are_not_limited(client):
    for _ in range(TIMES * 3):
        assert get(client, '/healthz').status_code == 200


def test_unmatched_paths_share_one_bucket_per_client(client):
    statuses = [get(client, f'/api/nope{i}').status_code for i in range(TIMES + 2)]
    assert statuses == [404] * TIMES + [429] * 2


def test_tracked_clients_stay_bounded():
    rates = [Rate(1, 60 * Duration.SECOND)]
    factory = PerClientBucketFactory(lambda name: InMemoryBucket(rates), max_buckets=5)
    try:
        for i in range(50):
            factory.get(factory.wrap_item(f'client-{i}'))
        assert factory.tracked() <= 5
    finally:
        factory.close()


@pytest.mark.skipif(not REDIS_URL, reason='set TEST_REDIS_URL to run the redis backend')
def test_redis_keys_expire():
    app = make_app(redis_enabled=True)
    redis_client = app.extensions['redis_client']
    redis_client.flushdb()
    get(app.test_client(), '/api/flowers')
    keys = redis_client.keys('flowerevolver-backend-rate-limit:*')
    assert len(keys) == 1
    assert 0 < redis_client.ttl(keys[0]) <= 120
