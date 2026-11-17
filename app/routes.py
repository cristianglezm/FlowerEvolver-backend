from flask import Blueprint, current_app, send_from_directory
from flask_cors import cross_origin

# a blueprint, registered by create_app(): routes added with @current_app.route in a module only exist in the
# first app created in the process, because Python imports the module once
files_blueprint = Blueprint('files', __name__)


@files_blueprint.route('/generated/<string:filepath>')
@cross_origin()
def generated(filepath):
    return send_from_directory("../" + current_app.config['GENERATED_FOLDER'], filepath, as_attachment=False)


@files_blueprint.route('/download/<string:filepath>')
@cross_origin()
def download(filepath):
    return send_from_directory("../" + current_app.config['GENERATED_FOLDER'], filepath, as_attachment=True)
