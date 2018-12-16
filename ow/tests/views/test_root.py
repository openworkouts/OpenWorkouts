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
    def john(self):
        user = User(firstname='John', lastname='Doe',
                    email='john.doe@example.net')
        user.password = 's3cr3t'
        return user

    @pytest.fixture
    def root(self, john):
        root = OpenWorkouts()
        root.add_user(john)
        workout = Workout(
            start=datetime(2015, 6, 28, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=30, sport='cycling'
        )
        john.add_workout(workout)
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

    def test_user_list(self, get_request, john):
        request = get_request
        response = user_list(request.root, request)
        assert list(response['users']) == [john]

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
        # All required fields (3) are marked in the form errors
        # You can see which fields are required in the schema
        # ow.schemas.user.UserAddSchema
        errors = response['form'].form.errors
        assert len(errors) == 3
        assert 'email' in errors
        assert 'firstname' in errors
        assert 'lastname' in errors

    def test_add_user_post_valid(self, post_request):
        request = post_request
        request.POST['nickname'] = 'addeduser'
        request.POST['email'] = 'addeduser@example.net'
        request.POST['firstname'] = 'added'
        request.POST['lastname'] = 'user'
        response = add_user(request.root, request)
        assert isinstance(response, HTTPFound)
        assert response.location.endswith('/userlist')
        # 1 nick name, as the default user has no nickname
        assert len(request.root.all_nicknames) == 1
        assert 'addeduser' in request.root.all_nicknames
