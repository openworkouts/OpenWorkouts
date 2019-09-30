from ow.models.bulk import BulkFiles


def migrate(root):
    """
    Adds the _bulk_files folder to the root object (a ow.models.BulkFiles
    instance, see ticket #77 for more information)

    >>> from ow.models.root import OpenWorkouts
    >>> from ow.models.bulk import BulkFiles
    >>> root = OpenWorkouts()
    >>> '_bulk_files' in root.keys()
    False
    >>> migrate(root)
    >>> '_bulk_files' in root.keys()
    True
    >>> isinstance(root['_bulk_files'], BulkFiles)
    True
    >>> len(root['_bulk_files'])
    0
    >>>
    """
    if '_bulk_files' not in root.keys():
        root['_bulk_files'] = BulkFiles()
