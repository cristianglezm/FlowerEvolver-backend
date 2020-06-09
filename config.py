class Config(object):
    ENV = 'development'
    DEBUG = True
    BUNDLE_ERRORS = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../FlowerEvolver.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GENERATED_FOLDER = './generated/'
    SECRET_KEY = ''

class ProductionConfig(Config):
    DEBUG = False
    ENV = 'production'
    @property
    def SQLALCHEMY_DATABASE_URI():
        return "mysql://{}:{}@{}/flowers".format(os.getenv("USER"), os.getenv("PASSWD"), os.getenv("HOST"))
    @property
    def SECRET_KEY():
        SECRET_KEY = os.environ.get("SECRET_KEY")
        if not SECRET_KEY:
            raise ValueError("No SECRET_KEY set for Flask application")
        return os.environ.get("SECRET_KEY")