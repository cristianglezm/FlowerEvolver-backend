import os
import structlog
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import default_exceptions

from .errors import JsonErrorApi
from .logging_config import configure_logging
from .middleware import register_metrics_middleware
from .metrics import init_metric_labels
from .rate_limit import register_rate_limiting


db = SQLAlchemy()
logger = structlog.get_logger(__name__)


def create_app():
    configure_logging()
    app = Flask(__name__, instance_relative_config=False)
    env = os.getenv("ENV", default="development")
    if env == "production":
        logger.info("config_loaded", env="production")
        app.config.from_object('config.ProductionConfig')
    else:
        logger.info("config_loaded", env="development")
        app.config.from_object('config.Config')

    @app.errorhandler(Exception)
    def handle_error(e):
        if isinstance(e, HTTPException):
            return jsonify(error=e.description), e.code
        logger.error("unhandled_exception", error=str(e))
        return jsonify(error="internal server error"), 500
    for ex in default_exceptions:
        app.register_error_handler(ex, handle_error)
    allowed_origins = os.getenv("ORIGINS", default="*").split(",")
    logger.info("cors_configured", allow_origins=allowed_origins)
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
    init_metric_labels(app.config)
    register_metrics_middleware(app)
    register_rate_limiting(app)
    db.init_app(app)
    api = JsonErrorApi(app)
    api.prefix = '/api'
    with app.app_context():
        from .api import FlowerResource, DescendantResource, MutationResource, DescriptionsResource
        from .routes import files_blueprint
        from .monitoring import monitoring_blueprint
        from .openapi import openapi_blueprint
        from .background import kafka_producer, kafka_consumer
        # a resource serves its collection and its items, but only the collection can POST: with a single
        # registration POST /flowers/1 would be accepted and crash (500) instead of answering 405
        api.add_resource(FlowerResource, '/flowers', endpoint='flowers')
        api.add_resource(FlowerResource, '/flowers/<int:flower_id>', endpoint='flower', methods=['GET'])
        api.add_resource(MutationResource, '/mutations', endpoint='mutations')
        api.add_resource(MutationResource, '/mutations/<int:mutation_original>', endpoint='mutation', methods=['GET'])
        api.add_resource(DescendantResource, '/descendants', endpoint='descendants')
        api.add_resource(DescendantResource, '/descendants/<int:father>', '/descendants/<int:father>/<int:mother>',
                         endpoint='descendant', methods=['GET'])
        api.add_resource(DescriptionsResource, '/descriptions', '/descriptions/<int:desc_id>')
        app.register_blueprint(files_blueprint)
        app.register_blueprint(monitoring_blueprint)
        app.register_blueprint(openapi_blueprint)
        kafka_producer.init_producer(app)
        kafka_consumer.start_consumer(app)
    return app
