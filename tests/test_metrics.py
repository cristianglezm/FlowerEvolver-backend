import pytest
from prometheus_client import REGISTRY
from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0


def scrape(client):
    response = client.get('/metrics', headers={'Authorization': f"Bearer {client.application.config['METRICS_API_KEY']}"})
    assert response.status_code == 200
    return response.get_data(as_text=True)


def gauge(text, name):
    for line in text.splitlines():
        if line.startswith(name + ' '):
            return float(line.split()[1])
    raise AssertionError(f'{name} is not exposed')


def test_create_counts_a_generated_flower(app):
    before = sample('flowers_generated_total', kind='create')
    assert app.test_client().post('/api/flowers', json={}).status_code == 200
    assert sample('flowers_generated_total', kind='create') == before + 1


def test_mutation_and_reproduction_are_counted_separately(app):
    client = app.test_client()
    original = client.post('/api/flowers', json={}).json['id']
    other = client.post('/api/flowers', json={}).json['id']
    mutations = sample('flowers_generated_total', kind='mutation')
    reproductions = sample('flowers_generated_total', kind='reproduction')
    assert client.post('/api/mutations', json={'original': original}).status_code == 200
    assert client.post('/api/descendants', json={'father': original, 'mother': other}).status_code == 200
    assert sample('flowers_generated_total', kind='mutation') == mutations + 1
    assert sample('flowers_generated_total', kind='reproduction') == reproductions + 1


def test_a_failed_request_is_not_counted(app):
    before = sample('flowers_generated_total', kind='mutation')
    assert app.test_client().post('/api/mutations', json={'original': 99999999}).status_code == 404
    assert sample('flowers_generated_total', kind='mutation') == before


@pytest.mark.parametrize('path, body, kind', [
    ('/api/flowers', {}, 'create'),
    ('/api/mutations', {'original': 1}, 'mutation'),
    ('/api/descendants', {'father': 1, 'mother': 2}, 'reproduction'),
])
def test_the_daily_limit_is_counted_by_kind(app, path, body, kind):
    app.config['FLOWER_LIMIT'] = -1
    before = sample('flower_limit_reached_total', kind=kind)
    assert app.test_client().post(path, json=body).status_code == 403
    assert sample('flower_limit_reached_total', kind=kind) == before + 1


def test_capacity_gauges_come_from_the_database(app):
    client = app.test_client()
    client.post('/api/flowers', json={})
    text = scrape(client)
    flowers = gauge(text, 'flowers_total')
    assert flowers >= 1
    assert gauge(text, 'flower_limit') == int(app.config['FLOWER_LIMIT'])
    assert gauge(text, 'descriptions_total') >= 0
    client.post('/api/flowers', json={})
    assert gauge(scrape(client), 'flowers_total') == flowers + 1


def test_every_series_exists_from_the_start(app):
    # otherwise the first events of a series are invisible to rate() and increase()
    for kind in ('create', 'share', 'mutation', 'reproduction'):
        assert REGISTRY.get_sample_value('flowers_generated_total', {'kind': kind}) is not None
    for kind in ('create', 'mutation', 'reproduction'):
        assert REGISTRY.get_sample_value('flower_limit_reached_total', {'kind': kind}) is not None
    for operation in ('make', 'draw', 'mutate', 'reproduce'):
        assert REGISTRY.get_sample_value('flower_evolver_invocations_total', {'operation': operation, 'status': 'failure'}) is not None
    topic = app.config['KAFKA_RESPONSE_TOPIC']
    assert REGISTRY.get_sample_value('kafka_messages_processed_total', {'topic': topic, 'status': 'success'}) is not None
