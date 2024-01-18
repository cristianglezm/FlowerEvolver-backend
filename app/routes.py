from flask import Flask, jsonify, send_from_directory
from flask import current_app
from flask_restful import request
from flask_cors import cross_origin

@current_app.route('/generated/<string:filepath>')
@cross_origin()
def generated(filepath):
    return send_from_directory("../" + current_app.config['GENERATED_FOLDER'], filepath, as_attachment=False)

@current_app.route('/download/<string:filepath>')
@cross_origin()
def download(filepath):
    return send_from_directory("../" + current_app.config['GENERATED_FOLDER'], filepath, as_attachment=True)
