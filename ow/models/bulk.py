import os
import logging
from shutil import unpack_archive, rmtree
from uuid import uuid1
from datetime import datetime, timezone

import pytz
from repoze.folder import Folder
from pyramid.security import Allow, Deny, Everyone, ALL_PERMISSIONS
from fitparse.utils import FitHeaderError, FitEOFError
from gpxpy.gpx import GPXXMLSyntaxException

from ow.utilities import create_blob
from ow.models.workout import Workout

log = logging.getLogger(__name__)


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
        self.loaded_info = {}  # per-file information (loaded or not, errors..)

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

    def extract(self, tmp_path, path):
        """
        Extract the files contained in this bulk/compressed file into the
        given path.
        """
        if self.compressed_file is None:
            return []

        # save the blob into a temporal file
        tmp_file_path = os.path.join(tmp_path, self.file_name)
        with open(tmp_file_path, 'wb') as tmp_file:
            with self.compressed_file.open() as blob:
                tmp_file.write(blob.read())
        # extract
        unpack_archive(tmp_file_path, path)
        # remove temporary file
        os.remove(tmp_file_path)
        # analyze the extracted contents, return some data
        extracted = []
        if os.path.exists(path):
            for extracted_file in os.listdir(path):
                extracted.append(os.path.join(path, extracted_file))
        return extracted

    def load(self, root, tmp_path):
        user = root.get_user_by_uid(self.uid)
        # extract
        tmp_extract_path = os.path.join(tmp_path, str(self.bfid))
        log.info(self.file_name + ' extracting to ' + tmp_extract_path)
        extracted = self.extract(tmp_path, tmp_extract_path)
        log.info(self.file_name + ' ' + str(len(extracted)) +
                 ' files extracted')

        # loop over extracted files and create the workouts, taking
        # care of duplicates. Store some stats/info in a dict, so we can
        # keep that somewhere, to show to the user later on
        for extracted_file in extracted:
            base_file_name = os.path.basename(extracted_file)
            log_header = self.file_name + '/' + base_file_name
            log.info(log_header + ' loading file')

            file_extension = os.path.splitext(base_file_name)[1].strip('.')

            # gpx files are text, but fit files are binary files
            open_mode = 'r'
            binary = False
            if file_extension == 'fit':
                open_mode = 'rb'
                binary = True

            with open(extracted_file, open_mode) as f_obj:
                blob = create_blob(
                    f_obj.read(), file_extension=file_extension, binary=binary)

            workout = Workout()
            workout.tracking_file = blob
            workout.tracking_filetype = file_extension

            try:
                workout.load_from_file()
            except (FitHeaderError, FitEOFError, GPXXMLSyntaxException) as e:
                log.error(log_header + ' error loading tracking file ')
                log.error(e)
                self.loaded_info[base_file_name] = {
                    'loaded': False,
                    'error': 'tracking file load error',
                    'workout': None,
                }
            else:
                # check for duplicates
                # hashed is not "complete" for a workout that has not been
                # added yet, as it does not have the owner set, so we have to
                # "build it"
                hashed = str(self.uid) + workout.hashed
                duplicate = root.get_workout_by_hash(hashed)
                if duplicate:
                    log.warning(
                        log_header +
                        ' cannot create workout, possible duplicate')
                    self.loaded_info[base_file_name] = {
                        'loaded': False,
                        'error': 'Possible duplicate workout',
                        'workout': None,
                    }
                else:
                    # add the workout only if no errors happened
                    user.add_workout(workout)
                    log.info(log_header + ' workout added')
                    self.loaded_info[base_file_name] = {
                        'loaded': True,
                        'error': None,
                        'workout': workout.workout_id,
                    }
                    self.workout_ids.append(workout.workout_id)

        # clean-up, we have to check if the temporary directory exists,
        # as extract() won't create such directory if the compressed file
        # is empty
        if os.path.exists(tmp_extract_path):
            rmtree(tmp_extract_path)

        # mark this bulk file as loaded
        self.loaded = datetime.now(timezone.utc)


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
