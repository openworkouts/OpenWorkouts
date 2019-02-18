"""
Mail handling code. Any periodic task related to send/get emails is here
"""

import fcntl
import logging
from repoze.sendmail.queue import ConsoleApp

log = logging.getLogger(__name__)


def queue_processor(env):
    """
    Process the email queue, reusing repoze.sendmail default queue management
    machinery.
    """
    # This mimics what is done by running the "qp" utility from
    # repoze.sendmail, but uses our default .ini settings instead of using a
    # separate ini file.

    # This function expects some qp.* parameters in the provided settings,
    # using the mail.* parameters as a fallback in case the former were not
    # there.

    # Before doing anything, check if a lock file exists. If it exists, exit
    # without doing anything, as another queue processor process is running.
    # See ticket #1389 for more information
    settings = env['registry'].settings
    lock_filename = settings.get('mail.queue_processor_lock')
    lock_file = open(lock_filename, 'w')
    try:
        fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        # Can't lock, probably another process is running, report to logging
        # and exit
        log.warning('Could not run the mail queue processing task, '
                    'could not acquire lock (maybe another process is '
                    'running?)')
        return False

    args = ['qp',
            '--hostname', settings.get('qp.host', settings.get('mail.host')),
            '--username', settings.get('qp.username',
                                       settings.get('mail.username')),
            '--password', settings.get('qp.password',
                                       settings.get('mail.password')),
            settings.get('mail.queue_path')]
    app = ConsoleApp(args)
    app.main()
