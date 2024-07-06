import string
import random
import json
from pydantic import BaseModel, ValidationError
from typing import List
from flask_restful import Resource, reqparse, request
from flask_restful import fields, marshal
from flask import current_app
from flask_cors import cross_origin
from pathlib import Path
from sqlalchemy import and_
from app.models import Flower, Ancestor, Mutation
from .FlowerEvolver import makeFlower, drawFlower, mutateFlower, reproduce
from . import db

flower_fields = {
    'id': fields.Integer,
    'genome': fields.String,
    'image': fields.String,
}

flower_list_fields = {
    'count': fields.Integer,
    'flowers': fields.List(fields.Nested(flower_fields)),
}

count_fields = {
    'count': fields.Integer
}


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
    P: int
    bias: int
    numLayers: int
    radius: int


class FlowerGenome(BaseModel):
    dna: DNA
    petals: Petals


class SharedFlower(BaseModel):
    Flower: FlowerGenome


flower_post_parser = reqparse.RequestParser()


def isOverLimit():
    flower = Flower.query.all()
    return len(flower) > int(current_app.config['FLOWER_LIMIT'])


class FlowerResource(Resource):
    @cross_origin()
    def get(self, flower_id=None):
        if flower_id:
            flower = Flower.query.filter_by(id=flower_id).first()
            if flower:
                current_app.logger.info(f"flower - get - {flower_id}")
                return marshal(flower, flower_fields)
            else:
                current_app.logger.info(f"flower - get - {flower_id} not found")
                return "flower not found", 404
        else:
            args = request.args.to_dict()
            limit = args.get('limit', 0)
            offset = args.get('offset', 0)
            count = args.get('count', 0)

            args.pop('limit', None)
            args.pop('offset', None)
            args.pop('count', None)

            flower = Flower.query.filter_by(**args).order_by(Flower.id.desc())
            if limit:
                flower = flower.limit(limit)

            if offset:
                flower = flower.offset(offset)

            if count:
                flower = flower.all()
                current_app.logger.info("flower - get - count")
                return marshal({
                    'count': len(flower)
                }, count_fields)

            flower = flower.all()
            current_app.logger.info("flower - get - all")
            return marshal({
                'count': len(flower),
                'flowers': [marshal(f, flower_fields) for f in flower]
            }, flower_list_fields)

    def get_random_filename(self):
        letters_and_digits = string.ascii_letters + string.digits
        random_filename = ''.join(random.choice(letters_and_digits) for i in range(20))
        return random_filename + '.json'

    @cross_origin()
    def post(self):
        if(isOverLimit()):
            current_app.logger.info("flower - post - max number reached.")
            return "max number of flowers reached, wait for tomorrow", 403
        args = flower_post_parser.parse_args()
        path = Path(current_app.config['GENERATED_FOLDER'])
        sharedFlower = request.get_json()
        if not sharedFlower:
            current_app.logger.info("flower - post - make Flower")
            flower = Flower(**args)
            db.session.add(flower)
            db.session.flush()
            status = makeFlower(flower.id, path.resolve())
            if(status.returncode != 0):
                current_app.logger.info(f"flower - post - make Flower cli error {status.stderr}")
                db.session.rollback()
                return "something went wrong while making the flower.", 400
            flower.genome = f"{flower.id}.json"
            flower.image = f"{flower.id}.png"
            db.session.commit()
            return marshal(flower, flower_fields)
        current_app.logger.info("flower - post - share Flower")
        try:
            shared_flower = SharedFlower(**sharedFlower)
        except ValidationError as e:
            current_app.logger.error(f"flower - post - share Flower - validation error - {e}")
            return "error sharing flower, probably bad format.", 400
        random_filename = self.get_random_filename()
        tmpFlower = Path(f"instance/{random_filename}")
        with open(tmpFlower.resolve(), 'w') as f:
            json.dump(shared_flower.model_dump(), f)
        flower = Flower(**args)
        db.session.add(flower)
        db.session.flush()
        status = drawFlower(flower.id, path.resolve(), tmpFlower.resolve())
        if(status.returncode != 0):
            db.session.rollback()
            tmpFlower.unlink()
            current_app.logger.error(f"flower - post - share Flower - drawFlower error - {status.stderr}")
            return "the flower genome file has invalid data.", 400
        flower.genome = f"{flower.id}.json"
        flower.image = f"{flower.id}.png"
        db.session.commit()
        tmpFlower.unlink()
        return marshal(flower, flower_fields)


