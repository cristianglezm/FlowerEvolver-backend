from ..models import Descriptions
from .. import db


def get_by_id(desc_id):
    return Descriptions.query.filter_by(id=desc_id).first()


def list_descriptions(filters, limit=0, offset=0):
    query = Descriptions.query.filter_by(**filters).order_by(Descriptions.id.desc())
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query.all()


def create(request_id, description):
    desc = Descriptions(id=request_id, description=description)
    db.session.add(desc)
    db.session.commit()
    return desc
