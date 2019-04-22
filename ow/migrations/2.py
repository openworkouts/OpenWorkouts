

def migrate(root):
    """
    Adds the "hashed" workout index to the main catalog, reindexing all
    existing workouts.

    >>> from decimal import Decimal
    >>> from datetime import datetime, timezone, timedelta
    >>> from ow.catalog import get_catalog
    >>> from ow.models.root import OpenWorkouts
    >>> from ow.models.user import User
    >>> from ow.models.workout import Workout
    >>> root = OpenWorkouts()
    >>> indexes = get_catalog(root)
    >>> 'hashed' in root.catalog
    True
    >>> del root.catalog['hashed']
    >>> 'hashed' in root.catalog
    False
    >>> user = User(email='user@example.net')
    >>> workout = Workout(start=datetime.now(timezone.utc))
    >>> workout.duration = timedelta(seconds=3600)
    >>> workout.distance = Decimal(30)
    >>> workout.sport = 'cycling'
    >>> workout.title = 'cycling in migrations'
    >>> root.add_user(user)
    >>> user.add_workout(workout)
    >>> migrate(root)
    >>> 'hashed' in root.catalog
    True
    >>> hashes = [h for h in root.catalog['hashed']._fwd_index]
    >>> workout.hashed in hashes
    True
    >>> 'some-faked-non-existant-hash' in hashes
    False
    """
    root._update_indexes()
    for user in root.users:
        for workout in user.workouts():
            root.reindex(workout)
