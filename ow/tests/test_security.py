import pytest

from pyramid.testing import DummyRequest

from ow.security import groupfinder
from ow.models.root import OpenWorkouts
from ow.models.user import User


class TestSecurity(object):

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['john'] = User(firstname='John', lastname='Doe',
                            email='john.doe@example.net')
        root['john'].password = 's3cr3t'
        return root

    def test_groupfinder(self, root):
        request = DummyRequest()
        request.root = root
        # User does exist
        assert groupfinder('john', request) == [str(root['john'].uid)]
        # User does not exist
        assert groupfinder('jack', request) == []
