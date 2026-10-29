from app import create_app


def test_the_tests_use_a_temporary_database_and_not_the_one_in_db():
    uri = create_app().config['SQLALCHEMY_DATABASE_URI']
    assert 'fe-tests-' in uri and uri.endswith('FlowerEvolver.db')
    assert 'db/FlowerEvolver.db' not in uri.replace('fe-tests-', '')
