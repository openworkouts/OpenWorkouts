

def groupfinder(uid, request):
    """
    Return the groups a user belongs to.

    So far, each user has its own group, we will use that to limit access so
    users can access only their own workouts. We will expand it later on to
    allow other users to view workouts from a given user
    """
    user = request.root.get_user_by_uid(str(uid))
    if user is not None:
        return [str(user.uid)]
    return []
