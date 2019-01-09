import os
from datetime import datetime
from unittest.mock import Mock

import pytest
from fitparse import FitFile
from fitparse.utils import FitHeaderError

from ow.fit import Fit


class TestFit(object):

    def get_fixture_path(self, filename):
        here = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(here, 'fixtures', filename)
        return path

    @pytest.fixture
    def fit(self):
        # fit file used in most of the tests below
        fit_path = self.get_fixture_path('20181230_101115.fit')
        fit = Fit(fit_path)
        return fit

    @pytest.fixture
    def values(self):
        return {
            'sport': 'cycling',
            'unknown_110': 'OpenWorkouts-testing',
            'start_time': datetime.now(),
            'total_timer_time': 3600,
            'total_elapsed_time': 3700,
            'total_distance': 60000,
            'total_ascent': 1200,
            'total_descent': 1100,
            'total_calories': 2000,
            'max_heart_rate': 180,
            'avg_heart_rate': 137,
            'max_cadence': 111,
            'avg_cadence': 90,
            'enhanced_max_speed': 16.666,
            'max_speed': 18666,
            'enhanced_avg_speed': 7.638,
            'avg_speed': 7838
        }

    @pytest.fixture
    def expected(self, values):
        return {
            'sport': 'cycling',
            'profile': 'OpenWorkouts-testing',
            'start': values['start_time'],
            'duration': 3600,
            'elapsed': 3700,
            'distance': 60000,
            'uphill': 1200,
            'downhill': 1100,
            'calories': 2000,
            'hr': [],
            'min_hr': None,
            'max_hr': 180,
            'avg_hr': 137,
            'cad': [],
            'min_cad': None,
            'max_cad': 111,
            'avg_cad': 90,
            'max_speed': 16.666,
            'avg_speed': 7.638,
            'atemp': [],
            'min_atemp': None,
            'max_atemp': 0,
            'avg_atemp': 0,
        }

    fit_files = [
        ('non-existant.fit', FileNotFoundError),
        ('20131013.gpx', FitHeaderError),  # GPX file
        ('20181230_101115.fit', None),  # FIT file
    ]

    @pytest.mark.parametrize(('filename', 'expected'), fit_files)
    def test__init__(self, filename, expected):
        fit_path = self.get_fixture_path(filename)
        if expected is None:
            fit = Fit(fit_path)
            assert isinstance(fit, Fit)
            assert fit.path == fit_path
            assert isinstance(fit.obj, FitFile)
            assert fit.data == {}
        else:
            with pytest.raises(expected):
                Fit(fit_path)

    def test_load_real_fit_file(self, fit):
        """
        Test loading data from a real fit file from a Garmin device
        """
        assert fit.data == {}
        fit.load()
        assert len(fit.data.keys()) == 23

    def test_load_extra_cases(self, fit, values, expected):
        """
        Test loading data from some mocked file, so we can be sure all the
        loading code is executed and covered by tests
        """
        # first mock the FitFile object in the fit object
        session = Mock()
        session.get_values.return_value = values
        fit.obj = Mock()
        # mock get_messages, no matter what we ask for, return a single
        # session list, which fits for the purpose of this test
        fit.obj.get_messages.return_value = [session]

        assert fit.data == {}

        # first load, we have all data we are supposed to have in the fit
        # file, so results are more or less like in the real test
        fit.load()
        assert len(fit.data.keys()) == 23
        for k in expected.keys():
            assert fit.data[k] == expected[k]

        # now, remove enhanced_max_speed, so the max_speed parameter is used
        values['enhanced_max_speed'] = None
        fit.load()
        assert len(fit.data.keys()) == 23
        for k in expected.keys():
            if k == 'max_speed':
                assert fit.data[k] != expected[k]
                assert fit.data[k] == 18.666
            else:
                assert fit.data[k] == expected[k]

        # now, do the same for the avg speed
        values['enhanced_max_speed'] = 16.666
        values['enhanced_avg_speed'] = None
        fit.load()
        assert len(fit.data.keys()) == 23
        for k in expected.keys():
            if k == 'avg_speed':
                assert fit.data[k] != expected[k]
                assert fit.data[k] == 7.838
            else:
                assert fit.data[k] == expected[k]

    def test_name(self, fit):
        # without loading first, no data, so it blows up
        with pytest.raises(KeyError):
            fit.name
        fit.load()
        # the default fit file has both profile and sport
        assert fit.name == 'Synapse cycling'
        # remove profile
        fit.data['profile'] = None
        assert fit.name == 'cycling'
        # change sport
        fit.data['sport'] = 'running'
        assert fit.name == 'running'

    def test__calculate_avg_atemp(self, fit):
        # before loading data, we don't have any info about the average temp
        assert 'avg_atemp' not in fit.data.keys()
        # loaded data, fit file didn't have that info pre-calculated
        fit.load()
        assert fit.data['avg_atemp'] == 0
        # this loads the needed temperature data into fit.data + calls
        # _calculate_avg_atemp
        fit.gpx
        # now we have the needed info
        assert fit.data['avg_atemp'] == 2

    def test_gpx_without_load(self, fit):
        # without loading first, no data, so it blows up
        with pytest.raises(KeyError):
            fit.gpx

    def test_gpx_real_fit_file(self, fit):
        """
        Test the gpx generation code with a real fit file from a garmin device
        """
        fit.load()
        # open a pre-saved gpx file, the generated gpx file has to be like
        # this one
        gpx_path = self.get_fixture_path('20181230_101115.gpx')
        with open(gpx_path, 'r') as gpx_file:
            expected = gpx_file.read()
        assert fit.gpx == expected

    def test_gpx_extra_cases(self, fit, values):
        """
        Test the gpx generation code with some mocked data, so we can be sure
        all the code is executed and covered by tests
        """
        # first mock the FitFile object in the fit object
        session = Mock()
        session.get_values.return_value = values
        fit.obj = Mock()
        # mock get_messages, no matter what we ask for, return a single
        # session list, which fits for the purpose of this test
        fit.obj.get_messages.return_value = [session]
        fit.load()
        # after loading data, mock again get_messages, this time return the
        # list of messages we will loop over to generate the gpx object
        first_values = {
            'temperature': 18,
            'heart_rate': 90,
            'cadence': 40,
            'position_long': -104549248,
            'position_lat': 508158836,
            'enhanced_altitude': 196.79999999999995,
            'enhanced_speed': 5.432,
            'timestamp': datetime.now()
        }
        first_record = Mock()
        first_record.get_values.return_value = first_values
        second_values = {
            'temperature': 16,
            'heart_rate': 110,
            'cadence': 70,
            'position_long': -104532648,
            'position_lat': 508987836,
            'enhanced_altitude': 210.79999999999995,
            'enhanced_speed': 10.432,
            'timestamp': datetime.now()
        }
        second_record = Mock()
        second_record.get_values.return_value = second_values

        third_values = {
            'temperature': 7,
            'heart_rate': 140,
            'cadence': 90,
            'position_long': -104532876,
            'position_lat': 508987987,
            'enhanced_altitude': 250.79999999999995,
            'enhanced_speed': 9.432,
            'timestamp': datetime.now()
        }
        third_record = Mock()
        third_record.get_values.return_value = third_values

        # set an hr value of 0, which will trigger the code that sets
        # the minimum heart rate value from the last known value
        fourth_values = {
            'temperature': -2,
            'heart_rate': 0,
            'cadence': 0,
            'position_long': -104532876,
            'position_lat': 508987987,
            'enhanced_altitude': 250.79999999999995,
            'enhanced_speed': 9.432,
            'timestamp': datetime.now()
        }
        fourth_record = Mock()
        fourth_record.get_values.return_value = fourth_values

        records = [
            first_record,
            second_record,
            third_record,
            fourth_record,
        ]

        fit.obj.get_messages.return_value = records
        xml = fit.gpx

        # now, ensure the proper data is in the xml file
        #
        # no 0 hr value is in there
        assert '<gpxtpx:hr>0</gpxtpx:hr>' not in xml
        # but the previous value is twice
        assert xml.count('<gpxtpx:hr>140</gpxtpx:hr>') == 2

        # the other values appear once
        assert xml.count('<gpxtpx:hr>90</gpxtpx:hr>') == 1
        assert xml.count('<gpxtpx:hr>110</gpxtpx:hr>') == 1
        for v in [18, 16, 7, -2]:
            assert '<gpxtpx:atemp>' + str(v) + '</gpxtpx:atemp>' in xml
        for v in [40, 70, 90, 0]:
            assert '<gpxtpx:cad>' + str(v) + '</gpxtpx:cad>' in xml

        # the name provided by the fit object is there
        assert '<name>' + fit.name + '</name>' in xml
        # and we have 4 track points, no need to check the latitude/longitude
        # conversion, as that is covered in the previous test with a real fit
        # and gpx files test
        assert xml.count('<trkpt lat') == 4
