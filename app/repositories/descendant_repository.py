from sqlalchemy import and_
from ..models import Flower, Descendant
from .. import db


def _children_of(father, mother):
    return Flower.query.join(Descendant, Flower.id == Descendant.id)\
        .filter(Descendant.father == father)\
        .filter(and_(Descendant.mother == mother))


def _children_of_either_parent(parent):
    return Flower.query.join(Descendant, Flower.id == Descendant.id)\
        .filter((Descendant.father == parent) | (Descendant.mother == parent))


def count_children_of(father, mother):
    return _children_of(father, mother).count()


def count_children_of_either_parent(parent):
    return _children_of_either_parent(parent).count()


def count_descendants(filters):
    return Descendant.query.filter_by(**filters).count()


def list_children_of(father, mother, limit=0, offset=0):
    query = _children_of(father, mother).order_by(Flower.id.desc())
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query.all()


def list_children_of_either_parent(parent, limit=0, offset=0):
    query = _children_of_either_parent(parent).order_by(Flower.id.desc())
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query.all()


def list_descendants(filters, limit=0, offset=0):
    query = Descendant.query.filter_by(**filters).order_by(Descendant.id.desc())
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query.all()


def new_descendant(father, mother):
    return Descendant(father=father, mother=mother)


def save(descendant):
    db.session.add(descendant)
    db.session.commit()
