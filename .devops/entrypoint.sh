#!/bin/sh
set -e
sh reset.sh || exit 1
export PROMETHEUS_MULTIPROC_DIR=${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc}
# clean folder right before gunicorn (see create_app, reset.sh)
rm -rf "$PROMETHEUS_MULTIPROC_DIR"
mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
# exec: gunicorn replaces this shell and becomes PID 1, so `docker stop` (SIGTERM) reaches it
# and the workers shut down gracefully instead of being killed after the timeout
exec gunicorn wsgi:app -c gunicorn_config.py \
    -w "${WEB_CONCURRENCY:-4}" --threads "${GUNICORN_THREADS:-2}" -b "0.0.0.0:${PORT:-5000}"
