import json
from pathlib import Path
import pytest
from prometheus_client import REGISTRY
from app.services.flower_evolver import (makeFlower, drawFlower, mutateFlower, reproduce,
                                         FlowerEvolverError, Params)

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
LEGACY_GENOME = Path(__file__).parent / 'data' / 'legacy_binary_genome.json'


def invocations(operation, status):
    return REGISTRY.get_sample_value('flower_evolver_invocations_total',
                                     {'operation': operation, 'status': status}) or 0


def assert_flower_files(folder, id):
    assert (folder / f"{id}.png").read_bytes().startswith(PNG_SIGNATURE)
    assert 'Flower' in json.loads((folder / f"{id}.json").read_text())


def test_make_flower_respects_params(tmp_path):
    makeFlower(1, tmp_path, Params(radius=32, layers=2))
    petals = json.loads((tmp_path / "1.json").read_text())['Flower']['petals']
    assert petals['radius'] == 32
    assert petals['numLayers'] == 2


def test_legacy_binary_genome_is_still_usable(tmp_path):
    genome = LEGACY_GENOME.read_text()
    drawFlower(1, tmp_path, genome)
    makeFlower(2, tmp_path)
    reproduce(1, 2, 3, tmp_path)
    mutateFlower(1, 4, tmp_path)
    for id in (1, 3, 4):
        assert_flower_files(tmp_path, id)


def test_draw_flower_rejects_invalid_genome(tmp_path):
    genome = json.loads(LEGACY_GENOME.read_text())
    genome['Flower']['dna']['genomes'] = genome['Flower']['dna']['genomes'][:1]
    with pytest.raises(FlowerEvolverError):
        drawFlower(1, tmp_path, json.dumps(genome))
    with pytest.raises(FlowerEvolverError):
        drawFlower(1, tmp_path, "not json")
    assert not (tmp_path / "1.json").exists()


def test_missing_parent_raises(tmp_path):
    makeFlower(1, tmp_path)
    with pytest.raises(FlowerEvolverError):
        reproduce(1, 99, 3, tmp_path)
    with pytest.raises(FlowerEvolverError):
        mutateFlower(99, 3, tmp_path)


def test_invocations_are_counted(tmp_path):
    success, failure = invocations('make', 'success'), invocations('reproduce', 'failure')
    makeFlower(1, tmp_path)
    with pytest.raises(FlowerEvolverError):
        reproduce(1, 99, 2, tmp_path)
    assert invocations('make', 'success') == success + 1
    assert invocations('reproduce', 'failure') == failure + 1
