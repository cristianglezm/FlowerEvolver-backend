from flask_restful import Resource, reqparse, request
from flask_restful import fields, marshal
from flask import current_app
from flask_cors import cross_origin
from pathlib import Path
from ..repositories import flower_repository, mutation_repository
from ..pagination import parse_list_args, count_fields
from ..services.flower_evolver import mutateFlower
from .. import db
from .flowers import flower_fields, is_over_limit

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
        if mutation_original:
            filters, limit, offset, count, error = parse_list_args(request.args.to_dict())
            if error:
                return error, 400

            res = mutation_repository.list_by_original(mutation_original, limit, offset)
            if count:
                current_app.logger.info("Mutations - get - count")
                return marshal({'count': len(res)}, count_fields)

            if res:
                current_app.logger.info(f"Mutations - get - {mutation_original} - all")
                return marshal(res, flower_fields)
            current_app.logger.info("Mutations - get - not found")
            return f"flower {str(mutation_original)} has no mutations", 404
        else:
            filters, limit, offset, count, error = parse_list_args(
                request.args.to_dict(), allowed_filters=('id', 'original'))
            if error:
                return error, 400

            mutations = mutation_repository.list_mutations(filters, limit, offset)
            if count:
                current_app.logger.info("Mutations - get - all - count")
                return marshal({'count': len(mutations)}, count_fields)

            current_app.logger.info("Mutations - get - all")
            return marshal({
                'count': len(mutations),
                'mutations': [marshal(m, mutation_fields) for m in mutations]
            }, mutations_list_fields)

    @cross_origin()
    def post(self):
        if(is_over_limit()):
            current_app.logger.info("Mutations - post - max number reached.")
            return "max number of flowers reached, wait for tomorrow", 403
        args = mutation_post_parser.parse_args()
        mutation = mutation_repository.new_mutation(**args)
        if Path(f"{current_app.config['GENERATED_FOLDER']}/{str(mutation.original)}.json").exists():
            flower = flower_repository.create()
            flower.genome = f"{str(flower.id)}.json"
            flower.image = f"{str(flower.id)}.png"
            mutation.id = flower.id
            path = Path(current_app.config['GENERATED_FOLDER'])
            status = mutateFlower(mutation.original, flower.id, path.resolve())
            if(status.returncode != 0):
                db.session.rollback()
                current_app.logger.info(f"Mutations - post - make mutation from original {str(mutation.original)} - error {status.stderr}")
                return f"Something went wrong when making mutations with original {mutation.original}", 400
            mutation_repository.save(mutation)
            current_app.logger.info(f"Mutations - post - make mutations from original {str(mutation.original)}")
            return marshal(flower, flower_fields)
        else:
            current_app.logger.info(f"Mutations - post - original {str(mutation.original)} not found")
            return f"original {str(mutation.original)} does not exists", 404
