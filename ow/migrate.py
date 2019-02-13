import pkgutil
import importlib
import logging
from bisect import insort, bisect_right

from pyramid_zodbconn import get_connection
from pyramid.scripting import prepare
from pyramid.paster import bootstrap
from pyramid.events import subscriber, ApplicationCreated

from transaction import commit

# Cache for maximum versions of migrations for packages
MAX_CACHE = {}
log = logging.getLogger(__name__)


def get_indexes(package_name):
    """
    Gets a sorted list of migrations in a package
    """
    package = importlib.import_module(package_name)
    indexes = []
    for (loader, name, ispkg) in pkgutil.iter_modules(package.__path__):
        try:
            insort(indexes, int(name))
        except ValueError:
            continue
    return indexes


def get_max(package_name):
    """
    Get the maximum version for a package of migrations
    """
    if package_name in MAX_CACHE:
        return MAX_CACHE[package_name]

    indexes = get_indexes(package_name)
    retval = 0
    if len(indexes) > 0:
        retval = indexes[-1]

    MAX_CACHE[package_name] = retval
    return retval


def set_max_version(zodb_root, package_name):
    """
    Set the version to the maximum in the zodb_root using the given package
    name
    """
    zodb_root = set_version(zodb_root, get_max(package_name))
    return zodb_root


def reset_version(request, version):
    """
    Forces the database version to a specific one and commits
    """
    dbroot = get_connection(request).root()
    set_version(dbroot, version)
    commit()


def set_version(zodb_root, version):
    """
    Sets the version
    """
    zodb_root['database_version'] = version
    return zodb_root


def run_migrations(request, root, package_name):
    """
    Run migrations from a package_name
    """
    indexes = get_indexes(package_name)
    dbroot = get_connection(request).root()
    current = dbroot.get('database_version', 0)
    migrations_to_apply = indexes[bisect_right(indexes, current):]
    if len(migrations_to_apply) == 0:
        log.info("Your database is in the latest version: '%i'. No migrations"
                 " will be applied." % current)
    else:
        log.info("Starting migrations from %i" % current)
    for index in migrations_to_apply:
        migration = importlib.import_module("%s.%s" % (package_name, index))
        if not hasattr(migration, 'migrate'):
            log.error('No migrate method found for %s' % migration.__name__)
            return False
        log.info("Running migration %i" % index)
        if hasattr(migration.migrate, '__doc__'):
            doc = migration.migrate.__doc__.strip().split('\n')
            description = []
            for line in doc:
                line = line.strip()
                if line == '':
                    break
                description.append(line)
            first_paragraph = ' '.join(description)
            log.info('"""%s"""' % first_paragraph)
        migration.migrate(root)
        set_version(dbroot, index)
        commit()


def closer_wrapper(env):
    closer = env['closer']
    registry = env['registry']
    root_factory = env['root_factory']
    package = registry.settings.get(
        'migrations_package', root_factory.__module__ + '.migrations')
    # Run migrations
    try:
        run_migrations(env['request'], env['root'], package)
    finally:
        closer()


def output(*args):  # pragma: nocover
    print(args)


def command_line_main(argv):
    """
    migrates the given database (Command line)

    This command will use the bootstrap system from pyramid to start the
    appllication without webserver.

    Use this function to create a command line caller for the migrations. Pass
    the sys.argv as parameter.
    """
    # Arguments
    args = argv[1:]
    if not len(args) == 1:
        output('You must provide at least one argument: configuration file')
        return 1
    config_uri = args[0]
    # Prepare application
    env = bootstrap(config_uri)
    closer_wrapper(env)
    return 0


@subscriber(ApplicationCreated)
def application_created(event):
    app = event.app
    env = prepare(registry=app.registry)
    closer_wrapper(env)


def includeme(config):
    config.scan('ow.migrate')
