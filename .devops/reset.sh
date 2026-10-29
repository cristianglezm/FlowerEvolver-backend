#!/bin/sh
# will delete generated content of the day and the database
if [ "$REWRITE_ENV" = "true" ]
then
  echo "rewriting env file..."
  echo "HOST=$HOST" > .env
  echo "DB=$DB" >> .env
  echo "PASSWD=$PASSWD" >> .env
  echo "USER=$USER" >> .env
  echo "ENV=$ENV" >> .env
  echo "ORIGINS=$ORIGINS" >> .env
  echo "FLOWER_LIMIT=$FLOWER_LIMIT" >> .env
  echo "SECRET_KEY=$SECRET_KEY" >> .env
  echo "KAFKA_ENABLED=$KAFKA_ENABLED" >> .env
  echo "KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP_SERVERS" >> .env
  echo "KAFKA_REQUEST_TOPIC=$KAFKA_REQUEST_TOPIC" >> .env
  echo "KAFKA_RESPONSE_TOPIC=$KAFKA_RESPONSE_TOPIC" >> .env
  echo "REDIS_ENABLED=$REDIS_ENABLED" >> .env
  echo "REDIS_URL=$REDIS_URL" >> .env
  echo "RATE_LIMIT_TIMES=$RATE_LIMIT_TIMES" >> .env
  echo "RATE_LIMIT_SECONDS=$RATE_LIMIT_SECONDS" >> .env
  echo "METRICS_API_KEY=$METRICS_API_KEY" >> .env
fi
# .env only provides defaults: a variable that is already set in the environment
# always wins.
# This is the same rule python-dotenv applies when the app loads .env.
if [ -f .env ]
then
  echo "loading defaults from .env..."
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
if [ "$ENV" != "production" ]
then
# rm db sqlite
  if [ -d db ]
  then
    echo "removing db"
    rm -rf db/*
    echo "removed db"
  else
    mkdir db
    echo "made folder db"
  fi
# reset mysql db and images and genomes of flowers
  rm -f generated/*.png generated/*.json
  echo "drop database $DB; create database $DB" | mysql -u ${USER} -h ${HOST} --password=${PASSWD}
fi
export FLASK_APP=manage.py
if [ "$ENV" = "production" ]
then
  echo "waiting for MySQL"
  until python -c "import socket, sys; socket.create_connection((sys.argv[1], 3306), timeout=5).close()" "${HOST}" 2>/dev/null
  do
    echo "MySQL is unavailable - sleeping"
    sleep 5
  done
fi
# migrations don't need the kafka consumer or redis
export KAFKA_ENABLED=false REDIS_ENABLED=false
if [ ! -f migrations/env.py ]
then
  flask db init
else
  # bring the database to the last known revision, `flask db migrate` refuses to run otherwise
  flask db upgrade
fi
flask db migrate
flask db upgrade || exit 1
