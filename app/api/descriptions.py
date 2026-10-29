from flask_restful import Resource, request
from flask_restful import fields, marshal
from flask import current_app
from flask_cors import cross_origin
from ..repositories import description_repository
from ..pagination import parse_list_args, count_fields

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
        if desc_id:
            res = description_repository.get_by_id(desc_id)
            if res:
                current_app.logger.info(f"Descriptions - get - {desc_id} - all")
                return marshal(res, descriptions_fields)
            current_app.logger.info("Descriptions - get - not found")
            return f"flower {str(desc_id)} has no description", 404

        filters, limit, offset, count, error = parse_list_args(
            request.args.to_dict(), allowed_filters=('id', 'description'))
        if error:
            return error, 400

        descriptions = description_repository.list_descriptions(filters, limit, offset)
        if count:
            current_app.logger.info("Descriptions - get - all - count")
            return marshal({'count': len(descriptions)}, count_fields)

        current_app.logger.info("Descriptions - get - all")
        return marshal({
            'count': len(descriptions),
            'descriptions': [marshal(d, descriptions_fields) for d in descriptions]
        }, descriptions_list_fields)
