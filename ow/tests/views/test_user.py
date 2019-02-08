import os
import json
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from shutil import copyfileobj
from unittest.mock import Mock, patch

import pytest

from ZODB.blob import Blob

from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response

from webob.multidict import MultiDict

from ow.models.root import OpenWorkouts
from ow.models.user import User
from ow.models.workout import Workout
from ow.views.renderers import OWFormRenderer
import ow.views.user as user_views


class TestUserViews(object):

    @pytest.fixture
    def john(self):
        user = User(firstname='John', lastname='Doe',
                    email='john.doe@example.net')
        user.password = 's3cr3t'
        return user

    @pytest.fixture
    def root(self, john):
        root = OpenWorkouts()
        root.add_user(john)
        workout = Workout(
            start=datetime(2015, 6, 28, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=30
        )
        john.add_workout(workout)
        return root

    @pytest.fixture
    def dummy_request(self, root):
        request = DummyRequest()
        request.root = root
        return request

    @pytest.fixture
    def profile_post_request(self, root, john):
        """
        This is a valid POST request to update an user profile.
        Form will validate, but nothing will be really updated/changed.
        """
        user = john
        request = DummyRequest()
        request.root = root
        request.method = 'POST'
        request.POST = MultiDict({
            'submit': True,
            'firstname': user.firstname,
            'lastname': user.lastname,
            'email': user.email,
            'bio': user.bio,
            'weight': user.weight,
            'height': user.height,
            'gender': user.gender,
            'birth_date': user.birth_date,
            'picture': user.picture,
            })
        return request

    @pytest.fixture
    def passwd_post_request(self, root):
        """
        This is a valid POST request to change the user password, but
        the form will not validate (empty fields)
        """
        request = DummyRequest()
        request.root = root
        request.method = 'POST'
        request.POST = MultiDict({
            'submit': True,
            'old_password': '',
            'password': '',
            'password_confirm': ''
            })
        return request

    @pytest.fixture
    def signup_post_request(self, root):
        """
        This is a valid POST request to signup a new user.
        """
        request = DummyRequest()
        request.root = root
        request.method = 'POST'
        request.POST = MultiDict({
            'submit': True,
            'nickname': 'JackBlack',
            'email': 'jack.black@example.net',
            'firstname': 'Jack',
            'lastname': 'Black',
            'password': 'j4ck s3cr3t',
            'password_confirm': 'j4ck s3cr3t'
            })
        return request

    def test_dashboard_redirect_unauthenticated(self, root):
        """
        Anoymous access to the root object, send the user to the login page.

        Instead of reusing the DummyRequest from the request fixture, we do
        Mock fully the request here, because we need to use
        authenticated_userid, which cannot be easily set in the DummyRequest
        """
        request = DummyRequest()
        request.root = root
        response = user_views.dashboard_redirect(root, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(root, 'login')

    def test_dashboard_redirect_authenticated(self, root, john):
        """
        Authenticated user accesing the root object, send the user to her
        dashboard

        Instead of reusing the DummyRequest from the request fixture, we do
        Mock fully the request here, because we need to use
        authenticated_userid, which cannot be easily set in the DummyRequest
        """
        alt_request = DummyRequest()
        request = Mock()
        request.root = root
        request.authenticated_userid = str(john.uid)
        request.resource_url = alt_request.resource_url
        response = user_views.dashboard_redirect(root, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(john)
        # if authenticated_userid is the id of an user that does not exist
        # anymore, we send the user to the logout page
        request.authenticated_userid = 'faked-uid'
        response = user_views.dashboard_redirect(root, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(root, 'logout')

    def test_dashboard(self, dummy_request, john):
        """
        Renders the user dashboard
        """
        request = dummy_request
        response = user_views.dashboard(john, request)
        assert len(response) == 6
        assert 'month_name' in response.keys()
        assert response['current_year'] == datetime.now().year
        assert response['current_day_name'] == datetime.now().strftime('%a')
        # this user has a single workout, in 2015
        assert response['viewing_year'] == 2015
        assert response['viewing_month'] == 6
        assert response['workouts'] == [w for w in john.workouts()]

    def test_dashboard_year(self, dummy_request, john):
        """
        Renders the user dashboard for a chosen year.
        """
        request = dummy_request
        # first test the year for which we know there is a workout
        request.GET['year'] = 2015
        response = user_views.dashboard(john, request)
        assert len(response) == 6
        assert 'month_name' in response.keys()
        assert response['current_year'] == datetime.now().year
        assert response['current_day_name'] == datetime.now().strftime('%a')
        # this user has a single workout, in 2015
        assert response['viewing_year'] == 2015
        assert response['viewing_month'] == 6
        assert response['workouts'] == [w for w in john.workouts()]
        # now, a year we know there is no workout info
        request.GET['year'] = 2000
        response = user_views.dashboard(john, request)
        assert len(response) == 6
        assert 'month_name' in response.keys()
        assert response['current_year'] == datetime.now().year
        assert response['current_day_name'] == datetime.now().strftime('%a')
        # this user has a single workout, in 2015
        assert response['viewing_year'] == 2000
        # we have no data for that year and we didn't ask for a certain month,
        # so the passing value for that is None
        assert response['viewing_month'] is None
        assert response['workouts'] == []

    def test_dashboard_year_month(self, dummy_request, john):
        """
        Renders the user dashboard for a chosen year and month.
        """
        request = dummy_request
        # first test the year/month for which we know there is a workout
        request.GET['year'] = 2015
        request.GET['month'] = 6
        response = user_views.dashboard(john, request)
        assert len(response) == 6
        assert 'month_name' in response.keys()
        assert response['current_year'] == datetime.now().year
        assert response['current_day_name'] == datetime.now().strftime('%a')
        # this user has a single workout, in 2015
        assert response['viewing_year'] == 2015
        assert response['viewing_month'] == 6
        assert response['workouts'] == [w for w in john.workouts()]
        # now, change month to one without values
        request.GET['month'] = 2
        response = user_views.dashboard(john, request)
        assert len(response) == 6
        assert 'month_name' in response.keys()
        assert response['current_year'] == datetime.now().year
        assert response['current_day_name'] == datetime.now().strftime('%a')
        # this user has a single workout, in 2015
        assert response['viewing_year'] == 2015
        assert response['viewing_month'] == 2
        assert response['workouts'] == []
        # now the month with data, but in a different year
        request.GET['year'] = 2010
        request.GET['month'] = 6
        response = user_views.dashboard(john, request)
        assert len(response) == 6
        assert 'month_name' in response.keys()
        assert response['current_year'] == datetime.now().year
        assert response['current_day_name'] == datetime.now().strftime('%a')
        # this user has a single workout, in 2015
        assert response['viewing_year'] == 2010
        assert response['viewing_month'] == 6
        assert response['workouts'] == []

    def test_dashboard_month(self, dummy_request, john):
        """
        Passing a month without a year when rendering the dashboard. The last
        year for which workout data is available is assumed
        """
        request = dummy_request
        # Set a month without workout data
        request.GET['month'] = 5
        response = user_views.dashboard(john, request)
        assert len(response) == 6
        assert 'month_name' in response.keys()
        assert response['current_year'] == datetime.now().year
        assert response['current_day_name'] == datetime.now().strftime('%a')
        # this user has a single workout, in 2015
        assert response['viewing_year'] == 2015
        assert response['viewing_month'] == 5
        assert response['workouts'] == []
        # now a month with data
        request.GET['month'] = 6
        response = user_views.dashboard(john, request)
        assert len(response) == 6
        assert 'month_name' in response.keys()
        assert response['current_year'] == datetime.now().year
        assert response['current_day_name'] == datetime.now().strftime('%a')
        # this user has a single workout, in 2015
        assert response['viewing_year'] == 2015
        assert response['viewing_month'] == 6
        assert response['workouts'] == [w for w in john.workouts()]

    def test_profile(self, dummy_request, john):
        """
        Renders the user profile page
        """
        request = dummy_request
        # profile page for the current day (no workouts avalable)
        response = user_views.profile(john, request)
        assert len(response.keys()) == 4
        current_month = datetime.now(timezone.utc).strftime('%Y-%m')
        assert response['current_month'] == current_month
        assert response['current_week'] is None
        assert response['workouts'] == []
        assert response['totals'] == {
            'distance': Decimal(0),
            'time': timedelta(0),
            'elevation': Decimal(0)
        }
        # profile page for a previous date, that has workouts
        request.GET['year'] = 2015
        request.GET['month'] = 6
        response = user_views.profile(john, request)
        assert len(response.keys()) == 4
        assert response['current_month'] == '2015-06'
        assert response['current_week'] is None
        workouts = john.workouts(2015, 6)
        assert response['workouts'] == workouts
        assert response['totals'] == {
            'distance': workouts[0].distance,
            'time': workouts[0].duration,
            'elevation': Decimal(0)
        }
        # same, passing a week, first on a week without workouts
        request.GET['year'] = 2015
        request.GET['month'] = 6
        request.GET['week'] = 25
        response = user_views.profile(john, request)
        assert len(response.keys()) == 4
        assert response['current_month'] == '2015-06'
        assert response['current_week'] == 25
        assert response['workouts'] == []
        assert response['totals'] == {
            'distance': Decimal(0),
            'time': timedelta(0),
            'elevation': Decimal(0)
        }
        # now in a week with workouts
        request.GET['year'] = 2015
        request.GET['month'] = 6
        request.GET['week'] = 26
        response = user_views.profile(john, request)
        assert len(response.keys()) == 4
        assert response['current_month'] == '2015-06'
        assert response['current_week'] == 26
        workouts = john.workouts(2015, 6)
        assert response['workouts'] == workouts
        assert response['totals'] == {
            'distance': workouts[0].distance,
            'time': workouts[0].duration,
            'elevation': Decimal(0)
        }

    def test_login_get(self, dummy_request):
        """
        GET request to access the login page
        """
        request = dummy_request
        response = user_views.login(request.root, request)
        assert response['message'] == ''
        assert response['email'] == ''
        assert response['password'] == ''
        assert response['redirect_url'] == request.resource_url(request.root)

    def test_login_get_return_to(self, dummy_request, john):
        """
        GET request to access the login page, if there is a page set to where
        the user should be sent to, the response "redirect_url" key will have
        such url
        """
        request = dummy_request
        workout = john.workouts()[0]
        workout_url = request.resource_url(workout)
        request.params['return_to'] = workout_url
        response = user_views.login(request.root, request)
        assert response['redirect_url'] == workout_url

    def test_login_post_wrong_email(self, dummy_request):
        request = dummy_request
        request.method = 'POST'
        request.POST['submit'] = True
        request.POST['email'] = 'jack@example.net'
        response = user_views.login(request.root, request)
        assert response['message'] == u'Wrong email address'

    def test_login_post_wrong_password(self, dummy_request):
        request = dummy_request
        request.method = 'POST'
        request.POST['submit'] = True
        request.POST['email'] = 'john.doe@example.net'
        request.POST['password'] = 'badpassword'
        response = user_views.login(request.root, request)
        assert response['message'] == u'Wrong password'

    @patch('ow.views.user.remember')
    def test_login_post_ok(self, rem, dummy_request, john):
        request = dummy_request
        request.method = 'POST'
        request.POST['submit'] = True
        request.POST['email'] = 'john.doe@example.net'
        request.POST['password'] = 's3cr3t'
        response = user_views.login(request.root, request)
        assert isinstance(response, HTTPFound)
        assert rem.called
        assert response.location == request.resource_url(john)

    @patch('ow.views.user.forget')
    def test_logout(self, forg, dummy_request):
        request = dummy_request
        response = user_views.logout(request.root, request)
        assert isinstance(response, HTTPFound)
        assert forg.called
        assert response.location == request.resource_url(request.root)

    extensions = ('png', 'jpg', 'jpeg', 'gif')

    @pytest.mark.parametrize('extension', extensions)
    def test_profile_picture(self, extension, dummy_request, john):
        """
        GET request to get the profile picture of an user.
        """
        request = dummy_request
        # Get the user
        user = john
        # Get the path to the image, then open it and copy it to a new Blob
        # object
        path = 'fixtures/image.' + extension
        image_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), path)
        blob = Blob()
        with open(image_path, 'rb') as infile, blob.open('w') as out:
            infile.seek(0)
            copyfileobj(infile, out)

        # Set the blob with the picture
        user.picture = blob

        # Call the profile_picture view
        response = user_views.profile_picture(user, request)
        assert isinstance(response, Response)
        assert response.status_int == 200
        assert response.content_type == 'image'

    def test_edit_profile_get(self, dummy_request, john):
        """
        GET request to the edit profile page, returns the form ready to
        be rendered
        """
        request = dummy_request
        user = john
        response = user_views.edit_profile(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        # no errors in the form (first load)
        assert response['form'].errorlist() == ''
        # the form carries along the proper data keys, taken from the
        # loaded user profile
        data = ['firstname', 'lastname', 'email', 'nickname', 'bio',
                'birth_date', 'height', 'weight', 'gender', 'timezone']
        assert list(response['form'].data.keys()) == data
        # and check the email to see data is properly loaded
        assert response['form'].data['email'] == 'john.doe@example.net'

    def test_edit_profile_post_ok(self, profile_post_request, john):
        request = profile_post_request
        user = john
        # Update the bio field
        bio = 'Some text about this user'
        request.POST['bio'] = bio
        response = user_views.edit_profile(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'profile')
        assert user.bio == bio

    def test_edit_profile_post_missing_required(
            self, profile_post_request, john):
        request = profile_post_request
        request.POST['email'] = ''
        user = john
        response = user_views.edit_profile(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        # error on the missing email field
        error = u'Please enter an email address'
        html_error = u'<ul class="error"><li>' + error + '</li></ul>'
        assert response['form'].errorlist() == html_error
        assert response['form'].errors_for('email') == [error]

    def test_edit_profile_post_ok_picture_empty_bytes(
            self, profile_post_request, john):
        """
        POST request with an empty picture, the content of
        request['POST'].picture is a empty bytes string (b'') which triggers
        a bug in formencode, we put a fix in place, test that
        (more in ow.user.views.edit_profile)
        """
        # for the purposes of this test, we can mock the picture
        picture = Mock()
        john.picture = picture
        request = profile_post_request
        user = john
        # Mimic what happens when a picture is not provided by the user
        request.POST['picture'] = b''
        response = user_views.edit_profile(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'profile')
        assert user.picture == picture

    def test_edit_profile_post_ok_missing_picture(
            self, profile_post_request, john):
        """
        POST request without picture
        """
        # for the purposes of this test, we can mock the picture
        picture = Mock()
        john.picture = picture
        request = profile_post_request
        user = john
        # No pic is provided in the request POST values
        del request.POST['picture']
        response = user_views.edit_profile(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'profile')
        assert user.picture == picture

    def test_edit_profile_post_ok_nickname(self, profile_post_request, john):
        """
        User with a nickname set saves profile without changing the profile,
        we have to be sure there are no "nickname already in use" errors
        """
        request = profile_post_request
        user = john
        user.nickname = 'mr_jones'
        # add the nickname, the default post request has not a nickname set
        request.POST['nickname'] = 'mr_jones'
        response = user_views.edit_profile(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'profile')

    def test_change_password_get(self, dummy_request, john):
        request = dummy_request
        user = john
        response = user_views.change_password(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        # no errors in the form (first load)
        assert response['form'].errorlist() == ''

    def test_change_password_post_ok(self, passwd_post_request, john):
        request = passwd_post_request
        user = john
        request.POST['old_password'] = 's3cr3t'
        request.POST['password'] = 'h1dd3n s3cr3t'
        request.POST['password_confirm'] = 'h1dd3n s3cr3t'
        response = user_views.change_password(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'profile')
        # password was changed
        assert not user.check_password('s3cr3t')
        assert user.check_password('h1dd3n s3cr3t')

    def test_change_password_post_no_values(self, passwd_post_request, john):
        request = passwd_post_request
        user = john
        response = user_views.change_password(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        error = u'Please enter a value'
        html_error = u'<ul class="error">'
        html_error += ('<li>' + error + '</li>') * 3  # 3 fields
        html_error += '</ul>'
        errorlist = response['form'].errorlist().replace('\n', '')
        assert errorlist == html_error
        assert response['form'].errors_for('old_password') == [error]
        assert response['form'].errors_for('password') == [error]
        assert response['form'].errors_for('password_confirm') == [error]
        # password was not changed
        assert user.check_password('s3cr3t')

    def test_change_password_post_bad_old_password(
            self, passwd_post_request, john):
        request = passwd_post_request
        user = john
        request.POST['old_password'] = 'FAIL PASSWORD'
        request.POST['password'] = 'h1dd3n s3cr3t'
        request.POST['password_confirm'] = 'h1dd3n s3cr3t'
        response = user_views.change_password(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        error = u'The given password does not match the existing one '
        html_error = u'<ul class="error"><li>' + error + '</li></ul>'
        assert response['form'].errorlist() == html_error
        assert response['form'].errors_for('old_password') == [error]
        # password was not changed
        assert user.check_password('s3cr3t')
        assert not user.check_password('h1dd3n s3cr3t')

    def test_change_password_post_password_mismatch(
            self, passwd_post_request, john):
        request = passwd_post_request
        user = john
        request.POST['old_password'] = 's3cr3t'
        request.POST['password'] = 'h1dd3n s3cr3ts'
        request.POST['password_confirm'] = 'h1dd3n s3cr3t'
        response = user_views.change_password(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        error = u'Fields do not match'
        html_error = u'<ul class="error"><li>' + error + '</li></ul>'
        assert response['form'].errorlist() == html_error
        assert response['form'].errors_for('password_confirm') == [error]
        # password was not changed
        assert user.check_password('s3cr3t')
        assert not user.check_password('h1dd3n s3cr3t')

    def test_signup_get(self, dummy_request):
        request = dummy_request
        response = user_views.signup(request.root, request)
        assert isinstance(response['form'], OWFormRenderer)
        # no errors in the form (first load)
        assert response['form'].errorlist() == ''

    def test_signup_post_ok(self, signup_post_request):
        request = signup_post_request
        assert 'jack.black@example.net' not in request.root.emails
        assert 'JackBlack' not in request.root.all_nicknames
        response = user_views.signup(request.root, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(request.root)
        assert 'jack.black@example.net' in request.root.emails
        assert 'JackBlack' in request.root.all_nicknames

    def test_signup_missing_required(self, signup_post_request):
        request = signup_post_request
        request.POST['email'] = ''
        assert 'jack.black@example.net' not in request.root.emails
        assert 'JackBlack' not in request.root.all_nicknames
        response = user_views.signup(request.root, request)
        assert isinstance(response['form'], OWFormRenderer)
        error = u'Please enter an email address'
        html_error = '<ul class="error">'
        html_error += '<li>' + error + '</li>'
        html_error += '</ul>'
        errorlist = response['form'].errorlist().replace('\n', '')
        assert errorlist == html_error
        assert response['form'].errors_for('email') == [error]
        assert 'jack.black@example.net' not in request.root.emails
        assert 'JackBlack' not in request.root.all_nicknames

    def test_signup_existing_nickname(self, signup_post_request, john):
        request = signup_post_request
        # assign john a nickname first
        john.nickname = 'john'
        # now set it for the POST request
        request.POST['nickname'] = 'john'
        # check jack is not there yet
        assert 'jack.black@example.net' not in request.root.emails
        assert 'JackBlack' not in request.root.all_nicknames
        # now signup as jack, but trying to set the nickname 'john'
        response = user_views.signup(request.root, request)
        assert isinstance(response['form'], OWFormRenderer)
        error = u'Another user is already using the nickname john'
        html_error = '<ul class="error">'
        html_error += '<li>' + error + '</li>'
        html_error += '</ul>'
        errorlist = response['form'].errorlist().replace('\n', '')
        assert errorlist == html_error
        assert response['form'].errors_for('nickname') == [error]
        # all the errors, and jack is not there
        assert 'jack.black@example.net' not in request.root.emails
        assert 'JackBlack' not in request.root.all_nicknames

    def test_signup_existing_email(self, signup_post_request):
        request = signup_post_request
        request.POST['email'] = 'john.doe@example.net'
        assert 'jack.black@example.net' not in request.root.emails
        assert 'JackBlack' not in request.root.all_nicknames
        response = user_views.signup(request.root, request)
        assert isinstance(response['form'], OWFormRenderer)
        error = u'Another user is already registered with the email '
        error += u'john.doe@example.net'
        html_error = '<ul class="error">'
        html_error += '<li>' + error + '</li>'
        html_error += '</ul>'
        errorlist = response['form'].errorlist().replace('\n', '')
        assert errorlist == html_error
        assert response['form'].errors_for('email') == [error]
        assert 'jack.black@example.net' not in request.root.emails
        assert 'JackBlack' not in request.root.all_nicknames

    def test_week_stats_no_stats(self, dummy_request, john):
        response = user_views.week_stats(john, dummy_request)
        assert isinstance(response, Response)
        assert response.content_type == 'application/json'
        # the body is a valid json-encoded stream
        obj = json.loads(response.body)
        assert obj == [
            {'distance': 0, 'elevation': 0, 'name': 'Mon',
             'time': '00', 'workouts': 0},
            {'distance': 0, 'elevation': 0, 'name': 'Tue',
             'time': '00', 'workouts': 0},
            {'distance': 0, 'elevation': 0, 'name': 'Wed',
             'time': '00', 'workouts': 0},
            {'distance': 0, 'elevation': 0, 'name': 'Thu',
             'time': '00', 'workouts': 0},
            {'distance': 0, 'elevation': 0, 'name': 'Fri',
             'time': '00', 'workouts': 0},
            {'distance': 0, 'elevation': 0, 'name': 'Sat',
             'time': '00', 'workouts': 0},
            {'distance': 0, 'elevation': 0, 'name': 'Sun',
             'time': '00', 'workouts': 0}
        ]

    def test_week_stats(self, dummy_request, john):
        workout = Workout(
            start=datetime.now(timezone.utc),
            duration=timedelta(minutes=60),
            distance=30,
            elevation=540
        )
        john.add_workout(workout)
        response = user_views.week_stats(john, dummy_request)
        assert isinstance(response, Response)
        assert response.content_type == 'application/json'
        # the body is a valid json-encoded stream
        obj = json.loads(response.body)
        assert len(obj) == 7
        for day in obj:
            if datetime.now(timezone.utc).strftime('%a') == day['name']:
                day['distance'] == 30
                day['elevation'] == 540
                day['time'] == '01'
                day['workouts'] == 1
            else:
                day['distance'] == 0
                day['elevation'] == 0
                day['time'] == '00'
                day['workouts'] == 0
