import json

from repoze.folder import Folder
from repoze.catalog.indexes.field import CatalogFieldIndex

from pyramid.security import Allow, Everyone

from ow.models.user import User
from ow.catalog import get_catalog


class OpenWorkouts(Folder):
    """
    Root object, contains basically all the users, and in turn
    the users contain their workouts.
    """

    __parent__ = __name__ = None

    __acl__ = [
               (Allow, Everyone, 'view'),
               (Allow, 'group:admins', 'edit')
              ]

    def _get_catalog_indexes(self):
        indexes = {
            'sport': CatalogFieldIndex('sport'),
        }
        return indexes

    def all_usernames(self):
        """
        Return all available usernames
        """
        return self.keys()

    def lowercase_usernames(self):
        """
        Return all available usernames in lower case. Useful for
        username uniqueness validation on signup
        """
        return [name.lower() for name in self.keys()]

    def emails(self):
        """
        Return all emails currently in use by users
        """
        return [u.email for u in self.users()]

    def lowercase_emails(self):
        """
        Returns all emails currently in use by users, transformed to
        lower case. This is useful to validate a new user email address
        against the currently used addresses
        """
        return [u.email.lower() for u in self.users()]

    def users(self):
        """
        Return all user objects
        """
        return [u for u in self.values() if isinstance(u, User)]

    def get_user(self, uid):
        return self.get(uid, None)

    def add_user(self, uid, **kw):
        u = User(**kw)
        self[uid] = u

    @property
    def sports(self):
        catalog = get_catalog(self)
        return [s for s in catalog['sport']._fwd_index]

    @property
    def sports_json(self):
        return json.dumps(self.sports)
