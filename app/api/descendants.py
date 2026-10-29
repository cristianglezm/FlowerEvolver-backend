from flask_restful import Resource, reqparse, request
from flask_restful import fields, marshal
from flask import current_app
from flask_cors import cross_origin
from pathlib import Path
from ..repositories import flower_repository, descendant_repository
from ..pagination import parse_list_args, count_fields
from ..services.flower_evolver import reproduce
from .. import db
from .flowers import flower_fields, is_over_limit

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
        if father and mother:
            filters, limit, offset, count, error = parse_list_args(request.args.to_dict())
            if error:
                return error, 400

            res = descendant_repository.list_children_of(father, mother, limit, offset)
            if count:
                current_app.logger.info("Descendants - get - count")
                return marshal({'count': len(res)}, count_fields)

            if res:
                current_app.logger.info(f"Descendants - get - all from - {father} and {mother}")
                return marshal(res, flower_fields)
            return f"Flowers by father id {str(father)} and mother id {str(mother)} not found", 404
        elif father:
            filters, limit, offset, count, error = parse_list_args(request.args.to_dict())
            if error:
                return error, 400

            res = descendant_repository.list_children_of_either_parent(father, limit, offset)
            if count:
                current_app.logger.info(f"Descendants - get - count from - {father}")
                return marshal({'count': len(res)}, count_fields)

            if res:
                current_app.logger.info(f"Descendants - get - all from - {father}")
                return marshal(res, flower_fields)
            current_app.logger.info(f"Descendants - get - not found from - {father}")
            return f"Flowers by father or mother id {str(father)} not found", 404
        else:
            filters, limit, offset, count, error = parse_list_args(
                request.args.to_dict(), allowed_filters=('id', 'father', 'mother'))
            if error:
                return error, 400

            descendants = descendant_repository.list_descendants(filters, limit, offset)
            if count:
                current_app.logger.info("Descendants - get - all - count")
                return marshal({'count': len(descendants)}, count_fields)

            current_app.logger.info("Descendants - get - all")
            return marshal({
                'count': len(descendants),
                'descendants': [marshal(d, descendant_fields) for d in descendants]
            }, descendant_list_fields)

    @cross_origin()
    def post(self):
        if(is_over_limit()):
            current_app.logger.info("Descendants - post - max number reached.")
            return "max number of flowers reached, wait for tomorrow", 403
        args = descendant_post_parser.parse_args()
        descendant = descendant_repository.new_descendant(**args)
        if Path(f"{current_app.config['GENERATED_FOLDER']}/{str(descendant.father)}.json").exists() and \
                Path(f"{current_app.config['GENERATED_FOLDER']}/{str(descendant.mother)}.json").exists():
            flower = flower_repository.create()
            flower.genome = f"{str(flower.id)}.json"
            flower.image = f"{str(flower.id)}.png"
            descendant.id = flower.id
            path = Path(current_app.config['GENERATED_FOLDER'])
            status = reproduce(descendant.father, descendant.mother, descendant.id, path.resolve())
            if(status.returncode != 0):
                db.session.rollback()
                current_app.logger.info(f"Descendants - post - reproduce - error - {status.stderr}")
                return f"Something went wrong then repoducing flowers with id {descendant.father} and {descendant.mother}", 400
            descendant_repository.save(descendant)
            current_app.logger.info("Descendants - post - reproduce")
            return marshal(flower, flower_fields)
        else:
            current_app.logger.info("Descendants - post - father or mother not found")
            return "Father or Mother has not been found", 404
