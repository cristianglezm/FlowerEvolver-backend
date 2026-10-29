import structlog
from flask import jsonify
from flask_restful import Api
from werkzeug.exceptions import HTTPException

logger = structlog.get_logger(__name__)


def error_response(message, status):
    """Every error of the API has the same shape: {"error": "<message>"}."""
    return jsonify(error=message), status


def _message(e):
    # flask-restful keeps the details of a failed argument in e.data, e.g. {'message': {'original': '...'}}
    data = getattr(e, 'data', None)
    if isinstance(data, dict) and 'message' in data:
        message = data['message']
        if isinstance(message, dict):
            return '; '.join(str(value) for value in message.values())
        return str(message)
    return e.description


class JsonErrorApi(Api):
    """flask-restful answers {"message": ...} on its routes, the rest of the app answers {"error": ...}."""

    def handle_error(self, e):
        if isinstance(e, HTTPException):
            return error_response(_message(e), e.code)
        logger.error("unhandled_exception", error=str(e))
        return error_response("internal server error", 500)
