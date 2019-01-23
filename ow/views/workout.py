from datetime import datetime, timedelta, time, timezone

import gpxpy

from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.view import view_config
from pyramid.response import Response
from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer

from ..schemas.workout import (
    UploadedWorkoutSchema,
    ManualWorkoutSchema,
    UpdateWorkoutSchema
)
from ..models.workout import Workout
from ..models.user import User
from ..utilities import slugify
from ..catalog import get_catalog, reindex_object, remove_from_catalog


@view_config(
    context=User,
    name='add-workout-manually',
    renderer='ow:templates/add_manual_workout.pt')
def add_workout_manually(context, request):
    form = Form(request, schema=ManualWorkoutSchema(),
                defaults={'duration_hours': '0',
                          'duration_minutes': '0',
                          'duration_seconds': '0'})

    if 'submit' in request.POST and form.validate():
        # exclude the three duration_* and start_* fields, so they won't be
        # "bind" to the object, we do calculate both the full duration in
        # seconds and the full datetime "start" and we save that
        excluded = ['duration_hours', 'duration_minutes', 'duration_seconds',
                    'start_date', 'start_time']
        workout = form.bind(Workout(), exclude=excluded)
        duration = timedelta(hours=form.data['duration_hours'],
                             minutes=form.data['duration_minutes'],
                             seconds=form.data['duration_seconds'])
        workout.duration = duration
        # create a time object first using the given hours and minutes
        start_time = time(form.data['start_time'][0],
                          form.data['start_time'][1])
        # combine the given start date with the built time object
        start = datetime.combine(form.data['start_date'], start_time,
                                 tzinfo=timezone.utc)
        workout.start = start
        context.add_workout(workout)
        return HTTPFound(location=request.resource_url(workout))

    return {
        'form': FormRenderer(form)
    }


@view_config(
    context=User,
    name='add-workout',
    renderer='ow:templates/add_workout.pt')
def add_workout(context, request):
    """
    Add a workout uploading a tracking file
    """
    # if not given a file there is an empty byte in POST, which breaks
    # our blob storage validator.
    # dirty fix until formencode fixes its api.is_empty method
    if isinstance(request.POST.get('tracking_file', None), bytes):
        request.POST['tracking_file'] = ''

    form = Form(request, schema=UploadedWorkoutSchema())

    if 'submit' in request.POST and form.validate():
        # Grab some information from the tracking file
        trackfile_ext = request.POST['tracking_file'].filename.split('.')[-1]
        # Create a Workout instance based on the input from the form
        workout = form.bind(Workout())
        # Add the type of tracking file
        workout.tracking_filetype = trackfile_ext
        # Add basic info gathered from the file
        workout.load_from_file()
        # Add the workout
        context.add_workout(workout)
        return HTTPFound(location=request.resource_url(workout))

    return {
        'form': FormRenderer(form)
    }


@view_config(
    context=Workout,
    name='edit',
    renderer='ow:templates/edit_manual_workout.pt')
def edit_workout(context, request):
    """
    Edit manually an existing workout. This won't let users attach/update
    tracking files, just manually edit of the values.
    """
    form = Form(request, schema=ManualWorkoutSchema(), obj=context)
    if 'submit' in request.POST and form.validate():
        # exclude the three duration_* and start_* fields, so they won't be
        # "bind" to the object, we do calculate both the full duration in
        # seconds and the full datetime "start" and we save that
        excluded = ['duration_hours', 'duration_minutes', 'duration_seconds',
                    'start_date', 'start_time']

        form.bind(context, exclude=excluded)

        duration = timedelta(hours=form.data['duration_hours'],
                             minutes=form.data['duration_minutes'],
                             seconds=form.data['duration_seconds'])
        context.duration = duration

        # create a time object first using the given hours and minutes
        start_time = time(form.data['start_time'][0],
                          form.data['start_time'][1])
        # combine the given start date with the built time object
        start = datetime.combine(form.data['start_date'], start_time,
                                 tzinfo=timezone.utc)
        context.start = start
        catalog = get_catalog(context)
        reindex_object(catalog, context)
        return HTTPFound(location=request.resource_url(context))

    return {
        'form': FormRenderer(form)
    }


@view_config(
    context=Workout,
    name='update-from-file',
    renderer='ow:templates/update_workout_from_file.pt')
def update_workout_from_file(context, request):
    # if not given a file there is an empty byte in POST, which breaks
    # our blob storage validator.
    # dirty fix until formencode fixes its api.is_empty method
    if isinstance(request.POST.get('tracking_file', None), bytes):
        request.POST['tracking_file'] = ''

    form = Form(request, schema=UpdateWorkoutSchema())
    if 'submit' in request.POST and form.validate():
        # Grab some information from the tracking file
        trackfile_ext = request.POST['tracking_file'].filename.split('.')[-1]
        # Update the type of tracking file
        context.tracking_filetype = trackfile_ext
        form.bind(context)
        # Override basic info gathered from the file
        context.load_from_file()
        catalog = get_catalog(context)
        reindex_object(catalog, context)
        return HTTPFound(location=request.resource_url(context))
    return {
        'form': FormRenderer(form)
    }


@view_config(
    context=Workout,
    name='delete',
    renderer='ow:templates/delete_workout.pt')
def delete_workout(context, request):
    """
    Delete a workout
    """
    if 'submit' in request.POST:
        if request.POST.get('delete', None) == 'yes':
            catalog = get_catalog(context)
            remove_from_catalog(catalog, context)
            del request.root[request.authenticated_userid][context.workout_id]
            return HTTPFound(location=request.resource_url(request.root))
    return {}


@view_config(
    context=Workout,
    renderer='ow:templates/workout.pt')
def workout(context, request):
    """
    Details page for a workout
    """
    start_point = {}
    if context.has_gpx:
        with context.tracking_file.open() as gpx_file:
            gpx_contents = gpx_file.read()
            gpx_contents = gpx_contents.decode('utf-8')
            gpx = gpxpy.parse(gpx_contents)
            if gpx.tracks:
                track = gpx.tracks[0]
                center_point = track.get_center()
                start_point = {'latitude': center_point.latitude,
                               'longitude': center_point.longitude,
                               'elevation': center_point.elevation}
    return {'start_point': start_point}


@view_config(
    context=Workout,
    name='gpx')
def workout_gpx(context, request):
    """
    Return a gpx file with the workout tracking information, if any.
    For now, simply return the gpx file if it has been attached to the
    workout.
    """
    if not context.has_gpx:
        return HTTPNotFound()
    # Generate a proper file name to suggest on the download
    gpx_slug = slugify(context.title) + '.gpx'
    return Response(
        content_type='application/xml',
        content_disposition='attachment; filename="%s"' % gpx_slug,
        body_file=context.tracking_file.open())


@view_config(
    context=Workout,
    name='map',
    renderer='ow:templates/workout-map.pt')
def workout_map(context, request):
    """
    Render a page that has only a map with tracking info
    """
    start_point = {}
    if context.has_gpx:
        with context.tracking_file.open() as gpx_file:
            gpx_contents = gpx_file.read()
            gpx_contents = gpx_contents.decode('utf-8')
            gpx = gpxpy.parse(gpx_contents)
            if gpx.tracks:
                track = gpx.tracks[0]
                center_point = track.get_center()
                start_point = {'latitude': center_point.latitude,
                               'longitude': center_point.longitude,
                               'elevation': center_point.elevation}
    return {'start_point': start_point}
