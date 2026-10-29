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
if [ -f .env ]
then
  echo "exporting .env file..."
  export $(cat .env | sed 's/#.*//g' | xargs)
fi
if [ "$ENV" != "production" ]
then
# rm db sqlite
  if [ -d db ]
  then
    echo "removing db"
    rm -R db/*
    echo "removed db"
  else
    mkdir db
    echo "made folder db"
  fi
# reset mysql db and images and genomes of flowers
  rm generated/*.png generated/*.json
#  echo "drop database $DB; create database $DB" | mysql -u ${USER} -h ${HOST} --password=${PASSWD}
fi
export FLASK_APP=FlowerEvolver.py
if [ "$ENV" = "production" ]
then
  echo "waiting for MySQL"
  until nc -z -v -w30 ${HOST} 3306
  do
    echo "MySQL is unavailable - sleeping"
    sleep 5
  done
fi
if [ ! -d migrations ]
then
  flask db init
fi
flask db migrate
flask db upgrade
