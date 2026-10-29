import time
from flask import request, g
from .metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_LATENCY_SECONDS


def register_metrics_middleware(app):
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def track_request_metrics(response):
        endpoint = request.url_rule.rule if request.url_rule else request.path
        if hasattr(g, 'start_time'):
            latency = time.time() - g.start_time
            HTTP_REQUEST_LATENCY_SECONDS.labels(endpoint=endpoint, method=request.method).observe(latency)
        HTTP_REQUESTS_TOTAL.labels(endpoint=endpoint, method=request.method, status_code=response.status_code).inc()
        return response
