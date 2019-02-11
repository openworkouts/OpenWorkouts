import os
import textwrap
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytz
import gpxpy
from repoze.folder import Folder
from pyramid.security import Allow, Deny, Everyone, ALL_PERMISSIONS

from ow.utilities import (
    GPXMinidomParser,
    copy_blob,
    create_blob,
    mps_to_kmph,
    save_map_screenshot,
    timedelta_to_hms
)

from ow.fit import Fit


class Workout(Folder):

    __parent__ = __name__ = None

    def __acl__(self):
        """
        If the workout is owned by a given user, only that user have access to
        it (for now). If not, everybody can view it, only admins can edit it.
        """
        uid = self.__parent__.uid
        permissions = [
            (Allow, str(uid), 'view'),
            (Allow, str(uid), 'edit'),
            (Allow, str(uid), 'delete'),
            (Deny, Everyone, ALL_PERMISSIONS)
        ]
        return permissions

    def __init__(self, **kw):
        super(Workout, self).__init__()
        # we do store datetime objects with UTC timezone
        self.start = kw.get('start', datetime.now(timezone.utc))
        self.sport = kw.get('sport', 'unknown')  # string
        self.title = kw.get('title', '')  # unicode string
        self.notes = kw.get('notes', '')  # unicode string
        self.duration = kw.get('duration', None)  # a timedelta object
        self.distance = kw.get('distance', None)  # kilometers, Decimal
        self.speed = kw.get('speed', {})
        self.hr_min = kw.get('hr_min', None)  # bpm, Decimal
        self.hr_max = kw.get('hr_max', None)  # bpm, Decimal
        self.hr_avg = kw.get('hr_avg', None)  # bpm, Decimal
        self.uphill = kw.get('uphill', None)
        self.downhill = kw.get('downhill', None)
        self.cad_min = kw.get('cad_min', None)
        self.cad_max = kw.get('cad_max', None)
        self.cad_avg = kw.get('cad_avg', None)
        self.atemp_min = kw.get('atemp_min', None)
        self.atemp_max = kw.get('atemp_max', None)
        self.atemp_avg = kw.get('atemp_avg', None)
        self.tracking_file = kw.get('tracking_file', None)  # Blob
        self.tracking_filetype = ''  # unicode string
        # attr to store ANT fit files. For now this file is used to
        # generate a gpx-encoded tracking file we then use through
        # the whole app
        self.fit_file = kw.get('fit_file', None)  # Blob

    @property
    def workout_id(self):
        return self.__name__

    @property
    def owner(self):
        return self.__parent__

    @property
    def end(self):
        if not self.duration:
            return None
        return self.start + self.duration

    @property
    def start_date(self):
        return self.start.strftime('%d/%m/%Y')

    @property
    def start_time(self):
        return self.start.strftime('%H:%M')

    def start_in_timezone(self, timezone):
        """
        Return a string representation of the start date and time,
        localized into the given timezone
        """
        _start = self.start.astimezone(pytz.timezone(timezone))
        return _start.strftime('%d/%m/%Y %H:%M (%Z)')

    def end_in_timezone(self, timezone):
        """
        Return a string representation of the end date and time,
        localized into the given timezone
        """
        _end = self.end.astimezone(pytz.timezone(timezone))
        return _end.strftime('%d/%m/%Y %H:%M (%Z)')

    def split_duration(self):
        return timedelta_to_hms(self.duration)

    @property
    def duration_hours(self):
        return str(self.split_duration()[0]).zfill(2)

    @property
    def duration_minutes(self):
        return str(self.split_duration()[1]).zfill(2)

    @property
    def duration_seconds(self):
        return str(self.split_duration()[2]).zfill(2)

    @property
    def _duration(self):
        return ':'.join(
            [self.duration_hours, self.duration_minutes, self.duration_seconds]
        )

    @property
    def rounded_distance(self):
        """
        Return rounded value for distance, '-' if the workout has no distance
        data (weight lifting, martial arts, table tennis, etc)
        """
        if self.distance:
            return round(self.distance, 2)
        return '-'

    @property
    def trimmed_notes(self):
        """
        Return a string with a reduced version of the full notes for this
        workout.
        """
        return textwrap.shorten(self.notes, width=225, placeholder=' ...')

    @property
    def has_hr(self):
        """
        True if this workout has heart rate data, False otherwise
        """
        data = [self.hr_min, self.hr_max, self.hr_avg]
        return data.count(None) == 0

    @property
    def hr(self):
        """
        Return a dict with rounded values for hr min, max and average,
        return None if there is no heart rate data for this workout
        """
        if self.has_hr:
            return {'min': round(self.hr_min),
                    'max': round(self.hr_max),
                    'avg': round(self.hr_avg)}
        return None

    @property
    def has_cad(self):
        """
        True if this workout has cadence data, False otherwise
        """
        data = [self.cad_min, self.cad_max, self.cad_avg]
        return data.count(None) == 0

    @property
    def cad(self):
        """
        Return a dict with rounded values for cadence min, max and average
        return None if there is no cadence data for this workout
        """
        if self.has_cad:
            return {'min': round(self.cad_min),
                    'max': round(self.cad_max),
                    'avg': round(self.cad_avg)}
        return None

    @property
    def has_atemp(self):
        """
        True if this workout has temperature data, False otherwise
        """
        data = [self.atemp_min, self.atemp_max, self.atemp_avg]
        return data.count(None) == 0

    @property
    def atemp(self):
        """
        Return a dict with rounded values for temperature min, max and average
        return None if there is no temperature data for this workout
        """
        if self.has_atemp:
            return {'min': round(self.atemp_min),
                    'max': round(self.atemp_max),
                    'avg': round(self.atemp_avg)}
        return None

    @property
    def tracking_file_path(self):
        """
        Get the path to the blob file attached as a tracking file.

        First check if the file was not committed to the db yet (new workout
        not saved yet) and use the path to the temporary file on the fs.
        If none is found there, go for the real blob file in the blobs
        directory
        """
        path = None
        if self.tracking_file:
            path = self.tracking_file._uncommitted()
            if path is None:
                path = self.tracking_file.committed()
        return path

    @property
    def fit_file_path(self):
        """
        Get the path to the blob file attached as a fit file.

        First check if the file was not committed to the db yet (new workout
        not saved yet) and use the path to the temporary file on the fs.
        If none is found there, go for the real blob file in the blobs
        directory
        """
        path = None
        if self.fit_file:
            path = self.fit_file._uncommitted()
            if path is None:
                path = self.fit_file.committed()
        return path

    def load_from_file(self):
        """
        Check which kind of tracking file we have for this workout, then call
        the proper method to load info from the tracking file
        """
        if self.tracking_filetype == 'gpx':
            self.load_from_gpx()
        elif self.tracking_filetype == 'fit':
            self.load_from_fit()

    def load_from_gpx(self):
        """
        Load some information from an attached gpx file. Return True if data
        had been succesfully loaded, False otherwise
        """
        with self.tracking_file.open() as gpx_file:
            gpx_contents = gpx_file.read()
            gpx_contents = gpx_contents.decode('utf-8')
            gpx = gpxpy.parse(gpx_contents)
            if gpx.tracks:
                track = gpx.tracks[0]
                # Start time comes in UTC/GMT/ZULU
                time_bounds = track.get_time_bounds()
                self.start = time_bounds.start_time
                # ensure this datetime start object is timezone-aware
                self.start = self.start.replace(tzinfo=timezone.utc)
                # get_duration returns seconds
                self.duration = timedelta(seconds=track.get_duration())
                # length_3d returns meters
                self.distance = Decimal(track.length_3d()) / Decimal(1000.00)
                ud = track.get_uphill_downhill()
                self.uphill = Decimal(ud.uphill)
                self.downhill = Decimal(ud.downhill)
                # If the user did not provide us with a title, and the gpx has
                # one, use that
                if not self.title and track.name:
                    self.title = track.name

                # Hack to calculate some values from the GPX 1.1 extensions,
                # using our own parser (gpxpy does not support those yet)
                tracks = self.parse_gpx()
                hr = []
                cad = []
                atemp = []
                for t in tracks:
                    hr += [
                        d['hr'] for d in tracks[t] if d['hr'] is not None]
                    cad += [
                        d['cad'] for d in tracks[t] if d['cad'] is not None]
                    atemp += [
                        d['atemp'] for d in tracks[t]
                        if d['atemp'] is not None]

                if hr:
                    self.hr_min = Decimal(min(hr))
                    self.hr_avg = Decimal(sum(hr)) / Decimal(len(hr))
                    self.hr_max = Decimal(max(hr))

                if cad:
                    self.cad_min = Decimal(min(cad))
                    self.cad_avg = Decimal(sum(cad)) / Decimal(len(cad))
                    self.cad_max = Decimal(max(cad))

                if atemp:
                    self.atemp_min = Decimal(min(atemp))
                    self.atemp_avg = Decimal(sum(atemp)) / Decimal(len(atemp))
                    self.atemp_max = Decimal(max(atemp))

                return True

        return False

    def parse_gpx(self):
        """
        Parse the gpx using minidom.

        This method is needed as a workaround to get HR/CAD/TEMP values from
        gpx 1.1 extensions (gpxpy does not handle them correctly so far)
        """
        if not self.has_gpx:
            # No gpx, nothing to return
            return {}

        # Get the path to the blob file, first check if the file was not
        # committed to the db yet (new workout not saved yet) and use the
        # path to the temporary file on the fs. If none is found there, go
        # for the final blob file
        gpx_path = self.tracking_file._p_blob_uncommitted
        if gpx_path is None:
            gpx_path = self.tracking_file._p_blob_committed

        # Create a parser, load the gpx and parse the tracks
        parser = GPXMinidomParser(gpx_path)
        parser.load_gpx()
        parser.parse_tracks()
        return parser.tracks

    def load_from_fit(self):
        """
        Try to load data from an ANT-compatible .fit file (if any has been
        added to this workout).

        "Load data" means:

        1. Copy over the uploaded fit file to self.fit_file, so we can keep
           that copy around for future use

        2. generate a gpx object from the fit file

        3. save the gpx object as the tracking_file, which then will be used
           by the current code to display and gather data to be displayed/shown
           to the user.

        4. Grab some basic info from the fit file and store it in the Workout
        """

        # we can call load_from_fit afterwards for updates. In such case, check
        # if the tracking file is a fit file uploaded to override the previous
        # one. If not, just reuse the existing fit file
        if self.tracking_filetype == 'fit':
            # backup the fit file
            self.fit_file = copy_blob(self.tracking_file)

        # create an instance of our Fit class
        fit = Fit(self.fit_file_path)
        fit.load()

        # fit -> gpx and store that as the main tracking file
        self.tracking_file = create_blob(fit.gpx, 'gpx')
        self.tracking_filetype = 'gpx'

        # grab the needed data from the fit file, update the workout
        self.sport = fit.data['sport']
        self.start = fit.data['start']
        # ensure this datetime start object is timezone-aware
        self.start = self.start.replace(tzinfo=timezone.utc)
        # duration comes in seconds, store a timedelta
        self.duration = timedelta(seconds=fit.data['duration'])
        if fit.data['distance']:
            # distance comes in meters
            self.distance = Decimal(fit.data['distance']) / Decimal(1000.00)
        if fit.data['uphill']:
            self.uphill = Decimal(fit.data['uphill'])
        if fit.data['downhill']:
            self.downhill = Decimal(fit.data['downhill'])
        # If the user did not provide us with a title, build one from the
        # info in the fit file
        if not self.title:
            self.title = fit.name

        if fit.data['max_speed']:
            self.speed['max'] = mps_to_kmph(fit.data['max_speed'])

        if fit.data['avg_speed']:
            self.speed['avg'] = mps_to_kmph(fit.data['avg_speed'])

        if fit.data['avg_hr']:
            self.hr_avg = Decimal(fit.data['avg_hr'])
            self.hr_min = Decimal(fit.data['min_hr'])
            self.hr_max = Decimal(fit.data['max_hr'])

        if fit.data['avg_cad']:
            self.cad_avg = Decimal(fit.data['avg_cad'])
            self.cad_min = Decimal(fit.data['min_cad'])
            self.cad_max = Decimal(fit.data['max_cad'])

        if fit.data['avg_atemp']:
            self.atemp_avg = Decimal(fit.data['avg_atemp'])
            self.atemp_min = Decimal(fit.data['min_atemp'])
            self.atemp_max = Decimal(fit.data['max_atemp'])

        return True

    @property
    def has_tracking_file(self):
        return self.tracking_file is not None

    @property
    def has_gpx(self):
        return self.has_tracking_file and self.tracking_filetype == 'gpx'

    @property
    def has_fit(self):
        return self.fit_file is not None

    def map_screenshot(self, request):
        """
        Return the static path to the screenshot image of the map for
        this workout (works only for workouts with gps tracking)
        """
        if not self.has_gpx:
            return None

        screenshot_name = os.path.join(
            str(self.owner.uid), str(self.workout_id) + '.png')
        current_path = os.path.abspath(os.path.dirname(__file__))
        screenshot_path = os.path.join(
            current_path, '../static/maps', screenshot_name)

        if not os.path.exists(screenshot_path):
            # screenshot does not exist, generate it
            save_map_screenshot(self, request)

        static_path = os.path.join('static/maps', screenshot_name)
        return request.static_url('ow:' + static_path)
