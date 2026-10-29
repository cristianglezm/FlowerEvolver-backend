import structlog
from flask_restful import Resource, reqparse, request
from flask_restful import fields, marshal
from flask_cors import cross_origin
from pathlib import Path
from flask import current_app
from ..repositories import flower_repository, descendant_repository
from ..pagination import parse_list_args, count_fields
from ..services.flower_evolver import reproduce
from .. import db
from .flowers import flower_fields, is_over_limit

logger = structlog.get_logger(__name__)

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
                logger.info("descendant_get_count", father=father, mother=mother)
                return marshal({'count': len(res)}, count_fields)

            if res:
                logger.info("descendant_get_by_parents", father=father, mother=mother)
                return marshal(res, flower_fields)
            logger.info("descendant_get_by_parents_not_found", father=father, mother=mother)
            return f"Flowers by father id {str(father)} and mother id {str(mother)} not found", 404
        elif father:
            filters, limit, offset, count, error = parse_list_args(request.args.to_dict())
            if error:
                return error, 400

            res = descendant_repository.list_children_of_either_parent(father, limit, offset)
            if count:
                logger.info("descendant_get_count_by_parent", parent=father)
                return marshal({'count': len(res)}, count_fields)

            if res:
                logger.info("descendant_get_by_parent", parent=father)
                return marshal(res, flower_fields)
            logger.info("descendant_get_by_parent_not_found", parent=father)
            return f"Flowers by father or mother id {str(father)} not found", 404
        else:
            filters, limit, offset, count, error = parse_list_args(
                request.args.to_dict(), allowed_filters=('id', 'father', 'mother'))
            if error:
                logger.info("descendant_get_invalid_filter", error=error)
                return error, 400

            descendants = descendant_repository.list_descendants(filters, limit, offset)
            if count:
                logger.info("descendant_get_all_count")
                return marshal({'count': len(descendants)}, count_fields)

            logger.info("descendant_get_all")
            return marshal({
                'count': len(descendants),
                'descendants': [marshal(d, descendant_fields) for d in descendants]
            }, descendant_list_fields)

    @cross_origin()
    def post(self):
        if(is_over_limit()):
            logger.info("descendant_post_over_limit")
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
                logger.info("descendant_post_reproduce_error", father=descendant.father,
                            mother=descendant.mother, error=status.stderr)
                return f"Something went wrong then repoducing flowers with id {descendant.father} and {descendant.mother}", 400
            descendant_repository.save(descendant)
            logger.info("descendant_post_reproduce", father=descendant.father, mother=descendant.mother, id=descendant.id)
            return marshal(flower, flower_fields)
        else:
            logger.info("descendant_post_parents_not_found", father=descendant.father, mother=descendant.mother)
            return "Father or Mother has not been found", 404
