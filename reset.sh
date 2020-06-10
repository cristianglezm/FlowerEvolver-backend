#!/bin/sh
# will delete generated content of the day and the database
if [ -f .env ]
then
  export $(cat .env | sed 's/#.*//g' | xargs)
fi
rm generated/*.png generated/*.json
echo "drop database $DB; create database $DB" | mysql -u ${USER} -h ${HOST} --password=${PASSWD}
python manager.py db init
python manager.py db migrate
python manager.py db upgrade

