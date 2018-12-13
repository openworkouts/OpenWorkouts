import pytest
from formencode.validators import Invalid
from pyramid_simpleform import State

from ow.models.user import User
from ow.schemas.user import PasswordMatch, UniqueUsername, UniqueEmail


class TestPasswordMatch(object):

    @pytest.fixture
    def state(self):
        user = User(email='test@example.net')
        user.password = 's3cr3t'
        state = State(user=user)
        return state

    def test_validate_python_match(self, state):
        validator = PasswordMatch()
        res = validator._validate_python('s3cr3t', state)
        assert res is None

    def test_validate_python_not_match(self, state):
        validator = PasswordMatch()
        with pytest.raises(Invalid):
            validator._validate_python('wr0ng#p4ss', state)


class TestUniqueUsername(object):

    @pytest.fixture
    def state(self):
        state = State(names=['test', 'existing'])
        return state

    def test_validate_python_exists(self, state):
        validator = UniqueUsername()
        with pytest.raises(Invalid):
            validator._validate_python('test', state)
        with pytest.raises(Invalid):
            validator._validate_python('ExiSTing', state)

    def test_validate_python_not_exists(self, state):
        validator = UniqueUsername()
        res = validator._validate_python('not-existing', state)
        assert res is None


class TestUniqueEmail(object):

    @pytest.fixture
    def state(self):
        state = State(emails=['test@example.net', 'existing@example.net'])
        return state

    def test_validate_python_exists(self, state):
        validator = UniqueEmail()
        with pytest.raises(Invalid):
            validator._validate_python('test@example.net', state)
        with pytest.raises(Invalid):
            validator._validate_python('ExiSTing@example.net', state)

    def test_validate_python_not_exists(self, state):
        validator = UniqueEmail()
        res = validator._validate_python('not-existing@example.net', state)
        assert res is None
