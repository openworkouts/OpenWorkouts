import os
from datetime import datetime, timezone, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
import pytz
from pyramid.security import Allow, Everyone, Deny, ALL_PERMISSIONS

from ow.models.user import User
from ow.models.root import OpenWorkouts
from ow.models.bulk import BulkFile, BulkFiles
from ow.utilities import create_blob


class TestBulkFile(object):

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['_bulk_files'] = BulkFiles()
        john = User(firstname='John', lastname='Doe',
                    email='john.doe@example.net')
        john.password = 's3cr3t'
        root.add_user(john)
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
        return root

    def test__acl__(self, root):
        bulk_file = root['_bulk_files'].values()[0]
        permissions = [
            (Allow, str(bulk_file.uid), 'view'),
            (Allow, str(bulk_file.uid), 'edit'),
            (Allow, str(bulk_file.uid), 'delete'),
            (Deny, Everyone, ALL_PERMISSIONS)
        ]
        assert bulk_file.__acl__() == permissions

    def test_uploaded_in_timezone(self, root):
        bulk_file = root['_bulk_files'].values()[0]
        timezones = ['UTC', 'Europe/Madrid', 'Asia/Tokyo', 'Canada/Pacific']
        for _timezone in timezones:
            expected = bulk_file.uploaded.astimezone(pytz.timezone(_timezone))
            expected = expected.strftime('%d/%m/%Y %H:%M (%Z)')
            assert bulk_file.uploaded_in_timezone(_timezone) == expected

    def test_loaded_in_timezone(self, root):
        timezones = ['UTC', 'Europe/Madrid', 'Asia/Tokyo', 'Canada/Pacific']
        # first try a non-loaded bulk file
        bulk_file = root['_bulk_files'].values()[0]
        for _timezone in timezones:
            assert bulk_file.loaded_in_timezone(_timezone) == ''
        # now, "mark" it as loaded, try again
        bulk_file.loaded = datetime.now(timezone.utc) - timedelta(hours=5)
        for _timezone in timezones:
            expected = bulk_file.loaded.astimezone(pytz.timezone(_timezone))
            expected = expected.strftime('%d/%m/%Y %H:%M (%Z)')
            assert bulk_file.loaded_in_timezone(_timezone) == expected

    @patch('ow.models.bulk.os')
    @patch('ow.models.bulk.unpack_archive')
    def test_extract_none(self, unpack_archive, _os, root):
        """
        Call extract on a bulk file without an associated compressed file.
        """
        user = root.users[0]
        uid = str(user.uid)
        bulk_file = BulkFile(uid=uid)
        with TemporaryDirectory() as tmp_path:
            extracted = bulk_file.extract(tmp_path, tmp_path)
            assert extracted == []
            assert len(os.listdir(tmp_path)) == 0
            assert not unpack_archive.called
            assert not _os.path.join.called
            assert not _os.remove.called

    params = (
        ('fixtures/bulk-fit.zip', {
            'extracted': [
                '2019-09-19-09-42-41.fit', '2019-09-17-09-42-50.fit'
            ],
        }),
        ('fixtures/bulk-fit.tgz', {
            'extracted': [
                '2019-09-19-09-42-41.fit', '2019-09-17-09-42-50.fit'
            ],
        }),
        ('fixtures/bulk-gpx.zip', {
            'extracted': [
                '20181230_101115.gpx', '20181231_110728.gpx'
            ],
        }),
        ('fixtures/bulk-gpx.tgz', {
            'extracted': [
                '20181230_101115.gpx', '20181231_110728.gpx'
            ],
        }),
        ('fixtures/bulk-empty.zip', {'extracted': []}),
    )

    @pytest.mark.parametrize(('filename', 'expected'), params)
    def test_extract(self, filename, expected, root):
        base_name, extension = os.path.splitext(filename)
        extension = extension.lstrip('.')

        user = root.users[0]
        uid = str(user.uid)

        bulk_file = BulkFile(uid=uid)
        bulk_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), filename)
        with open(bulk_file_path, 'rb') as _bulk_file:
            bulk_file.compressed_file = create_blob(
                _bulk_file.read(), file_extension=extension, binary=True)
        bulk_file.file_name = os.path.basename(filename)
        bulk_file.file_type = extension

        root['_bulk_files'].add_bulk_file(bulk_file)

        with TemporaryDirectory() as tmp_path:
            extracted = bulk_file.extract(tmp_path, tmp_path)
            assert expected['extracted'] == os.listdir(tmp_path)
            expected_extracted = [
                os.path.join(tmp_path, p) for p in expected['extracted']]
            assert extracted == expected_extracted

    params = (
        ('fixtures/bulk-fit.zip', {
            'extracted': [
                '2019-09-19-09-42-41.fit', '2019-09-17-09-42-50.fit'
            ],
            'loaded': [
                '2019-09-19-09-42-41.fit', '2019-09-17-09-42-50.fit'
            ],
        }),
        ('fixtures/bulk-fit.tgz', {
            'extracted': [
                '2019-09-19-09-42-41.fit', '2019-09-17-09-42-50.fit'
            ],
            'loaded': [
                '2019-09-19-09-42-41.fit', '2019-09-17-09-42-50.fit'
            ],
        }),
        ('fixtures/bulk-gpx.zip', {
            'extracted': [
                '20181230_101115.gpx', '20181231_110728.gpx'
            ],
            'loaded': [
                '20181230_101115.gpx', '20181231_110728.gpx'
            ],
        }),
        ('fixtures/bulk-gpx.tgz', {
            'extracted': [
                '20181230_101115.gpx', '20181231_110728.gpx'
            ],
            'loaded': [
                '20181230_101115.gpx', '20181231_110728.gpx'
            ],
        }),
        ('fixtures/bulk-empty.zip', {'extracted': [], 'loaded': []}),
        ('fixtures/bulk-invalid.zip', {
            'extracted': [
                'empty.fit', 'empty.gpx', 'invalid.fit', 'invalid.gpx',
                '20181230_101115.gpx', '20181230_101115-duplicate.gpx'
            ],
            'loaded': ['empty.gpx', '20181230_101115.gpx'],
        }),
    )

    @pytest.mark.parametrize(('filename', 'expected'), params)
    def test_load(self, filename, expected, root):
        base_name, extension = os.path.splitext(filename)
        extension = extension.lstrip('.')

        user = root.users[0]
        uid = str(user.uid)

        bulk_file = BulkFile(uid=uid)
        bulk_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), filename)
        with open(bulk_file_path, 'rb') as _bulk_file:
            bulk_file.compressed_file = create_blob(
                _bulk_file.read(), file_extension=extension, binary=True)
        bulk_file.file_name = os.path.basename(filename)
        bulk_file.file_type = extension

        root['_bulk_files'].add_bulk_file(bulk_file)

        assert list(user.workouts()) == []
        assert not bulk_file.loaded
        assert bulk_file.loaded_info == {}
        assert bulk_file.workout_ids == []

        num_extracted = len(expected['extracted'])
        num_loaded = len(expected['loaded'])
        with TemporaryDirectory() as tmp_path:
            bulk_file.load(root, tmp_path)
            assert isinstance(bulk_file.loaded, datetime)
            assert len(bulk_file.loaded_info.keys()) == num_extracted
            assert len(bulk_file.workout_ids) == num_loaded
            for key, value in bulk_file.loaded_info.items():
                if value['loaded']:
                    assert value['error'] is None
                    assert value['workout'] is not None
                else:
                    assert isinstance(value['error'], str)
                    assert len(value['error']) > 2
                    assert value['workout'] is None
            assert len(user.workouts()) == num_loaded


