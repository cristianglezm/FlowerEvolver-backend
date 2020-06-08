from flask import Flask, jsonify, send_from_directory
from flask import current_app

@current_app.route('/generated/<string:filepath>')
def generated(filepath):
    return send_from_directory(current_app.config['GENERATED_FOLDER'], filepath, as_attachment=False)

@current_app.route('/download/<string:filepath>')
def download(filepath):
    return send_from_directory(current_app.config['GENERATED_FOLDER'], filepath, as_attachment=True)