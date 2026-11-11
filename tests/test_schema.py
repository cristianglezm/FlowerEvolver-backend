import pytest
from sqlalchemy.dialects import mysql, sqlite
from sqlalchemy.schema import CreateTable
from app import db, models  # noqa: F401


def test_all_tables_are_registered():
    assert set(db.metadata.tables) == {'flower', 'descendant', 'mutation', 'descriptions'}


@pytest.mark.parametrize('dialect', [mysql.dialect(), sqlite.dialect()], ids=['mysql', 'sqlite'])
def test_every_table_can_be_created(dialect):
    for table in db.metadata.sorted_tables:
        CreateTable(table).compile(dialect=dialect)
