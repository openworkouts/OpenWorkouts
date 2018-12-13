import os
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
    def root(self):
        root = OpenWorkouts()
        root['john'] = User(firstname='John', lastname='Doe',
                            email='john.doe@example.net')
        root['john'].password = 's3cr3t'
        workout = Workout(
            start=datetime(2015, 6, 28, 12, 55, tzinfo=timezone.utc),
            duration=timedelta(minutes=60),
            distance=30
        )
        root['john'].add_workout(workout)
        return root

    @pytest.fixture
    def dummy_request(self, root):
        request = DummyRequest()
        request.root = root
        return request

    @pytest.fixture
    def profile_post_request(self, root):
        """
        This is a valid POST request to update an user profile.
        Form will validate, but nothing will be really updated/changed.
        """
        user = root['john']
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
            'username': 'JackBlack',
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

    def test_dashboard_redirect_authenticated(self, root):
        """
        Authenticated user accesing the root object, send the user to her
        dashboard

        Instead of reusing the DummyRequest from the request fixture, we do
        Mock fully the request here, because we need to use
        authenticated_userid, which cannot be easily set in the DummyRequest
        """
        request = Mock()
        request.root = root
        request.authenticated_userid = 'john'
        request.resource_url.return_value = '/dashboard'
        response = user_views.dashboard_redirect(root, request)
        assert isinstance(response, HTTPFound)
        assert response.location == '/dashboard'

    def test_dashboard(self, dummy_request):
        """
        Renders the user dashboard
        """
        request = dummy_request
        user = request.root['john']
        response = user_views.dashboard(user, request)
        assert response == {}

    def test_profile(self, dummy_request):
        """
        Renders the user profile page
        """
        request = dummy_request
        user = request.root['john']
        response = user_views.profile(user, request)
        assert response == {}

    def test_login_get(self, dummy_request):
        """
        GET request to access the login page
        """
        request = dummy_request
        response = user_views.login(request.root, request)
        assert response['message'] == ''
        assert response['username'] == ''
        assert response['password'] == ''
        assert response['redirect_url'] == request.resource_url(request.root)

    def test_login_get_return_to(self, dummy_request):
        """
        GET request to access the login page, if there is a page set to where
        the user should be sent to, the response "redirect_url" key will have
        such url
        """
        request = dummy_request
        workout = request.root['john'].workouts()[0]
        workout_url = request.resource_url(workout)
        request.params['return_to'] = workout_url
        response = user_views.login(request.root, request)
        assert response['redirect_url'] == workout_url

    def test_login_post_bad_username(self, dummy_request):
        request = dummy_request
        request.method = 'POST'
        request.POST['submit'] = True
        request.POST['username'] = 'jack'
        response = user_views.login(request.root, request)
        assert response['message'] == u'Bad username'

    def test_login_post_bad_password(self, dummy_request):
        request = dummy_request
        request.method = 'POST'
        request.POST['submit'] = True
        request.POST['username'] = 'john'
        request.POST['password'] = 'badpassword'
        response = user_views.login(request.root, request)
        assert response['message'] == u'Bad password'

    @patch('ow.views.user.remember')
    def test_login_post_ok(self, rem, dummy_request):
        request = dummy_request
        request.method = 'POST'
        request.POST['submit'] = True
        request.POST['username'] = 'john'
        request.POST['password'] = 's3cr3t'
        response = user_views.login(request.root, request)
        assert isinstance(response, HTTPFound)
        assert rem.called
        assert response.location == request.resource_url(request.root)

    @patch('ow.views.user.forget')
    def test_logout(self, forg, dummy_request):
        request = dummy_request
        response = user_views.logout(request.root, request)
        assert isinstance(response, HTTPFound)
        assert forg.called
        assert response.location == request.resource_url(request.root)

    extensions = ('png', 'jpg', 'jpeg', 'gif')

    @pytest.mark.parametrize('extension', extensions)
    def test_profile_picture(self, extension, dummy_request):
        """
        GET request to get the profile picture of an user.
        """
        request = dummy_request
        # Get the user
        user = request.root['john']
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

    def test_edit_profile_get(self, dummy_request):
        """
        GET request to the edit profile page, returns the form ready to
        be rendered
        """
        request = dummy_request
        user = request.root['john']
        response = user_views.edit_profile(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        # no errors in the form (first load)
        assert response['form'].errorlist() == ''
        # the form carries along the proper data keys, taken from the
        # loaded user profile
        data = ['firstname', 'lastname', 'email', 'bio', 'birth_date',
                'height', 'weight', 'gender']
        assert list(response['form'].data.keys()) == data
        # and check the email to see data is properly loaded
        assert response['form'].data['email'] == 'john.doe@example.net'

    def test_edit_profile_post_ok(self, profile_post_request):
        request = profile_post_request
        user = request.root['john']
        # Update the bio field
        bio = 'Some text about this user'
        request.POST['bio'] = bio
        response = user_views.edit_profile(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'profile')
        assert user.bio == bio

    def test_edit_profile_post_missing_required(self, profile_post_request):
        request = profile_post_request
        request.POST['email'] = ''
        user = request.root['john']
        response = user_views.edit_profile(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        # error on the missing email field
        error = u'Please enter an email address'
        html_error = u'<ul class="error"><li>' + error + '</li></ul>'
        assert response['form'].errorlist() == html_error
        assert response['form'].errors_for('email') == [error]

    def test_change_password_get(self, dummy_request):
        request = dummy_request
        user = request.root['john']
        response = user_views.change_password(user, request)
        assert isinstance(response['form'], OWFormRenderer)
        # no errors in the form (first load)
        assert response['form'].errorlist() == ''

    def test_change_password_post_ok(self, passwd_post_request):
        request = passwd_post_request
        user = request.root['john']
        request.POST['old_password'] = 's3cr3t'
        request.POST['password'] = 'h1dd3n s3cr3t'
        request.POST['password_confirm'] = 'h1dd3n s3cr3t'
        response = user_views.change_password(user, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(user, 'profile')
        # password was changed
        assert not user.check_password('s3cr3t')
        assert user.check_password('h1dd3n s3cr3t')

    def test_change_password_post_no_values(self, passwd_post_request):
        request = passwd_post_request
        user = request.root['john']
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

    def test_change_password_post_bad_old_password(self, passwd_post_request):
        request = passwd_post_request
        user = request.root['john']
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

    def test_change_password_post_password_mismatch(self, passwd_post_request):
        request = passwd_post_request
        user = request.root['john']
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
        assert 'JackBlack' not in request.root.all_usernames()
        response = user_views.signup(request.root, request)
        assert isinstance(response, HTTPFound)
        assert response.location == request.resource_url(request.root)
        assert 'JackBlack' in request.root.all_usernames()

    def test_signup_missing_required(self, signup_post_request):
        request = signup_post_request
        request.POST['email'] = ''
        assert 'JackBlack' not in request.root.all_usernames()
        response = user_views.signup(request.root, request)
        assert isinstance(response['form'], OWFormRenderer)
        error = u'Please enter an email address'
        html_error = '<ul class="error">'
        html_error += '<li>' + error + '</li>'
        html_error += '</ul>'
        errorlist = response['form'].errorlist().replace('\n', '')
        assert errorlist == html_error
        assert response['form'].errors_for('email') == [error]
        assert 'JackBlack' not in request.root.all_usernames()

    def test_signup_existing_username(self, signup_post_request):
        request = signup_post_request
        request.POST['username'] = 'john'
        assert 'JackBlack' not in request.root.all_usernames()
        response = user_views.signup(request.root, request)
        assert isinstance(response['form'], OWFormRenderer)
        error = u'Another user is already registered with the username john'
        html_error = '<ul class="error">'
        html_error += '<li>' + error + '</li>'
        html_error += '</ul>'
        errorlist = response['form'].errorlist().replace('\n', '')
        assert errorlist == html_error
        assert response['form'].errors_for('username') == [error]
        assert 'JackBlack' not in request.root.all_usernames()

    def test_signup_existing_email(self, signup_post_request):
        request = signup_post_request
        request.POST['email'] = 'john.doe@example.net'
        assert 'JackBlack' not in request.root.all_usernames()
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
        assert 'JackBlack' not in request.root.all_usernames()
