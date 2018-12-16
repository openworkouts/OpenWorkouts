from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.security import remember, forget
from pyramid.response import Response
from pyramid.i18n import TranslationStringFactory
from pyramid_simpleform import Form, State

from ..models.user import User
from ..schemas.user import (
    UserProfileSchema,
    ChangePasswordSchema,
    SignUpSchema,
)
from ..models.root import OpenWorkouts
from ..views.renderers import OWFormRenderer

_ = TranslationStringFactory('OpenWorkouts')


@view_config(context=OpenWorkouts)
def dashboard_redirect(context, request):
    """
    Send the user to his dashboard when accesing the root object,
    send to the login page if the user is not logged in.
    """
    if request.authenticated_userid:
        user = request.root.get_user_by_uid(request.authenticated_userid)
        if user:
            return HTTPFound(location=request.resource_url(user))
        else:
            # an authenticated user session, for an user that does not exist
            # anymore, logout!
            return HTTPFound(location=request.resource_url(context, 'logout'))
    return HTTPFound(location=request.resource_url(context, 'login'))


@view_config(
    context=OpenWorkouts,
    name='login',
    renderer='ow:templates/login.pt')
def login(context, request):
    message = ''
    email = ''
    password = ''
    return_to = request.params.get('return_to')
    redirect_url = return_to or request.resource_url(request.root)

    if 'submit' in request.POST:
        email = request.POST.get('email', None)
        user = context.get_user_by_email(email)
        if user:
            password = request.POST.get('password', None)
            if password is not None and user.check_password(password):
                headers = remember(request, str(user.uid))
                redirect_url = return_to or request.resource_url(user)
                return HTTPFound(location=redirect_url, headers=headers)
            else:
                message = _('Wrong password')
        else:
            message = _('Wrong email address')

    return {
        'message': message,
        'email': email,
        'password': password,
        'redirect_url': redirect_url
    }


@view_config(context=OpenWorkouts, name='logout')
def logout(context, request):
    headers = forget(request)
    return HTTPFound(location=request.resource_url(context), headers=headers)


@view_config(
    context=OpenWorkouts,
    name='signup',
    renderer='ow:templates/signup.pt')
def signup(context, request):
    state = State(emails=context.lowercase_emails,
                  names=context.lowercase_nicknames)
    form = Form(request, schema=SignUpSchema(), state=state)

    if 'submit' in request.POST and form.validate():
        user = form.bind(User(), exclude=['password_confirm'])
        context.add_user(user)
        # Send to login
        return HTTPFound(location=request.resource_url(context))

    return {
        'form': OWFormRenderer(form)
    }


@view_config(
    context=OpenWorkouts,
    name='forgot-password',
    renderer='ow:templates/forgot_password.pt')
def recover_password(context, request):
    # WIP
    Form(request)


@view_config(
    context=User,
    permission='view',
    renderer='ow:templates/dashboard.pt')
def dashboard(context, request):
    """
    Render a dashboard for the current user
    """
    # Add here some logic
    return {}


@view_config(
    context=User,
    permission='view',
    name='profile',
    renderer='ow:templates/profile.pt')
def profile(context, request):
    """
    "public" profile view, showing some workouts from this user, her
    basic info, stats, etc
    """
    return {}


@view_config(
    context=User,
    name='picture',
    permission='view')
def profile_picture(context, request):
    return Response(
        content_type='image',
        body_file=context.picture.open())


@view_config(
    context=User,
    permission='edit',
    name='edit',
    renderer='ow:templates/edit_profile.pt')
def edit_profile(context, request):
    form = Form(request, schema=UserProfileSchema(), obj=context)
    if 'submit' in request.POST and form.validate():
        # No picture? do not override it
        if not form.data['picture']:
            del form.data['picture']
        form.bind(context)
        # Saved, send the user to the public view of her profile
        return HTTPFound(location=request.resource_url(context, 'profile'))
    # prevent crashes on the form
    if 'picture' in form.data:
        del form.data['picture']
    return {'form': OWFormRenderer(form)}


@view_config(
    context=User,
    permission='edit',
    name='passwd',
    renderer='ow:templates/change_password.pt')
def change_password(context, request):
    form = Form(request, schema=ChangePasswordSchema(),
                state=State(user=context))
    if 'submit' in request.POST and form.validate():
        context.password = form.data['password']
        return HTTPFound(location=request.resource_url(context, 'profile'))
    return {'form': OWFormRenderer(form)}
