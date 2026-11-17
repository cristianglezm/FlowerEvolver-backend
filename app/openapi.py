"""OpenAPI document of the whole service (api, files, health and metrics) and its Swagger UI.

The document is OpenAPI 3.0.3 and not 3.1 on purpose: the Swagger UI of the swagger-ui-bundle package (4.15.5)
refuses to render a 3.1 document ("does not specify a valid version field"). Keep to the 3.0 subset, e.g. `example`
in a schema, not the `examples` list of JSON Schema.

GET /openapi.json  the document
GET /docs          Swagger UI (its files come from the swagger-ui-bundle package, nothing is loaded from a CDN)

The document is written here, next to the code, and tests/test_openapi.py keeps it honest: every route must
be documented, every documented route must exist, and real responses are validated against these schemas.
"""
import os
import swagger_ui_bundle
from flask import Blueprint, current_app, jsonify, abort, send_from_directory
from .schemas import SharedFlower

openapi_blueprint = Blueprint('openapi', __name__)

API_VERSION = os.getenv('API_VERSION', '1.0.0')
# The files the page needs, with their type. The type is set here and not guessed: Python asks the OS, and on Windows
# the registry often says .js is text/plain, which makes the browser refuse the script.
UI_FILES = {
    'swagger-ui.css': 'text/css',
    'swagger-ui-bundle.js': 'text/javascript',
    'swagger-ui-standalone-preset.js': 'text/javascript',
    'favicon-32x32.png': 'image/png',
    'favicon-16x16.png': 'image/png',
}


def _ref(kind, name):
    return {"$ref": f"#/components/{kind}/{name}"}


def _schema(name):
    return _ref("schemas", name)


def _json(schema):
    return {"application/json": {"schema": schema}}


def _array(name):
    return {"type": "array", "items": _schema(name)}


def _int_path(name, description):
    return {"name": name, "in": "path", "required": True, "description": description, "schema": {"type": "integer", "minimum": 1}}


def _filter(name, schema_type, description):
    return {"name": name, "in": "query", "required": False, "description": description, "schema": {"type": schema_type}}


def _responses(ok, *errors):
    responses = {"200": ok}
    for code in sorted(errors):
        responses[str(code)] = _ref("responses", {400: "BadRequest", 403: "LimitReached", 404: "NotFound", 415: "NotJson", 429: "RateLimited"}[code])
    return responses


def _ok(description, schema):
    return {"description": description, "content": _json(schema)}


LIST_QUERY = [_ref("parameters", "Limit"), _ref("parameters", "Offset"), _ref("parameters", "Count")]
TAGS = [
    {"name": "flowers", "description": "Flowers: random ones, or drawn from a shared genome."},
    {"name": "mutations", "description": "Mutate a flower into a new one."},
    {"name": "descendants", "description": "Reproduce two flowers into a new one."},
    {"name": "descriptions", "description": "Text descriptions of the flowers, generated in the background by FlowerEvolver-describe."},
    {"name": "files", "description": "The genome (.json) and the image (.png) of each flower."},
    {"name": "monitoring", "description": "Health checks and Prometheus metrics."},
]


def _flower_post_body():
    return {
        "required": True,
        "description": "An empty JSON object makes a new random flower. The genome of a shared flower draws that flower. "
                       "The Content-Type must be application/json even when the object is empty.",
        "content": {"application/json": {
            "schema": {"oneOf": [{"type": "object", "maxProperties": 0}, _schema("SharedFlower")]},
            "example": {},
        }},
    }


