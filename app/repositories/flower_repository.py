from ..models import Flower
from .. import db


def get_by_id(flower_id):
    return Flower.query.filter_by(id=flower_id).first()


def list_flowers(filters, limit=0, offset=0):
    query = Flower.query.filter_by(**filters).order_by(Flower.id.desc())
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query.all()


def total_count():
    return Flower.query.count()


def create(**kwargs):
    flower = Flower(**kwargs)
    db.session.add(flower)
    db.session.flush()
    return flower
