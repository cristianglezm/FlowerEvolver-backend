import os
import structlog
from flask import Flask, jsonify
from flask_cors import CORS
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import default_exceptions

from .logging_config import configure_logging
from .middleware import register_metrics_middleware
from .rate_limit import register_rate_limiting


db = SQLAlchemy()
logger = structlog.get_logger(__name__)


def create_app(start_background=True):
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
    register_metrics_middleware(app)
    register_rate_limiting(app)
    db.init_app(app)
    api = Api(app)
    api.prefix = '/api'
    with app.app_context():
        from .api import FlowerResource, DescendantResource, MutationResource, DescriptionsResource
        from .routes import generated, download
        from .monitoring import monitoring_blueprint
        from .background import kafka_producer, kafka_consumer
        api.add_resource(FlowerResource, '/flowers', '/flowers/<int:flower_id>')
        api.add_resource(MutationResource, '/mutations', '/mutations/<int:mutation_original>')
        api.add_resource(DescendantResource, '/descendants', '/descendants/<int:father>', '/descendants/<int:father>/<int:mother>')
        api.add_resource(DescriptionsResource, '/descriptions', '/descriptions/<int:desc_id>')
        app.register_blueprint(monitoring_blueprint)
        if start_background:
            kafka_producer.init_producer(app)
            kafka_consumer.start_consumer(app)
    return app
