from datetime import datetime, timedelta, timezone

import pytest

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.query import Eq

from ow.models.workout import Workout
from ow.models.user import User
from ow.models.root import OpenWorkouts

from ow.catalog import (
    get_catalog,
    update_indexes,
    install_catalog,
    remove_from_catalog,
    resources_from_query_results
    )


class TestCatalog(object):

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['john'] = User(firstname='John', lastname='Doe',
                            email='john.doe@example.net')
        root['john'].password = 's3cr3t'
        workout = Workout(
            start=datetime(2015, 6, 28, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=30, sport='cycling'
        )
        root['john'].add_workout(workout)
        return root

    def test_update_indexes_no_changes(self, root):
        catalog = get_catalog(root)
        indexes = root._get_catalog_indexes()
        changes = update_indexes(catalog, indexes)
        assert changes['added'] == []
        assert changes['removed'] == []

    def test_update_indexes_added(self, root):
        catalog = get_catalog(root)
        indexes = root._get_catalog_indexes()
        indexes['newindex'] = CatalogFieldIndex('newindex')
        changes = update_indexes(catalog, indexes)
        assert changes['added'] == ['newindex']
        assert changes['removed'] == []

    def test_update_indexes_removed(self, root):
        catalog = get_catalog(root)
        indexes = {'newindex': CatalogFieldIndex('newindex')}
        changes = update_indexes(catalog, indexes)
        assert changes['added'] == ['newindex']
        assert changes['removed'] == ['email', 'nickname', 'sport', 'hashed']

    def test_update_indexes_empty(self, root):
        catalog = get_catalog(root)
        indexes = {}
        changes = update_indexes(catalog, indexes)
        assert changes['added'] == []
        assert changes['removed'] == ['email', 'nickname', 'sport', 'hashed']

    def test_install_catalog(self):
        root = OpenWorkouts()
        assert isinstance(getattr(root, 'catalog', None), Catalog)
        del root.catalog
        assert getattr(root, 'catalog', None) is None
        install_catalog(root)
        assert isinstance(getattr(root, 'catalog', None), Catalog)

    def test_get_catalog_existing_catalog(self, root):
        assert isinstance(getattr(root, 'catalog', None), Catalog)
        catalog = get_catalog(root)
        assert catalog == root.catalog

    def test_get_catalog_not_existing_catalog(self):
        root = OpenWorkouts()
        assert isinstance(getattr(root, 'catalog', None), Catalog)
        del root.catalog
        assert getattr(root, 'catalog', None) is None
        catalog = get_catalog(root)
        assert isinstance(getattr(root, 'catalog', None), Catalog)
        assert catalog == root.catalog

    def test_get_catalog_root_child(self, root):
        user = root['john']
        assert getattr(user, 'catalog', None) is None
        catalog = get_catalog(user)
        assert getattr(user, 'catalog', None) is None
        assert isinstance(getattr(root, 'catalog', None), Catalog)
        assert catalog == root.catalog

    def test_remove_from_catalog(self, root):
        catalog = get_catalog(root)
        number, results = catalog.query(Eq('sport', 'cycling'))
        assert number == 1
        remove_from_catalog(catalog, root['john']['1'])
        number, results = catalog.query(Eq('sport', 'cycling'))
        assert number == 0

    def test_resources_from_query_results(self, root):
        catalog = get_catalog(root)
        number, results = catalog.query(Eq('sport', 'cycling'))
        resources = resources_from_query_results(catalog, results, root)
        assert root['john']['1'] in list(resources)
