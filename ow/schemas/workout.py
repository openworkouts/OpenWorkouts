from formencode import Schema, validators

from ow.schemas.blob import FieldStorageBlob


class UploadedWorkoutSchema(Schema):
    """
    Schema for a workout added with a fit, gpx, etc file.
    We ask only for the tracking file, title and notes, the rest of the workout
    data will be extracted from the uploaded file.
    """
    allow_extra_fields = True
    filter_extra_fields = True
    title = validators.UnicodeString(if_missing='')
    notes = validators.UnicodeString(if_missing='')
    # This one can not be none, it is a required field
    tracking_file = FieldStorageBlob(not_empty=True, whitelist=['gpx', 'fit'])


class ManualWorkoutSchema(Schema):
    """
    Schema for a workout added manually
    """
    allow_extra_fields = True
    filter_extra_fields = True
    sport = validators.UnicodeString(if_missing='')
    title = validators.UnicodeString(if_missing='')
    notes = validators.UnicodeString(if_missing='')
    start_date = validators.DateConverter(month_style='dd/mm/yyyy',
                                          not_empty=True)
    start_time = validators.TimeConverter(not_empty=True)
    # We split duration into three fields, so it is easier for users to provide
    # the full duration of a workout manually
    duration_hours = validators.Number(not_empty=True)
    duration_minutes = validators.Number(not_empty=True)
    duration_seconds = validators.Number(not_empty=True)
    distance = validators.Number(if_empty=0)


class UpdateWorkoutSchema(Schema):
    """
    Schema for the update of a workout using a fit, gpx, etc file.
    We ask only for the tracking file, any other data can be updated using
    the "manual update" view
    """
    allow_extra_fields = True
    filter_extra_fields = True
    # This one can not be none, it is a required field
    tracking_file = FieldStorageBlob(not_empty=True, whitelist=['gpx', 'fit'])
