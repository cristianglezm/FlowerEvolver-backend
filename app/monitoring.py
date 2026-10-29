import os
import structlog
from flask import Blueprint, jsonify, request, Response, current_app
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY, CollectorRegistry, multiprocess
from sqlalchemy import text
from . import db
from .background import kafka_producer, kafka_consumer

logger = structlog.get_logger(__name__)

monitoring_blueprint = Blueprint('monitoring', __name__)


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
    if not current_app.config['KAFKA_ENABLED']:
        return 'not_configured'
    producer = kafka_producer.get_producer()
    if producer is None or not producer.bootstrap_connected():
        return 'error'
    if not kafka_consumer.is_alive():
        return 'error'
    return 'ok'


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
        logger.warning("metrics_unauthorized", client_ip=request.remote_addr)
        return jsonify(error='unauthorized'), 401
    if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    logger.info("metrics_scraped")
    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)
