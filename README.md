# Flower Evolver Backend #

[![CI](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/ci.yml) [![Docker](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/docker.yml/badge.svg?branch=master)](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/docker.yml)

Flower Evolver backend, frontend can be found [here](https://github.com/cristianglezm/FlowerEvolver-frontend)

## Running local ##

* git clone https://github.com/cristianglezm/FlowerEvolver-backend
* cd FlowerEvolver-backend
* use Python 3.12 (the pinned dependencies, e.g. pydantic-core, have no wheels for 3.14 yet)
* pip install -r requirements.txt
* change .env as needed

```
HOST=localhost
DB=flowerevolver
PASSWD='passwd'
USER=user
ENV=production | development
ORIGINS=*
FLOWER_LIMIT=5000
SECRET_KEY='notreallyneeded'

# Kafka settings, backend produces to KAFKA_REQUEST_TOPIC and consumes
# descriptions from KAFKA_RESPONSE_TOPIC. See the FlowerEvolver-describe
# repo for the service that actually generates the descriptions.
KAFKA_ENABLED=False
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_REQUEST_TOPIC=descRequests
KAFKA_RESPONSE_TOPIC=descResponses

# Redis is only used for distributed rate limiting; when disabled (or
# unreachable) an in-process rate limiter is used instead, which is what
# you want on hosts without arbitrary outbound TCP access (e.g. PythonAnywhere).
REDIS_ENABLED=False
REDIS_URL=redis://localhost:6379

RATE_LIMIT_TIMES=5
RATE_LIMIT_SECONDS=10

# Bearer token required on GET /metrics
METRICS_API_KEY='sk_change_key'

```

* Run following commands:
    - export FLASK_APP=FlowerEvolver.py
    - flask db init
    - flask db migrate
    - flask db upgrade
    - flask run

## Running docker ##

I recommend using the compose file from [frontend](https://github.com/cristianglezm/FlowerEvolver-frontend.git)
read the README-docker.md in [frontend](https://github.com/cristianglezm/FlowerEvolver-frontend.git) repo for how to.

Flowers are generated with the [flowerevolver](https://github.com/cristianglezm/FlowerEvolver-WASM)
python package (installed from requirements.txt), no executable is needed anymore.
PyPI only has glibc (manylinux) x86_64 wheels, so the Ubuntu image installs it directly while the
Alpine image compiles it from source in a build stage (needs network access to GitHub, ~1-2 minutes).
On arm64 hosts always compile from source (use the Alpine image or add a build stage to the Ubuntu one).

You can also pull the images from this
[repo](https://hub.docker.com/repository/docker/cristianglezm/fe) and change the env variables as needed.

Before running the script to build the image, change the .env variables if you need to.

* build image (alpine or ubuntu)
    * sh build_docker.sh "alpine"
    * sh build_docker.sh "ubuntu"
* pull image (alpine(300MB) or ubuntu(800MB))
    * docker pull cristianglezm/fe:backend-alpine-dev
    * docker pull cristianglezm/fe:backend-ubuntu-dev
* docker run -dp 5000:5000 -v generated:/app/generated -v migrations:/app/migrations \ 
    -v db:/app/db cristianglezm/fe:backend-alpine-dev --env-file .env --hostname backend
* browse to http://localhost:5000/api/flowers to get a list of flowers.
    (use webtools to send request, a rest client or the frontend website.)

## Running the full stack (Kafka, Redis, MySQL, Prometheus, Grafana) ##

For local testing of the description pipeline and observability, `docker-compose.yml`
in this repo brings up the backend alongside MySQL, Redis, Kafka (KRaft, single node),
their Prometheus exporters, Prometheus, Grafana, and the
[FlowerEvolver-describe](https://github.com/cristianglezm/FlowerEvolver-describe) service
that actually turns a `descRequests` image into a description.

* docker compose up -d (podman: podman compose -f docker-compose.yml -f docker-compose.podman.yml up -d)
* backend: http://localhost:5000
* describe: http://localhost:8000
* Prometheus: http://localhost:9090
* Grafana: http://localhost:3000 (admin/admin)

This is a testing/local convenience, not the production topology: backend and describe
are deployed separately (describe's ONNX models are too large for the free tier we
currently use for the backend), so in production they don't share the same Redis or
Kafka instance the way this compose file does for convenience.

`e2e_test.py` exercises this stack over real HTTP, including waiting for a description
to come back through the full backend -> Kafka -> describe -> Kafka -> backend round trip.

## Monitoring endpoints ##

* GET /healthz - liveness, always 200 if the process is up.
* GET /readyz - readiness, checks the database is reachable.
* GET /health - per-component status (`database`, `kafka`, `redis`); `kafka`/`redis`
  report `not_configured` rather than `error` when `KAFKA_ENABLED`/`REDIS_ENABLED` are false.
* GET /metrics - Prometheus exposition format, requires `Authorization: Bearer <METRICS_API_KEY>`.

## Routes and Responses ##

* /api/flowers

     POST 

     create a new flower sending a POST with an empty json
     or a flower genome to share it (check generated/1.json).

     GET

```javascript
    {
        count: Number,
        flowers:[{ id: Number, genome:String, image:String}, ...],
    }
```

* /api/flowers/:id

    GET

```javascript
    {
        id: Number, 
        genome:String, 
        image:String
    }
```
* /api/flowers?count=1

    GET

```javasript
    {
        count: Number
    }
```

* /api/mutations

    POST send

```javascript
   {original:Number}
```
    GET

```javascript
    {
        count: Number,
        mutations[{id: Number, original: Number}, ...]
    }
```
* /api/mutations/:original

    GET

```javascript
    {[
        {id: Number, genome: String, image: String},
        ...
    ]}
```
* /api/mutations?count=1

    GET

```javasript
    {
        count: Number
    }
```

* /api/descendants

    POST send

```javascript
   {
      father: Number,
      mother: Number
   }
```
    GET

```javascript
    {
        count: Number,
        descendants:[{id:Number, father: Number, mother: Number}, ...]
    }
```

* /api/descendants?count=1

    GET

```javasript
    {
        count: Number
    }
```

* /api/descendants/:father

    GET returns every descendant of :father (as father or mother)

```javascript
    {[
        {id: Number, genome: String, image: String},
        ...
    ]}
```
* /api/descendants/:father/:mother

    GET returns every descendant of :father and :mother

```javascript
    {[
        {id: Number, genome: String, image: String},
        ...
    ]}
```

* /api/descriptions

    GET

```javascript
    {
        count: Number,
        descriptions:[{id: Number, description: String}, ...]
    }
```

* /api/descriptions?count=1

    GET

```javasript
    {
        count: Number
    }
```

* /api/descriptions/:id

    GET

```javascript
    {
        id: Number,
        description: String
    }
```
