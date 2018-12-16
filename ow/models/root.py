import json

from repoze.folder import Folder
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.query import Eq

from pyramid.security import Allow, Everyone

from ow.models.user import User
from ow.catalog import (
    get_catalog,
    install_catalog,
    reindex_object,
    remove_from_catalog,
    resources_from_query_results
)


class OpenWorkouts(Folder):
    """
    Root object, contains basically all the users, and in turn
    the users contain their workouts.

    Users are stored in a dict-like structure, using a string containing
    the user id (uid) as a key, and the User object as the value.
    """

    __parent__ = __name__ = None

    __acl__ = [
               (Allow, Everyone, 'view'),
               (Allow, 'admins', 'edit')
              ]

    def __init__(self, **kw):
        install_catalog(self)
        super(OpenWorkouts, self).__init__(**kw)

    def _get_catalog_indexes(self):
        indexes = {
            'email': CatalogFieldIndex('email'),
            'sport': CatalogFieldIndex('sport'),
        }
        return indexes

    def reindex(self, obj):
        """
        Reindex the given object in the catalog
        """
        reindex_object(self.catalog, obj)

    def query(self, query):
        """
        Execute the given query on the catalog, returning the results
        (generator with events found or empty list if no results were found)
        """
        catalog = get_catalog(self)
        number, results = catalog.query(query)
        if number:
            return resources_from_query_results(catalog, results, self)
        return []

    def add_user(self, user):
        self.add(str(user.uid), user)
        self.reindex(user)

    def del_user(self, user):
        remove_from_catalog(self.catalog, user)
        self.remove(str(user.uid))

    def get_user_by_uid(self, uid):
        return self.get(str(uid), None)

    def get_user_by_email(self, email):
        if email is not None:
            # for some reason, when searching for None
            # the catalog will return all users
            res = self.query(Eq('email', email))
            if res:
                return next(res)
        return None

    @property
    def users(self):
        """
        Return all user objects
        """
        return [user for user in self.values() if isinstance(user, User)]

    @property
    def all_nicknames(self):
        """
        Return all available nicknames
        """
        return [user.nickname for user in self.users if user.nickname]

    @property
    def lowercase_nicknames(self):
        """
        Return all available nicknames in lower case. Useful for
        nickname uniqueness validation on signup
        """
        return [nick.lower() for nick in self.all_nicknames]

    @property
    def emails(self):
        """
        Return all emails currently in use by users
        """
        return [user.email for user in self.users]

    @property
    def lowercase_emails(self):
        """
        Returns all emails currently in use by users, transformed to
        lower case. This is useful to validate a new user email address
        against the currently used addresses
        """
        return [email.lower() for email in self.emails]

    @property
    def sports(self):
        return [s for s in self.catalog['sport']._fwd_index]

    @property
    def sports_json(self):
        return json.dumps(self.sports)
