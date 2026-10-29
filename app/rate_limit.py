import structlog
from flask import request, jsonify
from pyrate_limiter import Duration, InMemoryBucket, Limiter, Rate

logger = structlog.get_logger(__name__)

RATE_LIMIT_BUCKET_KEY = "flowerevolver-backend-rate-limit"


def _rates(app):
    return [Rate(app.config['RATE_LIMIT_TIMES'], app.config['RATE_LIMIT_SECONDS'] * Duration.SECOND)]


def _build_in_memory_limiter(app):
    bucket = InMemoryBucket(_rates(app))
    return Limiter(bucket), None


def _build_redis_limiter(app):
    import redis
    from pyrate_limiter import RedisBucket
    redis_client = redis.Redis.from_url(app.config['REDIS_URL'])
    redis_client.ping()
    bucket = RedisBucket.init(_rates(app), redis_client, RATE_LIMIT_BUCKET_KEY)
    return Limiter(bucket), redis_client


def build_rate_limiter(app):
    if app.config['REDIS_ENABLED']:
        try:
            limiter, redis_client = _build_redis_limiter(app)
            logger.info("rate_limiter_backend", backend="redis")
            return limiter, redis_client
        except Exception as e:
            logger.warning("redis_rate_limiter_unavailable", error=str(e))
    logger.info("rate_limiter_backend", backend="in-memory")
    return _build_in_memory_limiter(app)


def register_rate_limiting(app):
    limiter, redis_client = build_rate_limiter(app)
    app.extensions['rate_limiter'] = limiter
    app.extensions['redis_client'] = redis_client

    @app.before_request
    def enforce_rate_limit():
        if not request.path.startswith('/api/'):
            return
        key = f"{request.remote_addr}:{request.path}"
        if not limiter.try_acquire(key, blocking=False):
            logger.warning("rate_limit_exceeded", client_ip=request.remote_addr, path=request.path)
            return jsonify(error="Too Many Requests"), 429
