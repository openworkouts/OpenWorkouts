import os
from pyramid.paster import get_app, setup_logging

current_path = os.path.dirname(os.path.abspath(__file__))

os.environ['CHAMELEON_CACHE'] = os.path.join(current_path, '../var/tmp/chameleon/')
os.environ['PYTHON_EGG_CACHE'] = os.path.join(current_path, '../var/tmp/egg_cache')

ini_path = os.path.join(current_path, '../development.ini')
setup_logging(ini_path)
application = get_app(ini_path, 'main')