class TestBulkFiles(object):

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        root['_bulk_files'] = BulkFiles()
        return root

    def test__acl__(self, root):
        permissions = [
            (Allow, Everyone, 'view'),
            (Allow, 'admins', 'edit'),
            (Deny, Everyone, ALL_PERMISSIONS)
        ]
        assert root['_bulk_files'].__acl__() == permissions

    def test_add_bulk_file(self, root):
        assert len(root['_bulk_files']) == 0
        bulk_file = BulkFile(uid='faked-uid')
        root['_bulk_files'].add_bulk_file(bulk_file)
        assert len(root['_bulk_files']) == 1
        assert list(root['_bulk_files'].keys()) == [str(bulk_file.bfid)]
        assert list(root['_bulk_files'].values()) == [bulk_file]

    def test_get_by_uid(self, root):
        # no bulk files uploaded, trying to get one for 'faked-uid'
        bulk_files = root['_bulk_files'].get_by_uid('faked-uid')
        assert bulk_files == []
        # add a bulk file, trying to get it back
        bulk_file = BulkFile(uid='faked-uid')
        root['_bulk_files'].add_bulk_file(bulk_file)
        bulk_files = root['_bulk_files'].get_by_uid('faked-uid')
        assert bulk_files == [bulk_file]
        # trying to get files for another user, who did not upload anything
        bulk_files = root['_bulk_files'].get_by_uid('other-faked-uid')
        assert bulk_files == []
        # add another bulk file, for the same user, and get both files
        other_bulk_file = BulkFile(uid='faked-uid')
        root['_bulk_files'].add_bulk_file(other_bulk_file)
        bulk_files = root['_bulk_files'].get_by_uid('faked-uid')
        assert bulk_file in bulk_files
        assert other_bulk_file in bulk_files
        assert len(bulk_files) == 2
        # this user still did not upload anything, so no files returned for
        # him
        bulk_files = root['_bulk_files'].get_by_uid('other-faked-uid')
        assert bulk_files == []
