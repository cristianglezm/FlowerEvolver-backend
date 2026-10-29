import os
import sys
import time
import requests

SERVICE_URL = "http://localhost:5000"
METRICS_API_KEY = os.getenv("METRICS_API_KEY", "passwd")
DESCRIPTION_TIMEOUT_SECONDS = 60


def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def test_healthz():
    r = requests.get(f"{SERVICE_URL}/healthz")
    if r.status_code != 200:
        fail("healthz returned non-200")


def test_readyz():
    r = requests.get(f"{SERVICE_URL}/readyz")
    if r.status_code != 200:
        fail("readyz returned non-200")


def test_health_reports_kafka_and_redis_configured():
    r = requests.get(f"{SERVICE_URL}/health")
    if r.status_code != 200:
        fail("health returned non-200")
    components = r.json().get("components", {})
    if components.get("kafka") != "ok":
        fail(f"expected kafka to be ok, got {components.get('kafka')}")
    if components.get("redis") != "ok":
        fail(f"expected redis to be ok, got {components.get('redis')}")


def test_metrics_requires_api_key():
    r = requests.get(f"{SERVICE_URL}/metrics")
    if r.status_code != 401:
        fail("metrics without a key should be unauthorized")

    r = requests.get(f"{SERVICE_URL}/metrics", headers={"Authorization": f"Bearer {METRICS_API_KEY}"})
    if r.status_code != 200:
        fail("metrics with a valid key should return 200")


def create_flower():
    r = requests.post(f"{SERVICE_URL}/api/flowers", json={})
    if r.status_code != 200:
        fail(f"flower creation returned {r.status_code}")
    return r.json()


def test_create_flower():
    flower = create_flower()
    if "id" not in flower:
        fail("created flower is missing an id")
    return flower


def test_create_descendant(father, mother):
    r = requests.post(f"{SERVICE_URL}/api/descendants", json={"father": father, "mother": mother})
    if r.status_code != 200:
        fail(f"descendant creation returned {r.status_code}")
    return r.json()


def test_create_mutation(original):
    r = requests.post(f"{SERVICE_URL}/api/mutations", json={"original": original})
    if r.status_code != 200:
        fail(f"mutation creation returned {r.status_code}")
    return r.json()


def test_kafka_description_round_trip(flower_id):
    print(f"[INFO] Waiting up to {DESCRIPTION_TIMEOUT_SECONDS}s for a description of flower {flower_id}...")
    deadline = time.time() + DESCRIPTION_TIMEOUT_SECONDS
    while time.time() < deadline:
        r = requests.get(f"{SERVICE_URL}/api/descriptions/{flower_id}")
        if r.status_code == 200 and r.json().get("description"):
            print(f"[OK] Got description: {r.json()['description']!r}")
            return
        time.sleep(2)
    fail(f"no description was produced for flower {flower_id} within {DESCRIPTION_TIMEOUT_SECONDS}s "
         "(is the FlowerEvolver-describe service consuming descRequests?)")


if __name__ == "__main__":
    print("[INFO] Running E2E tests...")
    test_healthz()
    test_readyz()
    test_health_reports_kafka_and_redis_configured()
    test_metrics_requires_api_key()

    father = test_create_flower()
    mother = test_create_flower()
    test_create_descendant(father["id"], mother["id"])
    test_create_mutation(father["id"])

    test_kafka_description_round_trip(father["id"])
    print("[OK] All E2E tests passed")
