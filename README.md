# Flower Evolver Backend #

[![CI](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/ci.yml) [![CD](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/cd.yml/badge.svg?branch=master)](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/cd.yml)

Flower Evolver backend, frontend can be found [here](https://github.com/cristianglezm/FlowerEvolver-frontend)

## Running local ##

* git clone https://github.com/cristianglezm/FlowerEvolver-backend
* cd FlowerEvolver-backend
* use Python 3.12 (the pinned dependencies, e.g. pydantic-core, have no wheels for 3.14 yet)
* pip install -r requirements-dev.txt (runtime dependencies plus pytest, flake8 and requests for the e2e script;
  the images only install requirements.txt)
* `cp .env.example .env` and change it as needed. `.env.example` documents every setting (database, Kafka, Redis,
  rate limit, `METRICS_API_KEY`...). `.env` is ignored by git and is not copied into the image. Variables already in
  the environment win over `.env`.

* Run following commands:
    - export FLASK_APP=manage.py
    - flask db upgrade
    - flask run

* `.devops/reset.sh` runs on every container start and is also the daily reset job when you schedule it. Run it from
  the repo root. Flower rows and `generated/` files belong together, so they are reset together. With
  `ENV=production` it keeps the data: it waits for MySQL, checks the login (any problem is fatal) and upgrades the
  schema. With any other `ENV` it wipes `generated/` and `db/` (sqlite) and upgrades the schema; MySQL is never touched
  outside production, even if `DB_*` are set. `RESET_DATA=true|false` overrides that, e.g. `ENV=production RESET_DATA=true sh .devops/reset.sh` for a daily
  reset of a production setup. The database is set with `DB_HOST`, `DB_NAME`, `DB_USER` and `DB_PASSWD`.

### API documentation ###

* `/docs` is the Swagger UI and `/openapi.json` the OpenAPI 3.1 document of the whole service: the `/api` routes,
  the files, `/health*` and `/metrics` (like `/docs` of FastAPI, e.g. in FlowerEvolver-describe). The Swagger UI files
  come from the `swagger-ui-bundle` package, nothing is loaded from a CDN. `DOCS_ENABLED=false` turns both off.
* The document is written in `app/openapi.py`. `tests/test_openapi.py` fails when a route is not documented, when a
  documented route does not exist, and when a real response does not match its schema, so edit it with the code.
* Every error of the API is JSON: `{"error": "<message>"}`. POST requests need `Content-Type: application/json`
  (even for an empty body: `{}`), otherwise the answer is 415.
* Generate a client from it, e.g. `npx openapi-typescript http://localhost:5000/openapi.json -o api.d.ts`.

### Changing the database schema ###

The schema history is the `migrations/` folder and it is committed. `reset.sh` and the containers only apply it
(`flask db upgrade`), they never create revisions, so existing data is kept when the schema changes.

* after changing a model in `app/models.py`, on your machine:
    - `export FLASK_APP=manage.py`
    - `flask db upgrade` (bring your dev database to the current schema)
    - `flask db migrate -m "what changed"`
    - review the new file in `migrations/versions/` (autogenerate does not detect everything, e.g. renames
      look like a drop plus an add and would lose that column's data) and commit it
* `flask db check` fails when the models and the migrations differ, `.devops/test.sh` and the CI run it.
* `python -m pytest` needs no setup: the tests build their own temporary sqlite database from the committed migrations
  and ignore `ENV`, `KAFKA_ENABLED` and `REDIS_ENABLED` (see `tests/conftest.py`), so they never touch `db/`, MySQL, Redis
  or Kafka. Set `TEST_REDIS_URL` to also run the Redis rate limiter tests.


## Running docker ##

I recommend using the compose file from [frontend](https://github.com/cristianglezm/FlowerEvolver-frontend.git)
read the README-docker.md in [frontend](https://github.com/cristianglezm/FlowerEvolver-frontend.git) repo for how to.

Flowers are generated with the [flowerevolver](https://github.com/cristianglezm/FlowerEvolver-WASM)
python package (installed from requirements.txt), no executable is needed anymore.
PyPI has no musl wheels (and no Linux arm64 ones), so the image compiles it from source in a build stage
(needs network access to GitHub, a few minutes). There is only the Alpine image.

You can also pull the images from this
[repo](https://hub.docker.com/repository/docker/cristianglezm/fe) and change the env variables as needed.

The image does not contain `.env`: pass your settings with `--env-file .env` (after `cp .env.example .env`).

* build image
    * sh .devops/build_docker.sh
* pull image (~300MB)
    * docker pull cristianglezm/fe:backend-alpine-dev
* docker run -dp 5000:5000 --env-file .env --hostname backend -v generated:/app/generated \
    -v db:/app/db cristianglezm/fe:backend-alpine-dev
* browse to http://localhost:5000/api/flowers to get a list of flowers.
    (use webtools to send request, a rest client or the frontend website.)

## Running the full stack (Kafka, Redis, MySQL, Prometheus, Grafana) ##

For local testing of the description pipeline and observability, `docker-compose.yml`
in this repo brings up the backend alongside MySQL, Redis, Kafka (KRaft, single node),
their Prometheus exporters, Prometheus, Grafana, and the
[FlowerEvolver-describe](https://github.com/cristianglezm/FlowerEvolver-describe) service
that actually turns a `descRequests` image into a description.

* cp .env.example .env
* docker compose up -d (podman: podman compose -f docker-compose.yml -f docker-compose.podman.yml up -d)
* backend: http://localhost:5000
* describe: http://localhost:8000
* Prometheus: http://localhost:9090
* Grafana: http://localhost:3000 (admin/admin)

This is a testing/local convenience, not the production topology: backend and describe
are deployed separately (describe's ONNX models are too large for the free tier we
currently use for the backend), so in production they don't share the same Redis or
Kafka instance the way this compose file does for convenience.

`tests/e2e/e2e_test.py` exercises this stack over real HTTP (it is not part of the pytest run,
run it directly with `python tests/e2e/e2e_test.py` once the stack is up), including waiting for a description
to come back through the full backend -> Kafka -> describe -> Kafka -> backend round trip.

## Behind a proxy (PythonAnywhere, nginx) ##

The rate limit is per client address. Behind a reverse proxy or a load balancer `remote_addr` is the address of the
proxy, so every client would share one limit. Set `CLIENT_IP_HEADER` to the header the proxy fills with the client
address (`X-Real-IP` on PythonAnywhere and with the nginx of the compose stack; with `X-Forwarded-For` the last entry,
the one the proxy added, is used). It is read only when the setting is not empty, and a missing or malformed value
falls back to `remote_addr`. Set it only when every request goes through the proxy, see `app/client_ip.py`.

## Monitoring endpoints ##

* GET /healthz - liveness, always 200 if the process is up.
* GET /readyz - readiness, checks the database is reachable.
* GET /health - per-component status (`database`, `kafka`, `redis`); `kafka`/`redis`
  report `not_configured` rather than `error` when `KAFKA_ENABLED`/`REDIS_ENABLED` are false.
* GET /metrics - Prometheus exposition format, requires `Authorization: Bearer <METRICS_API_KEY>`.

## Routes and Responses ##

Every list route takes `limit` and `offset` (pagination). `?count=1` answers `{count: Number}` with **all** the rows
that match (the query filters, not `limit`/`offset`), which is what a pages widget needs to know how many pages to
draw: `pages = ceil(count / limit)`. `count=0` and `count=false` turn it off.

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
