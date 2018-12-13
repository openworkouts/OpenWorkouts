import json
from datetime import datetime, timedelta, timezone

import pytest

from ow.models.workout import Workout
from ow.models.user import User
from ow.models.root import OpenWorkouts


class TestRootOpenWorkouts(object):

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

    def test_all_usernames(self, root):
        # the method returns an OOBtree object
        assert [u for u in root.all_usernames()] == ['john']

    def test_lowercase_usernames(self, root):
        root.add_user(user_id='Jack', firstname='Jack', lastname='Dumb',
                      email='jack.dumb@example.net')
        assert root.lowercase_usernames() == ['jack', 'john']

    def test_emails(self, root):
        assert root.emails() == ['john.doe@example.net']

    def test_lowercase_emails(self, root):
        root.add_user(user_id='Jack', firstname='Jack', lastname='Dumb',
                      email='Jack.Dumb@example.net')
        assert root.lowercase_emails() == ['jack.dumb@example.net',
                                           'john.doe@example.net']

    def test_users(self, root):
        # the method returns an OOBtree object
        assert [u for u in root.users()] == [root['john']]

    def test_get_user(self, root):
        assert root.get_user('john') == root['john']
        assert root.get_user('jack') is None
        with pytest.raises(TypeError):
            root.get_user()

    def test_add_user(self, root):
        assert len(root.users()) == 1
        root.add_user(user_id='jack', firstname='Jack', lastname='Dumb',
                      email='jack.dumb@example.net')
        assert len(root.users()) == 2
        assert 'jack' in root.all_usernames()

    def test_sports(self, root):
        assert root.sports == ['cycling']
        workout = Workout(
            start=datetime(2015, 6, 29, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=10, sport='running')
        root['john'].add_workout(workout)
        assert root.sports == ['cycling', 'running']

    def test_sports_json(self, root):
        assert root.sports_json == json.dumps(["cycling"])
        workout = Workout(
            start=datetime(2015, 6, 29, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=10, sport='running')
        root['john'].add_workout(workout)
        assert root.sports_json == json.dumps(["cycling", "running"])
