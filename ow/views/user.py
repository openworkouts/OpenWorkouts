import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from io import BytesIO

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.view import view_config
from pyramid.security import remember, forget
from pyramid.response import Response
from pyramid.i18n import TranslationStringFactory, get_localizer
from pyramid_simpleform import Form, State
from pytz import common_timezones
from PIL import Image

from ..models.user import User
from ..schemas.user import (
    UserProfileSchema,
    ChangePasswordSchema,
    SignUpSchema,
)
from ..models.root import OpenWorkouts
from ..views.renderers import OWFormRenderer
from ..utilities import (
    timedelta_to_hms,
    get_verification_token,
    get_gender_names,
    get_available_locale_names,
    get_month_names,
    get_week_day_names
)
from ..mail import send_verification_email

_ = TranslationStringFactory('OpenWorkouts')
month_name = get_month_names()
weekday_name = get_week_day_names()


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
    # messages is a dict of pre-defined messages we would need to show to the
    # user when coming back to the login page after certain actions
    messages = {
        'already-verified': _('User has been verified already'),
        'link-sent': _('Verification link sent, please check your inbox'),
        'max-tokens-sent': _(
            'We already sent you the verification link more than three times')
    }
    message = request.GET.get('message', '')
    if message:
        message = messages.get(message, '')
    email = request.GET.get('email', '')
    password = ''
    return_to = request.params.get('return_to')
    redirect_url = return_to or request.resource_url(request.root)
    # If the user still has to verify the account, this will be set to the
    # proper link to re-send the verification email
    resend_verify_link = None

    if 'submit' in request.POST:
        email = request.POST.get('email', None)
        user = context.get_user_by_email(email)
        if user:
            if user.verified:
                password = request.POST.get('password', None)
                if password is not None and user.check_password(password):
                    # look for the value of locale for this user, to set the
                    # LOCALE cookie, so the UI appears on the pre-selected lang
                    default_locale = request.registry.settings.get(
                        'pyramid.default_locale_name')
                    locale = getattr(user, 'locale', default_locale)
                    request.response.set_cookie('_LOCALE_', locale)
                    # log in the user and send back to the place he wanted to
                    # visit
                    headers = remember(request, str(user.uid))
                    request.response.headers.extend(headers)
                    redirect_url = return_to or request.resource_url(user)
                    return HTTPFound(location=redirect_url,
                                     headers=request.response.headers)
                else:
                    message = _('Wrong password')
            else:
                message = _('You have to verify your account first')
                resend_verify_link = request.resource_url(
                    user, 'resend-verification-link'
                )
        else:
            message = _('Wrong email address')

    return {
        'message': message,
        'email': email,
        'password': password,
        'redirect_url': redirect_url,
        'resend_verify_link': resend_verify_link
    }


@view_config(context=OpenWorkouts, name='logout')
def logout(context, request):
    request.response.delete_cookie('_LOCALE_')
    headers = forget(request)
    request.response.headers.extend(headers)
    return HTTPFound(location=request.resource_url(context),
                     headers=request.response.headers)


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
        user.verified = False
        user.verification_token = get_verification_token()
        context.add_user(user)
        # send a verification link to the user email address
        send_verification_email(request, user)
        user.verification_tokens_sent += 1
        # Send to login
        return HTTPFound(location=request.resource_url(context))

    return {
        'form': OWFormRenderer(form)
    }


@view_config(
    context=User,
    name="verify",
    renderer='ow:templates/verify.pt')
def verify(context, request):
    redirect_url = request.resource_url(context)

    # user has been verified already, send to dashboard
    if getattr(context, 'verified', False):
        return HTTPFound(location=redirect_url)

    # Look for a verification token, then check if we can verify the user with
    # that token
    verified = len(request.subpath) > 0
    token = getattr(context, 'verification_token', False)
    verified = verified and token and str(token) == request.subpath[0]
    if verified:
        # verified, log in automatically and send to the dashboard
        context.verified = True
        headers = remember(request, str(context.uid))
        return HTTPFound(location=redirect_url, headers=headers)

    # if we can not verify the user, show a page with some info about it
    return {}


@view_config(
    context=User,
    name="resend-verification-link")
def resend_verification_link(context, request):
    """
    Send an email with the verification link, only if the user has not
    been verified yet
    """
    # the message to be shown when the user gets back to the login page
    query = {'message': 'already-verified'}
    if not context.verified:
        tokens_sent = getattr(context, 'verification_tokens_sent', 0)
        if tokens_sent > 3:
            # we already sent the token 3 times, we don't send it anymore
            query = {'message': 'max-tokens-sent', 'email': context.email}
        else:
            if context.verification_token is None:
                # for some reason the verification token is not there, get one
                context.verification_token = get_verification_token()
            send_verification_email(request, context)
            context.verification_tokens_sent = tokens_sent + 1
            query = {'message': 'link-sent', 'email': context.email}
    # Send to login
    url = request.resource_url(request.root, 'login', query=query)
    return HTTPFound(location=url)


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
    context=OpenWorkouts,
    name='profile',
    permission='view',
    renderer='ow:templates/profile.pt')
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
    if isinstance(context, OpenWorkouts):
        nickname = request.subpath[0]
        user = request.root.get_user_by_nickname(nickname)
        if user is None:
            return HTTPNotFound()
    else:
        user = context
    now = datetime.now(timezone.utc)
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    week = request.GET.get('week', None)
    workouts = user.workouts(year, month, week)
    totals = {
        'distance': Decimal(0),
        'time': timedelta(0),
        'elevation': Decimal(0)
    }

    for workout in workouts:
        totals['distance'] += (
            getattr(workout, 'distance', Decimal(0)) or Decimal(0))
        totals['time'] += (
            getattr(workout, 'duration', timedelta(0)) or timedelta(0))
        totals['elevation'] += (
            getattr(workout, 'uphill', Decimal(0)) or Decimal(0))

    localizer = get_localizer(request)
    user_gender = _('Unknown')
    for g in get_gender_names():
        if g[0] == user.gender:
            user_gender = localizer.translate(g[1])

    # get some data to be shown in the "profile stats" totals column
    profile_stats = {
        'sports': user.activity_sports,
        'years': user.activity_years,
        'current_year': request.GET.get('stats_year', now.year),
        'current_sport': request.GET.get('stats_sport', user.favorite_sport),
    }

    return {
        'user': user,
        'user_gender': user_gender,
        'workouts': workouts,
        'current_month': '{year}-{month}'.format(
            year=str(year), month=str(month).zfill(2)),
        'current_week': week,
        'totals': totals,
        'profile_stats': profile_stats
    }


