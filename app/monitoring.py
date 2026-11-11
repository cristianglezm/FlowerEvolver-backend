import os
import structlog
from flask import Blueprint, jsonify, request, Response, current_app
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry, multiprocess
from prometheus_client.core import GaugeMetricFamily
from sqlalchemy import text
from . import db
from .client_ip import client_ip
from .background import kafka_producer, kafka_consumer
from .repositories import flower_repository, description_repository

logger = structlog.get_logger(__name__)

monitoring_blueprint = Blueprint('monitoring', __name__)


class DatabaseGauges:
    """flowers_total, descriptions_total and flower_limit, computed when /metrics is scraped."""

    def __init__(self, app):
        self.app = app

    def collect(self):
        try:
            with self.app.app_context():
                flowers = flower_repository.total_count()
                descriptions = description_repository.total_count()
                limit = int(self.app.config['FLOWER_LIMIT'])
        except Exception as e:
            # no gauges is better than a failed scrape, the up/health metrics tell about the db
            logger.error("metrics_database_gauges_failed", error=str(e))
            return
        for name, doc, value in (
                ("flowers_total", "Flowers stored in the database.", flowers),
                ("descriptions_total", "Descriptions stored in the database.", descriptions),
                ("flower_limit", "Flowers allowed before new ones are refused (FLOWER_LIMIT).", limit)):
            gauge = GaugeMetricFamily(name, doc)
            gauge.add_metric([], value)
            yield gauge


@monitoring_blueprint.route('/healthz')
def healthz():
    return jsonify(status='ok')


@monitoring_blueprint.route('/readyz')
def readyz():
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify(status='ready')
    except Exception as e:
        logger.error("readyz_db_check_failed", error=str(e))
        return jsonify(status='not ready'), 503


def _database_status():
    try:
        db.session.execute(text('SELECT 1'))
        return 'ok'
    except Exception as e:
        logger.error("health_db_check_failed", error=str(e))
        return 'error'


def _kafka_status():
    """not_configured | ok | connecting | error

    ok          the producer and the consumer of this worker are connected to the cluster
    connecting  they are still starting (kafka and the other services start slowly)
    error       a thread died or the last connection attempt failed
    """
    if not current_app.config['KAFKA_ENABLED']:
        return 'not_configured'
    if kafka_producer.is_connected() and kafka_consumer.is_connected():
        return 'ok'
    if not (kafka_producer.is_alive() or kafka_producer.is_connected()) or not kafka_consumer.is_alive():
        logger.error("health_kafka_thread_not_running")
        return 'error'
    error = kafka_producer.last_error() if not kafka_producer.is_connected() else kafka_consumer.last_error()
    if error:
        logger.warning("health_kafka_not_connected", error=error)
        return 'error'
    return 'connecting'


def _redis_status():
    if not current_app.config['REDIS_ENABLED']:
        return 'not_configured'
    redis_client = current_app.extensions.get('redis_client')
    if redis_client is None:
        return 'error'
    try:
        redis_client.ping()
        return 'ok'
    except Exception as e:
        logger.error("health_redis_check_failed", error=str(e))
        return 'error'


@monitoring_blueprint.route('/health')
def health():
    components = {
        'database': _database_status(),
        'kafka': _kafka_status(),
        'redis': _redis_status(),
    }
    healthy = all(status in ('ok', 'not_configured') for status in components.values())
    return jsonify(status='ok' if healthy else 'degraded', components=components), 200 if healthy else 503


def _metrics_api_key_valid():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return False
    return auth[len('Bearer '):] == current_app.config['METRICS_API_KEY']


@monitoring_blueprint.route('/metrics')
def metrics():
    if not _metrics_api_key_valid():
        logger.warning("metrics_unauthorized", client_ip=client_ip(request))
        return jsonify(error='unauthorized'), 401
    if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    logger.info("metrics_scraped")
    # the capacity gauges are read from the database at scrape time, so they are exact and
    # do not depend on which worker made the flowers (counters are summed across workers)
    database_registry = CollectorRegistry()
    database_registry.register(DatabaseGauges(current_app._get_current_object()))
    return Response(generate_latest(registry) + generate_latest(database_registry), mimetype=CONTENT_TYPE_LATEST)
