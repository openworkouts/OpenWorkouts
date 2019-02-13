from pyramid.config import Configurator
from pyramid_zodbconn import get_connection
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.session import SignedCookieSessionFactory

from .models import appmaker
from .security import groupfinder


def root_factory(request):  # pragma: no cover
    conn = get_connection(request)
    return appmaker(conn.root())


def main(global_config, **settings):  # pragma: no cover
    """
    This function returns a Pyramid WSGI application.
    """
    session_factory = SignedCookieSessionFactory(
        secret=settings['session.secret'],
        cookie_name='ow-session')

    authn_policy = AuthTktAuthenticationPolicy(
        secret=settings['auth.secret'],
        callback=groupfinder,
        hashalg='sha512')

    authz_policy = ACLAuthorizationPolicy()

    config = Configurator(root_factory=root_factory, settings=settings)
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.set_session_factory(session_factory)
    config.include('pyramid_chameleon')
    config.include('pyramid_tm')
    config.include('pyramid_retry')
    config.include('pyramid_zodbconn')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_translation_dirs(
        'ow:locale',
        'formencode:i18n')
    config.scan()
    return config.make_wsgi_app()
