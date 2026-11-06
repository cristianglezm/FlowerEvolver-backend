import importlib
import config


def production_uri(monkeypatch, **env):
    for name in ('DB_USER', 'USER', 'PASSWD', 'HOST', 'DB'):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return importlib.reload(config).ProductionConfig.SQLALCHEMY_DATABASE_URI


def test_db_user_is_used_for_the_mysql_login(monkeypatch):
    uri = production_uri(monkeypatch, DB_USER='fe', USER='someone-else', PASSWD='pw', HOST='db', DB='flowers')
    assert uri == 'mysql://fe:pw@db/flowers'


def test_user_is_the_fallback_when_db_user_is_missing(monkeypatch):
    uri = production_uri(monkeypatch, USER='legacy', PASSWD='pw', HOST='db', DB='flowers')
    assert uri == 'mysql://legacy:pw@db/flowers'


def test_special_characters_in_the_password_are_escaped(monkeypatch):
    uri = production_uri(monkeypatch, DB_USER='fe', PASSWD='p@ss/w:rd#1', HOST='db', DB='flowers')
    assert uri == 'mysql://fe:p%40ss%2Fw%3Ard%231@db/flowers'
    importlib.reload(config)
