
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
        self.nickname = kw.get('nickname', '')
        self.firstname = kw.get('firstname', '')
        self.lastname = kw.get('lastname', '')
        self.email = kw.get('email', '')
        self.bio = kw.get('bio', '')
        self.birth_date = kw.get('birth_date', None)
        self.height = kw.get('height', None)
        self.weight = kw.get('weight', None)
        self.gender = kw.get('gender', 'female')
        self.picture = kw.get('picture', None)  # blob
        self.timezone = kw.get('timezone', 'UTC')
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

    def workouts(self, year=None, month=None):
        """
        Return this user workouts, sorted by date, from newer to older
        """
        workouts = self.values()
        if year:
            workouts = [w for w in workouts if w.start.year == year]
        if month:
            workouts = [w for w in workouts if w.start.month == month]
        workouts = sorted(workouts, key=attrgetter('start'))
        workouts.reverse()
        return workouts

    def workout_ids(self):
        return self.keys()

    @property
    def num_workouts(self):
        return len(self.workout_ids())

    @property
    def activity_years(self):
        return sorted(list(set(w.start.year for w in self.workouts())),
                      reverse=True)

    def activity_months(self, year):
        months = set(
            w.start.month for w in self.workouts() if w.start.year == year)
        return sorted(list(months))

    @property
    def activity_dates_tree(self):
        """
        Return a dict containing information about the activity for this
        user.

        Example:

        {
            2019: {
                1: {'cycling': 12, 'running': 1}
            },
            2018: {
                1: {'cycling': 10, 'running': 3},
                2: {'cycling': 14, 'swimming': 5}
            }
        }
        """
        tree = {}
        for workout in self.workouts():
            year = workout.start.year
            month = workout.start.month
            sport = workout.sport
            if year not in tree:
                tree[year] = {}
            if month not in tree[year]:
                tree[year][month] = {}
            if sport not in tree[year][month]:
                tree[year][month][sport] = 0
            tree[year][month][sport] += 1
        return tree
