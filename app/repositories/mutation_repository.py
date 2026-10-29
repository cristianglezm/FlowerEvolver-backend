from ..models import Flower, Mutation
from .. import db


def _by_original(original):
    return Flower.query.join(Mutation, Flower.id == Mutation.id).filter(Mutation.original == original)


def count_by_original(original):
    return _by_original(original).count()


def list_by_original(original, limit=0, offset=0):
    query = _by_original(original).order_by(Flower.id.desc())
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query.all()


def list_mutations(filters, limit=0, offset=0):
    query = Mutation.query.filter_by(**filters).order_by(Mutation.id.desc())
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query.all()


def count_mutations(filters):
    return Mutation.query.filter_by(**filters).count()


def new_mutation(original):
    return Mutation(original=original)


def save(mutation):
    db.session.add(mutation)
    db.session.commit()
