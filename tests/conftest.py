import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# The tests must never reach real services or real data, whatever the shell or .env say (the compose stack
# publishes redis and kafka on localhost, ENV may be production). Redis keeps its counters outside the process,
# so with REDIS_ENABLED the tests rate limit each other and leave keys behind, and a kafka consumer would join
# the group of the real stack. This runs before `config` is imported, and load_dotenv never overrides it.
os.environ['ENV'] = 'development'
os.environ['KAFKA_ENABLED'] = 'false'
os.environ['REDIS_ENABLED'] = 'false'
# the rate limiter has its own tests, the others make many requests in a few seconds
os.environ['RATE_LIMIT_TIMES'] = '100000'
os.environ['DOCS_ENABLED'] = 'true'

# a database of their own: nobody has to run reset.sh or `flask db upgrade` first, and db/ is never touched
_database_dir = tempfile.mkdtemp(prefix='fe-tests-')
atexit.register(shutil.rmtree, _database_dir, ignore_errors=True)
os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{_database_dir}/FlowerEvolver.db'


@pytest.fixture(scope='session', autouse=True)
def database():
    """The schema comes from the committed migrations, like in reset.sh and the containers."""
    from flask_migrate import Migrate, upgrade
    from app import create_app, db
    app = create_app()
    Migrate(app, db)  # what manage.py does, the app factory does not register it
    with app.app_context():
        upgrade(directory=str(ROOT / 'migrations'))
