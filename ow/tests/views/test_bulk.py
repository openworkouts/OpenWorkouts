import os
from io import BytesIO
from cgi import FieldStorage

import pytest

from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPFound

from webob.multidict import MultiDict

from ow.models.root import OpenWorkouts
from ow.models.user import User
from ow.models.bulk import BulkFile, BulkFiles
from ow.schemas.bulk import BulkFileSchema
from ow.utilities import create_blob

import ow.views.bulk as bulk_views


class TestBulkViews(object):

    # paths to sample compressed files we can use for testing.
    bulk_filenames = (
        # valid FIT files, in different compressed formats
        'fixtures/bulk-fit.zip',
        'fixtures/bulk-fit.tgz',
        # valid GPX files, also in different formats
        'fixtures/bulk-gpx.zip',
        'fixtures/bulk-gpx.tgz',
        # empty ZIP file
        'fixtures/bulk-empty.zip',
        # ZIP file containing invalid files in different formats
        'fixtures/bulk-invalid.zip'
    )

    def open_uploaded_file(self, path):
        """
        Open the uploaded compressed file fixture from disk
        """
        uploaded_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), path)
        uploaded_file = open(uploaded_file_path, 'rb')
        return uploaded_file

    def close_uploaded_file(self, uploaded_file):
        """
        Close the opened uploaded compressed file
        """
        uploaded_file.close()

    def create_filestorage(self, uploaded_file):
        """
        Create a FileStorage instance from an open compressed tracking file,
        suitable for testing file uploads later
        """
        storage = FieldStorage()
        storage.filename = os.path.basename(uploaded_file.name)
        storage.file = BytesIO(uploaded_file.read())
        storage.name = os.path.basename(uploaded_file.name)
        # This prevents FormEncode validator from thinking we are providing
        # more than one file for the upload, which crashes the tests
        storage.list = None
        return storage

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['_bulk_files'] = BulkFiles()
        john = User(firstname='John', lastname='Doe',
                    email='john.doe@example.net')
        john.password = 's3cr3t'
        root.add_user(john)

        """
        uid = str(john.uid)
        bulk_file = BulkFile(uid=uid)
        bulk_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/bulk-fit.zip')
        with open(bulk_file_path, 'rb') as _bulk_file:
            bulk_file.compressed_file = create_blob(
                _bulk_file.read(), file_extension='zip', binary=True)
        bulk_file.file_name = 'bulk-fit.zip'
        bulk_file.file_type = 'zip'
        root['_bulk_files'].add_bulk_file(bulk_file)
        """

        return root

    @pytest.fixture
    def dummy_request(self, root):
        request = DummyRequest()
        request.root = root
        return request

    def test_add_bulk_file_get(self, dummy_request):
        """
        Test the view that renders the "add bulk file" form
        """
        request = dummy_request
        user = request.root.users[0]
        assert len(request.root['_bulk_files']) == 0
        response = bulk_views.add_bulk_file(user, request)
        assert 'form' in response
        assert len(response['form'].form.errors) == 0
        assert isinstance(response['form'].form.schema, BulkFileSchema)
        # GET request, no bulk files have been saved
        assert len(request.root['_bulk_files']) == 0

    def test_add_bulk_file_post_invalid(self, dummy_request):
        """
        POST request to add a bulk file, without providing the required form
        data (actually, any bulk file at all).
        """
        request = dummy_request
        user = request.root.users[0]
        request.method = 'POST'
        request.POST = MultiDict({'submit': True})
        assert len(request.root['_bulk_files']) == 0
        response = bulk_views.add_bulk_file(user, request)
        assert 'form' in response
        # Only one required field in this case, the bulk file
        assert len(response['form'].form.errors) == 1
        # no bulk files have been saved
        assert len(request.root['_bulk_files']) == 0

    def test_add_bulk_file_post_invalid_bytes(self, dummy_request):
        """
        POST request to add a workout, without uploading a compressed file,
        which sends an empty bytes object (b'')
        """
        request = dummy_request
        user = request.root.users[0]
        request.method = 'POST'
        request.POST = MultiDict({
            'compressed_file': b'',
            'submit': True,
            })
        assert len(request.root['_bulk_files']) == 0
        response = bulk_views.add_bulk_file(user, request)
        assert 'form' in response
        # Only one required field in this case, the tracking file
        assert len(response['form'].form.errors) == 1
        # no bulk files have been saved
        assert len(request.root['_bulk_files']) == 0

    @pytest.mark.parametrize('filename', bulk_filenames)
    def test_add_workout_post_valid(self, filename, dummy_request):
        """
        POST request to add a bulk file
        """
        request = dummy_request
        uploaded_file = self.open_uploaded_file(filename)
        filestorage = self.create_filestorage(uploaded_file)
        user = request.root.users[0]
        request.method = 'POST'
        request.POST = MultiDict({
            'compressed_file': filestorage,
            'submit': True,
            })
        assert len(request.root['_bulk_files']) == 0
        response = bulk_views.add_bulk_file(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'bulk-files')
        assert len(request.root['_bulk_files']) == 1
        bulk_file = request.root['_bulk_files'].values()[0]
        assert isinstance(bulk_file, BulkFile)
        assert bulk_file.uid == str(user.uid)
        assert bulk_file.file_name == os.path.basename(filename)
        assert bulk_file.workout_ids == []
        assert bulk_file.loaded_info == {}
        assert not bulk_file.loaded
        self.close_uploaded_file(uploaded_file)

    def test_bulk_files_get(self, dummy_request):
        """
        Test the view that renders the "list of all bulk files for a user" page
        """
        request = dummy_request
        user = request.root.users[0]
        # empty _bulk_files
        assert len(request.root['_bulk_files']) == 0
        response = bulk_views.bulk_files(user, request)
        assert response == {'bulk_files': []}
        # let's add one bulk file
        uid = str(user.uid)
        bulk_file = BulkFile(uid=uid)
        bulk_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/bulk-fit.zip')
        with open(bulk_file_path, 'rb') as _bulk_file:
            bulk_file.compressed_file = create_blob(
                _bulk_file.read(), file_extension='zip', binary=True)
        bulk_file.file_name = 'bulk-fit.zip'
        bulk_file.file_type = 'zip'
        request.root['_bulk_files'].add_bulk_file(bulk_file)
        assert len(request.root['_bulk_files']) == 1
        response = bulk_views.bulk_files(user, request)
        assert response == {'bulk_files': [bulk_file]}
        # now, add another one for another (faked) user
        another_bulk_file = BulkFile(uid='faked-user-uid')
        another_bulk_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/bulk-gpx.zip')
        with open(another_bulk_file_path, 'rb') as _bulk_file:
            bulk_file.compressed_file = create_blob(
                _bulk_file.read(), file_extension='zip', binary=True)
        another_bulk_file.file_name = 'bulk-gpx.zip'
        another_bulk_file.file_type = 'zip'
        request.root['_bulk_files'].add_bulk_file(another_bulk_file)
        # there are 2 bulk files, 1 per user, so asking for one user
        # returns only one
        assert len(request.root['_bulk_files']) == 2
        response = bulk_views.bulk_files(user, request)
        assert response == {'bulk_files': [bulk_file]}
        assert response['bulk_files'][0].uid == str(user.uid)

    def test_delete_bulk_file_get(self, dummy_request):
        request = dummy_request
        user = request.root.users[0]
        # let's add one bulk file
        uid = str(user.uid)
        bulk_file = BulkFile(uid=uid)
        bulk_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/bulk-fit.zip')
        with open(bulk_file_path, 'rb') as _bulk_file:
            bulk_file.compressed_file = create_blob(
                _bulk_file.read(), file_extension='zip', binary=True)
        bulk_file.file_name = 'bulk-fit.zip'
        bulk_file.file_type = 'zip'
        request.root['_bulk_files'].add_bulk_file(bulk_file)
        assert len(request.root['_bulk_files']) == 1
        response = bulk_views.delete_bulk_file(bulk_file, request)
        assert response == {'user': user}
        assert len(request.root['_bulk_files']) == 1

    def test_delete_bulk_file_post_invalid(self, dummy_request):
        request = dummy_request
        request.method = 'POST'
        # invalid, missing confirmation delete hidden value
        request.POST = MultiDict({'submit': True})
        user = request.root.users[0]
        # let's add one bulk file
        uid = str(user.uid)
        bulk_file = BulkFile(uid=uid)
        bulk_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/bulk-fit.zip')
        with open(bulk_file_path, 'rb') as _bulk_file:
            bulk_file.compressed_file = create_blob(
                _bulk_file.read(), file_extension='zip', binary=True)
        bulk_file.file_name = 'bulk-fit.zip'
        bulk_file.file_type = 'zip'
        request.root['_bulk_files'].add_bulk_file(bulk_file)
        assert len(request.root['_bulk_files']) == 1
        response = bulk_views.delete_bulk_file(bulk_file, request)
        assert response == {'user': user}
        assert len(request.root['_bulk_files']) == 1

    def test_delete_bulk_file_post_valid(self, dummy_request):
        request = dummy_request
        request.method = 'POST'
        # invalid, missing confirmation delete hidden value
        request.POST = MultiDict({'submit': True, 'delete': 'yes'})
        user = request.root.users[0]
        # let's add one bulk file
        uid = str(user.uid)
        bulk_file = BulkFile(uid=uid)
        bulk_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures/bulk-fit.zip')
        with open(bulk_file_path, 'rb') as _bulk_file:
            bulk_file.compressed_file = create_blob(
                _bulk_file.read(), file_extension='zip', binary=True)
        bulk_file.file_name = 'bulk-fit.zip'
        bulk_file.file_type = 'zip'
        request.root['_bulk_files'].add_bulk_file(bulk_file)
        assert len(request.root['_bulk_files']) == 1
        response = bulk_views.delete_bulk_file(bulk_file, request)
        # after a successful delete, we send the user back to his dashboard
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'bulk-files')
        assert len(request.root['_bulk_files']) == 0
