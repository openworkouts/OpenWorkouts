from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer
from pyramid.i18n import TranslationStringFactory

from ..models.user import User
from ..models.bulk import BulkFile
from ..schemas.bulk import (
    BulkFileSchema,
)

_ = TranslationStringFactory('OpenWorkouts')


@view_config(
    context=User,
    permission='edit',
    name='add-bulk-file',
    renderer='ow:templates/add_bulk_file.pt')
def add_bulk_file(context, request):
    """
    Add a compressed file that should contain tracking files, so we can
    do a "bulk" upload of tracking files and workouts
    """
    # if not given a file there is an empty byte in POST, which breaks
    # our blob storage validator.
    # dirty fix until formencode fixes its api.is_empty method
    if isinstance(request.POST.get('compressed_file', None), bytes):
        request.POST['compressed_file'] = ''

    form = Form(request, schema=BulkFileSchema())

    if 'submit' in request.POST and form.validate():
        # get the extension of the compressed file. We use this later to
        # know how to decompress it.
        file_name = file_ext = request.POST['compressed_file'].filename
        file_ext = file_name.split('.')[-1]
        # Create a BulkFile instance based on the input from the form
        bulk_file = form.bind(BulkFile(uid=str(context.uid)))
        # Set the type of compressed file
        bulk_file.file_name = file_name
        bulk_file.file_type = file_ext

        # save the bulk file
        request.root['_bulk_files'].add_bulk_file(bulk_file)
        # Send the user to his/her bulk files page
        return HTTPFound(location=request.resource_url(context, 'bulk-files'))

    return {
        'form': FormRenderer(form),
    }


@view_config(
    context=User,
    permission='edit',
    name='bulk-files',
    renderer='ow:templates/bulk_files.pt')
def bulk_files(context, request):
    """
    Render a page where users can see their bulk uploads (finished,
    pending, status, etc)
    """
    return {
        'bulk_files': request.root['_bulk_files'].get_by_uid(context.uid)
    }
