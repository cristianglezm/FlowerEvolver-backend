from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import default_exceptions
from pathlib import Path
import settings

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    return jsonify(error=str(e)), code

for ex in default_exceptions:
    app.register_error_handler(ex, handle_error)


app.config['SQLALCHEMY_DATABASE_URI'] = settings.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = settings.SQLALCHEMY_TRACK_MODIFICATIONS
app.config['BUNDLE_ERRORS'] = settings.BUNDLE_ERRORS
app.config['GENERATED_FOLDER'] = settings.GENERATED_FOLDER

db = SQLAlchemy(app)
from models import *
migrate = Migrate(app, db)
api = Api(app)
api.prefix = '/api'

@app.route('/generated/<string:filepath>')
def generated(filepath):
    return send_from_directory(app.config['GENERATED_FOLDER'], filepath, as_attachment=False)

@app.route('/download/<string:filepath>')
def download(filepath):
    return send_from_directory(app.config['GENERATED_FOLDER'], filepath, as_attachment=True)