@view_config(
    context=User,
    name='picture',
    permission='view')
def profile_picture(context, request):
    if context.picture is None:
        return HTTPNotFound()

    size = request.GET.get('size', 0)
    # we will need a tuple, it does not matter if both values are the same,
    # Pillow will keep aspect ratio
    size = (int(size), int(size))

    image = Image.open(context.picture.open())

    if size > (0, 0) and size < image.size:
        # resize only if they are asking for smaller size, prevent
        # someone asking for a "too big" image
        image.thumbnail(size)

    body_file = BytesIO()
    image.save(body_file, format=image.format)
    return Response(content_type='image', body=body_file.getvalue())


@view_config(
    context=User,
    permission='edit',
    name='edit',
    renderer='ow:templates/edit_profile.pt')
def edit_profile(context, request):
    default_locale = request.registry.settings.get(
        'pyramid.default_locale_name')
    current_locale = request.cookies.get('_LOCALE_', default_locale)
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
        # set the cookie for the locale/lang
        request.response.set_cookie('_LOCALE_', form.data['locale'])
        current_locale = form.data['locale']
        # Saved, send the user to the public view of her profile
        return HTTPFound(location=request.resource_url(context, 'profile'),
                         headers=request.response.headers)

    # prevent crashes on the form
    if 'picture' in form.data:
        del form.data['picture']

    localizer = get_localizer(request)
    gender_names = [
        (g[0], localizer.translate(g[1])) for g in get_gender_names()]
    available_locale_names = [
        (l[0], localizer.translate(l[1])) for l in get_available_locale_names()
    ]

    return {'form': OWFormRenderer(form),
            'timezones': common_timezones,
            'gender_names': gender_names,
            'available_locale_names': available_locale_names,
            'current_locale': current_locale}


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
    localizer = get_localizer(request)
    stats = context.week_stats
    json_stats = []
    for day in stats:
        hms = timedelta_to_hms(stats[day]['time'])
        name = localizer.translate(weekday_name[day.weekday()])[:3]
        day_stats = {
            'name': name,
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
    name='month')
def month_stats(context, request):
    """
    For the given month, return a json-encoded stream containing
    per-day workouts information.
    """
    localizer = get_localizer(request)
    now = datetime.now(timezone.utc)
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    workouts = context.workouts(year, month)
    stats = {}

    for workout in workouts:
        start = workout.start.strftime('%Y-%m-%d')
        if start not in stats.keys():
            stats[start] = {
                'time': 0,  # seconds
                'distance': 0,  # kilometers
                'elevation': 0,  # meters
            }
        duration = getattr(workout, 'duration', None) or timedelta(0)
        stats[start]['time'] += duration.seconds
        distance = getattr(workout, 'distance', None) or 0
        stats[start]['distance'] += int(round(distance))
        elevation = getattr(workout, 'uphill', None) or 0
        stats[start]['elevation'] += int(elevation)

    json_stats = []
    for day in stats.keys():
        hms = timedelta_to_hms(timedelta(seconds=stats[day]['time']))
        hours_label = _('hour')
        if hms[0] > 1:
            hours_label = _('hours')
        time_formatted = ' '.join([
            str(hms[0]).zfill(2), localizer.translate(hours_label),
            str(hms[1]).zfill(2), localizer.translate(_('min.'))
        ])
        json_stats.append({
            'day': day,
            'time': stats[day]['time'],
            'time_formatted': time_formatted,
            'distance': stats[day]['distance'],
            'elevation': stats[day]['elevation']
        })

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
    localizer = get_localizer(request)
    stats = context.yearly_stats
    # this sets which month is 2 times in the stats, once this year, once
    # the previous year. We will show it a bit different in the UI (showing
    # the year too to prevent confusion)
    repeated_month = datetime.now(timezone.utc).date().month
    json_stats = []
    for month in stats:
        hms = timedelta_to_hms(stats[month]['time'])
        name = localizer.translate(month_name[month[1]])[:3]
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
                query={'year': str(month[0]), 'month': str(month[1])})
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
    localizer = get_localizer(request)
    stats = context.weekly_year_stats
    # this sets which month is 2 times in the stats, once this year, once
    # the previous year. We will show it a bit different in the UI (showing
    # the year too to prevent confusion)
    repeated_month = datetime.now(timezone.utc).date().month
    json_stats = []
    for week in stats:
        hms = timedelta_to_hms(stats[week]['time'])
        name = localizer.translate(month_name[week[1]])[:3]
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
                       'week': str(week[2])})
        }
        json_stats.append(week_stats)
    return Response(content_type='application/json',
                    charset='utf-8',
                    body=json.dumps(json_stats))