ancestor_fields = {
    'id': fields.Integer,
    'father': fields.Integer,
    'mother': fields.Integer
}


ancestor_list_fields = {
    'count': fields.Integer,
    'ancestors': fields.List(fields.Nested(ancestor_fields)),
}


ancestor_post_parser = reqparse.RequestParser()

ancestor_post_parser.add_argument('father', type=int, required=True, location=[
                                  'json'], help='father parameter is required')
ancestor_post_parser.add_argument('mother', type=int, required=True, location=[
                                  'json'], help='mother parameter is required')


class AncestorResource(Resource):
    @cross_origin()
    def get(self, father=None, mother=None):
        args = request.args.to_dict()
        limit = args.get('limit', 0)
        offset = args.get('offset', 0)
        count = args.get('count', 0)
        if father and mother:
            args.pop('limit', None)
            args.pop('offset', None)
            args.pop('count', None)

            res = Flower.query.join(Ancestor, Flower.id == Ancestor.id)\
                .filter(Ancestor.father == father)\
                .filter(and_(Ancestor.mother == mother)).order_by(Flower.id.desc())

            if limit:
                res = res.limit(limit)

            if offset:
                res = res.offset(offset)

            if count:
                res = res.all()
                current_app.logger.info("Ancestors - get - count")
                return marshal({
                    'count': len(res)
                }, count_fields)

            res = res.all()

            if res:
                current_app.logger.info(f"Ancestors - get - all from - {father} and {mother}")
                return marshal(res, flower_fields)
            else:
                return f"Flowers by father id {str(father)} and mother id {str(mother)} not found", 404
        elif father:
            args.pop('limit', None)
            args.pop('offset', None)
            args.pop('count', None)

            res = Flower.query.join(Ancestor, Flower.id == Ancestor.id)\
                .filter((Ancestor.father == father) | (Ancestor.mother == father)).order_by(Flower.id.desc())

            if limit:
                res = res.limit(limit)

            if offset:
                res = res.offset(offset)

            if count:
                res = res.all()
                current_app.logger.info(f"Ancestors - get - count from - {father}")
                return marshal({
                    'count': len(res)
                }, count_fields)

            res = res.all()
            if res:
                current_app.logger.info(f"Ancestors - get - all from - {father}")
                return marshal(res, flower_fields)
            else:
                current_app.logger.info(f"Ancestors - get - not found from - {father}")
                return f"Flowers by father or mother id {str(father)} not found", 404
        else:
            args.pop('limit', None)
            args.pop('offset', None)
            args.pop('count', None)

            ancestor = Ancestor.query.filter_by(**args).order_by(Ancestor.id.desc())
            if limit:
                ancestor = ancestor.limit(limit)

            if offset:
                ancestor = ancestor.offset(offset)

            if count:
                ancestor = ancestor.all()
                current_app.logger.info("Ancestors - get - all - count")
                return marshal({
                    'count': len(ancestor)
                }, count_fields)

            ancestor = ancestor.all()
            current_app.logger.info("Ancestors - get - all")
            return marshal({
                'count': len(ancestor),
                'ancestors': [marshal(a, ancestor_fields) for a in ancestor]
            }, ancestor_list_fields)

    @cross_origin()
    def post(self):
        if(isOverLimit()):
            current_app.logger.info("Ancestors - post - max number reached.")
            return "max number of flowers reached, wait for tomorrow", 403
        args = ancestor_post_parser.parse_args()
        ancestor = Ancestor(**args)
        if Path(f"{current_app.config['GENERATED_FOLDER']}/{str(ancestor.father)}.json").exists() and \
                Path(f"{current_app.config['GENERATED_FOLDER']}/{str(ancestor.mother)}.json").exists():
            flower = Flower()
            db.session.add(flower)
            db.session.flush()
            flower.genome = f"{str(flower.id)}.json"
            flower.image = f"{str(flower.id)}.png"
            ancestor.id = flower.id
            path = Path(current_app.config['GENERATED_FOLDER'])
            status = reproduce(ancestor.father, ancestor.mother, ancestor.id, path.resolve())
            if(status.returncode != 0):
                db.session.unroll()
                current_app.logger.info(f"Ancestors - post - reproduce - error - {status.stderr}")
                return f"Something went wrong then repoducing flowers with id {ancestor.father} and {ancestor.mother}", 400
            db.session.add(ancestor)
            db.session.commit()
            current_app.logger.info("Ancestors - post - reproduce")
            return marshal(flower, flower_fields)
        else:
            current_app.logger.info("Ancestors - post - father or mother not found")
            return "Father or Mother has not been found", 404


