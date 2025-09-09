import pytest
import json
from pathlib import Path
from app import create_app

base_url = "/api"


@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def assert_response_status(response, expected_status):
    assert response.status_code == expected_status


def assert_response_json_types(response, key_type_pairs):
    json_data = response.json
    for key, data_type in key_type_pairs:
        assert isinstance(json_data.get(key), data_type)


class TestFlowers:
    def test_create_flower(self, client):
        response = client.post(f"{base_url}/flowers", json={})
        assert_response_status(response, 200)

    def test_share_flower(self, client):
        json_path = Path('generated/1.json')
        with json_path.open('r') as file:
            flower_data = json.load(file)
            response = client.post(f"{base_url}/flowers", json=flower_data)
            assert_response_status(response, 200)

    def test_share_flower_missing_node_chromosome(self, client):
        json_path = Path('generated/1.json')
        with json_path.open('r') as file:
            flower_data = json.load(file)
            del flower_data['Flower']['dna']['genomes'][1]['nodeChromosomes']
            response = client.post(f"{base_url}/flowers", json=flower_data)
            assert_response_status(response, 400)

    def test_get_flowers(self, client):
        response = client.get(f"{base_url}/flowers")
        assert_response_status(response, 200)
        assert_response_json_types(response, [("count", int), ("flowers", list)])

    def test_get_flowers_count(self, client):
        response = client.get(f"{base_url}/flowers?count=1")
        assert_response_status(response, 200)
        assert_response_json_types(response, [("count", int)])

    def test_get_flower_by_id(self, client):
        response = client.get(f"{base_url}/flowers/1")
        assert_response_status(response, 200)
        assert_response_json_types(response, [("id", int), ("genome", str), ("image", str)])

    def test_get_flower_by_invalid_id(self, client):
        response = client.get(f"{base_url}/flowers/999999")
        assert_response_status(response, 404)

class TestDescriptions:
    def test_get_descriptions(self, client):
        response = client.get(f"{base_url}/descriptions")
        assert_response_status(response, 200)

    def test_get_descriptions_count(self, client):
        response = client.get(f"{base_url}/descriptions")
        assert_response_status(response, 200)
        assert_response_json_types(response, [("count", int), ("descriptions", list)])

    def test_get_descriptions_by_id(self, client):
        response = client.get(f"{base_url}/descriptions/1")
        assert_response_status(response, 404)

    def test_get_descriptions_by_invalid_id(self, client):
        response = client.get(f"{base_url}/descriptions/999999")
        assert_response_status(response, 404)

class TestMutations:
    def test_create_mutation(self, client):
        response = client.post(f"{base_url}/mutations", json={"original": 1})
        assert_response_status(response, 200)

    def test_create_mutation_invalid_data(self, client):
        response = client.post(f"{base_url}/mutations", json={"original": "invalid"})
        assert_response_status(response, 400)

    def test_get_mutations(self, client):
        response = client.get(f"{base_url}/mutations")
        assert_response_status(response, 200)
        assert_response_json_types(response, [("count", int), ("mutations", list)])

    def test_get_mutations_count(self, client):
        response = client.get(f"{base_url}/mutations?count=1")
        assert_response_status(response, 200)
        assert_response_json_types(response, [("count", int)])

    def test_get_mutations_by_original(self, client):
        response = client.get(f"{base_url}/mutations/1")
        assert_response_status(response, 200)
        assert isinstance(response.json, list)

    def test_get_mutations_by_invalid_id(self, client):
        response = client.get(f"{base_url}/mutations/999999")
        assert_response_status(response, 404)

    def test_create_mutation_xss(self, client):
        response = client.post(f"{base_url}/mutations", json={"original": "<script>alert('XSS')</script>"})
        assert_response_status(response, 400)


class TestAncestors:
    def test_create_ancestor(self, client):
        response = client.post(f"{base_url}/ancestors", json={"father": 1, "mother": 2})
        assert_response_status(response, 200)

    def test_create_ancestor_invalid_data(self, client):
        response = client.post(f"{base_url}/ancestors", json={"father": "invalid", "mother": "invalid"})
        assert_response_status(response, 400)

    def test_create_ancestor_xss(self, client):
        response = client.post(f"{base_url}/ancestors", json={"father": "<script>alert('XSS')</script>", "mother": 2})
        assert_response_status(response, 400)

    def test_get_ancestors(self, client):
        response = client.get(f"{base_url}/ancestors")
        assert_response_status(response, 200)
        assert_response_json_types(response, [("count", int), ("ancestors", list)])

    def test_get_ancestors_count(self, client):
        response = client.get(f"{base_url}/ancestors?count=1")
        assert_response_status(response, 200)
        assert_response_json_types(response, [("count", int)])

    def test_get_ancestors_by_father(self, client):
        response = client.get(f"{base_url}/ancestors/1")
        assert_response_status(response, 200)
        assert isinstance(response.json, list)

    def test_get_ancestors_by_father_and_mother(self, client):
        response = client.get(f"{base_url}/ancestors/1/2")
        assert_response_status(response, 200)
        assert isinstance(response.json, list)

    def test_get_ancestors_by_invalid_father(self, client):
        response = client.get(f"{base_url}/ancestors/999999")
        assert_response_status(response, 404)

    def test_get_ancestors_by_invalid_father_and_valid_mother(self, client):
        response = client.get(f"{base_url}/ancestors/999999/2")
        assert_response_status(response, 404)

    def test_get_ancestors_by_valid_father_and_invalid_mother(self, client):
        response = client.get(f"{base_url}/ancestors/1/9999999")
        assert_response_status(response, 404)

    def test_get_ancestors_by_invalid_father_and_mother(self, client):
        response = client.get(f"{base_url}/ancestors/9999999/999999")
        assert_response_status(response, 404)
