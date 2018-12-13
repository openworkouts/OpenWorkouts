from repoze.catalog.catalog import Catalog
from repoze.catalog.document import DocumentMap

from pyramid.traversal import find_resource, resource_path


def update_indexes(catalog, indexes={}):
    """
    Setup indexes in the catalog.

    Any index in indexes that does not exist in the catalog will be added to it
    Any index in the catalog that is not in indexes will be removed from it
    """
    added = []
    removed = []
    # add indexes
    for name, index in indexes.items():
        if name not in catalog:
            added.append(name)
            catalog[name] = index
    # remove indexes
    for name in list(catalog.keys()):
        if name not in indexes:
            removed.append(name)
            del catalog[name]
    return {'added': added, 'removed': removed}


def install_catalog(obj):
    """
    Install a catalog in an object.

    The indexes to be used are set up in a method called
    _get_catalog_indexes() in the object.
    """
    obj.catalog = Catalog()
    obj.catalog.document_map = DocumentMap()
    indexes = obj._get_catalog_indexes()
    update_indexes(obj.catalog, indexes)


def get_catalog(obj):
    """
    Return the catalog for this object:

      - if the object is the root folder and has no catalog, create one
        and return that

      - if the object is the root folder and has a catalog, return that

      - if the object is not the root folder and has a catalog by itself,
        return that

      - if the object is not the root folder and has not a catalog by itself,
        find the root and operate as described in the previous first 2 cases
    """
    # object has its own catalog
    catalog = getattr(obj, "catalog", None)
    if catalog is not None:
        # the object has a catalog
        return catalog

    # go backwards up to the root of the tree, if we find any parent with
    # a catalog, return that, otherwise keep on until the root object
    while obj.__parent__ is not None:
        obj = obj.__parent__
        catalog = getattr(obj, "catalog", None)
        if catalog is not None:
            return catalog

    # this code is run when the object is the root folder and has not a
    # catalog already
    install_catalog(obj)
    catalog = obj.catalog
    return catalog


def address_docid(catalog, obj):
    """
    Get the address and docid of an obj in the catalog
    (return None for the docid if it doesn't exist yet).
    """
    address = resource_path(obj)
    docid = catalog.document_map.docid_for_address(address)
    return address, docid


def reindex_object(catalog, obj):
    """
    Index or reindex an object.
    """
    address, docid = address_docid(catalog, obj)
    if docid is not None:
        # reindex an existing catalog entry
        catalog.reindex_doc(docid, obj)
    else:
        # new in the catalog
        docid = catalog.document_map.add(address)
        catalog.index_doc(docid, obj)


def remove_from_catalog(catalog, obj):
    """
    Handle removing of the address mapping and unindexing an object.
    """
    address, docid = address_docid(catalog, obj)
    if docid is not None:
        catalog.unindex_doc(docid)
        catalog.document_map.remove_docid(docid)


def resources_from_query_results(catalog, results, context):
    """
    Return an iterator to get to the objects from a query result
    (which returns "addresses", i.e. resource paths).
    results - the ressult from the query
    context - an object (root folder usually)
    """
    dm = catalog.document_map
    for docid in results:
        address = dm.address_for_docid(docid)
        yield find_resource(context, address)
