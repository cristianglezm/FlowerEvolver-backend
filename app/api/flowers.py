import string
import random
import json
import structlog
from pydantic import ValidationError
from flask_restful import Resource, reqparse, request
from flask_restful import fields, marshal
from flask import current_app
from flask_cors import cross_origin
from pathlib import Path
from ..schemas import SharedFlower
from ..services.flower_evolver import makeFlower, drawFlower
from ..repositories import flower_repository
from ..pagination import parse_list_args, count_fields
from .. import db

logger = structlog.get_logger(__name__)

flower_fields = {
    'id': fields.Integer,
    'genome': fields.String,
    'image': fields.String,
}

flower_list_fields = {
    'count': fields.Integer,
    'flowers': fields.List(fields.Nested(flower_fields)),
}

flower_post_parser = reqparse.RequestParser()


def is_over_limit():
    return flower_repository.total_count() > int(current_app.config['FLOWER_LIMIT'])


class FlowerResource(Resource):
    @cross_origin()
    def get(self, flower_id=None):
        if flower_id:
            flower = flower_repository.get_by_id(flower_id)
            if flower:
                logger.info("flower_get", flower_id=flower_id)
                return marshal(flower, flower_fields)
            else:
                logger.info("flower_get_not_found", flower_id=flower_id)
                return "flower not found", 404

        filters, limit, offset, count, error = parse_list_args(
            request.args.to_dict(), allowed_filters=('id', 'genome', 'image'))
        if error:
            logger.info("flower_get_invalid_filter", error=error)
            return error, 400

        flowers = flower_repository.list_flowers(filters, limit, offset)
        if count:
            logger.info("flower_get_count")
            return marshal({'count': len(flowers)}, count_fields)

        logger.info("flower_get_all")
        return marshal({
            'count': len(flowers),
            'flowers': [marshal(f, flower_fields) for f in flowers]
        }, flower_list_fields)

    def get_random_filename(self):
        letters_and_digits = string.ascii_letters + string.digits
        random_filename = ''.join(random.choice(letters_and_digits) for i in range(20))
        return random_filename + '.json'

    @cross_origin()
    def post(self):
        if(is_over_limit()):
            logger.info("flower_post_over_limit")
            return "max number of flowers reached, wait for tomorrow", 403
        args = flower_post_parser.parse_args()
        path = Path(current_app.config['GENERATED_FOLDER'])
        sharedFlower = request.get_json()
        if not sharedFlower:
            logger.info("flower_post_make_flower")
            flower = flower_repository.create(**args)
            status = makeFlower(flower.id, path.resolve())
            if(status.returncode != 0):
                logger.info("flower_post_make_flower_error", error=status.stderr)
                db.session.rollback()
                return "something went wrong while making the flower.", 400
            flower.genome = f"{flower.id}.json"
            flower.image = f"{flower.id}.png"
            db.session.commit()
            return marshal(flower, flower_fields)
        logger.info("flower_post_share_flower")
        try:
            shared_flower = SharedFlower(**sharedFlower)
        except ValidationError as e:
            logger.error("flower_post_share_flower_validation_error", error=str(e))
            return "error sharing flower, probably bad format.", 400
        random_filename = self.get_random_filename()
        tmpFlower = Path(f"instance/{random_filename}")
        with open(tmpFlower.resolve(), 'w') as f:
            json.dump(shared_flower.model_dump(), f)
        flower = flower_repository.create(**args)
        status = drawFlower(flower.id, path.resolve(), tmpFlower.resolve())
        if(status.returncode != 0):
            db.session.rollback()
            tmpFlower.unlink()
            logger.error("flower_post_share_flower_draw_error", error=status.stderr)
            return "the flower genome file has invalid data.", 400
        flower.genome = f"{flower.id}.json"
        flower.image = f"{flower.id}.png"
        db.session.commit()
        tmpFlower.unlink()
        return marshal(flower, flower_fields)
