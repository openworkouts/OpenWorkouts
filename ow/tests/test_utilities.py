import os
from datetime import timedelta, datetime
from unittest.mock import patch, Mock
from pyexpat import ExpatError
from xml.dom.minidom import Element

import pytest
from pyramid.testing import DummyRequest

from ow.models.root import OpenWorkouts
from ow.models.user import User
from ow.models.workout import Workout

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
    save_map_screenshot,
    timedelta_to_hms,
    get_week_days
)

from ow.tests.helpers import join


class TestUtilities(object):

    @pytest.fixture
    def john(self):
        john = User(firstname='John', lastname='Doe',
                    email='john.doe@example.net')
        john.password = 's3cr3t'
        return john

    @pytest.fixture
    def root(self, john):
        root = OpenWorkouts()
        root.add_user(john)
        john['1'] = Workout(
            duration=timedelta(minutes=60),
            distance=30
        )
        return root

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

    @patch('ow.utilities.shutil')
    @patch('ow.utilities.os')
    @patch('ow.utilities.Browser')
    def test_save_map_screenshot_no_gpx(
            self, Browser, os, shutil, root, john):
        request = DummyRequest()
        saved = save_map_screenshot(john['1'], request)
        assert not saved
        assert not Browser.called
        assert not os.path.abspath.called
        assert not os.path.dirname.called
        assert not os.path.join.called
        assert not os.path.exists.called
        assert not os.makedirs.called
        assert not shutil.move.called
        # even having a fit tracking file, nothing is done
        john['1'].tracking_file = 'faked fit file'
        john['1'].tracking_filetype = 'fit'
        saved = save_map_screenshot(john['1'], request)
        assert not saved
        assert not Browser.called
        assert not os.path.abspath.called
        assert not os.path.dirname.called
        assert not os.path.join.called
        assert not os.path.exists.called
        assert not os.makedirs.called
        assert not shutil.move.called

    @patch('ow.utilities.shutil')
    @patch('ow.utilities.os')
    @patch('ow.utilities.Browser')
    def test_save_map_screenshot_with_gpx(
            self, Browser, os, shutil, root, john):
        request = DummyRequest()
        browser = Mock()
        Browser.return_value = browser
        os.path.abspath.return_value = 'current_dir'
        os.path.join.side_effect = join
        # This mimics what happens when the directory for this user map
        # screenshots does not exist, which means we don'have to create one
        # (calling os.makedirs)
        os.path.exists.return_value = False

        map_url = request.resource_url(john['1'], 'map')

        john['1'].tracking_file = 'faked gpx content'
        john['1'].tracking_filetype = 'gpx'
        saved = save_map_screenshot(john['1'], request)
        assert saved
        Browser.assert_called_once_with('chrome', headless=True)
        browser.driver.set_window_size.assert_called_once_with(1300, 436)
        browser.visit.assert_called_once_with(map_url)
        browser.screenshot.assert_called_once
        os.path.abspath.assert_called_once
        assert os.path.dirname.called
        assert os.path.join.call_count == 2
        assert os.path.exists.called
        assert os.makedirs.called
        os.shutil.move.assert_called_once

    @patch('ow.utilities.shutil')
    @patch('ow.utilities.os')
    @patch('ow.utilities.Browser')
    def test_save_map_screenshot_with_gpx_makedirs(
            self, Browser, os, shutil, root, john):
        request = DummyRequest()
        browser = Mock()
        Browser.return_value = browser
        os.path.abspath.return_value = 'current_dir'
        os.path.join.side_effect = join
        # If os.path.exists returns True, makedirs is not called
        os.path.exists.return_value = True

        map_url = request.resource_url(john['1'], 'map')

        john['1'].tracking_file = 'faked gpx content'
        john['1'].tracking_filetype = 'gpx'
        saved = save_map_screenshot(john['1'], request)
        assert saved
        Browser.assert_called_once_with('chrome', headless=True)
        browser.driver.set_window_size.assert_called_once_with(1300, 436)
        browser.visit.assert_called_once_with(map_url)
        browser.screenshot.assert_called_once
        os.path.abspath.assert_called_once
        assert os.path.dirname.called
        assert os.path.join.call_count == 2
        assert os.path.exists.called
        assert not os.makedirs.called
        os.shutil.move.assert_called_once

    def test_timedelta_to_hms(self):
        value = timedelta(seconds=0)
        assert timedelta_to_hms(value) == (0, 0, 0)
        value = timedelta(seconds=3600)
        assert timedelta_to_hms(value) == (1, 0, 0)
        value = timedelta(seconds=3900)
        assert timedelta_to_hms(value) == (1, 5, 0)
        value = timedelta(seconds=3940)
        assert timedelta_to_hms(value) == (1, 5, 40)
        value = timedelta(seconds=4)
        assert timedelta_to_hms(value) == (0, 0, 4)
        value = timedelta(seconds=150)
        assert timedelta_to_hms(value) == (0, 2, 30)
        # try now something that is not a timedelta
        with pytest.raises(AttributeError):
            timedelta_to_hms('not a timedelta')

    def test_week_days(self):
        # get days from a monday, week starting on monday
        days = get_week_days(datetime(2019, 1, 21))
        assert len(days) == 7
        matches = [
            [days[0], datetime(2019, 1, 21)],
            [days[1], datetime(2019, 1, 22)],
            [days[2], datetime(2019, 1, 23)],
            [days[3], datetime(2019, 1, 24)],
            [days[4], datetime(2019, 1, 25)],
            [days[5], datetime(2019, 1, 26)],
            [days[6], datetime(2019, 1, 27)]
        ]
        for m in matches:
            assert m[0] == m[1]
        # get days from a wednesday, week starting on monday
        days = get_week_days(datetime(2019, 1, 23))
        assert len(days) == 7
        matches = [
            [days[0], datetime(2019, 1, 21)],
            [days[1], datetime(2019, 1, 22)],
            [days[2], datetime(2019, 1, 23)],
            [days[3], datetime(2019, 1, 24)],
            [days[4], datetime(2019, 1, 25)],
            [days[5], datetime(2019, 1, 26)],
            [days[6], datetime(2019, 1, 27)]
        ]
        for m in matches:
            assert m[0] == m[1]
        # get days from a monday, but week starting on sunday now
        days = get_week_days(datetime(2019, 1, 21), start_day=0)
        assert len(days) == 7
        matches = [
            [days[0], datetime(2019, 1, 20)],
            [days[1], datetime(2019, 1, 21)],
            [days[2], datetime(2019, 1, 22)],
            [days[3], datetime(2019, 1, 23)],
            [days[4], datetime(2019, 1, 24)],
            [days[5], datetime(2019, 1, 25)],
            [days[6], datetime(2019, 1, 26)]
        ]
        for m in matches:
            assert m[0] == m[1]


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
