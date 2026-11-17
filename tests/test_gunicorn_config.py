"""What the image needs from gunicorn_config.py, tried with gunicorn itself."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(sys.platform == 'win32', reason='gunicorn does not run on Windows')


@pytest.fixture(scope='session', autouse=True)
def database():
    """Nothing here uses the app, so the schema of conftest.py is not made for these tests."""


def _free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def test_gunicorn_reads_the_control_socket_setting():
    from gunicorn.app.base import Application

    class App(Application):
        def init(self, parser, opts, args):
            return None

        def load_config(self):
            self.load_config_from_file(str(ROOT / 'gunicorn_config.py'))

        def load(self):
            return None

    # a setting that gunicorn does not have is ignored without a word: this notices when an upgrade renames it
    assert 'control_socket_disable' in App().cfg.settings
    assert App().cfg.control_socket_disable is True


def test_a_home_that_cannot_be_written_does_not_make_the_control_server_fail(tmp_path):
    (tmp_path / 'tiny_wsgi.py').write_text(
        "def app(environ, start_response):\n"
        "    start_response('200 OK', [('Content-Type', 'text/plain')])\n"
        "    return [b'ok']\n"
    )
    port = _free_port()
    # the user of the image has no home: a place that cannot be made is the same, and does not depend on who runs this
    env = {**os.environ, 'HOME': '/proc/no-home/fe', 'PYTHONPATH': str(tmp_path)}
    env.pop('XDG_RUNTIME_DIR', None)
    server = subprocess.Popen(
        [sys.executable, '-m', 'gunicorn', 'tiny_wsgi:app', '-c', str(ROOT / 'gunicorn_config.py'),
         '-b', f'127.0.0.1:{port}', '--log-level', 'info'],
        env=env, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                socket.create_connection(('127.0.0.1', port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.fail('gunicorn did not start')
        # the control server is started with the arbiter, and says what is wrong in the first moments
        time.sleep(0.5)
    finally:
        server.terminate()
        output = server.communicate(timeout=20)[0]

    assert 'Control server error' not in output
    assert 'Permission denied' not in output
    assert 'Listening at' in output
