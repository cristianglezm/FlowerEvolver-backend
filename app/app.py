from singleton import *
from resources import FlowerResource
from resources import AncestorResource
from resources import MutationResource

api.add_resource(FlowerResource, '/flowers', '/flowers/<int:flower_id>')
api.add_resource(MutationResource, '/mutations', '/mutations/<int:mutation_original>')
api.add_resource(AncestorResource, '/ancestors', '/ancestors/<int:father>', '/ancestors/<int:father>/<int:mother>')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
