

def groupfinder(user_id, request):
    """
    Return the groups a user belongs to.

    So far, each user has its own group, we will use that to limit access so
    users can access only their own workouts. We will expand it later on to
    allow other users to view workouts from a given user
    """
    if user_id in request.root.all_usernames():
        return [user_id]
    return []
