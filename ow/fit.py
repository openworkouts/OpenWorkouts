from fitparse import FitFile
import gpxpy
import gpxpy.gpx

try:
    import lxml.etree as mod_etree  # Load LXML or fallback to cET or ET
except:
    try:
        import xml.etree.cElementTree as mod_etree
    except:
        import xml.etree.ElementTree as mod_etree

from ow.utilities import semicircles_to_degrees


class Fit(object):
    """
    A fit object, that can be used to load, parse, convert, etc ANT fit
    files
    """
    def __init__(self, path):
        self.path = path
        # FitFile object containing all data after opening the file with
        # python-fitparse
        self.obj = FitFile(path)
        # data is a temporary place to store info we got from the fit file,
        # so we don't have to loop over data in self.obj multiple times
        self.data = {}

    def load(self):
        """
        Load contents from the fit file
        """
        # get some basic info from the fit file
        #
        # IMPORTANT: only single-session fit files are supported right now
        sessions = list(self.obj.get_messages('session'))
        session = sessions[0]
        values = session.get_values()
        self.data['sport'] = values.get('sport', None)

        # in some garmin devices (520), you can have named profiles, which
        # can be used for different bikes or for different types of workouts
        # (training/races/etc)
        self.data['profile'] = values.get('unknown_110', None)

        # naive datetime object
        self.data['start'] = values.get('start_time', None)

        # seconds
        self.data['duration'] = values.get('total_timer_time', None)
        self.data['elapsed'] = values.get('total_elapsed_time', None)

        # meters
        self.data['distance'] = values.get('total_distance', None)

        # meters
        self.data['uphill'] = values.get('total_ascent', None)
        self.data['downhill'] = values.get('total_descent', None)

        self.data['calories'] = values.get('total_calories', None)

        # store here a list with all hr values
        self.data['hr'] = []
        self.data['min_hr'] = None
        self.data['max_hr'] = values.get('max_heart_rate', None)
        self.data['avg_hr'] = values.get('avg_heart_rate', None)

        # store here a list with all cad values
        self.data['cad'] = []
        self.data['min_cad'] = None
        self.data['max_cad'] = values.get('max_cadence', None)
        self.data['avg_cad'] = values.get('avg_cadence', None)

        self.data['max_speed'] = values.get('enhanced_max_speed', None)
        if self.data['max_speed'] is None:
            self.data['max_speed'] = values.get('max_speed', None)
            if self.data['max_speed'] is not None:
                self.data['max_speed'] = self.data['max_speed'] / 1000

        self.data['avg_speed'] = values.get('enhanced_avg_speed', None)
        if self.data['avg_speed'] is None:
            self.data['avg_speed'] = values.get('avg_speed', None)
            if self.data['avg_speed'] is not None:
                self.data['avg_speed'] = self.data['avg_speed'] / 1000

        # no temp values yet
        # store here a list with all temp values
        self.data['atemp'] = []
        self.data['min_atemp'] = None
        self.data['max_atemp'] = 0
        self.data['avg_atemp'] = 0

    @property
    def name(self):
        """
        Build a name based on some info from the fit file
        """
        if self.data['profile']:
            return self.data['profile'] + ' ' + self.data['sport']
        return self.data['sport']

    def _calculate_avg_atemp(self):
        temps = [t[0] for t in self.data['atemp']]
        if temps:
            self.data['avg_atemp'] = int(round(sum(temps)/len(temps)))
        return self.data['avg_atemp']

    @property
    def gpx(self):
        """
        Return valid xml-formatted gpx contents from the loaded fit file
        """
        # Create a gpx object, adding some basic metadata to it.
        #
        # The schema namespaces info is very important, in order to support
        # all the data we will extract from the fit file.
        gpx = gpxpy.gpx.GPX()
        gpx.creator = 'OpenWorkouts'
        gpx.schema_locations = [
            'http://www.topografix.com/GPX/1/1',
            'http://www.topografix.com/GPX/1/1/gpx.xsd',
            'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
            'http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd',
            'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
            'http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd'
        ]
        garmin_schemas = 'http://www.garmin.com/xmlschemas'
        gpx.nsmap['gpxtpx'] = garmin_schemas + '/TrackPointExtension/v1'
        gpx.nsmap['gpxx'] = garmin_schemas + '/GpxExtensions/v3'

        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx_track.name = self.name
        gpx.tracks.append(gpx_track)

        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        # namespace for the additional gpx extensions
        # (temperature, cadence, heart rate)
        namespace = '{gpxtpx}'
        # nsmap = {'ext': namespace[1:-1]}

        # loop over the 'record' messages in the fit file, which are the actual
        # data "recorded" by the device
        for message in self.obj.get_messages('record'):
            values = message.get_values()

            # Create an entry where we add the "gpx extensions" data, that will
            # be added to the track point later.
            extensions_root = mod_etree.Element(
                namespace + 'TrackPointExtension')

            atemp = mod_etree.Element(namespace + 'atemp')
            atemp_value = values.get('temperature', 0)
            atemp.text = str(atemp_value)
            atemp.tail = ''
            extensions_root.append(atemp)
            self.data['atemp'].append((atemp_value, values['timestamp']))
            if self.data['min_atemp'] is None:
                self.data['min_atemp'] = atemp_value
            elif atemp_value < self.data['min_atemp']:
                self.data['min_atemp'] = atemp_value
            if atemp_value > self.data['max_atemp']:
                self.data['max_atemp'] = atemp_value

            hr = mod_etree.Element(namespace + 'hr')
            hr_value = values.get('heart_rate', 0)
            if hr_value == 0:
                # don't allow hr values of 0, something may have gone wrong
                # with the heart rate monitor, so we use the previous value,
                # if any
                if self.data['hr']:
                    hr_value = self.data['hr'][-1][0]
            hr.text = str(hr_value)
            hr.tail = ''
            extensions_root.append(hr)
            self.data['hr'].append((hr_value, values['timestamp']))
            # min_hr None means we are on the first value, set it as min, we
            # don't want 0 values here. If it is not None, check if the current
            # value is lower than the current min, update accordingly
            if self.data['min_hr'] is None or hr_value < self.data['min_hr']:
                self.data['min_hr'] = hr_value

            cad = mod_etree.Element(namespace + 'cad')
            cad_value = values.get('cadence', 0)
            cad.text = str(cad_value)
            cad.tail = ''
            extensions_root.append(cad)
            self.data['cad'].append((cad_value, values['timestamp']))
            if self.data['min_cad'] is None:
                self.data['min_cad'] = cad_value
            elif cad_value < self.data['min_cad']:
                self.data['min_cad'] = cad_value

            # Create a gpx track point, that holds the "recorded" geo and speed
            # data, as well as the "gpx extensions" object
            if values.get('position_lat') and values.get('position_long'):
                track_point = gpxpy.gpx.GPXTrackPoint(
                    latitude=semicircles_to_degrees(values['position_lat']),
                    longitude=semicircles_to_degrees(values['position_long']),
                    elevation=values['enhanced_altitude'],
                    speed=values['enhanced_speed'],
                    time=values['timestamp']
                )

            track_point.extensions.append(extensions_root)

            gpx_segment.points.append(track_point)

        # if the fit file has temperature data, calculate the avg
        if self.data['atemp']:
            self._calculate_avg_atemp()

        # return a string containing the xml representation of the gpx object
        return gpx.to_xml()
