import transaction

from ow.models.root import OpenWorkouts
from ow.models.bulk import BulkFiles
from ow.catalog import get_catalog


def appmaker(zodb_root):
    if 'app_root' not in zodb_root:
        app_root = OpenWorkouts()
        app_root['_bulk_files'] = BulkFiles()
        zodb_root['app_root'] = app_root
        transaction.commit()
        # initialize the catalog for the first time
        get_catalog(app_root)
    return zodb_root['app_root']
