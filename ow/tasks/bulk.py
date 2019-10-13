import fcntl
import logging

log = logging.getLogger(__name__)


def process_compressed_files(env):
    """
    Go over any pending-to-be-processed compressed files for bulk-upload
    workouts from those files.
    """

    settings = env['registry'].settings
    lock_filename = settings.get('workouts.bulk_loading_lock')
    lock_file = open(lock_filename, 'w')
    try:
        fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        # Can't lock, probably another process is running, report to logging
        # and exit
        log.warning('Could not run the workout bulk load task, '
                    'could not acquire lock (maybe another process is '
                    'running?)')
        return False

    request = env['request']
    root = env['root']
    workouts_loaded = False
    tmp_path = settings.get('workouts.bulk_tmp_path')

    for bulk_file in root['_bulk_files'].values():
        if not bulk_file.loaded:
            bulk_file.load(root, tmp_path)
            workouts_loaded = True

    if workouts_loaded:
        request.tm.commit()

    return workouts_loaded
