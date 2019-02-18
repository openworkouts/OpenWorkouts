from unittest.mock import Mock, patch
from io import StringIO

import pytest

from ow.tasks.manager import TasksManager


def faked_task(env):
    """
    This is a helper method, used in the tests below, mimicing a real
    task we can add/remove to/from the task manager

    >>> faked_task('env')
    2
    >>>
    """
    return 0 + 2


class TestsTasksManager(object):

    @pytest.fixture
    def manager(self):
        tm = TasksManager()
        return tm

    def test__init__(self, manager):
        # once created, the manager has no tasks ready to be executed
        assert manager.managers == {}

    @patch('sys.stdout', new_callable=StringIO)
    def test_usage_empty(self, stdo, manager):
        # without tasks
        manager.usage('tasks-script')
        assert 'tasks-script /path/to/settings.ini' in stdo.getvalue()
        assert 'faked-task' not in stdo.getvalue()

    @patch('sys.stdout', new_callable=StringIO)
    def test_usage_with_tasks(self, stdo, manager):
        # with tasks
        manager.add_task('faked-task', faked_task)
        manager.usage('tasks-script')
        assert 'tasks-script /path/to/settings.ini' in stdo.getvalue()
        assert 'faked-task' in stdo.getvalue()
        assert faked_task.__doc__ in stdo.getvalue()

    def test_add_task(self, manager):
        assert manager.managers == {}
        manager.add_task('faked-task', faked_task)
        assert manager.managers == {'faked-task': faked_task}

    def test_override_task(self, manager):
        # if we call add_task on an existing task name, the task gets
        # overriden
        assert manager.managers == {}
        manager.add_task('faked-task', faked_task)
        assert manager.managers == {'faked-task': faked_task}
        manager.add_task('faked-task', 'some-faked-not-object-task')
        assert manager.managers == {'faked-task': 'some-faked-not-object-task'}

    def test_remove_task(self, manager):
        # try first to remove a non-existant task, nothing happens
        assert manager.managers == {}
        manager.remove_task('faked-task')
        assert manager.managers == {}
        manager.add_task('faked-task', faked_task)
        assert manager.managers == {'faked-task': faked_task}
        manager.remove_task('faked-task')
        assert manager.managers == {}

    @patch('sys.stdout', new_callable=StringIO)
    @patch('ow.tasks.manager.setup_logging')
    @patch('ow.tasks.manager.bootstrap')
    def test_run_empty(self, b, sl, stdo, manager):
        # we try to run a task that is not there, the usage method is called
        env = {'closer': Mock()}
        b.return_value = env
        manager.run('tasks-script', 'development.ini', 'faked-task')
        assert 'tasks-script /path/to/settings.ini' in stdo.getvalue()
        assert 'faked-task' not in stdo.getvalue()
        b.assert_called_with('development.ini')
        sl.assert_called_with('development.ini')
        assert env['closer'].called

    @patch('sys.stdout', new_callable=StringIO)
    @patch('ow.tasks.manager.setup_logging')
    @patch('ow.tasks.manager.bootstrap')
    def test_run_invalid_task(self, b, sl, stdo, manager):
        # we try to run a task that is not there, the usage method is called
        env = {'closer': Mock()}
        b.return_value = env
        manager.add_task('faked-task', faked_task)
        manager.run('tasks-script', 'development.ini', 'wipe-it-all')
        assert 'tasks-script /path/to/settings.ini' in stdo.getvalue()
        assert 'faked-task' in stdo.getvalue()
        assert faked_task.__doc__ in stdo.getvalue()
        b.assert_called_with('development.ini')
        sl.assert_called_with('development.ini')
        assert env['closer'].called

    @patch('ow.tasks.manager.setup_logging')
    @patch('ow.tasks.manager.bootstrap')
    def test_run_ok(self, b, sl, manager):
        # we try to run a task that is not there, the usage method is called
        env = {'closer': Mock()}
        b.return_value = env
        # for this test use this, easier to assert calls later
        mocked_faked_task = Mock()
        manager.add_task('faked-task', mocked_faked_task)
        manager.run('tasks-script', 'development.ini', 'faked-task')
        b.assert_called_with('development.ini')
        sl.assert_called_with('development.ini')
        mocked_faked_task.assert_called_with(env)
        assert env['closer'].called
