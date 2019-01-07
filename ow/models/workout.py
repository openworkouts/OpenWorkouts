
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytz
import gpxpy
from repoze.folder import Folder
from pyramid.security import Allow, Everyone
from ow.utilities import GPXMinidomParser


class Workout(Folder):

    __parent__ = __name__ = None

    def __acl__(self):
        """
        If the workout is owned by a given user, only that user have access to
        it (for now). If not, everybody can view it, only admins can edit it.
        """
        # Default permissions
        permissions = [
            (Allow, Everyone, 'view'),
            (Allow, 'group:admins', 'edit')
        ]

        uid = getattr(self.__parent__, 'uid', None)
        if uid is not None:
            # Change permissions in case this workout has an owner
            permissions = [
                (Allow, str(uid), 'view'),
                (Allow, str(uid), 'edit'),
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
        hours, remainder = divmod(int(self.duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return hours, minutes, seconds

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
            return round(self.distance, 1)
        return '-'

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

    def load_from_file(self):
        """
        Check which kind of tracking file we have for this workout, then call
        the proper method to load info from the tracking file
        """
        if self.tracking_filetype == 'gpx':
            self.load_from_gpx()

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

    @property
    def has_tracking_file(self):
        return self.tracking_file is not None

    @property
    def has_gpx(self):
        return self.has_tracking_file and self.tracking_filetype == 'gpx'
