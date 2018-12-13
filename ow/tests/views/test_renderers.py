
from datetime import date, datetime, timezone

import pytest
from pyramid.testing import DummyRequest
from pyramid_simpleform import Form

from ow.views.renderers import OWFormRenderer


class TestOWFormRenderer(object):

    @pytest.fixture
    def req(self):
        request = DummyRequest()
        return request

    @pytest.fixture
    def form(self, req):
        form = Form(req)
        return form

    @pytest.fixture
    def renderer(self, form):
        renderer = OWFormRenderer(form)
        return renderer

    def test_date(self, renderer):
        html = renderer.date('current_date')
        match = u'<input id="current_date" name="current_date" type="text" />'
        assert html == match

    def test_date_with_value(self, renderer):
        html = renderer.date('current_date', value=date(2016, 3, 17))
        match = u'<input id="current_date" name="current_date" type="text"'
        match += u' value="2016-03-17" />'
        assert html == match
        html = renderer.date(
            'current_date', value=datetime(2016, 3, 17, tzinfo=timezone.utc))
        match = u'<input id="current_date" name="current_date" type="text"'
        match += u' value="2016-03-17 00:00:00+00:00" />'
        assert html == match

    def test_date_with_format(self, renderer):
        html = renderer.date('current_date', value=date(2016, 3, 17),
                             date_format='%d/%m/%Y')
        match = u'<input id="current_date" name="current_date" type="text"'
        match += u' value="17/03/2016" />'
        assert html == match
        html = renderer.date(
            'current_date', value=datetime(2016, 3, 17, tzinfo=timezone.utc),
            date_format='%d/%m/%Y')
        assert html == match
