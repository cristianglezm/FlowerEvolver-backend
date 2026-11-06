#!/bin/sh
set -e
sh .devops/reset.sh
# fails when a model changed without a committed migration (flask db migrate -m "...")
FLASK_APP=manage.py flask db check
python -m pytest
python -m flake8 --per-file-ignores='app/__init__.py:F401'
