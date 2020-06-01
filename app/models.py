from singleton import db
from FlowerEvolver import *

class Flower(db.Model):
    __tablename__ = 'flower'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    genome = db.Column(db.String(255))
    image = db.Column(db.String(255))

    def __repr__(self):
        return "id: {}, genome: {}, image: {}".format(self.id, self.genome, self.image)

class Ancestor(db.Model):
    __tablename__ = 'ancestor'

    id = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False, primary_key=True)
    father = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False)
    mother = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False)

    def __repr__(self):
        return "id: {}, father: {}, mother: {}".format(self.id, self.father, self.mother)

class Mutation(db.Model):
    __tablename__ = 'mutation'

    id = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False, primary_key=True)
    original = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False)

    def __repr__(self):
        return "id: {}, original: {}".format(self.id, self.original)