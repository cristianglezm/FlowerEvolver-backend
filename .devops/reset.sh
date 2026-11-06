#!/bin/sh
# Start up script of the containers and daily reset job (cron at 00:00 UTC on PythonAnywhere).
#
# The flower rows and generated/<id>.png|json are tied by the flower id (mutations and
# descendants read the .json of the parent), so they are always reset together:
#   - generated/            images and genomes
#   - MySQL database $DB    on $HOST (the database host): dropped and created again
#   - db/                   sqlite files, used when ENV is not production
# and then the flask migrations recreate the schema. Nothing else creates the tables.
#
# What is reset depends on ENV, because the compose stack runs this on EVERY container start
# and keeps db_data and generated_data volumes so that a restart keeps the flowers:
#   ENV=production   keeps the data. Waits for MySQL, checks that DB_USER can log in
#                    (any MySQL problem is fatal), then only migrates.
#   any other ENV    resets everything (the daily job). A MySQL problem is only a warning
#                    here (dev machines and CI have no MySQL) and the migrations go to sqlite.
# RESET_DATA=true|false overrides that, e.g. a daily reset of a production setup:
#   ENV=production RESET_DATA=true sh .devops/reset.sh   (waits for MySQL, wipes, migrates MySQL)
#
# Run it from the repo root (relative paths); `flask` and `python` must be on the PATH.
# Settings already present in the environment (docker compose, PythonAnywhere, the shell)
# always win over .env, the same rule python-dotenv applies when the app loads .env.
#
# Optional:
#   RESET_DATA=true|false  see above
#   REWRITE_ENV=true       write .env from the current environment before anything else
#   MYSQL_WAIT_TRIES=60    tries (5 s apart) to reach MySQL before giving up (production)

log() { echo "reset.sh: $*"; }
die() { echo "reset.sh: ERROR: $*" >&2; exit 1; }

if [ ! -f manage.py ]
then
  die "manage.py not found in $(pwd), run this script from the repo root"
fi
command -v flask > /dev/null 2>&1 || die "flask is not on the PATH (activate the virtualenv?)"
command -v python > /dev/null 2>&1 || die "python is not on the PATH"

if [ "$REWRITE_ENV" = "true" ]
then
  log "rewriting .env from the environment"
  {
    echo "HOST=$HOST"
    echo "DB=$DB"
    echo "PASSWD=$PASSWD"
    echo "DB_USER=${DB_USER:-$USER}"
    echo "ENV=$ENV"
    echo "ORIGINS=$ORIGINS"
    echo "FLOWER_LIMIT=$FLOWER_LIMIT"
    echo "SECRET_KEY=$SECRET_KEY"
    echo "KAFKA_ENABLED=$KAFKA_ENABLED"
    echo "KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS"
    echo "KAFKA_REQUEST_TOPIC=$KAFKA_REQUEST_TOPIC"
    echo "KAFKA_RESPONSE_TOPIC=$KAFKA_RESPONSE_TOPIC"
    echo "REDIS_ENABLED=$REDIS_ENABLED"
    echo "REDIS_URL=$REDIS_URL"
    echo "RATE_LIMIT_TIMES=$RATE_LIMIT_TIMES"
    echo "RATE_LIMIT_SECONDS=$RATE_LIMIT_SECONDS"
    echo "METRICS_API_KEY=$METRICS_API_KEY"
  } > .env
fi

if [ -f .env ]
then
  log "loading defaults from .env (variables already set are kept)"
  while IFS='=' read -r key value || [ -n "$key" ]
  do
    case "$key" in
      ''|'#'*|*[!A-Za-z0-9_]*|[0-9]*) continue ;;
    esac
    if [ -z "$(eval "printf '%s' \"\${$key+set}\"")" ]
    then
      value=$(printf '%s' "$value" | sed -e 's/[[:space:]]*#.*$//' -e "s/^[\"']//" -e "s/[\"']\$//")
      export "$key=$value"
    fi
  done < .env
fi

# DB_USER is the name of the mysql login. The old name, USER, is the login name of the shell
# user too (docker compose substitutes the shell's value over .env), so it is only a fallback.
if [ -z "$DB_USER" ] && [ -n "$USER" ]
then
  log "DB_USER is not set, falling back to USER=$USER"
  DB_USER="$USER"
fi
export DB_USER

export FLASK_APP=manage.py

