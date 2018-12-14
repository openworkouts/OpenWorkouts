from datetime import datetime, timedelta, timezone

import pytest

from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPFound

from webob.multidict import MultiDict

from ow.models.workout import Workout
from ow.models.user import User
from ow.models.root import OpenWorkouts

from ow.views.root import user_list, add_user

from ow.schemas.user import UserAddSchema


class TestRootOpenWorkoutsViews(object):

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['john'] = User(firstname='John', lastname='Doe',
                            email='john.doe@example.net')
        root['john'].password = 's3cr3t'
        workout = Workout(
            start=datetime(2015, 6, 28, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=30, sport='cycling'
        )
        root['john'].add_workout(workout)
        return root

    @pytest.fixture
    def get_request(self, root):
        request = DummyRequest()
        request.root = root
        return request

    @pytest.fixture
    def post_request(self, root):
        request = DummyRequest()
        request.root = root
        request.method = 'POST'
        # Fill in this with the required field values, depending on the test
        request.POST = MultiDict({
            'submit': True,
            })
        return request

    def test_user_list(self, get_request):
        request = get_request
        response = user_list(request.root, request)
        assert list(response['users']) == [request.root['john']]

    def test_add_user_get(self, get_request):
        request = get_request
        response = add_user(request.root, request)
        assert 'form' in response
        assert len(response['form'].form.errors) == 0
        assert isinstance(response['form'].form.schema, UserAddSchema)

    def test_add_user_post_invalid(self, post_request):
        request = post_request
        response = add_user(request.root, request)
        assert 'form' in response
        # All required fields (4) are marked in the form errors
        # You can see which fields are required in the schema
        # ow.schemas.user.UserAddSchema
        assert len(response['form'].form.errors) == 4

    def test_add_user_post_valid(self, post_request):
        request = post_request
        request.POST['uid'] = 'addeduser'
        request.POST['email'] = 'addeduser@example.net'
        request.POST['firstname'] = 'added'
        request.POST['lastname'] = 'user'
        response = add_user(request.root, request)
        assert isinstance(response, HTTPFound)
        assert response.location.endswith('/userlist')
        assert len(request.root.all_usernames()) == 2
        assert 'addeduser' in request.root.all_usernames()
