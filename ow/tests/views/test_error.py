from unittest.mock import patch, Mock

import pytest
from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPFound

from ow.models.root import OpenWorkouts
from ow.views.error import not_found, forbidden, exceptions


class TestErrorViews(object):

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        return root

    @pytest.fixture
    def req(self, root):
        request = DummyRequest()
        request.root = root
        # Our error views will override the status_int for request.response,
        # but pyramid DummyRequest objects do not have that attribute
        request.response = Mock()
        return request

    def test_not_found(self, req):
        request = req
        response = not_found(request)
        assert response['url'] == request.resource_url(request.root)
        assert request.response.status_int == 404

    def test_forbidden_not_logged_in(self):
        # use a mocked request, as we cannot override authenticated_userid
        # easily on a dummyrequest
        request = Mock()
        request.authenticated_userid = None
        request.resource_url.return_value = '/login'
        response = forbidden(request)
        assert isinstance(response, HTTPFound)
        assert 'login' in response.location

    def test_forbidden_logged_in(self):
        request = Mock()
        request.authenticated_userid = 'john'
        request.resource_url.return_value = '/'
        response = forbidden(request)
        assert response['url'] == request.resource_url(request.root)
        assert request.response.status_int == 403

    @patch('ow.views.error.log')
    def test_exceptions(self, log, req):
        request = req
        response = exceptions(request.root, request)
        assert log.error.called
        assert response['url'] == request.resource_url(request.root)
        assert request.response.status_int == 500
