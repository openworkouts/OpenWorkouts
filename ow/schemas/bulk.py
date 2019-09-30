from formencode import Schema, validators

from ow.schemas.blob import FieldStorageBlob


class BulkFileSchema(Schema):
    """
    Schema for a compressed file used to upload workouts in "bulk" mode.
    We ask only for the compressed file.
    """
    allow_extra_fields = True
    filter_extra_fields = True
    # This one can not be none, it is a required field
    compressed_file = FieldStorageBlob(not_empty=True,
                                       whitelist=['zip', 'tgz'])
