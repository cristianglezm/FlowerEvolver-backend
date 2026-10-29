from . import db


class Flower(db.Model):
    __tablename__ = 'flower'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    genome = db.Column(db.String(255))
    image = db.Column(db.String(255))

    def __repr__(self):
        return f"id: {self.id}, genome: {self.genome}, image: {self.image}"


class Descendant(db.Model):
    __tablename__ = 'descendant'

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


class Descriptions(db.Model):
    __tablename__ = 'descriptions'

    id = db.Column(db.Integer, db.ForeignKey('flower.id'), nullable=False, primary_key=True)
    description = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"id: {self.id}, description:{self.description}"