def _paths():
    over_limit = "Answers 403 once the number of flowers reached FLOWER_LIMIT, until the daily reset. "
    new_flower = "The response is the new flower. A description is requested in the background when Kafka is enabled. "
    return {
        "/api/flowers": {
            "get": {
                "tags": ["flowers"], "operationId": "listFlowers", "summary": "List flowers",
                "parameters": LIST_QUERY + [_filter("id", "integer", "Only the flower with this id."),
                                            _filter("genome", "string", "Only flowers with this genome file name."),
                                            _filter("image", "string", "Only flowers with this image file name.")],
                "responses": _responses(_ok("The flowers, or only their count when `count` is present.", {"oneOf": [_schema("FlowerList"), _schema("Count")]}), 400, 429),
            },
            "post": {
                "tags": ["flowers"], "operationId": "createFlower", "summary": "Make a new flower",
                "description": new_flower + over_limit, "requestBody": _flower_post_body(),
                "responses": _responses(_ok("The new flower.", _schema("Flower")), 400, 403, 415, 429),
            },
        },
        "/api/flowers/{flower_id}": {
            "get": {
                "tags": ["flowers"], "operationId": "getFlower", "summary": "Get a flower",
                "parameters": [_int_path("flower_id", "Id of the flower.")],
                "responses": _responses(_ok("The flower.", _schema("Flower")), 404, 429),
            },
        },
        "/api/mutations": {
            "get": {
                "tags": ["mutations"], "operationId": "listMutations", "summary": "List mutations",
                "parameters": LIST_QUERY + [_filter("id", "integer", "Only the mutation that made this flower."),
                                            _filter("original", "integer", "Only mutations of this flower.")],
                "responses": _responses(_ok("The mutations, or only their count when `count` is present.", {"oneOf": [_schema("MutationList"), _schema("Count")]}), 400, 429),
            },
            "post": {
                "tags": ["mutations"], "operationId": "createMutation", "summary": "Mutate a flower",
                "description": new_flower + over_limit + "404 when the original flower does not exist.",
                "requestBody": {"required": True, "content": _json(_schema("MutationRequest"))},
                "responses": _responses(_ok("The new, mutated flower.", _schema("Flower")), 400, 403, 404, 415, 429),
            },
        },
        "/api/mutations/{mutation_original}": {
            "get": {
                "tags": ["mutations"], "operationId": "listMutationsOfFlower", "summary": "Flowers that are mutations of a flower",
                "parameters": [_int_path("mutation_original", "Id of the original flower.")] + LIST_QUERY,
                "responses": _responses(_ok("The mutated flowers, or only their count when `count` is present.", {"oneOf": [_array("Flower"), _schema("Count")]}), 400, 404, 429),
            },
        },
        "/api/descendants": {
            "get": {
                "tags": ["descendants"], "operationId": "listDescendants", "summary": "List descendants",
                "parameters": LIST_QUERY + [_filter("id", "integer", "Only the descendant with this flower id."),
                                            _filter("father", "integer", "Only descendants of this father."),
                                            _filter("mother", "integer", "Only descendants of this mother.")],
                "responses": _responses(_ok("The descendants, or only their count when `count` is present.", {"oneOf": [_schema("DescendantList"), _schema("Count")]}), 400, 429),
            },
            "post": {
                "tags": ["descendants"], "operationId": "createDescendant", "summary": "Reproduce two flowers",
                "description": new_flower + over_limit + "404 when the father or the mother does not exist.",
                "requestBody": {"required": True, "content": _json(_schema("DescendantRequest"))},
                "responses": _responses(_ok("The new flower.", _schema("Flower")), 400, 403, 404, 415, 429),
            },
        },
        "/api/descendants/{father}": {
            "get": {
                "tags": ["descendants"], "operationId": "listDescendantsOfParent", "summary": "Flowers that have this flower as father or mother",
                "parameters": [_int_path("father", "Id of the parent flower (as father or as mother).")] + LIST_QUERY,
                "responses": _responses(_ok("The descendants, or only their count when `count` is present.", {"oneOf": [_array("Flower"), _schema("Count")]}), 400, 404, 429),
            },
        },
        "/api/descendants/{father}/{mother}": {
            "get": {
                "tags": ["descendants"], "operationId": "listDescendantsOfParents", "summary": "Flowers of a pair of parents",
                "parameters": [_int_path("father", "Id of the father."), _int_path("mother", "Id of the mother.")] + LIST_QUERY,
                "responses": _responses(_ok("The descendants, or only their count when `count` is present.", {"oneOf": [_array("Flower"), _schema("Count")]}), 400, 404, 429),
            },
        },
        "/api/descriptions": {
            "get": {
                "tags": ["descriptions"], "operationId": "listDescriptions", "summary": "List descriptions",
                "parameters": LIST_QUERY + [_filter("id", "integer", "Only the description of this flower id."),
                                            _filter("description", "string", "Only descriptions with exactly this text.")],
                "responses": _responses(_ok("The descriptions, or only their count when `count` is present.", {"oneOf": [_schema("DescriptionList"), _schema("Count")]}), 400, 429),
            },
        },
        "/api/descriptions/{desc_id}": {
            "get": {
                "tags": ["descriptions"], "operationId": "getDescription", "summary": "Get the description of a flower",
                "description": "404 also while the description is not ready yet (or when Kafka is disabled).",
                "parameters": [_int_path("desc_id", "Id of the flower.")],
                "responses": _responses(_ok("The description.", _schema("Description")), 404, 429),
            },
        },
        "/generated/{filepath}": {
            "get": {
                "tags": ["files"], "operationId": "getGeneratedFile", "summary": "Image or genome of a flower",
                "description": "`<id>.png` is the image, `<id>.json` the genome (it can be shared with POST /api/flowers).",
                "parameters": [{"name": "filepath", "in": "path", "required": True, "schema": {"type": "string", "example": "1.png"}}],
                "responses": {"200": {"description": "The file.", "content": {"image/png": {"schema": {"type": "string", "format": "binary"}},
                                                                              "application/json": {"schema": {"type": "object"}}}},
                              "404": _ref("responses", "NotFound")},
            },
        },
        "/download/{filepath}": {
            "get": {
                "tags": ["files"], "operationId": "downloadGeneratedFile", "summary": "Download the image or genome of a flower",
                "description": "Same files as /generated, sent as an attachment.",
                "parameters": [{"name": "filepath", "in": "path", "required": True, "schema": {"type": "string", "example": "1.json"}}],
                "responses": {"200": {"description": "The file as an attachment.", "headers": {"Content-Disposition": {"schema": {"type": "string"}}},
                                      "content": {"image/png": {"schema": {"type": "string", "format": "binary"}},
                                                  "application/json": {"schema": {"type": "object"}}}},
                              "404": _ref("responses", "NotFound")},
            },
        },
        "/healthz": {
            "get": {"tags": ["monitoring"], "operationId": "healthz", "summary": "Liveness",
                    "description": "The process is running. It does not check any dependency.",
                    "responses": {"200": _ok("Alive.", _schema("Status"))}},
        },
        "/readyz": {
            "get": {"tags": ["monitoring"], "operationId": "readyz", "summary": "Readiness",
                    "description": "Ready when the database answers. Kafka and Redis do not matter here.",
                    "responses": {"200": _ok("Ready.", _schema("Status")), "503": _ok("The database does not answer.", _schema("Status"))}},
        },
        "/health": {
            "get": {"tags": ["monitoring"], "operationId": "health", "summary": "Health of every component",
                    "description": "Kafka is reported per worker process (each one has its own producer and consumer), so right after "
                                   "a start it can answer `connecting` for a few seconds.",
                    "responses": {"200": _ok("Everything configured is ok.", _schema("Health")),
                                  "503": _ok("Something configured is not ok (status `degraded`).", _schema("Health"))}},
        },
        "/metrics": {
            "get": {"tags": ["monitoring"], "operationId": "metrics", "summary": "Prometheus metrics",
                    "description": "Needs `Authorization: Bearer <METRICS_API_KEY>`. Not meant to be exposed to the internet.",
                    "security": [{"bearerAuth": []}],
                    "responses": {"200": {"description": "Prometheus text format.", "content": {"text/plain": {"schema": {"type": "string"}}}},
                                  "401": {"description": "Missing or wrong key.", "content": _json(_schema("Error"))}}},
        },
    }


