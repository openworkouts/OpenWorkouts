import logging

from pyramid.view import (
    view_config,
    notfound_view_config,
    forbidden_view_config
)
from pyramid.httpexceptions import HTTPFound

log = logging.getLogger(__name__)


@notfound_view_config(renderer='ow:templates/404.pt')
def not_found(request):
    """
    This is the view that handles 404 (not found) http responses
    """
    request.response.status_int = 404
    return {
        'url': request.resource_url(request.root)
    }


@forbidden_view_config(renderer='ow:templates/403.pt')
def forbidden(request):
    """
    This is the actual view called for 403 (forbidden) http requests
    If the user is already logged in, show the 403 page, if not, send her
    to the login page
    """
    if request.authenticated_userid:
        request.response.status_int = 403
        return {
            'url': request.resource_url(request.root)
        }
    login_url = request.resource_url(
        request.root, 'login', query=dict(return_to=request.url))
    return HTTPFound(location=login_url)


@view_config(
    context=Exception,
    renderer='ow:templates/500.pt',
    permission='__no_permission_required__')
def exceptions(context, request):
    """
    This is the view that handles 500 (Internal Server Error) http responses
    The exceptions are logged to the log file before showing the error page
    """
    log.error("The error was: %s" % context, exc_info=(context))
    request.response.status_int = 500
    return {
        'url': request.resource_url(request.root)
    }
