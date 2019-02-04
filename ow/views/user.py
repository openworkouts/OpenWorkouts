import json
from calendar import month_name
from datetime import datetime, timezone

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.security import remember, forget
from pyramid.response import Response
from pyramid.i18n import TranslationStringFactory
from pyramid_simpleform import Form, State
from pytz import common_timezones

from ..models.user import User
from ..schemas.user import (
    UserProfileSchema,
    ChangePasswordSchema,
    SignUpSchema,
)
from ..models.root import OpenWorkouts
from ..views.renderers import OWFormRenderer
from ..utilities import timedelta_to_hms

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
def recover_password(context, request):  # pragma: no cover
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
    # Look at the year we are viewing, if none is passed in the request,
    # pick up the latest/newer available with activity
    viewing_year = request.GET.get('year', None)
    if viewing_year is None:
        available_years = context.activity_years
        if available_years:
            viewing_year = available_years[0]
    else:
        # ensure this is an integer
        viewing_year = int(viewing_year)

    # Same for the month, if there is a year set
    viewing_month = None
    if viewing_year:
        viewing_month = request.GET.get('month', None)
        if viewing_month is None:
            available_months = context.activity_months(viewing_year)
            if available_months:
                # we pick up the latest month available for the year,
                # which means the current month in the current year
                viewing_month = available_months[-1]
        else:
            # ensure this is an integer
            viewing_month = int(viewing_month)

    # pick up the workouts to be shown in the dashboard
    workouts = context.workouts(viewing_year, viewing_month)

    return {
        'current_year': datetime.now(timezone.utc).year,
        'current_day_name': datetime.now(timezone.utc).strftime('%a'),
        'month_name': month_name,
        'viewing_year': viewing_year,
        'viewing_month': viewing_month,
        'workouts': workouts
    }


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
    now = datetime.now(timezone.utc)
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    week = request.GET.get('week', None)
    return {
        'workouts': context.workouts(year, month, week),
        'current_month': '{year}-{month}'.format(
            year=str(year), month=str(month).zfill(2)),
        'current_week': week
    }


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
    # if not given a file there is an empty byte in POST, which breaks
    # our blob storage validator.
    # dirty fix until formencode fixes its api.is_empty method
    if isinstance(request.POST.get('picture', None), bytes):
        request.POST['picture'] = ''

    nicknames = request.root.lowercase_nicknames
    if context.nickname:
        # remove the current user nickname from the list, preventing form
        # validation error
        nicknames.remove(context.nickname.lower())
    state = State(emails=request.root.lowercase_emails, names=nicknames)
    form = Form(request, schema=UserProfileSchema(), state=state, obj=context)

    if 'submit' in request.POST and form.validate():
        # No picture? do not override it
        if not form.data['picture']:
            del form.data['picture']
        form.bind(context)
        # reindex
        request.root.reindex(context)
        # Saved, send the user to the public view of her profile
        return HTTPFound(location=request.resource_url(context, 'profile'))

    # prevent crashes on the form
    if 'picture' in form.data:
        del form.data['picture']

    return {'form': OWFormRenderer(form),
            'timezones': common_timezones}


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


@view_config(
    context=User,
    permission='view',
    name='week')
def week_stats(context, request):
    stats = context.week_stats
    json_stats = []
    for day in stats:
        hms = timedelta_to_hms(stats[day]['time'])
        day_stats = {
            'name': day.strftime('%a'),
            'time': str(hms[0]).zfill(2),
            'distance': int(round(stats[day]['distance'])),
            'elevation': int(stats[day]['elevation']),
            'workouts': stats[day]['workouts']
        }
        json_stats.append(day_stats)
    return Response(content_type='application/json',
                    charset='utf-8',
                    body=json.dumps(json_stats))


@view_config(
    context=User,
    permission='view',
    name='monthly')
def last_months_stats(context, request):
    """
    Return a json-encoded stream with statistics for the last 12 months
    """
    stats = context.yearly_stats
    # this sets which month is 2 times in the stats, once this year, once
    # the previous year. We will show it a bit different in the UI (showing
    # the year too to prevent confusion)
    repeated_month = datetime.now(timezone.utc).date().month
    json_stats = []
    for month in stats:
        hms = timedelta_to_hms(stats[month]['time'])
        name = month_name[month[1]][:3]
        if month[1] == repeated_month:
            name += ' ' + str(month[0])
        month_stats = {
            'id': str(month[0]) + '-' + str(month[1]).zfill(2),
            'name': name,
            'time': str(hms[0]).zfill(2),
            'distance': int(round(stats[month]['distance'])),
            'elevation': int(stats[month]['elevation']),
            'workouts': stats[month]['workouts'],
            'url': request.resource_url(
                context, 'profile',
                query={'year': str(month[0]), 'month': str(month[1])},
                anchor='workouts')
        }
        json_stats.append(month_stats)
    return Response(content_type='application/json',
                    charset='utf-8',
                    body=json.dumps(json_stats))


@view_config(
    context=User,
    permission='view',
    name='weekly')
def last_weeks_stats(context, request):
    """
    Return a json-encoded stream with statistics for the last 12-months, but
    in a per-week basis
    """
    stats = context.weekly_year_stats
    # this sets which month is 2 times in the stats, once this year, once
    # the previous year. We will show it a bit different in the UI (showing
    # the year too to prevent confusion)
    repeated_month = datetime.now(timezone.utc).date().month
    json_stats = []
    for week in stats:
        hms = timedelta_to_hms(stats[week]['time'])
        name = month_name[week[1]][:3]
        if week[1] == repeated_month:
            name += ' ' + str(week[0])
        week_stats = {
            'id': '-'.join(
                [str(week[0]), str(week[1]).zfill(2), str(week[2])]),
            'week': str(week[3]),  # the number of week in the current month
            'name': name,
            'time': str(hms[0]).zfill(2),
            'distance': int(round(stats[week]['distance'])),
            'elevation': int(stats[week]['elevation']),
            'workouts': stats[week]['workouts'],
            'url': request.resource_url(
                context, 'profile',
                query={'year': str(week[0]),
                       'month': str(week[1]),
                       'week': str(week[2])},
                anchor='workouts')
        }
        json_stats.append(week_stats)
    return Response(content_type='application/json',
                    charset='utf-8',
                    body=json.dumps(json_stats))
