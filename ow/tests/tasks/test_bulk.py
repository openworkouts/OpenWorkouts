from unittest.mock import patch, Mock

import pytest

from ow.tasks.bulk import process_compressed_files


class TestBulkTasks(object):

    @pytest.fixture
    def settings(self):
        settings = {
            'workouts.bulk_tmp_path': '/tmp',
            'workouts.bulk_loading_lock': '/tmp/queue-processor.lock'}
        return settings

    @pytest.fixture
    def root(self):
        root = {
            '_bulk_files': {}
        }
        return root

    @pytest.fixture
    def env(self, settings, root):
        env = {
            'request': Mock(),
            'root': root,
            'registry': Mock(settings=settings)
        }
        return env

    @patch('fcntl.lockf')
    @patch('ow.tasks.bulk.log')
    def test_process_compressed_files_no_files(self, log, lockf, env):
        workouts_loaded = process_compressed_files(env)
        # the lockf was called, to set the lock on the lock file
        assert lockf.called
        # no warnings shown
        assert not log.warning.called
        # nothing loaded, no transaction committed
        assert not workouts_loaded
        assert not env['request'].tm.commit.called

    @patch('fcntl.lockf')
    @patch('ow.tasks.bulk.log')
    def test_process_compressed_files_single_file(self, log, lockf, env):
        bulk_file = Mock(loaded=False)
        env['root']['_bulk_files']['faked-bulk_id'] = bulk_file
        workouts_loaded = process_compressed_files(env)
        # the lockf was called, to set the lock on the lock file
        assert lockf.called
        # no warnings shown
        assert not log.warning.called
        # file loaded, transaction commited
        bulk_file.load.assert_called_once_with(
            env['root'],
            env['registry'].settings['workouts.bulk_tmp_path'])
        assert workouts_loaded
        env['request'].tm.commit.assert_called_once

    @patch('fcntl.lockf')
    @patch('ow.tasks.bulk.log')
    def test_process_compressed_files_already_loaded(self, log, lockf, env):
        bulk_file = Mock(loaded=True)
        env['root']['_bulk_files']['faked-bulk_id'] = bulk_file
        workouts_loaded = process_compressed_files(env)
        # the lockf was called, to set the lock on the lock file
        assert lockf.called
        # no warnings shown
        assert not log.warning.called
        # file already loaded, no transaction commited
        assert not bulk_file.load.called
        assert not workouts_loaded
        assert not env['request'].tm.commit.called

    @patch('fcntl.lockf')
    @patch('ow.tasks.bulk.log')
    def test_process_compressed_files_multiple_files(self, log, lockf, env):
        bulk_file = Mock(loaded=False)
        loaded_bulk_file = Mock(loaded=True)
        additional_bulk_file = Mock(loaded=False)
        env['root']['_bulk_files']['faked-bulk_id'] = bulk_file
        env['root']['_bulk_files']['loaded-bulk_id'] = loaded_bulk_file
        env['root']['_bulk_files']['additional-bulk_id'] = additional_bulk_file
        workouts_loaded = process_compressed_files(env)
        # the lockf was called, to set the lock on the lock file
        assert lockf.called
        # no warnings shown
        assert not log.warning.called
        # 2 files loaded, transaction commited once
        bulk_file.load.assert_called_once_with(
            env['root'],
            env['registry'].settings['workouts.bulk_tmp_path'])
        assert not loaded_bulk_file.load.called
        additional_bulk_file.load.assert_called_once_with(
            env['root'],
            env['registry'].settings['workouts.bulk_tmp_path'])
        assert workouts_loaded
        env['request'].tm.commit.assert_called_once

    @patch('fcntl.lockf')
    @patch('ow.tasks.bulk.log')
    def test_process_compressed_files_lock_ioerror(self, log, lockf, env):
        """
        A second call to this task, while a first call is still running,
        does not do anything, just log a warning message to the logger
        """
        # Make lock raise an IOError, mimicing what happens when the lock has
        # been acquired by another process
        e = IOError('could not lock file!')
        lockf.side_effect = e

        workouts_loaded = process_compressed_files(env)
        # Exception raised, False returned
        assert workouts_loaded is False

        # Calls: fcntl.lock has been called, then the IOError was raised
        # and no more calls to the api have been made
        assert lockf.called

        assert not log.info.called
        assert not log.error.called
        # except for the log call, which was a warning
        assert log.warning.called
        log_msg = log.warning.call_args_list[0][0][0]
        assert 'not run the workout bulk load task' in log_msg
        assert 'could not acquire lock' in log_msg
