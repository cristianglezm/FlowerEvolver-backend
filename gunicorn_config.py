import os
from prometheus_client import multiprocess  # noqa: F401


def post_worker_exit(server, worker):
    prom_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if prom_dir and os.path.isdir(prom_dir):
        worker_metric_file = os.path.join(prom_dir, f"gauge_live_{worker.pid}.db")
        if os.path.exists(worker_metric_file):
            os.remove(worker_metric_file)


# Nobody runs `gunicornc` in the container. The control socket is made in the home of the user, and the user of
# the image has none (`adduser -H`), so gunicorn logged `Control server error: [Errno 13] Permission denied:
# '/home/fe'` at every start. gunicorn 25.1 and later have it, older ones ignore the setting.
control_socket_disable = True
