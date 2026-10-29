from pydantic import BaseModel
from typing import List, Union


class Link(BaseModel):
    layer: str
    neuron: str


class Connection(BaseModel):
    dest: Link
    frozen: bool
    gradient: float
    src: Link
    weight: float


class ConnectionChromosome(BaseModel):
    Connection: Connection
    enabled: bool
    frozen: bool


class NodeChromosome(BaseModel):
    actType: str
    biasWeight: float
    layerID: str
    neuronID: str
    nrnType: str


class Genome(BaseModel):
    ConnectionChromosomes: List[ConnectionChromosome]
    GenomeID: str
    SpeciesID: str
    cppn: bool
    fitness: float
    nodeChromosomes: List[NodeChromosome]
    rnnAllowed: bool


class DNA(BaseModel):
    genomes: List[Genome]


class Petals(BaseModel):
    P: Union[float, int]
    bias: Union[float, int]
    numLayers: int
    radius: int


class FlowerGenome(BaseModel):
    dna: DNA
    petals: Petals


class SharedFlower(BaseModel):
    Flower: FlowerGenome
