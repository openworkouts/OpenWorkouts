import pytest
from unittest.mock import patch, Mock

from ow.tasks.mail import queue_processor


class TestQueueProcessor(object):

    @pytest.fixture
    def settings(self):
        settings = {
            'qp.host': 'hostname',
            'qp.username': 'username',
            'qp.password': 'xxxxxxxx',
            'mail.queue_path': '/some/path',
            'mail.queue_processor_lock': '/tmp/queue-processor.lock'}
        return settings

    @pytest.fixture
    def alt_settings(self):
        alt_settings = {
            'mail.host': 'mail-hostname',
            'mail.username': 'mail-username',
            'mail.password': 'yyyyyyyyyyyyy',
            'mail.queue_path': '/some/path',
            'mail.queue_processor_lock': '/tmp/queue-processor.lock'}
        return alt_settings

    def wrap_settings(self, settings):
        registry = Mock(settings=settings)
        return {'registry': registry}

    def params(self, settings):
        """
        Return a list of arguments that ressembles what should be passed
        to the ConsoleApp queue processor in the "real" code
        """
        args = ['qp',
                '--hostname', settings.get('qp.host',
                                           settings.get('mail.host')),
                '--username', settings.get('qp.username',
                                           settings.get('mail.username')),
                '--password', settings.get('qp.password',
                                           settings.get('mail.password')),
                settings.get('mail.queue_path')]
        return args

    @patch('fcntl.lockf')
    @patch('ow.tasks.mail.ConsoleApp')
    def test_queue_processor_settings(self, ca, lockf, settings):
        queue_processor(self.wrap_settings(settings))
        ca.assert_called_with(self.params(settings))
        # the lockf was called, to set the lock on the lock file
        assert lockf.called

    @patch('fcntl.lockf')
    @patch('ow.tasks.mail.ConsoleApp')
    def test_queue_processor_alt_settings(self, ca, lockf, alt_settings):
        queue_processor(self.wrap_settings(alt_settings))
        ca.assert_called_with(self.params(alt_settings))
        # the lockf was called, to set the lock on the lock file
        assert lockf.called

    @patch('fcntl.lockf')
    @patch('ow.tasks.mail.log')
    @patch('ow.tasks.mail.ConsoleApp')
    def test_queue_processor_lock_ioerror(self, ca, log, lockf, settings):
        """
        A second call to the queue processor while a previous run is still
        running will find a lock on the lock file, which means this call cannot
        continue, so it is aborted and a warning message is logged to the
        logging facilities
        """
        # Make lock raise an IOError, mimicing what happens when the lock has
        # been acquired by another process
        e = IOError('could not lock file!')
        lockf.side_effect = e

        ret = queue_processor(self.wrap_settings(settings))
        # Exception raised, False returned
        assert ret is False

        # Calls: fcntl.lock has been called, then the IOError was raised
        # and no more calls to the api have been made
        assert lockf.called
        assert not ca.called

        # except for the log call, which was a warning
        assert log.warning.called
