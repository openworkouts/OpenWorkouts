from decimal import Decimal
from datetime import datetime, timedelta, timezone
from uuid import uuid1
from operator import attrgetter

import bcrypt
from repoze.folder import Folder
from pyramid.security import Allow

from ow.catalog import get_catalog, reindex_object
from ow.utilities import get_week_days


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

    def stats(self, year=None, month=None):
        year = year or datetime.now().year
        stats = {
            'workouts': 0,
            'time': timedelta(seconds=0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
            'sports': {}
        }

        for workout in self.workouts(year=year, month=month):
            stats['workouts'] += 1
            stats['time'] += workout.duration or timedelta(seconds=0)
            stats['distance'] += workout.distance or Decimal(0)
            stats['elevation'] += workout.uphill or Decimal(0)

            if workout.sport not in stats['sports']:
                stats['sports'][workout.sport] = {
                    'workouts': 0,
                    'time': timedelta(seconds=0),
                    'distance': Decimal(0),
                    'elevation': Decimal(0),
                }

            stats['sports'][workout.sport]['workouts'] += 1
            stats['sports'][workout.sport]['time'] += (
                workout.duration or timedelta(0))
            stats['sports'][workout.sport]['distance'] += (
                workout.distance or Decimal(0))
            stats['sports'][workout.sport]['elevation'] += (
                workout.uphill or Decimal(0))

        return stats

    def get_week_stats(self, day):
        """
        Return some stats for the week the given day is in.
        """
        week = get_week_days(day)

        # filter workouts
        workouts = []
        for workout in self.workouts():
            if week[0].date() <= workout.start.date() <= week[-1].date():
                workouts.append(workout)

        # build stats
        stats = {}
        for week_day in week:
            stats[week_day] = {
                'workouts': 0,
                'time': timedelta(0),
                'distance': Decimal(0),
                'elevation': Decimal(0),
                'sports': {}
            }
            for workout in workouts:
                if workout.start.date() == week_day.date():
                    day = stats[week_day]  # less typing, avoid long lines
                    day['workouts'] += 1
                    day['time'] += workout.duration or timedelta(seconds=0)
                    day['distance'] += workout.distance or Decimal(0)
                    day['elevation'] += workout.uphill or Decimal(0)
                    if workout.sport not in day['sports']:
                        day['sports'][workout.sport] = {
                            'workouts': 0,
                            'time': timedelta(seconds=0),
                            'distance': Decimal(0),
                            'elevation': Decimal(0),
                        }
                    day['sports'][workout.sport]['workouts'] += 1
                    day['sports'][workout.sport]['time'] += (
                        workout.duration or timedelta(0))
                    day['sports'][workout.sport]['distance'] += (
                        workout.distance or Decimal(0))
                    day['sports'][workout.sport]['elevation'] += (
                        workout.uphill or Decimal(0))

        return stats

    @property
    def week_stats(self):
        """
        Helper that returns the week stats for the current week
        """
        return self.get_week_stats(datetime.now(timezone.utc))

    @property
    def week_totals(self):
        week_stats = self.week_stats
        return {
            'distance': sum([week_stats[t]['distance'] for t in week_stats]),
            'time': sum([week_stats[t]['time'] for t in week_stats],
                        timedelta())
        }

    @property
    def yearly_stats(self):
        """
        Return per-month stats for the last 12 months
        """
        # set the boundaries for looking for workouts afterwards,
        # we need the current date as the "end date" and one year
        # ago from that date. Then we set the start at the first
        # day of that month.
        end = datetime.now(timezone.utc)
        start = (end - timedelta(days=365)).replace(day=1)

        # build the stats, populating first the dict with empty values
        # for each month.
        stats = {}
        for days in range((end - start).days):
            day = (start + timedelta(days=days)).date()
            if (day.year, day.month) not in stats.keys():
                stats[(day.year, day.month)] = {
                    'workouts': 0,
                    'time': timedelta(0),
                    'distance': Decimal(0),
                    'elevation': Decimal(0),
                    'sports': {}
                }

        # now loop over workouts, filtering and then adding stats to the
        # proper place
        for workout in self.workouts():
            if start.date() <= workout.start.date() <= end.date():
                # less typing, avoid long lines
                month = stats[
                    (workout.start.date().year, workout.start.date().month)]
                month['workouts'] += 1
                month['time'] += workout.duration or timedelta(seconds=0)
                month['distance'] += workout.distance or Decimal(0)
                month['elevation'] += workout.uphill or Decimal(0)
                if workout.sport not in month['sports']:
                    month['sports'][workout.sport] = {
                        'workouts': 0,
                        'time': timedelta(seconds=0),
                        'distance': Decimal(0),
                        'elevation': Decimal(0),
                    }
                month['sports'][workout.sport]['workouts'] += 1
                month['sports'][workout.sport]['time'] += (
                    workout.duration or timedelta(0))
                month['sports'][workout.sport]['distance'] += (
                    workout.distance or Decimal(0))
                month['sports'][workout.sport]['elevation'] += (
                    workout.uphill or Decimal(0))

        return stats
