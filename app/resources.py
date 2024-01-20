from flask_restful import Resource, reqparse, request
from flask_restful import fields, marshal_with, marshal
from flask import current_app
from flask_cors import cross_origin
from app.models import Flower, Ancestor, Mutation
from app.FlowerEvolver import *
from . import db

from pathlib import Path
from sqlalchemy import and_, or_

flower_fields = {
    'id': fields.Integer,
    'genome': fields.String,
    'image': fields.String,
}
flower_list_fields = {
    'count': fields.Integer,
    'flowers': fields.List(fields.Nested(flower_fields)),
}

count_fields ={
    'count': fields.Integer
}

flower_post_parser = reqparse.RequestParser()

class FlowerResource(Resource):
    @cross_origin()
    def get(self, flower_id=None):
        if flower_id:
            flower = Flower.query.filter_by(id=flower_id).first()
            if flower:
                return marshal(flower, flower_fields)
            else:
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
                return marshal({
                    'count': len(flower)
                }, count_fields)

            flower = flower.all()

            return marshal({
                'count': len(flower),
                'flowers': [marshal(f, flower_fields) for f in flower]
            }, flower_list_fields)
    @cross_origin()
    def post(self):
        args = flower_post_parser.parse_args()
        flower = Flower(**args)
        db.session.add(flower)
        db.session.commit()
        path = Path(current_app.config['GENERATED_FOLDER'])
        makeFlower(flower.id, path.resolve())
        flower.genome = str(flower.id) + '.json'
        flower.image = str(flower.id) + '.png'
        db.session.add(flower)
        db.session.commit()
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

ancestor_post_parser.add_argument('father', type=int, required=True, location=['json'], help='father parameter is required')
ancestor_post_parser.add_argument('mother', type=int, required=True, location=['json'], help='mother parameter is required')


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
                return marshal({
                    'count': len(res)
                }, count_fields)

            res = res.all()

            if res:
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
                return marshal({
                    'count': len(res)
                }, count_fields)

            res = res.all()
            if res:
                return marshal(res, flower_fields)
            else:
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
                return marshal({
                    'count': len(ancestor)
                }, count_fields)

            ancestor = ancestor.all()

            return marshal({
                'count': len(ancestor),
                'ancestors': [marshal(a, ancestor_fields) for a in ancestor]
            }, ancestor_list_fields)
    @cross_origin()
    def post(self):
        args = ancestor_post_parser.parse_args()
        ancestor = Ancestor(**args)
        if Path(f"{current_app.config['GENERATED_FOLDER']}/{str(ancestor.father)}.json").exists() and \
                Path(f"{current_app.config['GENERATED_FOLDER']}/{str(ancestor.mother)}.json").exists():
            flower = Flower()
            db.session.add(flower)
            db.session.commit()
            flower.genome = f"{str(flower.id)}.json"
            flower.image = f"{str(flower.id)}.png"
            db.session.add(flower)
            db.session.commit()
            ancestor.id = flower.id
            path = Path(current_app.config['GENERATED_FOLDER'])
            reproduce(ancestor.father,ancestor.mother,ancestor.id, path.resolve())
            db.session.add(ancestor)
            db.session.commit()
            return marshal(flower, flower_fields)
        else:
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

mutation_post_parser.add_argument('original', type=int, required=True, location=['json'], help='original parameter is required')

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
                return marshal({
                    'count': len(res)
                }, count_fields)

            res = res.all()
            if res:
                return marshal(res, flower_fields)
            else:
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
                return marshal({
                    'count': len(mutation)
                }, count_fields)

            mutation = mutation.all()

            return marshal({
                'count': len(mutation),
                'mutations': [marshal(m, mutation_fields) for m in mutation]
            }, mutations_list_fields)
    @cross_origin()
    def post(self):
        args = mutation_post_parser.parse_args()
        mutation = Mutation(**args)
        if Path(f"{current_app.config['GENERATED_FOLDER']}/{str(mutation.original)}.json").exists():
            flower = Flower()
            db.session.add(flower)
            db.session.commit()
            flower.genome = f"{str(flower.id)}.json"
            flower.image = f"{str(flower.id)}.png"
            db.session.add(flower)
            db.session.commit()
            mutation.id = flower.id
            path = Path(current_app.config['GENERATED_FOLDER'])
            mutateFlower(mutation.original, flower.id, path.resolve())
            db.session.add(mutation)
            db.session.commit()
            return marshal(flower, flower_fields)
        else:
            return f"original {str(mutation.original)} does not exists", 404
