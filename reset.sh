#!/bin/sh
# will delete generated content of the day and the database
if [ -f .env ]
then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi
if [ -d db ]
then
  rm -R db/*
else
  mkdir db
fi
rm generated/*.png generated/*.json
echo "drop database $DB; create database $DB" | mysql -u ${USER} -h ${HOST} --password=${PASSWD}
export FLASK_APP=FlowerEvolver.py
if [ ! -d migrations ]
then
    flask db init
fi
flask db migrate
flask db upgrade
