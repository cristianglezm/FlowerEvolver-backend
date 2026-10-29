import threading
import structlog
from flask import request, jsonify
from pyrate_limiter import BucketFactory, Duration, InMemoryBucket, Limiter, Rate, RateItem

logger = structlog.get_logger(__name__)

RATE_LIMIT_KEY_PREFIX = "flowerevolver-backend-rate-limit"
# upper bound of clients tracked in memory by one process
MAX_TRACKED_CLIENTS = 10_000


def _rates(app):
    return [Rate(app.config['RATE_LIMIT_TIMES'], app.config['RATE_LIMIT_SECONDS'] * Duration.SECOND)]


class PerClientBucketFactory(BucketFactory):
    """One bucket per key (client ip + route).

    ``Limiter(bucket)`` would share a single bucket between every key, so one noisy
    client would exhaust the limit of everybody else. This factory gives each key its
    own bucket and keeps the number of tracked keys bounded.
    """

    def __init__(self, build_bucket, max_buckets=MAX_TRACKED_CLIENTS, schedule_leak=True):
        self._build_bucket = build_bucket
        self._max_buckets = max_buckets
        self._schedule_leak = schedule_leak
        self._buckets = {}
        self._lock = threading.Lock()

    def _bucket_for(self, name):
        with self._lock:
            bucket = self._buckets.get(name)
            if bucket is None:
                if len(self._buckets) >= self._max_buckets:
                    self._make_room()
                bucket = self._build_bucket(name)
                self._buckets[name] = bucket
                if self._schedule_leak:
                    self.schedule_leak(bucket)
            return bucket

    def _make_room(self):
        # first drop clients that are not limited right now, then the oldest ones
        for name in [n for n, b in self._buckets.items() if b.count() == 0]:
            self._drop(name)
        overflow = len(self._buckets) - self._max_buckets + 1
        for name in list(self._buckets)[:max(overflow, 0)]:
            self._drop(name)

    def _drop(self, name):
        bucket = self._buckets.pop(name)
        if self._schedule_leak:
            self.dispose(bucket)

    def wrap_item(self, name, weight=1):
        return RateItem(name, self._bucket_for(name).now(), weight=weight)

    def get(self, item):
        return self._bucket_for(item.name)

    def tracked(self):
        return len(self._buckets)


def _build_in_memory_limiter(app):
    rates = _rates(app)
    return Limiter(PerClientBucketFactory(lambda name: InMemoryBucket(rates))), None


def _build_redis_limiter(app):
    import redis
    from pyrate_limiter import RedisBucket
    rates = _rates(app)
    redis_client = redis.Redis.from_url(app.config['REDIS_URL'])
    redis_client.ping()

    def build_bucket(name):
        return RedisBucket.init(rates, redis_client, f"{RATE_LIMIT_KEY_PREFIX}:{name}")

    # redis leaks old entries itself, only the keys need to expire (see enforce_rate_limit)
    return Limiter(PerClientBucketFactory(build_bucket, schedule_leak=False)), redis_client


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


def rate_limit_key(req):
    # the route template (/api/flowers/<int:flower_id>), not the path: otherwise every id
    # would get its own bucket and walking /api/flowers/1, /2, /3... would never be limited
    route = req.url_rule.rule if req.url_rule else "unmatched"
    return f"{req.remote_addr}:{route}"


def register_rate_limiting(app):
    limiter, redis_client = build_rate_limiter(app)
    app.extensions['rate_limiter'] = limiter
    app.extensions['redis_client'] = redis_client
    redis_ttl = app.config['RATE_LIMIT_SECONDS'] * 2

    @app.before_request
    def enforce_rate_limit():
        if not request.path.startswith('/api/'):
            return
        key = rate_limit_key(request)
        try:
            allowed = limiter.try_acquire(key, blocking=False)
            if redis_client is not None:
                redis_client.expire(f"{RATE_LIMIT_KEY_PREFIX}:{key}", redis_ttl)
        except Exception as e:
            # a broken limiter must not take the api down with it
            logger.error("rate_limiter_failed", error=str(e))
            return
        if not allowed:
            logger.warning("rate_limit_exceeded", client_ip=request.remote_addr, path=request.path)
            return jsonify(error="Too Many Requests"), 429
