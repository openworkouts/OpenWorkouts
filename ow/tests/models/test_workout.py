import os
from io import BytesIO
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch, Mock

import pytest
from pyramid.security import Allow, Everyone, Deny, ALL_PERMISSIONS

from ow.models.workout import Workout
from ow.models.user import User
from ow.models.root import OpenWorkouts
from ow.utilities import create_blob

from ow.tests.helpers import join


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
        workout = Workout()
        with pytest.raises(AttributeError):
            workout.__acl__()
        # Now permissions on a workout that has been added to a user
        uid = str(root['john'].uid)
        workout = root['john']['1']
        permissions = [
            (Allow, uid, 'view'),
            (Allow, uid, 'edit'),
            (Allow, uid, 'delete'),
            (Deny, Everyone, ALL_PERMISSIONS)
        ]
        assert workout.__acl__() == permissions

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

    def test_owner(self, root):
        # workout with owner
        assert root['john']['1'].owner == root['john']
        # workout without owner
        w = Workout()
        assert w.owner is None

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

    def test_start_in_timezone(self):
        start_date = datetime.now(tz=timezone.utc)
        str_start_date = start_date.strftime('%d/%m/%Y %H:%M (%Z)')
        workout = Workout(start=start_date)
        assert workout.start_in_timezone('UTC') == str_start_date
        assert workout.start_in_timezone('Europe/Madrid') != str_start_date
        assert workout.start_in_timezone('America/Vancouver') != str_start_date

    def test_end_in_timezone(self):
        start_date = datetime.now(tz=timezone.utc)
        end_date = start_date + timedelta(minutes=60)
        str_end_date = end_date.strftime('%d/%m/%Y %H:%M (%Z)')
        workout = Workout(start=start_date, duration=timedelta(minutes=60))
        assert workout.end_in_timezone('UTC') == str_end_date
        assert workout.end_in_timezone('Europe/Madrid') != str_end_date
        assert workout.end_in_timezone('America/Vancouver') != str_end_date

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

    def test__duration(self):
        # covering the property that shows the duration of a workout properly
        # formatted in hours:minutes:seconds
        duration = timedelta(hours=1, minutes=30, seconds=15)
        workout = Workout(duration=duration)
        assert workout._duration == '01:30:15'

    def test_rounded_distance_no_value(self):
        workout = Workout()
        assert workout.rounded_distance == '-'

    def test_rounded_distance(self):
        workout = Workout()
        workout.distance = 44.44444444
        assert workout.rounded_distance == 44.44

    def test_hashed(self, root):
        # first test a workout that is attached to a user
        workout = root['john']['1']
        assert workout.hashed == (
            str(workout.owner.uid) +
            workout.start.strftime('%Y%m%d%H%M%S') +
            str(workout.duration.seconds) +
            str(workout.distance)
        )
        # now a workout that is not (no owner info)
        workout = Workout(
            start_time=datetime.now(timezone.utc),
            duration=timedelta(seconds=3600),
            distance=Decimal(30)
        )
        assert workout.hashed == (
            workout.start.strftime('%Y%m%d%H%M%S') +
            str(workout.duration.seconds) +
            str(workout.distance)
        )
        # now an empty workout...
        workout = Workout()
        with pytest.raises(AttributeError):
            assert workout.hashed == (
                workout.start.strftime('%Y%m%d%H%M%S') +
                str(workout.duration.seconds) +
                str(workout.distance)
            )

    def test_trimmed_notes(self):
        workout = Workout()
        assert workout.notes == ''
        assert workout.trimmed_notes == ''
        workout.notes = 'very short notes'
        assert workout.notes == 'very short notes'
        assert workout.trimmed_notes == 'very short notes'
        workout.notes = 'long notes now, repeated' * 1000
        assert len(workout.notes) == 24000
        assert len(workout.trimmed_notes) == 224
        assert workout.trimmed_notes.endswith(' ...')

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

    def test_tracking_file_path(self):
        workout = Workout()
        # no tracking file, path is None
        assert workout.tracking_file_path is None
        # workout still not saved to the db
        workout.tracking_file = Mock()
        workout.tracking_file._uncommitted.return_value = '/tmp/blobtempfile'
        workout.tracking_file.committed.return_value = None
        assert workout.tracking_file_path == '/tmp/blobtempfile'
        workout.tracking_file._uncommitted.return_value = None
        workout.tracking_file.committed.return_value = '/var/db/blobs/blobfile'
        assert workout.tracking_file_path == '/var/db/blobs/blobfile'

    def test_fit_file_path(self):
        workout = Workout()
        # no tracking file, path is None
        assert workout.fit_file_path is None
        # workout still not saved to the db
        workout.fit_file = Mock()
        workout.fit_file._uncommitted.return_value = '/tmp/blobtempfile'
        workout.fit_file.committed.return_value = None
        assert workout.fit_file_path == '/tmp/blobtempfile'
        workout.fit_file._uncommitted.return_value = None
        workout.fit_file.committed.return_value = '/var/db/blobs/blobfile'
        assert workout.fit_file_path == '/var/db/blobs/blobfile'

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

    def test_load_from_file_fit(self):
        workout = Workout()
        workout.tracking_filetype = 'fit'
        with patch.object(workout, 'load_from_fit') as lff:
            workout.load_from_file()
            assert lff.called

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

    fit_params = (
        # complete fit file from a garmin 520 device
        ('fixtures/20181230_101115.fit', {
            'start': datetime(2018, 12, 30, 9, 11, 15, tzinfo=timezone.utc),
            'duration': timedelta(0, 13872, 45000),
            'distance': Decimal('103.4981999999999970896169543'),
            'title': 'Synapse cycling',
            'hr': {'min': 93, 'max': 170, 'avg': 144},
            'cad': {'min': 0, 'max': 121, 'avg': 87},
            'atemp': {'min': -4, 'max': 15, 'avg': 2},
            'gpx_file': 'fixtures/20181230_101115.gpx'}),
        # fit file from a garmin 520 without heart rate or cadence data
        ('fixtures/20181231_110728.fit', {
            'start': datetime(2018, 12, 31, 10, 7, 28, tzinfo=timezone.utc),
            'duration': timedelta(0, 2373, 142000),
            'distance': Decimal('6.094909999999999854480847716'),
            'title': 'Synapse cycling',
            'hr': None,
            'cad': None,
            'atemp': {'min': -1, 'max': 11, 'avg': 1},
            'gpx_file': 'fixtures/20181231_110728.gpx'}),
    )

    @pytest.mark.parametrize(('filename', 'expected'), fit_params)
    def test_load_from_fit(self, filename, expected):
        """
        Load a fit file located in tests/fixtures using the load_from_fit()
        method of the Workout model, then check that certain attrs on the
        workout are updated correctly.

        Ensure also that the proper gpx file is created automatically from
        the fit file, with the proper contents (we have a matching gpx file
        in tests/fixtures for each fit file)
        """
        # expected values
        start = expected['start']
        duration = expected['duration']
        distance = expected['distance']
        title = expected['title']
        hr = expected['hr']
        cad = expected['cad']
        atemp = expected['atemp']
        # gpx_file = expected['gpx_file']

        workout = Workout()

        # Check the values are different by default
        assert workout.start != start
        assert workout.duration != duration
        assert workout.distance != distance

        # by default no tracking file and no fit file are associated with this
        # workout.
        assert workout.tracking_file is None
        assert workout.fit_file is None
        assert not workout.has_tracking_file
        assert not workout.has_gpx
        assert not workout.has_fit

        fit_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), filename)

        # gpx_file_path = os.path.join(
        #     os.path.dirname(os.path.dirname(__file__)), gpx_file)

        # add the fit file as a blob to tracking_file
        with open(fit_file_path, 'rb') as fit_file:
            fit_blob = create_blob(fit_file.read(), file_extension='fit',
                                   binary=True)
        workout.tracking_file = fit_blob
        workout.tracking_filetype = 'fit'

        res = workout.load_from_fit()

        assert res is True
        assert workout.start == start
        assert workout.duration == duration
        assert isinstance(workout.distance, Decimal)
        assert round(workout.distance) == round(distance)
        # The title of the workout is taken from the gpx file
        assert workout.title == title

        if hr is not None:
            for k in hr.keys():
                # We use 'fail' as the fallback in the getattr call
                # because None is one of the posible values, and we
                # want to be sure those attrs are there
                value = getattr(workout, 'hr_' + k, 'fail')
                # Use round() to avoid problems when comparing long
                # Decimal objects
                assert round(hr[k]) == round(value)

        if cad is not None:
            for k in cad.keys():
                value = getattr(workout, 'cad_' + k, 'fail')
                assert round(cad[k]) == round(value)

        if atemp is not None:
            for k in atemp.keys():
                value = getattr(workout, 'atemp_' + k, 'fail')
                assert round(atemp[k]) == round(value)

        assert workout.tracking_file is not None
        # the tracking file type is set back to gpx, as we have
        # automatically generated the gpx version
        assert workout.tracking_filetype == 'gpx'
        assert workout.fit_file is not None
        assert workout.has_tracking_file
        assert workout.has_gpx
        assert workout.has_fit

    def test_has_tracking_file(self, root):
        workout = root['john']['1']
        # without tracking file
        assert not workout.has_tracking_file
        # with tracking file
        workout.tracking_file = 'faked tracking file'
        assert workout.has_tracking_file

    def test_has_gpx(self, root):
        workout = root['john']['1']
        # without tracking file
        assert not workout.has_gpx
        workout.tracking_filetype = 'fit'
        assert not workout.has_gpx
        # with non-gpx tracking file
        workout.tracking_file = 'faked tracking file'
        workout.tracking_filetype = 'fit'
        assert not workout.has_gpx
        # with gpx tracking file
        workout.tracking_file = 'faked tracking file'
        workout.tracking_filetype = 'gpx'
        assert workout.has_gpx

    def test_has_fit(self, root):
        workout = root['john']['1']
        # without tracking file
        assert not workout.has_fit
        # tracking_file is a fit, this should not happen, as uploading a fit
        # puts the fit file into .fit_file and generates a gpx for
        # .tracking_file
        workout.tracking_file = 'faked tracking file'
        workout.tracking_filetype = 'fit'
        assert not workout.has_fit
        # now, having a fit file returns true
        workout.fit_file = 'faked fit file'
        assert workout.has_fit
        # no matter what we have in tracking_file
        workout.tracking_filetype = 'gpx'
        assert workout.has_fit
        workout.tracking_file = None
        workout.tracking_filetype = None
        assert workout.has_fit

    def test_map_screenshot_name(self, root):
        workout = root['john']['1']
        assert workout.map_screenshot_name == (
            str(root['john'].uid) + '/' + str(workout.workout_id) + '.png')

    def test_map_screenshot_path(self, root):
        workout = root['john']['1']
        assert workout.map_screenshot_path.endswith(
            'static/maps/' + workout.map_screenshot_name)

    @patch('ow.models.workout.os')
    def test_map_screenshot_no_gpx(self, os, root):
        workout = root['john']['1']
        assert workout.map_screenshot is None
        assert not os.path.join.called
        assert not os.path.exists.called

    @patch('ow.models.workout.os')
    def test_map_screenshot_no_shot(self, os, root):
        """
        A workout with a tracking file has no map screenshot
        """
        # This says "no screenshot found"
        os.path.exists.return_value = False

        workout = root['john']['1']
        workout.tracking_file = 'faked gpx file'
        workout.tracking_filetype = 'gpx'

        assert workout.map_screenshot is None
        assert os.path.join.called
        os.path.exists.assert_called_once_with(workout.map_screenshot_path)

    @patch('ow.models.workout.os')
    def test_map_screenshot_has_shot(self, os, root):
        """
        A workout with a tracking file has a map screenshot, the path to that
        is returned without doing anything else
        """
        # This says "yeah, we have a screenshot"
        os.path.exists.return_value = True
        os.path.abspath.return_value = '/'
        os.path.join.side_effect = join

        workout = root['john']['1']
        workout.tracking_file = 'faked gpx file'
        workout.tracking_filetype = 'gpx'
        uid = str(root['john'].uid)
        assert workout.map_screenshot == 'ow:/static/maps/' + uid + '/1.png'
        os.path.exists.assert_called_once_with(workout.map_screenshot_path)
        assert os.path.join.called
