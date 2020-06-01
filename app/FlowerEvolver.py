import os
import subprocess
from pathlib import Path

def getFlowerEvolverExe():
    exe = "FlowerEvolver"
    if os.name == 'nt':
        exe += ".exe"

    path = Path("../bin/{}".format(exe))
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
        return "layers: {}, radius: {}, p: {}, bias: {}".format(self.layers, self.radius, self.p, self.bias)

def makeFlower(id, folder, params = Params()):
    command = "{} -cli -n 1 -l {} -r {} -p {} -b {} -sf {}.json  -si {}.png".format(str(getFlowerEvolverExe()),params.layers, params.radius, params.p, params.bias,\
                str(os.path.join(folder, str(id))),str(os.path.join(folder, str(id))))
    process = subprocess.Popen(command)
    return process.communicate()

def mutateFlower(original, id, folder, params = Params()):
    command = "{} -cli -lf {}.json -l {} -r {} -p {} -b {} -m 1 -sf {}.json -si {}.png".format(str(getFlowerEvolverExe()), str(os.path.join(folder, str(original))),\
                params.layers, params.radius, params.p, params.bias, str(os.path.join(folder, str(id))), str(os.path.join(folder, str(id))))
    process = subprocess.Popen(command)
    return process.communicate()

def reproduce(father, mother, child, folder, params = Params()):
    command = "{} -cli -repr {}.json {}.json -l {} -r {} -p {} -b {} -m 1 -sf {}.json -si {}.png".format(str(getFlowerEvolverExe()),\
                str(os.path.join(folder, str(father))), str(os.path.join(folder, str(mother))), params.layers, params.radius, params.p,\
                params.bias,str(os.path.join(folder, str(child))), str(os.path.join(folder, str(child))))
    process = subprocess.Popen(command)
    return process.communicate()