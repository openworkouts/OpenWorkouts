from pyramid.view import view_config
from pyramid_simpleform import Form, State
from pyramid_simpleform.renderers import FormRenderer
from pyramid.httpexceptions import HTTPFound

from ..models.root import OpenWorkouts
from ..models.user import User
from ..schemas.user import UserAddSchema


@view_config(
    context=OpenWorkouts,
    permission='edit',
    name='userlist',
    renderer='ow:templates/user_list.pt')
def user_list(context, request):
    """
    Show a list of all the users to admins
    """
    users = context.users
    return {'users': users}


@view_config(
    context=OpenWorkouts,
    permission='edit',
    name='adduser',
    renderer='ow:templates/add_user.pt')
def add_user(context, request):
    """
    Form to add a user
    """
    state = State(emails=context.lowercase_emails,
                  names=context.lowercase_nicknames)

    form = Form(request, schema=UserAddSchema(), state=state)

    if 'submit' in request.POST and form.validate():
        user = form.bind(User())
        context[str(user.uid)] = user
        return HTTPFound(location=request.resource_url(context, 'userlist'))

    return {
        'form': FormRenderer(form)
    }


@view_config(
    context=OpenWorkouts,
    permission='view',
    name='promo',
    renderer='ow:templates/openworkouts.pt')
def promo(context, request):
    return {}
