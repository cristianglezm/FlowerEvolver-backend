import string
import random
import json
from pydantic import BaseModel, ValidationError
from typing import List, Union
from flask_restful import Resource, reqparse, request
from flask_restful import fields, marshal
from flask import current_app
from flask_cors import cross_origin
from pathlib import Path
from sqlalchemy import and_
from app.models import Flower, Descendant, Mutation, Descriptions
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
    P: Union[float, int]
    bias: Union[float, int]
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


descendant_fields = {
    'id': fields.Integer,
    'father': fields.Integer,
    'mother': fields.Integer
}


descendant_list_fields = {
    'count': fields.Integer,
    'descendants': fields.List(fields.Nested(descendant_fields)),
}


descendant_post_parser = reqparse.RequestParser()

descendant_post_parser.add_argument('father', type=int, required=True, location=[
                                    'json'], help='father parameter is required')
descendant_post_parser.add_argument('mother', type=int, required=True, location=[
                                    'json'], help='mother parameter is required')


class DescendantResource(Resource):
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

            res = Flower.query.join(Descendant, Flower.id == Descendant.id)\
                .filter(Descendant.father == father)\
                .filter(and_(Descendant.mother == mother)).order_by(Flower.id.desc())

            if limit:
                res = res.limit(limit)

            if offset:
                res = res.offset(offset)

            if count:
                res = res.all()
                current_app.logger.info("Descendants - get - count")
                return marshal({
                    'count': len(res)
                }, count_fields)

            res = res.all()

            if res:
                current_app.logger.info(f"Descendants - get - all from - {father} and {mother}")
                return marshal(res, flower_fields)
            else:
                return f"Flowers by father id {str(father)} and mother id {str(mother)} not found", 404
        elif father:
            args.pop('limit', None)
            args.pop('offset', None)
            args.pop('count', None)

            res = Flower.query.join(Descendant, Flower.id == Descendant.id)\
                .filter((Descendant.father == father) | (Descendant.mother == father)).order_by(Flower.id.desc())

            if limit:
                res = res.limit(limit)

            if offset:
                res = res.offset(offset)

            if count:
                res = res.all()
                current_app.logger.info(f"Descendants - get - count from - {father}")
                return marshal({
                    'count': len(res)
                }, count_fields)

            res = res.all()
            if res:
                current_app.logger.info(f"Descendants - get - all from - {father}")
                return marshal(res, flower_fields)
            else:
                current_app.logger.info(f"Descendants - get - not found from - {father}")
                return f"Flowers by father or mother id {str(father)} not found", 404
        else:
            args.pop('limit', None)
            args.pop('offset', None)
            args.pop('count', None)

            descendant = Descendant.query.filter_by(**args).order_by(Descendant.id.desc())
            if limit:
                descendant = descendant.limit(limit)

            if offset:
                descendant = descendant.offset(offset)

            if count:
                descendant = descendant.all()
                current_app.logger.info("Descendants - get - all - count")
                return marshal({
                    'count': len(descendant)
                }, count_fields)

            descendant = descendant.all()
            current_app.logger.info("Descendants - get - all")
            return marshal({
                'count': len(descendant),
                'descendants': [marshal(d, descendant_fields) for d in descendant]
            }, descendant_list_fields)

    @cross_origin()
    def post(self):
        if(isOverLimit()):
            current_app.logger.info("Descendants - post - max number reached.")
            return "max number of flowers reached, wait for tomorrow", 403
        args = descendant_post_parser.parse_args()
        descendant = Descendant(**args)
        if Path(f"{current_app.config['GENERATED_FOLDER']}/{str(descendant.father)}.json").exists() and \
                Path(f"{current_app.config['GENERATED_FOLDER']}/{str(descendant.mother)}.json").exists():
            flower = Flower()
            db.session.add(flower)
            db.session.flush()
            flower.genome = f"{str(flower.id)}.json"
            flower.image = f"{str(flower.id)}.png"
            descendant.id = flower.id
            path = Path(current_app.config['GENERATED_FOLDER'])
            status = reproduce(descendant.father, descendant.mother, descendant.id, path.resolve())
            if(status.returncode != 0):
                db.session.unroll()
                current_app.logger.info(f"Descendants - post - reproduce - error - {status.stderr}")
                return f"Something went wrong then repoducing flowers with id {descendant.father} and {descendant.mother}", 400
            db.session.add(descendant)
            db.session.commit()
            current_app.logger.info("Descendants - post - reproduce")
            return marshal(flower, flower_fields)
        else:
            current_app.logger.info("Descendants - post - father or mother not found")
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


descriptions_fields = {
    'id': fields.Integer,
    'description': fields.String
}


descriptions_list_fields = {
    'count': fields.Integer,
    'descriptions': fields.List(fields.Nested(descriptions_fields)),
}


class DescriptionsResource(Resource):
    @cross_origin()
    def get(self, desc_id=None):
        args = request.args.to_dict()
        limit = args.get('limit', 0)
        offset = args.get('offset', 0)
        count = args.get('count', 0)

        if desc_id:
            res = Descriptions.query.filter_by(id=desc_id).first()

            if res:
                current_app.logger.info(f"Descriptions - get - {desc_id} - all")
                return marshal(res, descriptions_fields)
            else:
                current_app.logger.info("Descriptions - get - not found")
                return f"flower {str(desc_id)} has no description", 404
        else:
            args.pop('limit', None)
            args.pop('offset', None)
            args.pop('count', None)

            desc = Descriptions.query.filter_by(**args).order_by(Descriptions.id.desc())
            if limit:
                desc = desc.limit(limit)

            if offset:
                desc = desc.offset(offset)

            if count:
                desc = desc.all()
                current_app.logger.info("Descriptions - get - all - count")
                return marshal({
                    'count': len(desc)
                }, count_fields)

            desc = desc.all()
            current_app.logger.info("Descriptions - get - all")
            return marshal({
                'count': len(desc),
                'descriptions': [marshal(d, descriptions_fields) for d in desc]
            }, descriptions_list_fields)
