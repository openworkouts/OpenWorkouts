from decimal import Decimal
from datetime import datetime, timedelta, timezone

import pytest
from pyramid.security import Allow, Everyone, Deny, ALL_PERMISSIONS

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
        permissions = [
            (Allow, uid, 'view'),
            (Allow, uid, 'edit'),
            (Deny, Everyone, ALL_PERMISSIONS),
        ]
        assert root['john'].__acl__() == permissions

    def test__str__(self, root):
        email = root['john'].email
        uid = str(root['john'].uid)
        assert root['john'].__str__() == u'User: ' + uid + ' (' + email + ')'

    def test__repr__(self, root):
        email = root['john'].email
        uid = str(root['john'].uid)
        expected = u'<ow.models.user.User: ' + uid + ' (' + email + ')>'
        assert root['john'].__repr__() == expected

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

    def test_favorite_sport(self, root):
        assert root['john'].favorite_sport is None
        # add a cycling workout
        workout = Workout(
            sport='cycling',
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=120),
            distance=66,
        )
        root['john'].add_workout(workout)
        assert root['john'].favorite_sport == 'cycling'
        # add a running workout, both sports have same amount of workouts,
        # favorite is picked up reversed alphabetically
        workout = Workout(
            sport='running',
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=45),
            distance=5,
        )
        root['john'].add_workout(workout)
        assert root['john'].favorite_sport == 'running'
        # add another cycling workout, now that is the favorite sport
        workout = Workout(
            sport='cycling',
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=60),
            distance=30,
        )
        root['john'].add_workout(workout)
        assert root['john'].favorite_sport == 'cycling'

    def test_activity_sports(self, root):
        assert root['john'].activity_sports == []
        workout = Workout(
            sport='cycling',
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=120),
            distance=66,
        )
        root['john'].add_workout(workout)
        assert root['john'].activity_sports == ['cycling']
        workout = Workout(
            sport='running',
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=45),
            distance=5,
        )
        root['john'].add_workout(workout)
        assert root['john'].activity_sports == ['cycling', 'running']

    def test_activity_years(self, root):
        assert root['john'].activity_years == []
        workout = Workout(
            sport='cycling',
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=120),
            distance=66,
        )
        root['john'].add_workout(workout)
        assert root['john'].activity_years == [datetime.now(timezone.utc).year]
        workout = Workout(
            sport='running',
            start=datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=45),
            distance=5,
        )
        root['john'].add_workout(workout)
        assert root['john'].activity_years == [
            datetime.now(timezone.utc).year,
            2018
        ]

    def test_activity_months(self, root):
        # we have to pass a year parameter
        with pytest.raises(TypeError):
            root['john'].activity_months()
        now = datetime.now(timezone.utc)
        assert root['john'].activity_months(now.year) == []
        workout = Workout(
            sport='cycling',
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=120),
            distance=66,
        )
        root['john'].add_workout(workout)
        assert root['john'].activity_months(now.year) == [now.month]
        assert root['john'].activity_months(now.year-1) == []
        assert root['john'].activity_months(now.year+1) == []
        workout = Workout(
            sport='running',
            start=datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=45),
            distance=5,
        )
        root['john'].add_workout(workout)
        assert root['john'].activity_months(now.year) == [now.month]
        assert root['john'].activity_months(2018) == [11]
        assert root['john'].activity_months(now.year+1) == []

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

    def test_stats(self, root):
        expected_no_stats = {
            'workouts': 0,
            'time': timedelta(seconds=0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
            'sports': {}
        }
        # no stats
        assert root['john'].stats() == expected_no_stats
        # add a cycling workout
        workout = Workout(
            start=datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=(60*4)),
            distance=115,
            sport='cycling')
        root['john'].add_workout(workout)
        # asking for a different year, future
        assert root['john'].stats(2019) == expected_no_stats
        # asking for a different year, past
        assert root['john'].stats(2016) == expected_no_stats
        # asking fot the year the workout is in
        assert root['john'].stats(2018) == {
            'workouts': 1,
            'time': timedelta(minutes=(60*4)),
            'distance': Decimal(115),
            'elevation': Decimal(0),
            'sports': {
                'cycling': {
                    'workouts': 1,
                    'time': timedelta(minutes=(60*4)),
                    'distance': Decimal(115),
                    'elevation': Decimal(0),
                }
            }
        }
        # add a second cycling workout
        workout = Workout(
            start=datetime(2018, 11, 26, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=(60*3)),
            distance=100,
            sport='cycling')
        root['john'].add_workout(workout)
        assert root['john'].stats(2018) == {
            'workouts': 2,
            'time': timedelta(minutes=(60*7)),
            'distance': Decimal(215),
            'elevation': Decimal(0),
            'sports': {
                'cycling': {
                    'workouts': 2,
                    'time': timedelta(minutes=(60*7)),
                    'distance': Decimal(215),
                    'elevation': Decimal(0),
                }
            }
        }
        # add a running workout
        workout = Workout(
            start=datetime(2018, 11, 26, 16, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=(60)),
            distance=10,
            sport='running')
        root['john'].add_workout(workout)
        assert root['john'].stats(2018) == {
            'workouts': 3,
            'time': timedelta(minutes=(60*8)),
            'distance': Decimal(225),
            'elevation': Decimal(0),
            'sports': {
                'cycling': {
                    'workouts': 2,
                    'time': timedelta(minutes=(60*7)),
                    'distance': Decimal(215),
                    'elevation': Decimal(0),
                },
                'running': {
                    'workouts': 1,
                    'time': timedelta(minutes=(60)),
                    'distance': Decimal(10),
                    'elevation': Decimal(0),
                }
            }
        }
        # ensure the stats for future/past years did not change after
        # adding those workouts
        assert root['john'].stats(2019) == expected_no_stats
        assert root['john'].stats(2016) == expected_no_stats

    def test_get_week_stats(self, root):
        expected_no_stats_per_day = {
            'workouts': 0,
            'time': timedelta(0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
            'sports': {}
        }

        expected_no_stats = {}
        for i in range(19, 26):
            day = datetime(2018, 11, i, 10, 00, tzinfo=timezone.utc)
            expected_no_stats[day] = expected_no_stats_per_day

        day = datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc)
        assert root['john'].get_week_stats(day) == expected_no_stats

        # add a cycling workout
        workout = Workout(
            start=datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=(60*4)),
            distance=115,
            sport='cycling')
        root['john'].add_workout(workout)

        # check a week in the future
        day = datetime(2019, 11, 25, 10, 00, tzinfo=timezone.utc)
        week_stats = root['john'].get_week_stats(day)
        for day in week_stats:
            assert week_stats[day] == expected_no_stats_per_day

        # check a week in the past
        day = datetime(2017, 11, 25, 10, 00, tzinfo=timezone.utc)
        week_stats = root['john'].get_week_stats(day)
        for day in week_stats:
            assert week_stats[day] == expected_no_stats_per_day

        # Check the week where the workout is
        day = datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc)
        week_stats = root['john'].get_week_stats(day)
        for day in week_stats:
            if day.day == 25:
                # this is the day where we have a workout
                assert week_stats[day] == {
                    'workouts': 1,
                    'time': timedelta(minutes=(60*4)),
                    'distance': Decimal(115),
                    'elevation': Decimal(0),
                    'sports': {
                        'cycling': {
                            'workouts': 1,
                            'time': timedelta(minutes=(60*4)),
                            'distance': Decimal(115),
                            'elevation': Decimal(0)
                        }
                    }
                }
            else:
                # day without workout
                assert week_stats[day] == expected_no_stats_per_day

        # add a second cycling workout
        workout = Workout(
            start=datetime(2018, 11, 23, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=(60*3)),
            distance=100,
            sport='cycling')
        root['john'].add_workout(workout)
        day = datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc)
        week_stats = root['john'].get_week_stats(day)
        for day in week_stats:
            if day.day == 25:
                # this is the day where we have a workout
                assert week_stats[day] == {
                    'workouts': 1,
                    'time': timedelta(minutes=(60*4)),
                    'distance': Decimal(115),
                    'elevation': Decimal(0),
                    'sports': {
                        'cycling': {
                            'workouts': 1,
                            'time': timedelta(minutes=(60*4)),
                            'distance': Decimal(115),
                            'elevation': Decimal(0)
                        }
                    }
                }
            elif day.day == 23:
                # this is the day where we have a workout
                assert week_stats[day] == {
                    'workouts': 1,
                    'time': timedelta(minutes=(60*3)),
                    'distance': Decimal(100),
                    'elevation': Decimal(0),
                    'sports': {
                        'cycling': {
                            'workouts': 1,
                            'time': timedelta(minutes=(60*3)),
                            'distance': Decimal(100),
                            'elevation': Decimal(0)
                        }
                    }
                }
            else:
                # day without workout
                assert week_stats[day] == expected_no_stats_per_day

    def test_week_stats(self, root):
        expected_no_stats_per_day = {
            'workouts': 0,
            'time': timedelta(0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
            'sports': {}
        }

        # no workouts for the current week (this tests is for coverage
        # purposes mostly, as the main logic is tested in test_get_week_stats)
        day = datetime.now(timezone.utc)
        week_stats = root['john'].get_week_stats(day)
        for day in week_stats:
            assert week_stats[day] == expected_no_stats_per_day

    def test_week_totals(self, root):
        # no data, empty totals
        assert root['john'].week_totals == {
            'distance': Decimal(0),
            'time': timedelta(0)
        }

    def test_yearly_stats(self, root):
        expected_no_stats_per_month = {
            'workouts': 0,
            'time': timedelta(0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
            'sports': {}
        }

        yearly_stats = root['john'].yearly_stats
        for month, stats in yearly_stats.items():
            assert stats == expected_no_stats_per_month

        # add a cycling workout
        start_date = datetime.now(timezone.utc)
        workout = Workout(
            start=start_date,
            duration=timedelta(minutes=(60*4)),
            uphill=1200,
            distance=115,
            sport='cycling')
        root['john'].add_workout(workout)

        yearly_stats = root['john'].yearly_stats
        for month, stats in yearly_stats.items():
            if month == (start_date.year, start_date.month):
                assert stats == {
                    'workouts': 1,
                    'time': timedelta(minutes=(60*4)),
                    'distance': Decimal(115),
                    'elevation': Decimal(1200),
                    'sports': {
                        'cycling': {'distance': Decimal(115),
                                    'elevation': Decimal(1200),
                                    'time': timedelta(minutes=(60*4)),
                                    'workouts': 1}
                    }
                }
            else:
                assert stats == expected_no_stats_per_month

        # add a second cycling workout
        workout = Workout(
            start=start_date,
            duration=timedelta(minutes=(30)),
            uphill=500,
            distance=20,
            sport='cycling')
        root['john'].add_workout(workout)

        yearly_stats = root['john'].yearly_stats
        for month, stats in yearly_stats.items():
            if month == (start_date.year, start_date.month):
                assert stats == {
                    'workouts': 2,
                    'time': timedelta(minutes=((60*4)+30)),
                    'distance': Decimal(115+20),
                    'elevation': Decimal(1200+500),
                    'sports': {
                        'cycling': {'distance': Decimal(115+20),
                                    'elevation': Decimal(1200+500),
                                    'time': timedelta(minutes=((60*4)+30)),
                                    'workouts': 2}
                    }
                }
            else:
                assert stats == expected_no_stats_per_month

        # add a running workout
        workout = Workout(
            start=start_date,
            duration=timedelta(minutes=(60)),
            uphill=200,
            distance=5,
            sport='running')
        root['john'].add_workout(workout)

        yearly_stats = root['john'].yearly_stats
        for month, stats in yearly_stats.items():
            if month == (start_date.year, start_date.month):
                assert stats == {
                    'workouts': 3,
                    'time': timedelta(minutes=((60*4)+30+60)),
                    'distance': Decimal(115+20+5),
                    'elevation': Decimal(1200+500+200),
                    'sports': {
                        'cycling': {'distance': Decimal(115+20),
                                    'elevation': Decimal(1200+500),
                                    'time': timedelta(minutes=((60*4)+30)),
                                    'workouts': 2},
                        'running': {'distance': Decimal(5),
                                    'elevation': Decimal(200),
                                    'time': timedelta(minutes=(60)),
                                    'workouts': 1}
                    }
                }
            else:
                assert stats == expected_no_stats_per_month

    def test_weekly_year_stats(self, root):
        expected_no_stats_per_week = {
            'workouts': 0,
            'time': timedelta(0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
            'sports': {}
        }

        weekly_year_stats = root['john'].weekly_year_stats
        for week, stats in weekly_year_stats.items():
            assert stats == expected_no_stats_per_week

        # add a cycling workout
        start_date = datetime.now(timezone.utc)
        workout = Workout(
            start=start_date,
            duration=timedelta(minutes=(60*4)),
            uphill=1200,
            distance=115,
            sport='cycling')
        root['john'].add_workout(workout)

        weekly_year_stats = root['john'].weekly_year_stats
        workout_week = (start_date.year, start_date.month,
                        start_date.isocalendar()[1])
        for week, stats in weekly_year_stats.items():
            if week[:3] == workout_week:
                assert stats == {
                    'workouts': 1,
                    'time': timedelta(minutes=(60*4)),
                    'distance': Decimal(115),
                    'elevation': Decimal(1200),
                    'sports': {
                        'cycling': {'distance': Decimal(115),
                                    'elevation': Decimal(1200),
                                    'time': timedelta(minutes=(60*4)),
                                    'workouts': 1}
                    }
                }
            else:
                assert stats == expected_no_stats_per_week

        # add a second cycling workout
        workout = Workout(
            start=start_date,
            duration=timedelta(minutes=(30)),
            uphill=500,
            distance=20,
            sport='cycling')
        root['john'].add_workout(workout)

        weekly_year_stats = root['john'].weekly_year_stats
        workout_week = (start_date.year, start_date.month,
                        start_date.isocalendar()[1])
        for week, stats in weekly_year_stats.items():
            if week[:3] == workout_week:
                assert stats == {
                    'workouts': 2,
                    'time': timedelta(minutes=((60*4)+30)),
                    'distance': Decimal(115+20),
                    'elevation': Decimal(1200+500),
                    'sports': {
                        'cycling': {'distance': Decimal(115+20),
                                    'elevation': Decimal(1200+500),
                                    'time': timedelta(minutes=((60*4)+30)),
                                    'workouts': 2}
                    }
                }
            else:
                assert stats == expected_no_stats_per_week

        # add a running workout
        workout = Workout(
            start=start_date,
            duration=timedelta(minutes=(60)),
            uphill=200,
            distance=5,
            sport='running')
        root['john'].add_workout(workout)

        weekly_year_stats = root['john'].weekly_year_stats
        workout_week = (start_date.year, start_date.month,
                        start_date.isocalendar()[1])
        for week, stats in weekly_year_stats.items():
            if week[:3] == workout_week:
                assert stats == {
                    'workouts': 3,
                    'time': timedelta(minutes=((60*4)+30+60)),
                    'distance': Decimal(115+20+5),
                    'elevation': Decimal(1200+500+200),
                    'sports': {
                        'cycling': {'distance': Decimal(115+20),
                                    'elevation': Decimal(1200+500),
                                    'time': timedelta(minutes=((60*4)+30)),
                                    'workouts': 2},
                        'running': {'distance': Decimal(5),
                                    'elevation': Decimal(200),
                                    'time': timedelta(minutes=(60)),
                                    'workouts': 1}
                    }
                }
            else:
                assert stats == expected_no_stats_per_week

    def test_sport_totals(self, root):
        # user has no workouts, so no totals
        assert root['john'].sport_totals() == {
            'workouts': 0,
            'time': timedelta(0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
        }
        # add a cycling workout happening now
        workout = Workout(
            sport='cycling',
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=120),
            distance=66,
        )
        root['john'].add_workout(workout)
        # only one workout, one sport, so the default will show totals
        # for that sport
        assert root['john'].sport_totals() == {
            'workouts': 1,
            'time': timedelta(minutes=120),
            'distance': Decimal(66),
            'elevation': Decimal(0),
        }
        # Add a running workout
        workout = Workout(
            sport='running',
            start=datetime(2018, 11, 25, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=45),
            distance=5,
        )
        root['john'].add_workout(workout)
        # the favorite sport is running now
        assert root['john'].sport_totals() == {
            'workouts': 1,
            'time': timedelta(minutes=45),
            'distance': Decimal(5),
            'elevation': Decimal(0),
        }
        # but we can get the totals for cycling too
        assert root['john'].sport_totals('cycling') == {
            'workouts': 1,
            'time': timedelta(minutes=120),
            'distance': Decimal(66),
            'elevation': Decimal(0),
        }
        # adding a new cycling workout, in a different year
        workout = Workout(
            sport='cycling',
            start=datetime(2017, 11, 25, 10, 00, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=32,
        )
        root['john'].add_workout(workout)
        # now cycling is the favorite sport
        assert root['john'].sport_totals() == {
            'workouts': 2,
            'time': timedelta(minutes=180),
            'distance': Decimal(98),
            'elevation': Decimal(0),
        }
        # but we can get running stats too
        assert root['john'].sport_totals('running') == {
            'workouts': 1,
            'time': timedelta(minutes=45),
            'distance': Decimal(5),
            'elevation': Decimal(0),
        }
        # there are no running activities for 2016
        assert root['john'].sport_totals('running', 2016) == {
            'workouts': 0,
            'time': timedelta(0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
        }
        # and not activities for cycling in 2016 neither
        assert root['john'].sport_totals('cycling', 2016) == {
            'workouts': 0,
            'time': timedelta(0),
            'distance': Decimal(0),
            'elevation': Decimal(0),
        }
        # and we can get the separate totals for cycling in different years
        year = datetime.now(timezone.utc).year
        assert root['john'].sport_totals('cycling', year) == {
            'workouts': 1,
            'time': timedelta(minutes=120),
            'distance': Decimal(66),
            'elevation': Decimal(0),
        }
        assert root['john'].sport_totals('cycling', 2017) == {
            'workouts': 1,
            'time': timedelta(minutes=60),
            'distance': Decimal(32),
            'elevation': Decimal(0),
        }
