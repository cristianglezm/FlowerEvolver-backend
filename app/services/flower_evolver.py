import functools
from pathlib import Path
import flowerevolver as fe
from ..metrics import FLOWER_EVOLVER_INVOCATIONS_TOTAL, FLOWER_EVOLVER_INVOCATION_DURATION_SECONDS


class FlowerEvolverError(Exception):
    pass


class Params:
    layers = 3
    radius = 64
    p = 6.0
    bias = 1.0

    def __init__(self, layers=3, radius=64, p=6.0, bias=1.0):
        self.layers = layers
        self.radius = radius
        self.p = p
        self.bias = bias

    def __repr__(self):
        return f"layers: {self.layers}, radius: {self.radius}, p: {self.p}, bias: {self.bias}"


def _tracked(operation):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with FLOWER_EVOLVER_INVOCATION_DURATION_SECONDS.labels(operation=operation).time():
                    result = func(*args, **kwargs)
            except (ValueError, RuntimeError, OSError) as e:
                FLOWER_EVOLVER_INVOCATIONS_TOTAL.labels(operation=operation, status="failure").inc()
                raise FlowerEvolverError(str(e)) from e
            FLOWER_EVOLVER_INVOCATIONS_TOTAL.labels(operation=operation, status="success").inc()
            return result
        return wrapper
    return decorator


def _load(folder, id):
    return fe.Flower.from_json((Path(folder) / f"{id}.json").read_text())


def _save(folder, id, genome, png):
    (Path(folder) / f"{id}.png").write_bytes(png)
    (Path(folder) / f"{id}.json").write_text(genome)


def _save_flower(folder, id, flower):
    _save(folder, id, flower.to_json(), flower.petals.image.to_png_bytes())


@_tracked("make")
def makeFlower(id, folder, params=Params()):
    flower = fe.make_flower(params.radius, params.layers, params.p, params.bias)
    _save_flower(folder, id, flower)


@_tracked("draw")
def drawFlower(id, folder, genome):
    flower = fe.Flower.from_json(genome)
    petals = flower.petals
    image = fe.draw_flower(flower.dna, petals.radius, petals.num_layers, petals.P, petals.bias)
    _save(folder, id, flower.to_json(), image.to_png_bytes())


@_tracked("mutate")
def mutateFlower(original, id, folder, params=Params()):
    dna = _load(folder, original).dna
    flower = fe.mutate(dna, params.radius, params.layers, params.p, params.bias)
    _save_flower(folder, id, flower)


@_tracked("reproduce")
def reproduce(father, mother, child, folder, params=Params()):
    father_dna = _load(folder, father).dna
    mother_dna = _load(folder, mother).dna
    flower = fe.reproduce(father_dna, mother_dna, params.radius, params.layers, params.p, params.bias)
    _save_flower(folder, child, flower)
