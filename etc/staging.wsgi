import os
os.environ['CHAMELEON_CACHE'] = '/home/staging/tmp/chameleon'
os.environ['PYTHON_EGG_CACHE'] = '/home/staging/tmp/egg_cache'

from pyramid.paster import get_app, setup_logging
ini_path = '/home/staging/repos/OpenWorkouts-current/staging.ini'
setup_logging(ini_path)
application = get_app(ini_path, 'main')
