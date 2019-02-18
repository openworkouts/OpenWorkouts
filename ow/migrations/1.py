
def migrate(root):
    """
    Adds the verified and verification token attributesfor all existing users,
    setting verified to True (verifying all users automatically)

    >>> from ow.models.root import OpenWorkouts
    >>> from ow.models.user import User
    >>> root = OpenWorkouts()
    >>> user = User(email='user@example.net')
    >>> assert getattr(user, 'verified', None) is not None
    >>> delattr(user, 'verified')
    >>> assert getattr(user, 'verified', None) is None
    >>> root.add_user(user)
    >>> assert getattr(user, 'verified', None) is None
    >>> migrate(root)
    >>> user = root.users[0]
    >>> assert getattr(user, 'verified', None) is not None
    >>> assert user.verified
    """
    for user in root.users:
        if getattr(user, 'verified', None) is None:
            user.verified = True
            user.verification_token = None