def _components():
    shared = SharedFlower.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas = dict(shared.pop("$defs", {}))
    schemas["SharedFlower"] = shared

    def obj(strict=True, **properties):
        schema = {"type": "object", "required": list(properties), "properties": properties}
        if strict:
            schema["additionalProperties"] = False
        return schema

    integer = {"type": "integer"}
    schemas.update({
        "Error": obj(error={"type": "string"}),
        "Count": obj(count=integer),
        "Flower": obj(id=integer, genome={"type": "string", "example": "1.json"}, image={"type": "string", "example": "1.png"}),
        "FlowerList": obj(count=integer, flowers=_array("Flower")),
        "Mutation": obj(id=integer, original=integer),
        "MutationList": obj(count=integer, mutations=_array("Mutation")),
        "MutationRequest": obj(strict=False, original=integer),
        "Descendant": obj(id=integer, father=integer, mother=integer),
        "DescendantList": obj(count=integer, descendants=_array("Descendant")),
        "DescendantRequest": obj(strict=False, father=integer, mother=integer),
        "Description": obj(id=integer, description={"type": "string"}),
        "DescriptionList": obj(count=integer, descriptions=_array("Description")),
        "Status": obj(status={"type": "string"}),
        "Health": obj(status={"enum": ["ok", "degraded"]}, components=obj(
            database={"enum": ["ok", "error"]},
            kafka={"enum": ["not_configured", "ok", "connecting", "error"]},
            redis={"enum": ["not_configured", "ok", "error"]})),
    })

    def error(description):
        return {"description": description, "content": _json(_schema("Error"))}

    return {
        "schemas": schemas,
        "parameters": {
            "Limit": {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 0},
                      "description": "Maximum number of rows. Note that `limit=0` returns no rows."},
            "Offset": {"name": "offset", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 0},
                       "description": "Rows to skip."},
            "Count": {"name": "count", "in": "query", "required": False, "allowEmptyValue": True, "schema": {"type": "string"},
                      "description": "When present (`count=1`; `0` and `false` turn it off), the response is only `{\"count\": n}`: all the rows that match, "
                                     "ignoring limit and offset. It is what a pages widget needs to know how many pages to draw."},
        },
        "responses": {
            "BadRequest": error("Invalid input: an unknown filter, a `limit` or `offset` that is not a non-negative integer, a missing "
                                "field, or a genome that cannot be drawn."),
            "LimitReached": error("The number of flowers reached FLOWER_LIMIT, wait for the daily reset."),
            "NotFound": error("The flower, file or route does not exist."),
            "NotJson": error("The request does not have the `application/json` Content-Type."),
            "RateLimited": error("Too many requests: RATE_LIMIT_TIMES per RATE_LIMIT_SECONDS for each client ip and route."),
        },
        "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
    }


