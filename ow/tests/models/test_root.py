import json
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone

import pytest
from repoze.catalog.catalog import Catalog

from ow.models.workout import Workout
from ow.models.user import User
from ow.models.root import OpenWorkouts


class TestRootOpenWorkouts(object):

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

    def test__init__(self, root):
        # a new OpenWorkouts instance has a catalog created automatically
        assert isinstance(root.catalog, Catalog)
        assert len(root.catalog) == 3
        for key in ['email', 'nickname', 'sport']:
            assert key in root.catalog

    def test_add_user_ok(self, root):
        assert len(root.users) == 1
        user = User(firstname='New', lastname='For Testing',
                    email='new.for.testing@example.net')
        root.add_user(user)
        assert len(root.users) == 2
        assert user in root.users

    def test_add_user_invalid(self, root):
        assert len(root.users) == 1
        with pytest.raises(AttributeError):
            root.add_user('faked-user-object')

    def test_del_user_ok(self, root, john):
        assert len(root.users) == 1
        root.del_user(john)
        assert len(root.users) == 0

    def test_del_user_failure(self, root):
        assert len(root.users) == 1
        with pytest.raises(AttributeError):
            root.add_user('faked-user-object')

    def test_get_user_by_uid(self, root, john):
        # first, get an user that does exist
        user = root.get_user_by_uid(str(john.uid))
        assert user == john
        # now, without converting first to str, works too
        user = root.get_user_by_uid(john.uid)
        assert user == john
        # now, something that is not there
        new_user = User(firstname='someone', lastname='else',
                        email='someone.else@example.net')
        user = root.get_user_by_uid(new_user.uid)
        assert user is None
        # now, something that is not an uid
        user = root.get_user_by_uid('faked-user-uid')
        assert user is None

    def test_get_user_by_email(self, root, john):
        # first, get an user that does exist
        user = root.get_user_by_email(str(john.email))
        assert user == john
        # now, something that is not there
        new_user = User(firstname='someone', lastname='else',
                        email='someone.else@example.net')
        user = root.get_user_by_email(new_user.email)
        assert user is None
        # now, something that is not an email
        user = root.get_user_by_email('faked-user-email')
        assert user is None
        # passing in None
        user = root.get_user_by_email(None)
        assert user is None
        # passing in something that is not None or a string will break
        # the query code
        with pytest.raises(TypeError):
            user = root.get_user_by_email(False)
        with pytest.raises(TypeError):
            user = root.get_user_by_email(Mock())

    def test_users(self, root, john):
        assert root.users == [john]

    def test_all_nicknames(self, root, john):
        # the existing user has not a nickname, and empty nicknames are not
        # added to the list of nicknames
        assert root.all_nicknames == []
        # now set one
        john.nickname = 'MrJohn'
        assert root.all_nicknames == ['MrJohn']

    def test_lowercase_nicknames(self, root, john):
        # the existing user has not a nickname
        assert root.lowercase_nicknames == []
        # now set one
        john.nickname = 'MrJohn'
        assert root.lowercase_nicknames == ['mrjohn']

    def test_emails(self, root):
        assert root.emails == ['john.doe@example.net']

    def test_lowercase_emails(self, root):
        user = User(firstname='Jack', lastname='Dumb',
                    email='Jack.Dumb@example.net')
        root.add_user(user)
        assert root.lowercase_emails == ['john.doe@example.net',
                                         'jack.dumb@example.net']

    def test_sports(self, root, john):
        assert root.sports == ['cycling']
        workout = Workout(
            start=datetime(2015, 6, 29, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=10, sport='running')
        john.add_workout(workout)
        assert root.sports == ['cycling', 'running']

    def test_sports_json(self, root, john):
        assert root.sports_json == json.dumps(["cycling"])
        workout = Workout(
            start=datetime(2015, 6, 29, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=10, sport='running')
        john.add_workout(workout)
        assert root.sports_json == json.dumps(["cycling", "running"])
