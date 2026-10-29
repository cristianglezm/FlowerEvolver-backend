import json
import mimetypes
from pathlib import Path
import jsonschema
import pytest
from openapi_spec_validator import validate

import config
from app import create_app
from app.openapi import build_spec

SPEC = build_spec()
SAMPLE_GENOME = Path(__file__).parent / 'data' / 'sample_genome.json'
METRICS_KEY = {'Authorization': 'Bearer sk_change_key'}
METHODS = ('get', 'post', 'put', 'patch', 'delete')


def resolve(node):
    """Follows a $ref to #/components/<kind>/<name>."""
    while '$ref' in node:
        _, _, kind, name = node['$ref'].split('/')
        node = SPEC['components'][kind][name]
    return node


def check_response(response, path, method):
    """The response must be documented (status and content type) and its body must match the schema."""
    operation = SPEC['paths'][path][method]
    assert str(response.status_code) in operation['responses'], \
        f'{method.upper()} {path} answered {response.status_code}, documented: {list(operation["responses"])}'
    documented = resolve(operation['responses'][str(response.status_code)])
    content_type = response.content_type.split(';')[0]
    assert content_type in documented.get('content', {}), \
        f'{method.upper()} {path} {response.status_code} answered {content_type}, documented: {list(documented.get("content", {}))}'
    schema = documented['content'][content_type].get('schema', {})
    if content_type == 'application/json':
        jsonschema.Draft202012Validator({'components': SPEC['components'], **schema}).validate(response.get_json())


@pytest.fixture(scope='module')
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture(scope='module')
def client(app):
    return app.test_client()


@pytest.fixture(scope='module')
def ids(app, client):
    """Two flowers, a mutation of the first, a descendant of both and the description of the second."""
    a = client.post('/api/flowers', json={}).get_json()['id']
    b = client.post('/api/flowers', json={}).get_json()['id']
    mutation = client.post('/api/mutations', json={'original': a}).get_json()['id']
    descendant = client.post('/api/descendants', json={'father': a, 'mother': b}).get_json()['id']
    from app.repositories import description_repository
    with app.app_context():
        description_repository.create(b, 'a flower used by the OpenAPI tests')
    return {'a': a, 'b': b, 'mutation': mutation, 'descendant': descendant, 'missing': 99999999}


def test_the_document_is_valid_openapi():
    validate(SPEC)


def test_the_document_is_openapi_3_0_because_the_bundled_swagger_ui_cannot_render_3_1():
    assert SPEC['openapi'].startswith('3.0.')
    assert 'examples' not in json.dumps(SPEC['components']['schemas']), 'use `example`, `examples` is JSON Schema (3.1)'


def operations_of_the_app(app):
    found = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static' or rule.endpoint.startswith('openapi.'):
            continue
        path = rule.rule
        for converter in rule._converters:
            path = path.replace(next(part for part in (f'<int:{converter}>', f'<string:{converter}>', f'<{converter}>') if part in path), f'{{{converter}}}')
        for method in rule.methods - {'HEAD', 'OPTIONS'}:
            found.add((path, method.lower()))
    return found


def test_every_route_is_documented_and_every_documented_route_exists(app):
    documented = {(path, method) for path, item in SPEC['paths'].items() for method in item if method in METHODS}
    routes = operations_of_the_app(app)
    assert routes - documented == set(), 'routes missing from app/openapi.py'
    assert documented - routes == set(), 'documented in app/openapi.py but not in the app'


