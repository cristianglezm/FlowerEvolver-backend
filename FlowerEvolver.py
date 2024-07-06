from flask.cli import FlaskGroup
from flask_migrate import Migrate
from dotenv import load_dotenv
from app import create_app, db
import logging
from logging.handlers import RotatingFileHandler

load_dotenv('.env')
app = create_app()

handler = RotatingFileHandler('instance/app.log', maxBytes=100000, backupCount=1)
handler.setLevel(logging.ERROR)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

app.logger.addHandler(handler)

cli = FlaskGroup(app)
migrate = Migrate(app, db)
migrate.init_app(app)

if __name__ == '__main__':
    cli()