mutation_fields = {
    'id': fields.Integer,
    'original': fields.Integer
}

mutations_list_fields = {
    'count': fields.Integer,
    'mutations': fields.List(fields.Nested(mutation_fields)),
}

mutation_post_parser = reqparse.RequestParser()

mutation_post_parser.add_argument('original', type=int, required=True, location=[
                                  'json'], help='original parameter is required')


class MutationResource(Resource):
    @cross_origin()
    def get(self, mutation_original=None):
        args = request.args.to_dict()
        limit = args.get('limit', 0)
        offset = args.get('offset', 0)
        count = args.get('count', 0)

        if mutation_original:
            res = Flower.query.join(Mutation, Flower.id == Mutation.id)\
                        .filter(Mutation.original == mutation_original).order_by(Flower.id.desc())
            if limit:
                res = res.limit(limit)
            if offset:
                res = res.offset(offset)

            if count:
                res = res.all()
                current_app.logger.info("Mutations - get - count")
                return marshal({
                    'count': len(res)
                }, count_fields)

            res = res.all()
            if res:
                current_app.logger.info(f"Mutations - get - {mutation_original} - all")
                return marshal(res, flower_fields)
            else:
                current_app.logger.info("Mutations - get - not found")
                return f"flower {str(mutation_original)} has no mutations", 404
        else:
            args.pop('limit', None)
            args.pop('offset', None)
            args.pop('count', None)

            mutation = Mutation.query.filter_by(**args).order_by(Mutation.id.desc())
            if limit:
                mutation = mutation.limit(limit)

            if offset:
                mutation = mutation.offset(offset)

            if count:
                mutation = mutation.all()
                current_app.logger.info("Mutations - get - all - count")
                return marshal({
                    'count': len(mutation)
                }, count_fields)

            mutation = mutation.all()
            current_app.logger.info("Mutations - get - all")
            return marshal({
                'count': len(mutation),
                'mutations': [marshal(m, mutation_fields) for m in mutation]
            }, mutations_list_fields)

    @cross_origin()
    def post(self):
        if(isOverLimit()):
            current_app.logger.info("Mutations - post - max number reached.")
            return "max number of flowers reached, wait for tomorrow", 403
        args = mutation_post_parser.parse_args()
        mutation = Mutation(**args)
        if Path(f"{current_app.config['GENERATED_FOLDER']}/{str(mutation.original)}.json").exists():
            flower = Flower()
            db.session.add(flower)
            db.session.flush()
            flower.genome = f"{str(flower.id)}.json"
            flower.image = f"{str(flower.id)}.png"
            mutation.id = flower.id
            path = Path(current_app.config['GENERATED_FOLDER'])
            status = mutateFlower(mutation.original, flower.id, path.resolve())
            if(status.returncode != 0):
                db.session.rollback()
                current_app.logger.info(f"Mutations - post - make mutation from original {str(mutation.original)} - error {status.stderr}")
                return f"Something went wrong when making mutations with original {mutation.original}", 400
            db.session.add(mutation)
            db.session.commit()
            current_app.logger.info(f"Mutations - post - make mutations from original {str(mutation.original)}")
            return marshal(flower, flower_fields)
        else:
            current_app.logger.info(f"Mutations - post - original {str(mutation.original)} not found")
            return f"original {str(mutation.original)} does not exists", 404