# (summary, method, url, json body, expected status, documented path)
CASES = [
    ('create a flower', 'post', '/api/flowers', {}, 200, '/api/flowers'),
    ('share a flower', 'post', '/api/flowers', 'SAMPLE', 200, '/api/flowers'),
    ('share a bad genome', 'post', '/api/flowers', {'Flower': 1}, 400, '/api/flowers'),
    ('post without json', 'post', '/api/flowers', None, 415, '/api/flowers'),
    ('list flowers', 'get', '/api/flowers', None, 200, '/api/flowers'),
    ('list flowers, filtered', 'get', '/api/flowers?id={a}&limit=5&offset=0', None, 200, '/api/flowers'),
    ('count flowers', 'get', '/api/flowers?count=1', None, 200, '/api/flowers'),
    ('unknown filter', 'get', '/api/flowers?bogus=1', None, 400, '/api/flowers'),
    ('limit is not a number', 'get', '/api/flowers?limit=abc', None, 400, '/api/flowers'),
    ('get a flower', 'get', '/api/flowers/{a}', None, 200, '/api/flowers/{flower_id}'),
    ('flower not found', 'get', '/api/flowers/{missing}', None, 404, '/api/flowers/{flower_id}'),
    ('mutate', 'post', '/api/mutations', {'original': '{a}'}, 200, '/api/mutations'),
    ('mutate without original', 'post', '/api/mutations', {}, 400, '/api/mutations'),
    ('mutate a missing flower', 'post', '/api/mutations', {'original': '{missing}'}, 404, '/api/mutations'),
    ('mutate without json', 'post', '/api/mutations', None, 415, '/api/mutations'),
    ('list mutations', 'get', '/api/mutations', None, 200, '/api/mutations'),
    ('count mutations', 'get', '/api/mutations?count=1', None, 200, '/api/mutations'),
    ('mutations: unknown filter', 'get', '/api/mutations?bogus=1', None, 400, '/api/mutations'),
    ('mutations of a flower', 'get', '/api/mutations/{a}', None, 200, '/api/mutations/{mutation_original}'),
    ('count mutations of a flower', 'get', '/api/mutations/{a}?count=1', None, 200, '/api/mutations/{mutation_original}'),
    ('mutations of a flower: bad limit', 'get', '/api/mutations/{a}?limit=-1', None, 400, '/api/mutations/{mutation_original}'),
    ('no mutations', 'get', '/api/mutations/{missing}', None, 404, '/api/mutations/{mutation_original}'),
    ('reproduce', 'post', '/api/descendants', {'father': '{a}', 'mother': '{b}'}, 200, '/api/descendants'),
    ('reproduce without mother', 'post', '/api/descendants', {'father': '{a}'}, 400, '/api/descendants'),
    ('reproduce missing parents', 'post', '/api/descendants', {'father': '{missing}', 'mother': '{b}'}, 404, '/api/descendants'),
    ('reproduce without json', 'post', '/api/descendants', None, 415, '/api/descendants'),
    ('list descendants', 'get', '/api/descendants', None, 200, '/api/descendants'),
    ('count descendants', 'get', '/api/descendants?count=1', None, 200, '/api/descendants'),
    ('descendants: unknown filter', 'get', '/api/descendants?bogus=1', None, 400, '/api/descendants'),
    ('descendants of a parent', 'get', '/api/descendants/{a}', None, 200, '/api/descendants/{father}'),
    ('descendants of a parent: bad limit', 'get', '/api/descendants/{a}?offset=x', None, 400, '/api/descendants/{father}'),
    ('no descendants of a parent', 'get', '/api/descendants/{missing}', None, 404, '/api/descendants/{father}'),
    ('descendants of two parents', 'get', '/api/descendants/{a}/{b}', None, 200, '/api/descendants/{father}/{mother}'),
    ('count descendants of two parents', 'get', '/api/descendants/{a}/{b}?count=1', None, 200, '/api/descendants/{father}/{mother}'),
    ('descendants of two parents: bad limit', 'get', '/api/descendants/{a}/{b}?limit=x', None, 400, '/api/descendants/{father}/{mother}'),
    ('no descendants of two parents', 'get', '/api/descendants/{a}/{missing}', None, 404, '/api/descendants/{father}/{mother}'),
    ('list descriptions', 'get', '/api/descriptions', None, 200, '/api/descriptions'),
    ('count descriptions', 'get', '/api/descriptions?count=1', None, 200, '/api/descriptions'),
    ('descriptions: unknown filter', 'get', '/api/descriptions?bogus=1', None, 400, '/api/descriptions'),
    ('get a description', 'get', '/api/descriptions/{b}', None, 200, '/api/descriptions/{desc_id}'),
    ('no description yet', 'get', '/api/descriptions/{a}', None, 404, '/api/descriptions/{desc_id}'),
    ('image', 'get', '/generated/{a}.png', None, 200, '/generated/{filepath}'),
    ('genome', 'get', '/generated/{a}.json', None, 200, '/generated/{filepath}'),
    ('file not found', 'get', '/generated/nope.png', None, 404, '/generated/{filepath}'),
    ('download', 'get', '/download/{a}.json', None, 200, '/download/{filepath}'),
    ('download not found', 'get', '/download/nope.json', None, 404, '/download/{filepath}'),
    ('healthz', 'get', '/healthz', None, 200, '/healthz'),
    ('readyz', 'get', '/readyz', None, 200, '/readyz'),
    ('health', 'get', '/health', None, 200, '/health'),
    ('metrics', 'get', '/metrics', 'KEY', 200, '/metrics'),
    ('metrics without key', 'get', '/metrics', None, 401, '/metrics'),
]


def fill(value, ids):
    if isinstance(value, str):
        return value.format(**ids) if '{' in value else value
    if isinstance(value, dict):
        return {key: ids[v[1:-1]] if isinstance(v, str) and v.startswith('{') and v.endswith('}') else v for key, v in value.items()}
    return value


