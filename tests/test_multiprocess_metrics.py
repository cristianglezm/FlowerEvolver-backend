import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_create_app_works_when_the_multiprocess_folder_does_not_exist_yet(tmp_path):
    """The container sets PROMETHEUS_MULTIPROC_DIR but entrypoint.sh creates the folder after reset.sh ran
    `flask db upgrade`, so creating the app (and its labelled metrics) must not need the folder to exist.
    prometheus_client reads the variable when it is imported, hence the separate process."""
    folder = tmp_path / 'prometheus_multiproc'
    env = {**os.environ, 'PROMETHEUS_MULTIPROC_DIR': str(folder), 'ENV': 'development',
           'KAFKA_ENABLED': 'false', 'REDIS_ENABLED': 'false'}
    result = subprocess.run([sys.executable, '-c', 'from app import create_app; create_app()'],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    assert folder.is_dir()
    assert any(file.name.startswith('counter_') for file in folder.iterdir())