def build_spec():
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "FlowerEvolver Backend",
            "version": API_VERSION,
            "description": "Makes, mutates and reproduces flowers, stores them and their descriptions. Every error of the API is JSON: "
                           "`{\"error\": \"<message>\"}`. Requests to /api are rate limited (429).",
        },
        "tags": TAGS,
        "paths": _paths(),
        "components": _components(),
    }


@openapi_blueprint.before_request
def docs_enabled():
    if not current_app.config['DOCS_ENABLED']:
        abort(404)


@openapi_blueprint.route('/openapi.json')
def openapi_json():
    return jsonify(build_spec())


@openapi_blueprint.route('/docs')
@openapi_blueprint.route('/docs/')
def docs():
    return DOCS_PAGE


@openapi_blueprint.route('/docs/assets/<path:filename>')
def docs_assets(filename):
    if filename not in UI_FILES:
        abort(404)
    return send_from_directory(swagger_ui_bundle.swagger_ui_path, filename, mimetype=UI_FILES[filename], max_age=86400)


DOCS_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>FlowerEvolver Backend API</title>
  <link rel="icon" href="/docs/assets/favicon-32x32.png">
  <link rel="stylesheet" href="/docs/assets/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="/docs/assets/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({url: "/openapi.json", dom_id: "#swagger-ui", deepLinking: true, tryItOutEnabled: true});
  </script>
</body>
</html>
"""
