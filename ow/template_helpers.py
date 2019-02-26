from pyramid.events import subscriber, BeforeRender
from pyramid.i18n import TranslationStringFactory, get_localizer

from ow.utilities import timedelta_to_hms

_ = TranslationStringFactory('OpenWorkouts')


@subscriber(BeforeRender)
def add_renderer_globals(event):  # pragma: no cover
    event['timedelta_to_hms'] = timedelta_to_hms
    event['_'] = _
    event['get_localizer'] = get_localizer
