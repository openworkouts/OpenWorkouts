from unittest.mock import patch

from ow.models import appmaker
from ow.models.root import OpenWorkouts


class TestAppMaker(object):

    @patch('ow.models.transaction')
    def test_appmaker(self, t):
        """
        Calling appmaker on a new zodb (without an OpenWorkouts root folder in
        it), a new root object is added, the transaction is committed to the
        zodb and the new root object is returned
        """
        zodb_root = {}
        app = appmaker(zodb_root)
        assert isinstance(app, OpenWorkouts)
        assert t.commit.called

    @patch('ow.models.transaction')
    def test_appmaker_already_existing_root(self, t):
        """
        Calling appmaker with a zodb that has an OpenWorkouts root, nothing
        changes in that zodb
        """
        zodb_root = {'app_root': 'faked-root-object'}
        app = appmaker(zodb_root)
        assert app == 'faked-root-object'
        assert not t.commit.called