@pytest.mark.parametrize('summary, method, url, body, status, path', CASES, ids=[case[0] for case in CASES])
def test_real_responses_match_the_document(client, ids, summary, method, url, body, status, path):
    kwargs = {}
    if body == 'SAMPLE':
        kwargs['json'] = json.loads(SAMPLE_GENOME.read_text())
    elif body == 'KEY':
        kwargs['headers'] = METRICS_KEY
    elif body is not None:
        kwargs['json'] = fill(body, ids)
    response = getattr(client, method)(fill(url, ids), **kwargs)
    assert response.status_code == status
    check_response(response, path, method)


@pytest.mark.parametrize('path, method, body', [
    ('/api/flowers', 'post', {}),
    ('/api/mutations', 'post', {'original': 1}),
    ('/api/descendants', 'post', {'father': 1, 'mother': 2}),
])
def test_the_daily_limit_answers_403_as_documented(app, client, path, method, body):
    app.config['FLOWER_LIMIT'] = -1
    try:
        response = client.post(path, json=body)
    finally:
        app.config['FLOWER_LIMIT'] = config.Config.FLOWER_LIMIT
    assert response.status_code == 403
    check_response(response, path, method)


def test_not_ready_and_degraded_are_documented(app, client, monkeypatch):
    from app import db

    def broken(*args, **kwargs):
        raise RuntimeError('db is down')
    monkeypatch.setattr(db.session, 'execute', broken)
    for path in ('/readyz', '/health'):
        response = client.get(path)
        assert response.status_code == 503
        check_response(response, path, 'get')


def test_rate_limited_requests_answer_429_as_documented(monkeypatch):
    monkeypatch.setattr(config.Config, 'RATE_LIMIT_TIMES', 1)
    client = create_app().test_client()
    assert client.get('/api/flowers/1').status_code in (200, 404)
    response = client.get('/api/flowers/1')
    assert response.status_code == 429
    check_response(response, '/api/flowers/{flower_id}', 'get')


def test_every_documented_status_is_exercised_by_these_tests():
    exercised = {(path, method, status) for _, method, _, _, status, path in CASES}
    exercised |= {(p, 'post', 403) for p in ('/api/flowers', '/api/mutations', '/api/descendants')}
    exercised |= {('/readyz', 'get', 503), ('/health', 'get', 503)}
    exercised |= {(path, method, 429) for path, item in SPEC['paths'].items() if path.startswith('/api/') for method in item}
    documented = {(path, method, int(status)) for path, item in SPEC['paths'].items() for method, op in item.items()
                  for status in op['responses']}
    assert documented - exercised == set(), 'documented but never checked against a real response'


def test_openapi_json_and_swagger_ui_are_served(client):
    assert client.get('/openapi.json').get_json() == SPEC
    page = client.get('/docs')
    assert page.status_code == 200 and b'swagger-ui' in page.data and b'/openapi.json' in page.data
    assert client.get('/docs/').status_code == 200
    bundle = client.get('/docs/assets/swagger-ui-bundle.js')
    assert bundle.status_code == 200 and 'javascript' in bundle.content_type
    assert client.get('/docs/assets/swagger-ui.css').status_code == 200
    assert client.get('/docs/assets/swagger-ui-bundle.js.map').status_code == 404   # only what the page needs
    assert client.get('/docs/assets/../../etc/passwd').status_code == 404


def test_docs_can_be_turned_off(monkeypatch):
    monkeypatch.setattr(config.Config, 'DOCS_ENABLED', False)
    client = create_app().test_client()
    for path in ('/openapi.json', '/docs', '/docs/assets/swagger-ui.css'):
        assert client.get(path).status_code == 404
    assert client.get('/healthz').status_code == 200


@pytest.mark.parametrize('url', ['/api/flowers/1', '/api/mutations/1', '/api/descendants/1', '/api/descendants/1/2'])
def test_items_are_read_only(client, url):
    # used to answer 500: the item route accepted POST and the handler crashed on the unexpected argument
    response = client.post(url, json={})
    assert response.status_code == 405
    assert response.get_json() == {'error': 'The method is not allowed for the requested URL.'}


def test_swagger_ui_files_get_their_type_even_when_the_os_guesses_wrong(client, monkeypatch):
    # Windows takes the type from the registry, where .js is often text/plain: the browser then refuses the script
    monkeypatch.setattr(mimetypes, 'guess_type', lambda *args, **kwargs: ('text/plain', None))
    types = {'swagger-ui-bundle.js': 'javascript', 'swagger-ui-standalone-preset.js': 'javascript',
             'swagger-ui.css': 'text/css', 'favicon-32x32.png': 'image/png'}
    for name, expected in types.items():
        response = client.get(f'/docs/assets/{name}')
        assert response.status_code == 200
        assert expected in response.content_type, f'{name} is served as {response.content_type}'
