from pyramid.events import subscriber, BeforeRender

from ow.utilities import timedelta_to_hms


@subscriber(BeforeRender)
def add_renderer_globals(event):  # pragma: no cover
    event['timedelta_to_hms'] = timedelta_to_hms
