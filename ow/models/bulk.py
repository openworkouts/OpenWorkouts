from uuid import uuid1
from datetime import datetime, timedelta, timezone

from repoze.folder import Folder
from pyramid.security import Allow, Deny, Everyone, ALL_PERMISSIONS

import pytz


class BulkFile(Folder):

    """
    Object that maps to a compressed file uploaded by a user to upload several
    workout tracking files at once.
    """

    __parent__ = __name__ = None

    def __acl__(self):
        """
        Owner of the compressed file has full permissions to the file, as well
        as system admins. Everybody else has no permissions.
        """
        permissions = [
            (Allow, str(self.uid), 'view'),
            (Allow, str(self.uid), 'edit'),
            (Allow, str(self.uid), 'delete'),
            (Deny, Everyone, ALL_PERMISSIONS)
        ]
        return permissions

    def __init__(self, **kw):
        super(BulkFile, self).__init__()
        self.bfid = uuid1()
        self.uid = kw['uid']  # required, so let it blow if none is given
        self.uploaded = kw.get('uploaded', datetime.now(timezone.utc))
        self.compressed_file = kw.get('compressed_file', None)  # Blob
        self.file_name = ''  # unicode string
        self.file_type = ''  # unicode string
        self.loaded = False  # datetime when workouts have been loaded
        self.workout_ids = []  # ids of the workouts loaded from this file

    def _in_timezone(self, timezone, value):
        """
        Return a string representation of the given value  date and time,
        localized into the given timezone
        """
        _value = value.astimezone(pytz.timezone(timezone))
        return _value.strftime('%d/%m/%Y %H:%M (%Z)')

    def uploaded_in_timezone(self, timezone):
        return self._in_timezone(timezone, self.uploaded)

    def loaded_in_timezone(self, timezone):
        if self.loaded:
            return self._in_timezone(timezone, self.loaded)
        return ''


class BulkFiles(Folder):

    """
    Container for bulk upload compressed files
    """

    __parent__ = __name__ = None

    def __acl__(self):
        """
        Everybody can view, super users can edit
        """
        permissions = [
            (Allow, Everyone, 'view'),
            (Allow, 'admins', 'edit'),
            (Deny, Everyone, ALL_PERMISSIONS)
        ]
        return permissions

    def add_bulk_file(self, bulk_file):
        self[str(bulk_file.bfid)] = bulk_file

    def get_by_uid(self, uid):
        """
        Return bulk files owned by the given uid
        """
        return [self[bf] for bf in self if self[bf].uid == str(uid)]
