import os

# The tests run on the sqlite database made by `flask db upgrade` and must never reach real
# services, whatever the shell or .env say (the compose stack publishes redis and kafka on
# localhost). Redis keeps its counters outside the process, so with REDIS_ENABLED the tests
# rate limit each other and leave keys behind, and a kafka consumer would join the group of the
# real stack. This runs before `config` is imported, and load_dotenv never overrides it.
os.environ['ENV'] = 'development'
os.environ['KAFKA_ENABLED'] = 'false'
os.environ['REDIS_ENABLED'] = 'false'