# mysql_check: can ${DB_USER} log in to ${DB}?   mysql_reset: drop and create ${DB}
# exit codes: 0 ok, 1 not reachable yet (retry), 2 refused (credentials/privileges), 3 no mysqlclient
mysql_task() {
  python - "$1" <<'PY'
import os, sys
try:
    import MySQLdb
except ImportError:
    print("mysqlclient is not installed", file=sys.stderr)
    sys.exit(3)
task = sys.argv[1]
db = os.environ["DB"]
try:
    conn = MySQLdb.connect(host=os.environ["HOST"], user=os.environ["DB_USER"],
                           passwd=os.environ["PASSWD"], connect_timeout=5,
                           **({"db": db} if task == "check" else {}))
    if task == "reset":
        cur = conn.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS `{db}`")
        cur.execute(f"CREATE DATABASE `{db}`")
    conn.close()
except MySQLdb.OperationalError as e:
    print(f"{e.args[0]}: {e.args[1] if len(e.args) > 1 else e}", file=sys.stderr)
    sys.exit(2 if e.args[0] in (1044, 1045, 1049, 1142) else 1)
PY
}

wait_for_mysql() {
  tries="${MYSQL_WAIT_TRIES:-60}"
  attempt=1
  denied=0
  while [ "$attempt" -le "$tries" ]
  do
    mysql_task check
    status=$?
    case "$status" in
      0) log "MySQL is up and ${DB_USER}@${HOST}/${DB} can log in"; return 0 ;;
      3) return 1 ;;
      2)
        # the mysql image only accepts connections after it created its user, so a few
        # refusals can still be a start up race, many are a real credentials problem
        denied=$((denied + 1))
        if [ "$denied" -ge 3 ]
        then
          echo "reset.sh: ERROR: MySQL is reachable but refuses ${DB_USER}@${HOST}/${DB}." >&2
          echo "  - DB_USER / PASSWD / DB here must be the ones MySQL was created with." >&2
          echo "  - the mysql image creates its user only when its data volume is empty:" >&2
          echo "    after changing them run 'compose down -v' to drop the db volume." >&2
          echo "  - docker compose reads \${DB_USER} from the shell before .env, check" >&2
          echo "    'compose config | grep MYSQL_' shows the same user." >&2
          return 1
        fi
        ;;
      *) denied=0 ;;
    esac
    log "MySQL not ready at ${HOST}:3306 (attempt ${attempt}/${tries}), sleeping"
    attempt=$((attempt + 1))
    sleep 5
  done
  echo "reset.sh: ERROR: gave up waiting for MySQL at ${HOST}:3306" >&2
  return 1
}

reset_mysql() {
  log "dropping and creating the MySQL database ${DB} on ${HOST}"
  mysql_task reset
}

if [ "$ENV" = "production" ]
then
  RESET_DATA="${RESET_DATA:-false}"
else
  RESET_DATA="${RESET_DATA:-true}"
fi

if [ "$ENV" = "production" ]
then
  for var in HOST DB DB_USER PASSWD
  do
    eval "value=\${$var}"
    [ -n "$value" ] || die "$var is empty or not set (ENV=production needs HOST, DB, DB_USER and PASSWD)"
  done
  if [ "$HOST" = "localhost" ] || [ "$HOST" = "127.0.0.1" ]
  then
    log "warning: HOST=$HOST, inside a container the database is another host (compose sets HOST=db)"
  fi
  log "production: ${DB_USER}@${HOST}/${DB}, kafka=${KAFKA_ENABLED:-false}, redis=${REDIS_ENABLED:-false}, reset=${RESET_DATA}"
  wait_for_mysql || exit 1
  if [ "$RESET_DATA" = "true" ]
  then
    rm -f generated/*.png generated/*.json
    log "removed generated files"
    reset_mysql || die "could not reset the MySQL database (does ${DB_USER} have DROP/CREATE on ${DB}?)"
  fi
else
  log "ENV=${ENV:-development}: sqlite database, reset=${RESET_DATA}"
  if [ "$RESET_DATA" = "true" ]
  then
    if [ -d db ]
    then
      rm -rf db/*
      log "removed db"
    else
      mkdir db
      log "made folder db"
    fi
    rm -f generated/*.png generated/*.json
    log "removed generated files"
    if [ -n "$HOST" ] && [ -n "$DB" ] && [ -n "$DB_USER" ]
    then
      reset_mysql || log "WARNING: MySQL database ${DB} on ${HOST} was NOT reset (not production, continuing)"
    fi
  fi
fi

# migrations don't need the kafka consumer or redis
export KAFKA_ENABLED=false REDIS_ENABLED=false
if [ ! -f migrations/env.py ]
then
  flask db init || die "flask db init failed"
else
  # bring the database to the last known revision, `flask db migrate` refuses to run otherwise
  flask db upgrade || die "flask db upgrade failed"
fi
flask db migrate || die "flask db migrate failed"
flask db upgrade || die "flask db upgrade failed"
log "done"
