from unittest.mock import Mock, patch

import pytest

from pyramid.testing import DummyRequest
from pyramid_mailer.message import Message

from ow.models.root import OpenWorkouts
from ow.models.user import User
from ow.utilities import get_verification_token
from ow.mail import idna_encode_recipients, send_verification_email


class TestMail(object):

    @pytest.fixture
    def root(self):
        root = OpenWorkouts()
        user = User(email='user@example.net')
        user.verification_token = get_verification_token()
        root.add_user(user)
        return root

    def test_idna_encode_recipients(self):
        message = Message(subject='s', recipients=['a@a.com'], body='b')
        assert message.recipients == ['a@a.com']
        message = idna_encode_recipients(message)
        assert message.recipients == ['a@a.com']
        message.recipients.append(u'a@\xfc.de')
        assert message.recipients == ['a@a.com', u'a@\xfc.de']
        message = idna_encode_recipients(message)
        assert message.recipients == ['a@a.com', 'a@xn--tda.de']

    @patch('ow.mail.get_mailer')
    @patch('ow.mail.Message')
    @patch('ow.mail.render')
    def test_send_verification_email(self, r, m, gm, root):
        mailer = Mock()
        gm.return_value = mailer
        message = Mock()
        message.recipients = ['user@example.net']
        m.return_value = message
        body = Mock()
        r.return_value = body
        request = DummyRequest()
        request.root = root
        user = root.users[0]
        send_verification_email(request, user)
        verify_link = request.resource_url(
            user, 'verify', user.verification_token)
        r.assert_called_once_with(
            'ow:templates/mail_verify_account.pt',
            {'user': user, 'verify_link': verify_link},
            request
        )
        m.assert_called_once
        m.call_args_list[0][1]['recipients'] == user.email
        m.call_args_list[0][1]['body'] == body
        mailer.send_to_queue.assert_called_once_with(message)
