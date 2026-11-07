import importlib
import config

NAMES = ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWD', 'HOST', 'DB', 'USER', 'PASSWD')


def production_uri(monkeypatch, **env):
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return importlib.reload(config).ProductionConfig.SQLALCHEMY_DATABASE_URI


def teardown_module(module):
    importlib.reload(config)


def test_the_db_names_build_the_mysql_uri(monkeypatch):
    uri = production_uri(monkeypatch, DB_HOST='db', DB_NAME='flowers', DB_USER='fe', DB_PASSWD='pw')
    assert uri == 'mysql://fe:pw@db/flowers'


def test_the_old_generic_names_are_not_read(monkeypatch):
    # USER is your shell login, HOST/DB/PASSWD are too generic: they must never end up in the uri
    uri = production_uri(monkeypatch, DB_HOST='db', DB_NAME='flowers', DB_USER='fe', DB_PASSWD='pw',
                         HOST='other', DB='other', USER='someone-else', PASSWD='other')
    assert uri == 'mysql://fe:pw@db/flowers'
    assert production_uri(monkeypatch, HOST='db', DB='flowers', USER='legacy', PASSWD='pw') == 'mysql://:@/'


def test_special_characters_in_the_password_are_escaped(monkeypatch):
    uri = production_uri(monkeypatch, DB_HOST='db', DB_NAME='flowers', DB_USER='fe', DB_PASSWD='p@ss/w:rd#1')
    assert uri == 'mysql://fe:p%40ss%2Fw%3Ard%231@db/flowers'
