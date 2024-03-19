from flask.cli import FlaskGroup
from flask_migrate import Migrate
from dotenv import load_dotenv
from app import create_app, db

load_dotenv('.env')
app = create_app()

cli = FlaskGroup(app)
migrate = Migrate(app, db)
migrate.init_app(app)

if __name__ == '__main__':
    cli()
