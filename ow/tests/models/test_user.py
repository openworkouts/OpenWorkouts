from datetime import datetime, timedelta, timezone

import pytest
from pyramid.security import Allow

from ow.models.root import OpenWorkouts
from ow.models.workout import Workout
from ow.models.user import User


class TestUser(object):
    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['john'] = User(firstname='John', lastname='Doe',
                            email='john.doe@example.net')
        root['john'].password = 's3cr3t'
        return root

    @pytest.fixture
    def workouts(self):
        workouts = [Workout(sport='running'),
                    Workout(sport='cycling'),
                    Workout(sport='swimming')]
        return workouts

    def test_user_attrs(self, root):
        assert root['john'].firstname == 'John'
        assert root['john'].lastname == 'Doe'
        assert root['john'].email == 'john.doe@example.net'

    def test__acl__(self, root):
        uid = str(root['john'].uid)
        permissions = [(Allow, uid, 'edit'), (Allow, uid, 'view')]
        assert root['john'].__acl__() == permissions

    def test__str__(self, root):
        email = root['john'].email
        uid = str(root['john'].uid)
        assert root['john'].__str__() == u'User: ' + email + ' (' + uid + ')'

    def test_fullname(self, root):
        assert root['john'].fullname == 'John Doe'

    def test_password_is_encrypted(self, root):
        assert root['john'].password != 's3cr3t'

    def test_check_wrong_password(self, root):
        assert not root['john'].check_password('badpass')

    def test_check_good_password(self, root):
        assert root['john'].check_password('s3cr3t')

    def test_add_workout(self, root, workouts):
        # First add all workouts at once
        for workout in workouts:
            root['john'].add_workout(workout)
        # Then check they are there, in the correct position/number
        for workout in workouts:
            index = workouts.index(workout) + 1
            assert root['john'][str(index)] == workout

    def test_workouts(self, root, workouts):
        # First add all workouts at once
        for workout in workouts:
            root['john'].add_workout(workout)
        # workouts() will return the workouts sorted from newest to oldest
        workouts.reverse()
        assert list(root['john'].workouts()) == workouts
        assert list(root['john'].workout_ids()) == ['1', '2', '3']
        assert root['john'].num_workouts == len(workouts)

    def test_activity_dates_tree(self, root):
        # first an empty test
        assert root['john'].activity_dates_tree == {}
        # now add a cycling workout in a given date (25/11/2018)
        workout = Workout(
            start=datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=(60*4)),
            distance=115,
            sport='cycling')
        root['john'].add_workout(workout)
        assert root['john'].activity_dates_tree == {
            2018: {11: {'cycling': 1}}
        }
        # add a running workout on the same date
        workout = Workout(
            start=datetime(2018, 11, 25, 16, 30, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=12,
            sport='running')
        root['john'].add_workout(workout)
        assert root['john'].activity_dates_tree == {
            2018: {11: {'cycling': 1, 'running': 1}}
        }
        # add a swimming workout on a different date, same year
        workout = Workout(
            start=datetime(2018, 8, 15, 11, 30, tzinfo=timezone.utc),
            duration=timedelta(minutes=30),
            distance=2,
            sport='swimming')
        root['john'].add_workout(workout)
        assert root['john'].activity_dates_tree == {
            2018: {8: {'swimming': 1},
                   11: {'cycling': 1, 'running': 1}}
        }
        # now add some more cycling in a different year
        # add a swimming workout on a different date, same year
        workout = Workout(
            start=datetime(2017, 4, 15, 15, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=(60*3)),
            distance=78,
            sport='cycling')
        root['john'].add_workout(workout)
        assert root['john'].activity_dates_tree == {
            2017: {4: {'cycling': 1}},
            2018: {8: {'swimming': 1},
                   11: {'cycling': 1, 'running': 1}}
        }
