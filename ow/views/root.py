from pyramid.view import view_config
from pyramid_simpleform import Form
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
    users = context.users()
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
    form = Form(request, schema=UserAddSchema())

    if 'submit' in request.POST and form.validate():
        uid = request.POST['uid']
        user = form.bind(User(), exclude=['uid'])
        context[uid] = user
        return HTTPFound(location=request.resource_url(context, 'userlist'))

    return {
        'form': FormRenderer(form)
    }
