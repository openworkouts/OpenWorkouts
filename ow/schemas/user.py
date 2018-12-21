from pyramid.i18n import TranslationStringFactory
from formencode import Schema, validators
from pytz import common_timezones

from ow.schemas.blob import FieldStorageBlob

_ = TranslationStringFactory('OpenWorkouts')


class PasswordMatch(validators.UnicodeString):
    messages = {
        "dont_match": _('The given password does not match the existing one '),
    }

    def _validate_python(self, value, state):
        super(PasswordMatch, self)._validate_python(value, state)
        if not state.user.check_password(value):
            raise validators.Invalid(
                self.message('dont_match', state), value, state)


class UniqueNickname(validators.UnicodeString):
    messages = {
        "name_exists": _('Another user is already using the nickname %(name)s')
    }

    def _validate_python(self, value, state):
        super(UniqueNickname, self)._validate_python(value, state)
        if value.lower() in state.names:
            raise validators.Invalid(
                self.message('name_exists', state, name=value), value, state)


class UniqueEmail(validators.Email):
    messages = {
        "email_exists": _('Another user is already registered with the email '
                          '%(email)s')
    }

    def _validate_python(self, value, state):
        super(UniqueEmail, self)._validate_python(value, state)
        if value.lower() in state.emails:
            raise validators.Invalid(
                self.message('email_exists', state, email=value), value, state)


class UserAddSchema(Schema):
    """
    Schema to add a new user
    """
    allow_extra_fields = True
    filter_extra_fields = True
    email = UniqueEmail(not_empty=True)
    nickname = UniqueNickname(if_missing='')
    firstname = validators.UnicodeString()
    lastname = validators.UnicodeString()
    group = validators.UnicodeString(if_missing='')


class UserProfileSchema(Schema):
    """
    Schema for the "edit profile" form for users
    """
    allow_extra_fields = True
    filter_extra_fields = True
    firstname = validators.UnicodeString(not_empty=True)
    lastname = validators.UnicodeString(not_empty=True)
    email = validators.Email(not_empty=True)
    nickname = UniqueNickname(if_missing='')
    bio = validators.UnicodeString(if_missing='')
    birth_date = validators.DateConverter(month_style='dd/mm/yyyy')
    height = validators.Number()
    weight = validators.Number()
    gender = validators.OneOf(('male', 'female'), not_empty=True)
    picture = FieldStorageBlob(if_emtpy=None, if_missing=None,
                               whitelist=['jpg', 'jpeg', 'png', 'gif'])
    timezone = validators.OneOf(common_timezones, if_missing='UTC')


class ChangePasswordSchema(Schema):
    allow_extra_fields = True
    filter_extra_fields = True

    old_password = PasswordMatch(not_empty=True)
    password = validators.UnicodeString(min=9, not_empty=True)
    password_confirm = validators.UnicodeString(not_empty=True)
    chained_validators = [validators.FieldsMatch(
        'password', 'password_confirm')]


class SignUpSchema(Schema):
    """
    Schema for the sign up of new users
    """
    allow_extra_fields = True
    filter_extra_fields = True
    nickname = UniqueNickname(if_missing='')
    firstname = validators.UnicodeString(not_empty=True)
    lastname = validators.UnicodeString(not_empty=True)
    email = UniqueEmail(not_empty=True)
    password = validators.UnicodeString(min=9, not_empty=True)
    password_confirm = validators.UnicodeString(not_empty=True)
    chained_validators = [validators.FieldsMatch(
        'password', 'password_confirm')]


class RecoverPasswordSchema(Schema):
    """
    Schema for the password recovery
    """
    allow_extra_fields = True
    filter_extra_fields = True
    nickname = UniqueNickname(if_missing='')
    email = UniqueEmail(not_empty=True)
