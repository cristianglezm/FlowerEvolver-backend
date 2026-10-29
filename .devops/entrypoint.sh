#!/bin/sh
sh reset.sh
export PROMETHEUS_MULTIPROC_DIR=${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc}
rm -rf "$PROMETHEUS_MULTIPROC_DIR"
mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
gunicorn wsgi:app -c gunicorn_config.py -w 4 --threads 2 -b 0.0.0.0:5000
