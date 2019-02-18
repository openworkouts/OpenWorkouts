from unittest.mock import Mock, patch

import pytest

from pyramid.testing import DummyRequest

from ow.tasks.manager import TasksManager
from ow.tasks.run import command_line


@patch('ow.tasks.manager.setup_logging')
@patch('ow.tasks.manager.bootstrap')
@patch('ow.tasks.run.sys')
@patch('ow.tasks.run.TasksManager')
class TestCommandLine(object):
    """
    Tests covering the command_line method that allows users to execute the
    tasks manager from a CLI.
    """

    @pytest.fixture
    def registry(self):
        """
        Mock a pyramid registry
        """
        registry = Mock()
        registry.settings = {}
        return registry

    @pytest.fixture
    def env(self, registry):
        env = {'request': DummyRequest(),
               'root': {},
               'closer': Mock(),
               'registry': registry}
        return env

    @pytest.fixture
    def manager(self):
        tm = TasksManager()
        tm.usage = Mock()
        tm.usage.return_value = 'faked manager usage'
        return tm

    def test_wrong_params(self, tm, mysys, b, manager, env):
        mysys.argv = ['script', 'one', 'two', 'three']
        mysys.exit.side_effect = ValueError('sysexit')
        tm.return_value = manager
        b.return_value = env
        with pytest.raises(ValueError):
            command_line()
        mysys.exit.assert_called_with(1)

    @patch('ow.tasks.run.queue_processor')
    def test_right_params_send_emails(
            self, qp, tm, mysys, b, sl, manager, env):
        mysys.argv = ['tasks-script', 'tests.ini', 'send_emails']
        qp.return_value = None
        tm.return_value = manager
        b.return_value = env
        command_line()
        qp.assert_called_with(env)
