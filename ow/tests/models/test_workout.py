import os
from io import BytesIO
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from pyramid.security import Allow, Everyone

from ow.models.workout import Workout
from ow.models.user import User
from ow.models.root import OpenWorkouts


class TestWorkoutModels(object):

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['john'] = User(firstname='John', lastname='Doe',
                            email='john.doe@example.net')
        root['john'].password = 's3cr3t'
        root['john']['1'] = Workout(
            start=datetime(2015, 6, 28, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=30
        )
        return root

    def test__acl__(self, root):
        # First check permissions for a workout without parent
        permissions = [(Allow, Everyone, 'view'),
                       (Allow, 'group:admins', 'edit')]
        workout = Workout()
        assert workout.__acl__() == permissions

        # Now permissions on a workout that has been added to a user
        uid = str(root['john'].uid)
        permissions = [(Allow, uid, 'view'), (Allow, uid, 'edit')]
        assert root['john']['1'].__acl__() == permissions

    def test_runthrough(self, root):
        """
        Just a simple run through to see if those objects click
        """
        root['joe'] = User(firstname='Joe', lastname='Di Maggio')
        assert(u'Joe Di Maggio' == root['joe'].fullname)
        joe = root['joe']
        start = datetime(2015, 6, 5, 19, 1, tzinfo=timezone.utc)
        duration = timedelta(minutes=20)
        distance = Decimal('0.25')  # 250m
        w = Workout(start=start, duration=duration, sport='swimming',
                    notes=u'Yay, I swam!', distance=distance)
        joe['1'] = w
        expected = datetime(2015, 6, 5, 19, 21, tzinfo=timezone.utc)
        assert expected == joe['1'].end
        assert 250 == joe['1'].distance * 1000

    def test_workout_id(self, root):
        assert root['john']['1'].workout_id == '1'

    def test_end(self, root):
        # workout without duration, it has no end
        workout = Workout()
        assert workout.end is None
        # workout with duration, end is start_time + duration
        expected = datetime(2015, 6, 28, 13, 55, tzinfo=timezone.utc)
        assert root['john']['1'].end == expected

    def test_start_date(self):
        start_date = datetime.now()
        workout = Workout(start=start_date)
        assert workout.start_date == start_date.strftime('%d/%m/%Y')

    def test_start_time(self):
        start_date = datetime.now()
        workout = Workout(start=start_date)
        assert workout.start_time == start_date.strftime('%H:%M')

    def test_split_duration(self):
        # return the same hours, minutes, seconds we provided when creating
        # the workout instance
        duration = timedelta(hours=1, minutes=30, seconds=15)
        workout = Workout(duration=duration)
        assert workout.split_duration() == (1, 30, 15)
        # If the duration is longer than a day, return the calculation of
        # in hours, minutes, seconds too
        duration = timedelta(days=1, hours=1, minutes=30, seconds=15)
        workout = Workout(duration=duration)
        assert workout.split_duration() == (25, 30, 15)

    def test_duration_hours_minutes_seconds(self):
        duration = timedelta(hours=1, minutes=30, seconds=15)
        workout = Workout(duration=duration)
        assert workout.duration_hours == '01'
        assert workout.duration_minutes == '30'
        assert workout.duration_seconds == '15'

    def test_rounded_distance_no_value(self):
        workout = Workout()
        assert workout.rounded_distance == '-'

    def test_rounded_distance(self):
        workout = Workout()
        workout.distance = 44.44444444
        assert workout.rounded_distance == 44.4

    def test_has_hr(self):
        workout = Workout()
        assert not workout.has_hr
        workout.hr_min = 90
        assert not workout.has_hr
        workout.hr_max = 180
        assert not workout.has_hr
        workout.hr_avg = 120
        assert workout.has_hr

    def test_hr(self):
        workout = Workout()
        assert workout.hr is None
        workout.hr_min = 90
        assert workout.hr is None
        workout.hr_max = 180
        assert workout.hr is None
        workout.hr_avg = 120
        assert workout.hr['min'] == 90
        assert workout.hr['max'] == 180
        assert workout.hr['avg'] == 120

    def test_has_cad(self):
        workout = Workout()
        assert not workout.has_cad
        workout.cad_min = 0
        assert not workout.has_cad
        workout.cad_max = 110
        assert not workout.has_cad
        workout.cad_avg = 50
        assert workout.has_cad

    def test_cad(self):
        workout = Workout()
        assert workout.cad is None
        workout.cad_min = 0
        assert workout.cad is None
        workout.cad_max = 110
        assert workout.cad is None
        workout.cad_avg = 50
        assert workout.cad['min'] == 0
        assert workout.cad['max'] == 110
        assert workout.cad['avg'] == 50

    def test_has_atemp(self):
        workout = Workout()
        assert not workout.has_atemp
        workout.atemp_min = 0
        assert not workout.has_atemp
        workout.atemp_max = 12
        assert not workout.has_atemp
        workout.atemp_avg = 5
        assert workout.has_atemp

    def test_atemp(self):
        workout = Workout()
        assert workout.atemp is None
        workout.atemp_min = 0
        assert workout.atemp is None
        workout.atemp_max = 12
        assert workout.atemp is None
        workout.atemp_avg = 5
        assert workout.atemp['min'] == 0
        assert workout.atemp['max'] == 12
        assert workout.atemp['avg'] == 5

    def test_load_from_file_invalid(self):
        workout = Workout()
        workout.tracking_filetype = 'alf'
        with patch.object(workout, 'load_from_gpx') as lfg:
            workout.load_from_file()
            assert not lfg.called

    def test_load_from_file_gpx(self):
        workout = Workout()
        workout.tracking_filetype = 'gpx'
        with patch.object(workout, 'load_from_gpx') as lfg:
            workout.load_from_file()
            assert lfg.called

    gpx_params = (
        # GPX 1.0 file, no extensions
        ('fixtures/20131013.gpx', {
            'start': datetime(2013, 10, 13, 5, 28, 26, tzinfo=timezone.utc),
            'duration': timedelta(seconds=27652),
            'distance': Decimal(98.12598431852807),
            'title': 'A ride I will never forget',
            'blob': 'path',
            'hr': {'min': None, 'max': None, 'avg': None},
            'cad': {'min': None, 'max': None, 'avg': None},
            'atemp': {'min': None, 'max': None, 'avg': None}}),
        # GPX 1.0 file, no extensions, missing elevation
        ('fixtures/20131013-without-elevation.gpx', {
            'start': datetime(2013, 10, 13, 5, 28, 26, tzinfo=timezone.utc),
            'duration': timedelta(seconds=27652),
            'distance': Decimal(98.12598431852807),
            'title': 'A ride I will never forget',
            'blob': None,
            'hr': {'min': None, 'max': None, 'avg': None},
            'cad': {'min': None, 'max': None, 'avg': None},
            'atemp': {'min': None, 'max': None, 'avg': None}}),
        # GPX 1.1 file with extensions
        ('fixtures/20160129-with-extensions.gpx', {
            'start': datetime(2016, 1, 29, 8, 12, 9, tzinfo=timezone.utc),
            'duration': timedelta(seconds=7028),
            'distance': Decimal(48.37448557752049237024039030),
            'title': 'Cota counterclockwise + end bonus',
            'blob': 'path',
            'hr': {'min': Decimal(100), 'max': Decimal(175),
                   'avg': Decimal(148.365864144454008055618032813072)},
            'cad': {'min': Decimal(0), 'max': Decimal(110),
                    'avg': Decimal(67.41745485812553740326741187)},
            'atemp': {'min': Decimal(-4), 'max': Decimal(14),
                      'avg': Decimal(-0.3869303525365434221840068788)}}),
        )

    @pytest.mark.parametrize(('filename', 'expected'), gpx_params)
    def test_load_from_gpx(self, filename, expected):
        """
        Load a gpx file located in tests/fixtures using the load_from_gpx()
        method of the Workout model, then check that certain attrs on the
        workout are updated correctly
        """
        # expected values
        start = expected['start']
        duration = expected['duration']
        distance = expected['distance']
        title = expected['title']
        blob = expected['blob']
        hr = expected['hr']
        cad = expected['cad']
        atemp = expected['atemp']

        workout = Workout()

        # Check the values are different by default
        assert workout.start != start
        assert workout.duration != duration
        assert workout.distance != distance

        gpx_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), filename)
        with patch.object(workout, 'tracking_file') as tf:
            with open(gpx_file_path, 'r') as gpx_file:
                tf.open.return_value = BytesIO(gpx_file.read().encode('utf-8'))
                # Set the path to the blob object containing the gpx file.
                # more info in models.workout.Workout.parse_gpx()
                tf._p_blob_uncommitted = gpx_file_path
                if blob is None:
                    # set the uncommited blob to None, mimicing what happens
                    # with a workout saved into the db (transaction.commit())
                    tf._p_blob_uncommitted = None
                    tf._p_blob_committed = gpx_file_path
                # Without this, has_gpx() will return False
                workout.tracking_filetype = 'gpx'
                res = workout.load_from_gpx()
                assert res is True
                assert workout.start == start
                assert workout.duration == duration
                assert isinstance(workout.distance, Decimal)
                assert round(workout.distance) == round(distance)
                # The title of the workout is taken from the gpx file
                assert workout.title == title
                for k in hr.keys():
                    # We use 'fail' as the fallback in the getattr call because
                    # None is one of the posible values, and we want to be sure
                    # those attrs are there
                    #
                    # The keys are the same for the hr, cad and atemp dicts, so
                    # we can do all tests in one loop
                    #
                    # If the expected value is not None, use round() to avoid
                    # problems when comparing long Decimal objects
                    value = getattr(workout, 'hr_'+k, 'fail')
                    if hr[k] is None:
                        assert hr[k] == value
                    else:
                        assert round(hr[k]) == round(value)

                    value = getattr(workout, 'cad_'+k, 'fail')
                    if cad[k] is None:
                        assert cad[k] == value
                    else:
                        assert round(cad[k]) == round(value)

                    value = getattr(workout, 'atemp_'+k, 'fail')
                    if atemp[k] is None:
                        assert atemp[k] == value
                    else:
                        assert round(atemp[k]) == round(value)

    def test_load_from_gpx_no_tracks(self):
        """
        If we load an empty (but valid) gpx file (i.e., no tracks information)
        the attrs on the workout are not updated, the call to load_from_gpx()
        returns False
        """
        workout = Workout()

        # We do not check the start time, it would need some mocking on the
        # datetime module and there is no need really
        assert workout.duration is None
        assert workout.distance is None

        gpx_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/empty.gpx')
        with patch.object(workout, 'tracking_file') as tf:
            with open(gpx_file_path, 'r') as gpx_file:
                tf.open.return_value = BytesIO(gpx_file.read().encode('utf-8'))
                res = workout.load_from_gpx()
                assert res is False
                assert workout.duration is None
                assert workout.distance is None
                assert workout.title == ''
                for k in ['max', 'min', 'avg']:
                    for a in ['hr_', 'cad_', 'atemp_']:
                        assert getattr(workout, a+k, 'fail') is None

    def test_parse_gpx_no_gpx_file(self):
        """
        Test the behaviour of parse_gpx() when we call it on a workout without
        a gpx tracking file. The behaviour of such method when the workout has
        a gpx tracking file is covered by the test_load_from_gpx() test above
        """
        workout = Workout()
        res = workout.parse_gpx()
        assert res == {}

    def test_has_tracking_file(self, root):
        workout = root['john']['1']
        # without tracking file
        assert workout.has_tracking_file is False
        # with tracking file
        workout.tracking_file = 'faked tracking file'
        assert workout.has_tracking_file is True

    def test_has_gpx(self, root):
        workout = root['john']['1']
        # without tracking file
        assert workout.has_gpx is False
        workout.tracking_filetype = 'fit'
        assert workout.has_gpx is False
        # with non-gpx tracking file
        workout.tracking_file = 'faked tracking file'
        workout.tracking_filetype = 'fit'
        assert workout.has_gpx is False
        # with gpx tracking file
        workout.tracking_file = 'faked tracking file'
        workout.tracking_filetype = 'gpx'
        assert workout.has_gpx is True
