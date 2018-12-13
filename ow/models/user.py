
from uuid import uuid1
from operator import attrgetter

import bcrypt
from repoze.folder import Folder
from pyramid.security import Allow

from ow.catalog import get_catalog, reindex_object


class User(Folder):

    __parent__ = __name__ = None

    def __acl__(self):
        permissions = [
            (Allow, str(self.uid), 'edit'),
            (Allow, str(self.uid), 'view'),
        ]
        return permissions

    def __init__(self, **kw):
        self.uid = kw.get('uid', uuid1())
        self.firstname = kw.get('firstname', '')
        self.lastname = kw.get('lastname', '')
        self.email = kw.get('email', '')
        self.bio = kw.get('bio', '')
        self.birth_date = kw.get('birth_date', None)
        self.height = kw.get('height', None)
        self.weight = kw.get('weight', None)
        self.gender = kw.get('gender', 'female')
        self.picture = kw.get('picture', None)  # blob
        self.__password = None
        self.last_workout_id = 0
        super(User, self).__init__()

    def __str__(self):
        return u'User: %s (%s)' % (self.email, self.uid)

    @property
    def password(self):
        return self.__password

    @password.setter
    def password(self, password=None):
        """
        Sets a password for the user, hashing with bcrypt.
        """
        password = password.encode('utf-8')
        self.__password = bcrypt.hashpw(password, bcrypt.gensalt())

    def check_password(self, password):
        """
        Check a plain text password against a hashed one
        """
        hashed = bcrypt.hashpw(password.encode('utf-8'), self.__password)
        return hashed == self.__password

    @property
    def fullname(self):
        """
        Naive implementation of fullname: firstname + lastname
        """
        return u'%s %s' % (self.firstname, self.lastname)

    def add_workout(self, workout):
        # This returns the main catalog at the root folder
        catalog = get_catalog(self)
        self.last_workout_id += 1
        workout_id = str(self.last_workout_id)
        self[workout_id] = workout
        reindex_object(catalog, workout)

    def workouts(self):
        """
        Return this user workouts, sorted by date, from newer to older
        """
        workouts = sorted(self.values(), key=attrgetter('start'))
        workouts.reverse()
        return workouts

    def workout_ids(self):
        return self.keys()

    @property
    def num_workouts(self):
        return len(self.workout_ids())
