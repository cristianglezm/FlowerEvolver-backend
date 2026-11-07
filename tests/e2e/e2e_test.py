import os
import sys
import time
import requests

SERVICE_URL = "http://localhost:5000"
METRICS_API_KEY = os.getenv("METRICS_API_KEY", "passwd")
DESCRIPTION_TIMEOUT_SECONDS = 60
HEALTH_TIMEOUT_SECONDS = 180


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
    # kafka, redis and describe start slowly: wait until /health says everything is up
    deadline = time.time() + HEALTH_TIMEOUT_SECONDS
    last = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{SERVICE_URL}/health", timeout=5)
            last = (r.status_code, r.json())
            components = last[1].get("components", {})
            if r.status_code == 200 and components.get("kafka") == "ok" and components.get("redis") == "ok":
                return
        except (requests.RequestException, ValueError) as e:
            last = (None, str(e))
        time.sleep(3)
    fail(f"/health did not report kafka and redis ok within {HEALTH_TIMEOUT_SECONDS}s, last answer: {last}")


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
