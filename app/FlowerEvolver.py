import os
import subprocess
from pathlib import Path

def getFlowerEvolverExe():
    exe = "FlowerEvolver"
    if os.name == 'nt':
        exe += ".exe"

    path = Path(f"bin/{exe}")
    return path.resolve()

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

def makeFlower(id, folder, params = Params()):
    exe = str(getFlowerEvolverExe())
    joinedPath = str(os.path.join(str(folder), str(id)))
    command = f"{exe} -cli -n 1 -l {params.layers} -r {params.radius} -p {params.p} -b {params.bias} -sf {joinedPath}.json -si {joinedPath}.png"
    process = subprocess.Popen(command, shell=False)
    return process.communicate()

def mutateFlower(original, id, folder, params = Params()):
    exe = str(getFlowerEvolverExe())
    joinedPath = str(os.path.join(str(folder), str(id)))
    originalPath = str(os.path.join(str(folder), str(original)))
    command = f"{exe} -cli -lf {originalPath}.json -l {params.layers} -r {params.radius} -p {params.p} -b {params.bias} -m 1 -sf {joinedPath}.json -si {joinedPath}.png"
    process = subprocess.Popen(command, shell=False)
    return process.communicate()

def reproduce(father, mother, child, folder, params = Params()):
    exe = str(getFlowerEvolverExe())
    childPath = str(os.path.join(str(folder), str(child)))
    fatherPath = str(os.path.join(str(folder), str(father)))
    motherPath = str(os.path.join(str(folder), str(mother)))
    command = f"{exe} -cli -repr {fatherPath}.json {motherPath}.json -l {params.layers} -r {params.radius} -p {params.p} -b {params.bias} -sf {childPath}.json -si {childPath}.png"
    process = subprocess.Popen(command, shell=False)
    return process.communicate()
