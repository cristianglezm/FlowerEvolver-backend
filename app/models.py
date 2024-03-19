from flask import Blueprint
from . import db

flowers_blueprint = Blueprint('flowers', __name__)
ancestors_blueprint = Blueprint('ancestors', __name__)
mutations_blueprint = Blueprint('mutations', __name__)


class Flower(db.Model):
    __tablename__ = 'flower'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    genome = db.Column(db.String(255))
    image = db.Column(db.String(255))

    def __repr__(self):
        return f"id: {self.id}, genome: {self.genome}, image: {self.image}"


class Ancestor(db.Model):
    __tablename__ = 'ancestor'

    id = db.Column(db.Integer, db.ForeignKey('flower.id'),
                   nullable=False, primary_key=True)
    father = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False)
    mother = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False)

    def __repr__(self):
        return f"id: {self.id}, father: {self.father}, mother: {self.mother}"


class Mutation(db.Model):
    __tablename__ = 'mutation'

    id = db.Column(db.Integer, db.ForeignKey('flower.id'),
                   nullable=False, primary_key=True)
    original = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False)

    def __repr__(self):
        return f"id: {self.id}, original: {self.original}"
