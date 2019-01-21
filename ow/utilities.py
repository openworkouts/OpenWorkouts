import re
import os
import logging
import subprocess
from datetime import datetime
from decimal import Decimal
from shutil import copyfileobj

from unidecode import unidecode
from xml.dom import minidom
from ZODB.blob import Blob

log = logging.getLogger(__name__)


def slugify(text, delim=u'-'):
    """
    Generates an ASCII-only slug.
    from http://flask.pocoo.org/snippets/5/
    """
    _punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
    result = []
    text = unidecode(text)
    for word in _punct_re.split(text.lower()):
        result.extend(word.split())
    return delim.join(result)


class GPXMinidomParser(object):
    """
    GPX parser, using minidom from the base library.

    We need this as a workaround, as gpxpy does not handle GPX 1.1 extensions
    correctly right now (and we have not been able to fix it).

    This method is inspired by this blog post:

    http://castfortwo.blogspot.com.au/2014/06/
    parsing-strava-gpx-file-with-python.html
    """

    def __init__(self, gpx_path):
        self.gpx_path = gpx_path
        self.gpx = None
        self.tracks = {}

    def load_gpx(self):
        """
        Load the given gpx file into a minidom doc, normalize it and set
        self.gpx to the document root so we can reuse it later on
        """
        doc = minidom.parse(self.gpx_path)
        doc.normalize()
        self.gpx = doc.documentElement

    def parse_tracks(self):
        """
        Loop over all the tracks found in the gpx, parsing them
        """
        for trk in self.gpx.getElementsByTagName('trk'):
            self.parse_track(trk)

    def parse_track(self, trk):
        """
        Parse the given track, extracting all the information and putting it
        into a dict where the key is the track name and the value is a list
        of data for the the different segments and points in the track.

        All the data is saved in self.tracks
        """
        name = trk.getElementsByTagName('name')[0].firstChild.data
        if name not in self.tracks:
            self.tracks[name] = []

        for trkseg in trk.getElementsByTagName('trkseg'):
            for trkpt in trkseg.getElementsByTagName('trkpt'):
                lat = Decimal(trkpt.getAttribute('lat'))
                lon = Decimal(trkpt.getAttribute('lon'))

                # There could happen there is no elevation data
                ele = trkpt.getElementsByTagName('ele')
                if ele:
                    ele = Decimal(ele[0].firstChild.data)
                else:
                    ele = None

                rfc3339 = trkpt.getElementsByTagName('time')[0].firstChild.data
                try:
                    t = datetime.strptime(
                        rfc3339, '%Y-%m-%dT%H:%M:%S.%fZ')
                except ValueError:
                    t = datetime.strptime(
                        rfc3339, '%Y-%m-%dT%H:%M:%SZ')

                hr = None
                cad = None
                atemp = None
                extensions = trkpt.getElementsByTagName('extensions')
                if extensions:
                    extensions = extensions[0]
                    trkPtExt = extensions.getElementsByTagName(
                        'gpxtpx:TrackPointExtension')[0]
                    if trkPtExt:
                        hr_ext = trkPtExt.getElementsByTagName('gpxtpx:hr')
                        cad_ext = trkPtExt.getElementsByTagName('gpxtpx:cad')
                        atemp_ext = trkPtExt.getElementsByTagName(
                            'gpxtpx:atemp')
                        if hr_ext:
                            hr = Decimal(hr_ext[0].firstChild.data)
                        if cad_ext:
                            cad = Decimal(cad_ext[0].firstChild.data)
                        if atemp_ext:
                            atemp = Decimal(atemp_ext[0].firstChild.data)

                self.tracks[name].append({
                    'lat': lat,
                    'lon': lon,
                    'ele': ele,
                    'time': t,
                    'hr': hr,
                    'cad': cad,
                    'atemp': atemp})


def semicircles_to_degrees(semicircles):
    return semicircles * (180 / pow(2, 31))


def degrees_to_semicircles(degrees):
    return degrees * (pow(2, 31) / 180)


def miles_to_kms(miles):
    factor = 0.62137119
    return miles / factor


def kms_to_miles(kms):
    factor = 0.62137119
    return kms * factor


def meters_to_kms(meters):
    return meters / 1000


def kms_to_meters(kms):
    return kms * 1000


def mps_to_kmph(mps):
    """
    Transform a value from meters-per-second to kilometers-per-hour
    """
    return mps * 3.6


def kmph_to_mps(kmph):
    """
    Transform a value from kilometers-per-hour to meters-per-second
    """
    return kmph * 0.277778


def copy_blob(blob):
    """
    Create a copy of a blob object, returning another blob object that is
    the copy of the given blob file.
    """
    new_blob = Blob()
    if getattr(blob, 'file_extension', None):
        new_blob.file_extension = blob.file_extension
    with blob.open('r') as orig_blob, new_blob.open('w') as dest_blob:
        orig_blob.seek(0)
        copyfileobj(orig_blob, dest_blob)
    return new_blob


def create_blob(data, file_extension, binary=False):
    """
    Create a ZODB blob file from some data, return the blob object
    """
    blob = Blob()
    blob.file_extension = file_extension
    with blob.open('w') as open_blob:
        # use .encode() to convert the string to bytes if needed
        if not binary and not isinstance(data, bytes):
            data = data.encode('utf-8')
        open_blob.write(data)
    return blob


def save_map_screenshot(workout):
    if workout.has_gpx:
        current_path = os.path.abspath(os.path.dirname(__file__))
        tool_path = os.path.join(current_path, '../bin/screenshot_map')

        screenshots_path = os.path.join(
            current_path, 'static/maps', str(workout.owner.uid))
        if not os.path.exists(screenshots_path):
            os.makedirs(screenshots_path)

        screenshot_path = os.path.join(
            screenshots_path, str(workout.workout_id))
        screenshot_path += '.png'

        subprocess.run(
            [tool_path, str(workout.owner.uid), str(workout.workout_id),
             screenshot_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return True

    return False
