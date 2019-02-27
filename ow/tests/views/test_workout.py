import os
import json
from io import BytesIO
from datetime import datetime, timedelta, timezone
from cgi import FieldStorage
from unittest.mock import Mock, patch, PropertyMock

import pytest

from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import Response

from webob.multidict import MultiDict

from ow.models.root import OpenWorkouts
from ow.models.user import User
from ow.models.workout import Workout
from ow.schemas.workout import (
    ManualWorkoutSchema,
    UploadedWorkoutSchema,
    UpdateWorkoutSchema,
    )
import ow.views.workout as workout_views


class TestWorkoutViews(object):

    # paths to gpx files we can use for testing, used in some of the tests
    # as py.test fixtures
    gpx_filenames = (
        # GPX 1.0 file, no extensions
        'fixtures/20131013.gpx',
        # GPX 1.0 file, no extensions, missing elevation
        'fixtures/20131013-without-elevation.gpx',
        # GPX 1.1 file with extensions
        'fixtures/20160129-with-extensions.gpx',
        )

    def open_uploaded_file(self, path):
        """
        Open the uploaded tracking file fixture from disk
        """
        uploaded_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), path)
        uploaded_file = open(uploaded_file_path, 'r')
        return uploaded_file

    def close_uploaded_file(self, uploaded_file):
        """
        Close the opened uploaded tracking file
        """
        uploaded_file.close()

    def create_filestorage(self, uploaded_file):
        """
        Create a FileStorage instance from an open uploaded tracking file,
        suitable for testing file uploads later
        """
        storage = FieldStorage()
        storage.filename = os.path.basename(uploaded_file.name)
        storage.file = BytesIO(uploaded_file.read().encode('utf-8'))
        storage.name = os.path.basename(uploaded_file.name)
        # This prevents FormEncode validator from thinking we are providing
        # more than one file for the upload, which crashes the tests
        storage.list = None
        return storage

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['john'] = User(firstname='John', lastname='Doe',
                            email='john.doe@example.net')
        root['john'].password = 's3cr3t'
        workout = Workout(
            start=datetime(2015, 6, 28, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=30
        )
        root['john'].add_workout(workout)
        return root

    @pytest.fixture
    def dummy_request(self, root):
        request = DummyRequest()
        request.root = root
        return request

    @pytest.fixture
    def valid_post_request(self, root):
        request = DummyRequest()
        request.root = root
        request.method = 'POST'
        request.POST = MultiDict({
            'start_date': '21/12/2015',
            'start_time': '8:30',
            'duration_hours': '3',
            'duration_minutes': '30',
            'duration_seconds': '20',
            'distance': '10',
            'submit': True,
            })
        return request

    def test_add_workout_manually_get(self, dummy_request):
        """
        Test the view that renders the "add workout manually" form
        """
        request = dummy_request
        user = request.root['john']
        response = workout_views.add_workout_manually(user, request)
        assert 'form' in response
        assert len(response['form'].form.errors) == 0
        assert isinstance(response['form'].form.schema, ManualWorkoutSchema)

    def test_add_workout_manually_post_invalid(self, dummy_request):
        """
        POST request to add a workout manually, without providing the required
        form data.
        """
        request = dummy_request
        user = request.root['john']
        request.method = 'POST'
        request.POST = MultiDict({'submit': True})
        response = workout_views.add_workout_manually(user, request)
        assert 'form' in response
        # All required fields (6) are marked in the form errors
        assert len(response['form'].form.errors) == 6

    add_workout_params = [
        # no title, no sport, we generate a title based on when the
        # workout started
        ({'title': None, 'sport': None}, 'Morning workout'),
        # no title, sport given, we use the sport too in the automatically
        # generated title
        ({'title': None, 'sport': 'cycling'}, 'Morning cycling workout'),
        # title given, no sport, we use the provided title
        ({'title': 'Example workout', 'sport': None}, 'Example workout'),
        # title given, sport too, we use the provided title
        ({'title': 'Example workout', 'sport': 'cycling'}, 'Example workout'),
    ]

    @pytest.mark.parametrize(('params', 'expected'), add_workout_params)
    def test_add_workout_manually_post_valid(self, params, expected,
                                             valid_post_request):
        """
        POST request to add a workout manually, providing the needed data
        """
        request = valid_post_request
        if params['title'] is not None:
            request.POST['title'] = params['title']
        if params['sport'] is not None:
            request.POST['sport'] = params['sport']
        user = request.root['john']
        assert len(user.workouts()) == 1
        response = workout_views.add_workout_manually(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location.endswith('/2/')
        assert len(user.workouts()) == 2
        assert user['2'].title == expected

    def test_add_workout_get(self, dummy_request):
        """
        Test the view that renders the "add workout by upload tracking file"
        form
        """
        request = dummy_request
        user = request.root['john']
        response = workout_views.add_workout(user, request)
        assert 'form' in response
        assert len(response['form'].form.errors) == 0
        assert isinstance(response['form'].form.schema, UploadedWorkoutSchema)

    def test_add_workout_post_invalid(self, dummy_request):
        """
        POST request to add a workout by uploading a tracking file, without
        providing the required form data.
        """
        request = dummy_request
        user = request.root['john']
        request.method = 'POST'
        request.POST = MultiDict({'submit': True})
        response = workout_views.add_workout(user, request)
        assert 'form' in response
        # Only one required field in this case, the tracking file
        assert len(response['form'].form.errors) == 1

    def test_add_workout_post_invalid_bytes(self, dummy_request):
        """
        POST request to add a workout, without uploading a tracking file,
        which sends an empty bytes object (b'')
        """
        request = dummy_request
        user = request.root['john']
        request.method = 'POST'
        request.POST = MultiDict({
            'tracking_file': b'',
            'submit': True,
            })
        assert len(request.root['john'].workouts()) == 1
        response = workout_views.add_workout(user, request)
        assert 'form' in response
        # Only one required field in this case, the tracking file
        assert len(response['form'].form.errors) == 1

    @pytest.mark.parametrize('filename', gpx_filenames)
    def test_add_workout_post_valid(self, filename, dummy_request):
        """
        POST request to add a workout, uploading a tracking file
        """
        request = dummy_request
        uploaded_file = self.open_uploaded_file(filename)
        filestorage = self.create_filestorage(uploaded_file)
        user = request.root['john']
        request.method = 'POST'
        request.POST = MultiDict({
            'tracking_file': filestorage,
            'submit': True,
            })
        assert len(request.root['john'].workouts()) == 1
        response = workout_views.add_workout(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location.endswith('/2/')
        assert len(request.root['john'].workouts()) == 2
        self.close_uploaded_file(uploaded_file)

    def test_edit_workout_get(self, dummy_request):
        """
        Test the view that renders the "edit workout" form
        """
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        response = workout_views.edit_workout(workout, request)
        assert 'form' in response
        assert len(response['form'].form.errors) == 0
        assert isinstance(response['form'].form.schema, ManualWorkoutSchema)

    def test_edit_workout_post_invalid(self, dummy_request):
        """
        POST request to edit a workout, without providing the required form
        data (like removing data from required fields).
        """
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        request.method = 'POST'
        request.POST = MultiDict({'submit': True})
        response = workout_views.edit_workout(workout, request)
        assert 'form' in response
        # All required fields (6) are marked in the form errors
        assert len(response['form'].form.errors) == 6

    def test_edit_workout_post_valid(self, valid_post_request):
        """
        POST request to edit a workout, providing the needed data
        """
        request = valid_post_request
        user = request.root['john']
        workout = user.workouts()[0]
        assert len(user.workouts()) == 1
        assert workout.start == datetime(
            2015, 6, 28, 12, 55, tzinfo=timezone.utc)
        response = workout_views.edit_workout(workout, request)
        assert isinstance(response, HTTPFound)
        assert response.location.endswith('/1/')
        assert len(user.workouts()) == 1
        assert user.workouts()[0].start == datetime(
            2015, 12, 21, 8, 30, tzinfo=timezone.utc)

    def test_update_workout_from_file_get(self, dummy_request):
        """
        Test the view that renders the "update workout from file" form
        """
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        response = workout_views.update_workout_from_file(workout, request)
        assert 'form' in response
        assert len(response['form'].form.errors) == 0
        assert isinstance(response['form'].form.schema, UpdateWorkoutSchema)

    def test_update_workout_from_file_post_invalid(self, dummy_request):
        """
        POST request to update a workout by uploading a tracking file, without
        providing the required form data.
        """
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        request.method = 'POST'
        request.POST = MultiDict({'submit': True})
        response = workout_views.update_workout_from_file(workout, request)
        assert 'form' in response
        # Only one required field in this case, the tracking file
        assert len(response['form'].form.errors) == 1

    def test_update_workout_from_file_post_invalid_bytes(self, dummy_request):
        """
        POST request to update a workout, without uploading a tracking file,
        which sends an empty bytes object (b'')
        """
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        request.method = 'POST'
        request.POST = MultiDict({
            'tracking_file': b'',
            'submit': True,
            })
        response = workout_views.update_workout_from_file(workout, request)
        assert 'form' in response
        # Only one required field in this case, the tracking file
        assert len(response['form'].form.errors) == 1

    @pytest.mark.parametrize('filen', gpx_filenames)
    def test_update_workout_from_file_post_valid(self, filen, dummy_request):
        """
        POST request to update a workout, uploading a tracking file
        """
        filename = filen
        request = dummy_request
        uploaded_file = self.open_uploaded_file(filename)
        filestorage = self.create_filestorage(uploaded_file)
        user = request.root['john']
        workout = user.workouts()[0]
        request.method = 'POST'
        request.POST = MultiDict({
            'tracking_file': filestorage,
            'submit': True,
            })
        assert len(user.workouts()) == 1
        response = workout_views.update_workout_from_file(workout, request)
        assert isinstance(response, HTTPFound)
        assert response.location.endswith('/1/')
        assert len(request.root['john'].workouts()) == 1
        self.close_uploaded_file(uploaded_file)

    def test_delete_workout_get(self, dummy_request):
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        response = workout_views.delete_workout(workout, request)
        assert response == {}

    def test_delete_workout_post_invalid(self, dummy_request):
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        request.method = 'POST'
        # invalid, missing confirmation delete hidden value
        request.POST = MultiDict({'submit': True})
        response = workout_views.delete_workout(workout, request)
        # we do reload the page asking for confirmation
        assert response == {}

    def test_delete_workout_post_valid(self, root):
        """
        Valid POST request to delete a workout.
        Instead of reusing the DummyRequest from the request fixture, we do
        Mock fully the request here, because we need to use
        authenticated_userid, which cannot be easily set in the DummyRequest
        """
        request = Mock()
        request.root = root
        request.method = 'POST'
        request.resource_url.return_value = '/dashboard/'
        # invalid, missing confirmation delete hidden value
        request.POST = MultiDict({'submit': True, 'delete': 'yes'})
        user = request.root['john']
        workout = user.workouts()[0]
        # A real request will have the current logged in user id, which we need
        # for deleting the workout
        request.authenticated_userid = 'john'
        response = workout_views.delete_workout(workout, request)
        # after a successful delete, we send the user back to his dashboard
        assert isinstance(response, HTTPFound)
        assert response.location.endswith('/')
        assert len(user.workouts()) == 0

    def test_workout_without_gpx(self, dummy_request):
        """
        Test the view that renders the workout details page for a workout
        without tracking data
        """
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        response = workout_views.workout(workout, request)
        assert response['start_point'] == {}

    def test_workout_with_gpx(self, dummy_request):
        """
        Test the view that renders the workout details page for a workout
        with a gpx tracking file. We use a gpx from the test fixtures
        """
        request = dummy_request
        # expected values (from the gpx fixture file)
        expected = {'latitude': 37.108735040304566,
                    'longitude': 25.472489344630546,
                    'elevation': None}

        user = request.root['john']
        workout = user.workouts()[0]
        # to ensure has_gpx returns true
        workout.tracking_filetype = 'gpx'

        gpx_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/20131013.gpx')
        with patch.object(workout, 'tracking_file') as tf:
            with open(gpx_file_path, 'r') as gpx_file:
                tf.open.return_value = BytesIO(gpx_file.read().encode('utf-8'))
                response = workout_views.workout(workout, request)
                assert response['start_point'] == expected

    def test_workout_gpx_no_gpx(self, dummy_request):
        """
        The view that renders the gpx contents attached to a workout return a
        404 if the workout has no gpx
        """
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        response = workout_views.workout_gpx(workout, request)
        assert isinstance(response, HTTPNotFound)

    def test_workout_gpx(self, dummy_request):
        """
        The view that renders the gpx contents attached to a workout returns a
        response containing the gpx contents, as with the proper content_type
        and all
        """
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        # to ensure has_gpx returns true
        workout.tracking_filetype = 'gpx'

        # part of the expected body, so we can assert later
        expected_body = b'<gpx version="1.1" creator="OpenWorkouts"'

        gpx_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/20131013.gpx')
        with patch.object(workout, 'tracking_file') as tf:
            with open(gpx_file_path, 'r') as gpx_file:
                tf.open.return_value = BytesIO(gpx_file.read().encode('utf-8'))
                response = workout_views.workout_gpx(workout, request)
                assert response.status_code == 200
                assert response.content_type == 'application/xml'
                assert expected_body in response.body

    def test_workout_map_no_gpx(self, dummy_request):
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        response = workout_views.workout_map(workout, request)
        assert response == {'start_point': {}}

    def test_workout_map(self, dummy_request):
        request = dummy_request
        user = request.root['john']
        workout = user.workouts()[0]
        # to ensure has_gpx returns true
        workout.tracking_filetype = 'gpx'
        gpx_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/20131013.gpx')
        with patch.object(workout, 'tracking_file') as tf:
            with open(gpx_file_path, 'r') as gpx_file:
                tf.open.return_value = BytesIO(gpx_file.read().encode('utf-8'))
                response = workout_views.workout_map(workout, request)
                assert response == {
                    'start_point': {
                        'elevation': None,
                        'latitude': 37.108735040304566,
                        'longitude': 25.472489344630546
                    }
                }

    @patch('ow.views.workout.save_map_screenshot')
    def test_workout_map_shot_generate_map(self, save_map, dummy_request):
        """
        Call the view that returns the url to the screenshot of a workout
        tracking map, without a map being generated previously, the map is
        generated using save_map_screenshot
        """
        def static_url(url):
            return url
        request = dummy_request
        # mock static url to make testing this a bit easier
        request.static_url = static_url
        user = request.root['john']
        workout = user.workouts()[0]
        # we mock map_screenshot so the first access is None, triggering the
        # save_map_screenshot call. The second access returns a string we can
        # use with static_url for testing purposes
        type(workout).map_screenshot = PropertyMock(
            side_effect=[None, 'ow:static/maps/somemap.png'])
        response = workout_views.workout_map_shot(workout, request)
        save_map.assert_called_once_with(workout, request)
        assert isinstance(response, Response)
        assert response.content_type == 'application/json'
        # the body is a valid json-encoded stream
        obj = json.loads(response.body)
        assert 'ow:static/maps/somemap.png' in obj['url']

    @patch('ow.views.workout.save_map_screenshot')
    def test_workout_map_shot_existing(self, save_map, dummy_request):
        """
        Call the view that returns the url to the screenshot of a workout
        tracking map, with an existing map already there
        """
        def static_url(url):
            return url
        request = dummy_request
        # mock static url to make testing this a bit easier
        request.static_url = static_url
        user = request.root['john']
        workout = user.workouts()[0]
        type(workout).map_screenshot = PropertyMock(
            side_effect=['ow:static/maps/somemap.png',
                         'ow:static/maps/somemap.png'])
        response = workout_views.workout_map_shot(workout, request)
        assert not save_map.called
        assert isinstance(response, Response)
        assert response.content_type == 'application/json'
        # the body is a valid json-encoded stream
        obj = json.loads(response.body)
        assert 'ow:static/maps/somemap.png' in obj['url']
