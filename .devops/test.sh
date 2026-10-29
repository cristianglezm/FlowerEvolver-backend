#!/bin/sh
set -e
sh .devops/reset.sh
python -m pytest
python -m flake8 --per-file-ignores='app/__init__.py:F401'
