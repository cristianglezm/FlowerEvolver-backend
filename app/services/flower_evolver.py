import os
import subprocess
from pathlib import Path
from ..metrics import FLOWER_EVOLVER_INVOCATIONS_TOTAL, FLOWER_EVOLVER_INVOCATION_DURATION_SECONDS


def getFlowerEvolverExe():
    exe = "FlowerEvolver"
    if os.name == 'nt':
        exe += ".exe"

    path = Path(f"bin/{exe}")
    return path.resolve()


def _run(operation, commandArr):
    with FLOWER_EVOLVER_INVOCATION_DURATION_SECONDS.labels(operation=operation).time():
        status = subprocess.run(commandArr)
    FLOWER_EVOLVER_INVOCATIONS_TOTAL.labels(
        operation=operation, status="success" if status.returncode == 0 else "failure").inc()
    return status


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


def makeFlower(id, folder, params=Params()):
    exe = str(getFlowerEvolverExe())
    joinedPath = str(os.path.join(str(folder), str(id)))
    commandArr = [f"{exe}", "-cli", "-n", "1", "-l", f"{params.layers}", "-r", f"{params.radius}",
                  "-p", f"{params.p}", "-b", f"{params.bias}", "-sf", f"{joinedPath}.json", "-si", f"{joinedPath}.png"]
    return _run("make", commandArr)


def drawFlower(id, folder, jsonfile):
    exe = str(getFlowerEvolverExe())
    joinedPath = str(os.path.join(str(folder), str(id)))
    commandArr = [f"{exe}", "-cli", "-lf", f"{jsonfile}", "-sf", f"{joinedPath}.json", "-si", f"{joinedPath}.png"]
    return _run("draw", commandArr)


def mutateFlower(original, id, folder, params=Params()):
    exe = str(getFlowerEvolverExe())
    joinedPath = str(os.path.join(str(folder), str(id)))
    originalPath = str(os.path.join(str(folder), str(original)))
    commandArr = [f"{exe}", "-cli", "-lf", f"{originalPath}.json", "-l", f"{params.layers}",
                  "-r", f"{params.radius}", "-p", f"{params.p}", "-b", f"{params.bias}",
                  "-m", "1", "-sf", f"{joinedPath}.json", "-si", f"{joinedPath}.png"]
    return _run("mutate", commandArr)


def reproduce(father, mother, child, folder, params=Params()):
    exe = str(getFlowerEvolverExe())
    childPath = str(os.path.join(str(folder), str(child)))
    fatherPath = str(os.path.join(str(folder), str(father)))
    motherPath = str(os.path.join(str(folder), str(mother)))
    commandArr = [f"{exe}", "-cli", "-repr", f"{fatherPath}.json", f"{motherPath}.json", "-l", f"{params.layers}",
                  "-r", f"{params.radius}", "-p", f"{params.p}", "-b", f"{params.bias}",
                  "-sf", f"{childPath}.json", "-si", f"{childPath}.png"]
    return _run("reproduce", commandArr)
