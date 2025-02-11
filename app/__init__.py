import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import default_exceptions


db = SQLAlchemy()


def create_app():
    app = Flask(__name__, instance_relative_config=False)
    env = os.getenv("ENV", default="development")
    if env == "production":
        print('|> Loaded production config')
        app.config.from_object('config.ProductionConfig')
    else:
        print('|> Loaded development config')
        app.config.from_object('config.Config')

    @app.errorhandler(Exception)
    def handle_error(e):
        code = 500
        if isinstance(e, HTTPException):
            code = e.code
        return jsonify(error=str(e)), code
    for ex in default_exceptions:
        app.register_error_handler(ex, handle_error)
    allowed_origins = os.getenv("ORIGINS", default="*").split(",")
    print(f"|> Using {allowed_origins} for origins")
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
    db.init_app(app)
    api = Api(app)
    api.prefix = '/api'
    with app.app_context():
        from .models import (flowers_blueprint, ancestors_blueprint, mutations_blueprint)
        from .resources import (FlowerResource, AncestorResource, MutationResource)
        from .routes import generated, download
        api.add_resource(FlowerResource, '/flowers', '/flowers/<int:flower_id>')
        api.add_resource(MutationResource, '/mutations', '/mutations/<int:mutation_original>')
        api.add_resource(AncestorResource, '/ancestors', '/ancestors/<int:father>', '/ancestors/<int:father>/<int:mother>')

        app.register_blueprint(flowers_blueprint)
        app.register_blueprint(ancestors_blueprint)
        app.register_blueprint(mutations_blueprint)
    return app
