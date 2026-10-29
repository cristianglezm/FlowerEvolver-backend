import os


def _bool_env(name, default=False):
    return os.getenv(name, default=str(default)).strip().lower() in ('true', '1', 'yes')


class Config(object):
    ENV = 'development'
    DEBUG = True
    BUNDLE_ERRORS = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../db/FlowerEvolver.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GENERATED_FOLDER = 'generated/'
    FLOWER_LIMIT = os.getenv('FLOWER_LIMIT', default=5000)
    # SECRET_KEY = ''

    KAFKA_ENABLED = _bool_env('KAFKA_ENABLED', default=False)
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', default='localhost:9092')
    KAFKA_REQUEST_TOPIC = os.getenv('KAFKA_REQUEST_TOPIC', default='descRequests')
    KAFKA_RESPONSE_TOPIC = os.getenv('KAFKA_RESPONSE_TOPIC', default='descResponses')

    REDIS_ENABLED = _bool_env('REDIS_ENABLED', default=False)
    REDIS_URL = os.getenv('REDIS_URL', default='redis://localhost:6379')

    RATE_LIMIT_TIMES = int(os.getenv('RATE_LIMIT_TIMES', default=5))
    RATE_LIMIT_SECONDS = int(os.getenv('RATE_LIMIT_SECONDS', default=10))

    METRICS_API_KEY = os.getenv('METRICS_API_KEY', default='sk_change_key')


class ProductionConfig(Config):
    DEBUG = False
    ENV = 'production'
    FLOWER_LIMIT = os.getenv('FLOWER_LIMIT', default=5000)
    SQLALCHEMY_DATABASE_URI = f"mysql://{os.getenv('USER')}:{os.getenv('PASSWD')}@{os.getenv('HOST')}/{os.getenv('DB')}"
    SQLALCHEMY_POOL_RECYCLE = 299
    SQLALCHEMY_POOL_TIMEOUT = 20
    # @property
    # def SECRET_KEY():
    #    SECRET_KEY = os.environ.get("SECRET_KEY")
    #    if not SECRET_KEY:
    #        raise ValueError("No SECRET_KEY set for Flask application")
    #    return os.environ.get("SECRET_KEY")
