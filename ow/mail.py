import logging

from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message, Attachment
from pyramid.renderers import render
from pyramid.i18n import TranslationStringFactory

import premailer

_ = TranslationStringFactory('OpenWorkouts')

log = logging.getLogger(__name__)


def idna_encode_recipients(message):
    """
    Given a pyramid_mailer.message.Message instance, check if the recipient(s)
    domain name(s) contain non-ascii characters and, if so, encode the domain
    name part of the address(es) properly

    >>> from pyramid_mailer.message import Message
    >>> message = Message(subject='s', recipients=['a@a.com'], body='b')
    >>> assert message.recipients == ['a@a.com']
    >>> message = idna_encode_recipients(message)
    >>> assert message.recipients == ['a@a.com']
    >>> message.recipients.append(u'a@\xfc.de')
    >>> assert message.recipients == ['a@a.com', u'a@\xfc.de']
    >>> message = idna_encode_recipients(message)
    >>> message.recipients
    ['a@a.com', 'a@xn--tda.de']
    """
    recipients = []
    for rcpt in message.recipients:
        username, domain = rcpt.split('@')
        recipients.append(
            '@'.join([username, domain.encode('idna').decode('utf-8')]))
    message.recipients = recipients
    return message


def send_verification_email(request, user):
    subject = _('Welcome to OpenWorkouts')
    txt_template = 'ow:templates/mail_verify_account_txt.pt'
    html_template = 'ow:templates/mail_verify_account_html.pt'
    verify_link = request.resource_url(user, 'verify', user.verification_token)
    context = {'user': user, 'verify_link': verify_link}
    mailer = get_mailer(request)
    txt_body = render(txt_template, context, request)
    html_body = premailer.transform(render(html_template, context, request))
    message = Message(
        subject=subject,
        recipients=[user.email],
        body=Attachment(data=txt_body,
                        content_type="text/plain; charset=utf-8",
                        transfer_encoding="quoted-printable"),
        html=Attachment(data=html_body,
                        content_type="text/html; charset=utf-8",
                        transfer_encoding="quoted-printable")
    )
    message = idna_encode_recipients(message)
    mailer.send_to_queue(message)
