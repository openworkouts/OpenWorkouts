import os
from pyexpat import ExpatError
from xml.dom.minidom import Element

import pytest

from ow.utilities import (
    slugify,
    GPXMinidomParser,
    semicircles_to_degrees,
    degrees_to_semicircles,
    miles_to_kms,
    kms_to_miles,
    meters_to_kms,
    kms_to_meters,
    mps_to_kmph,
    kmph_to_mps,
)


class TestUtilities(object):

    def test_slugify(self):
        res = slugify(u'long story SHORT      ')
        assert res == u'long-story-short'
        res = slugify(u'bla \u03ba\u03b1\u03bb\u03ac \u03c0\u03b1\u03c2')
        assert res == u'bla-kala-pas'

    def test_slugify_special_chars(self):
        res = slugify(u'(r)-[i]\u00AE')
        assert res == u'r-i-r'

    def test_semicircles_to_degrees(self):
        assert semicircles_to_degrees(10) == 10 * (180 / pow(2, 31))

    def test_degrees_to_semicircles(self):
        assert degrees_to_semicircles(10) == 10 * (pow(2, 31) / 180)

    def test_miles_to_kms(self):
        assert miles_to_kms(100) == 100 / 0.62137119

    def test_kms_to_miles(self):
        assert kms_to_miles(100) == 100 * 0.62137119

    def test_meters_to_kms(self):
        assert meters_to_kms(1000) == 1

    def test_kms_to_meters(self):
        assert kms_to_meters(1) == 1000

    def test_mps_to_kmph(self):
        assert mps_to_kmph(5) == 5 * 3.6

    def test_kmph_to_mps(self):
        assert kmph_to_mps(30) == 30 * 0.277778


class TestGPXParseMinidom(object):

    def gpx_file(self, filename):
        """
        Return the full path to the given filename from the available fixtures
        """
        here = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(here, 'fixtures', filename)
        return path

    def test_load_gpx_invalid(self):
        gpx_file = self.gpx_file('invalid.gpx')
        parser = GPXMinidomParser(gpx_file)
        with pytest.raises(ExpatError):
            parser.load_gpx()
        assert parser.gpx is None

    gpx_files = [
        ('empty.gpx', Element),
        ('20131013.gpx', Element),  # GPX 1.0 file
        ('20160129-with-extensions.gpx', Element),  # GPX 1.1 file with ext.
    ]

    @pytest.mark.parametrize(('filename', 'expected'), gpx_files)
    def test_load_gpx(self, filename, expected):
        """
        Loading valid gpx files ends in the gpx attribute of the parser
        being a xml.dom.minidom.Element object, not matter if the gpx file
        is empty or a 1.0/1.1 gpx file.
        """
        gpx_file = self.gpx_file(filename)
        parser = GPXMinidomParser(gpx_file)
        parser.load_gpx()
        assert isinstance(parser.gpx, expected)

    def test_parse_tracks_empty_gpx(self):
        gpx_file = self.gpx_file('empty.gpx')
        parser = GPXMinidomParser(gpx_file)
        parser.load_gpx()
        parser.parse_tracks()
        assert parser.tracks == {}

    def test_parse_tracks_1_0_gpx(self):
        """
        Parsing a GPX 1.0 file with no extensions. The points in the track
        contain keys for the well-known extensions (hr, cad, atemp), but their
        values are None
        """
        gpx_file = self.gpx_file('20131013.gpx')
        parser = GPXMinidomParser(gpx_file)
        parser.load_gpx()
        parser.parse_tracks()
        keys = list(parser.tracks.keys())
        assert keys == [u'A ride I will never forget']
        point = parser.tracks[keys[0]][0]
        data = ['lat', 'lon', 'ele', 'time']
        for d in data:
            assert point[d] is not None
        extensions = ['hr', 'cad', 'atemp']
        for e in extensions:
            assert point[e] is None

    def test_parse_tracks_1_1_gpx(self):
        """
        Parsing a GPX 1.1 file with extensions. The points in the track contain
        keys for the well-known extensions (hr, cad, atemp), with the values
        taken from the gpx file (although we test only that they are not None)
        """
        gpx_file = self.gpx_file('20160129-with-extensions.gpx')
        parser = GPXMinidomParser(gpx_file)
        parser.load_gpx()
        parser.parse_tracks()
        keys = list(parser.tracks.keys())
        assert keys == [
            u'Cota counterclockwise + end bonus']
        point = parser.tracks[keys[0]][0]
        data = ['lat', 'lon', 'ele', 'time']
        for d in data:
            assert point[d] is not None
        extensions = ['hr', 'cad', 'atemp']
        for e in extensions:
            assert point[e] is not None
