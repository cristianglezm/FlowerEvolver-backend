from ..models import Flower, Mutation
from .. import db


def list_by_original(original, limit=0, offset=0):
    query = Flower.query.join(Mutation, Flower.id == Mutation.id)\
        .filter(Mutation.original == original).order_by(Flower.id.desc())
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


def new_mutation(original):
    return Mutation(original=original)


def save(mutation):
    db.session.add(mutation)
    db.session.commit()
