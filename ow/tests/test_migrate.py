import os
from shutil import copyfile
from unittest.mock import patch, Mock

import pytest

from ow import migrate


class MigrateUnitTests(object):
    def test_includeme(self):
        config = Mock()
        migrate.includeme(config)
        config.scan.assert_called_with('ow.migrate')

    @patch('ow.migrate.run_migrations')
    def test_closer_wrapper_ok(self, run):
        closer = Mock()
        env = dict(
            registry=Mock(settings={}),
            root_factory=Mock(__module__='mytest'),
            request=1,
            root=2,
            closer=closer)
        migrate.closer_wrapper(env)
        run.assert_called_with(1, 2, 'mytest.migrations')
        assert closer.called

    @patch('ow.migrate.closer_wrapper')
    @patch('ow.migrate.prepare')
    def test_application_created_ok(self, prepare, wrap):
        event = Mock()
        migrate.application_created(event)
        assert prepare.called
        assert wrap.called

    @patch('ow.migrate.output')
    def test_command_line_no_conf(self, pr):
        ret = migrate.command_line_main(['test.py'])
        assert ret == 1
        assert pr.called

    @patch('ow.migrate.closer_wrapper')
    @patch('ow.migrate.bootstrap')
    def test_command_line_no(self, bs, wrap):
        ret = migrate.command_line_main(['test.py', 'dev.ini'])
        assert ret == 0
        assert bs.called
        assert wrap.called

    @patch('ow.migrate.commit')
    @patch('ow.migrate.get_connection')
    def test_reset_version(self, pget_connection, pcommit):
        zodb = {}
        pget_connection.return_value.root.return_value = zodb
        migrate.reset_version('myrequest', 25)
        assert zodb == {'database_version': 25}
        pcommit.asert_called_with()


def cleanup():
    """
    Clean up pyc files generated while running the following test suite
    """
    migrations = os.path.join(os.path.dirname(__file__), 'migrations')
    for f in os.listdir(migrations):
        if '.pyc' in f or 'fail' in f or f == '3.py':
            os.remove(os.path.join(migrations, f))


class mocked_get_connection(object):
    """
    This is a class we can use to mock pyramid_zodbconn.get_connection()
    (see test_run_migrations)
    """
    def __init__(self, versions=0):
        self.versions = versions

    def root(self):
        return {'database_version': self.versions}


class MigrateTests(object):

    package_name = 'ow.tests.migrations'
    ini_path = os.path.join(os.path.dirname(__file__), 'migrations')

    def test_get_indexes_ok(self):
        indexes = migrate.get_indexes(self.package_name)
        assert isinstance(indexes, list)
        assert len(indexes) == 2

    def test_get_indexes_fail(self):
        migrate.get_indexes(self.package_name)
        with pytest.raises(ImportError):
            migrate.get_indexes('nonexistent.module.migrations')

    def test_get_indexes_invalid(self):
        # Create a new migration file with an invalid name, so the get_indexes
        # will raise a ValueError exception
        copyfile(os.path.join(os.path.dirname(__file__), 'migrations/1.py'),
                 os.path.join(os.path.dirname(__file__), 'migrations/fail.py'))
        indexes = migrate.get_indexes(self.package_name)
        assert isinstance(indexes, list)
        assert len(indexes) == 2

    def test_get_max_in_max_cache(self):
        with patch.dict(migrate.MAX_CACHE, {self.package_name: 10}):
            max_version = migrate.get_max(self.package_name)
            assert max_version == 10

    def test_get_max(self):
        max_version = migrate.get_max(self.package_name)
        assert max_version == 2

    def test_version(self):
        # instead of a real ZODB root, we do use a simple dict here,
        # it should be enough for what need to test.
        root = {}
        root = migrate.set_version(root, 10)
        assert root['database_version'] == 10

    def test_max_version(self):
        # instead of a real ZODB root, we do use a simple dict here,
        # it should be enough for what need to test.
        root = {}
        root = migrate.set_max_version(root, self.package_name)
        assert root['database_version'] == 2

    @patch('ow.migrate.get_connection')
    @patch('ow.tests.migrations.1.output')
    @patch('ow.tests.migrations.2.output')
    def test_run_all_migrations(self, pr2, pr1, gc):
        """
        Test that all migrations apply
        """
        gc.return_value = mocked_get_connection()
        migrate.run_migrations(None, {}, self.package_name)
        cleanup()
        assert pr1.called
        assert pr2.called

    @patch('ow.migrate.get_connection')
    def test_run_no_migrations(self, gc):
        """
        Test that there are no more migrations to apply
        """
        gc.return_value = mocked_get_connection(versions=2)
        migrate.run_migrations(None, {}, self.package_name)

    @patch('ow.migrate.get_connection')
    @patch('ow.tests.migrations.1.output')
    @patch('ow.tests.migrations.2.output')
    def test_run_invalid_migrations(self, pr2, pr1, gc):
        """
        Test what happens if a migration does not contains the proper migrate
        method
        """
        invalid_migration = open(os.path.join(os.path.dirname(__file__),
                                              'migrations/3.py'), 'w')
        invalid_migration.write('# This is an empty migration, just for tests')
        invalid_migration.write('def no_migrate_method_here():')
        invalid_migration.write('    print "Nothing to see here!"')
        invalid_migration.close()
        gc.return_value = mocked_get_connection(versions=0)
        migrate.run_migrations(None, {}, self.package_name)
        assert pr1.called
        assert pr2.called
