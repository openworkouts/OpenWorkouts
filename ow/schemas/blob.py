from shutil import copyfileobj

from pyramid.i18n import TranslationStringFactory

from formencode.validators import FieldStorageUploadConverter, Invalid
from ZODB.blob import Blob


_ = TranslationStringFactory('OpenWorkouts')


class FieldStorageBlob(FieldStorageUploadConverter):
    messages = dict(
        badExtension=_('Please upload a valid file type.'))

    def __init__(self, *args, **kw):
        self.whitelist = kw.get('whitelist', None)
        super(FieldStorageBlob, self).__init__(*args, **kw)

    def _convert_to_python(self, value, state):
        """
        Converts a field upload into a ZODB blob

        >>> from io import BytesIO
        >>> from contextlib import contextmanager
        >>> ifile = lambda: 1
        >>> @contextmanager
        ... def likefile():
        ...     yield BytesIO(b'1234')
        >>> ifile.file = likefile()
        >>> ifile.filename = 'test.pdf'
        >>> validator = FieldStorageBlob()
        >>> blob = validator._convert_to_python(ifile, None)
        >>> blob  # doctest: +ELLIPSIS
        <ZODB.blob.Blob object at 0x...>
        >>> blob.open('r').read()
        b'1234'
        >>> blob.file_extension
        'pdf'
        """
        value = super(FieldStorageBlob, self)._convert_to_python(value, state)
        file_extension = value.filename.rsplit('.', 1)[-1]
        blob = Blob()
        blob.file_extension = file_extension
        with value.file as infile, blob.open('w') as out:
            infile.seek(0)
            copyfileobj(infile, out)
        return blob

    def _validate_python(self, value, state):
        """
        Validates the uploaded file versus a whitelist of file extensions

        >>> from unittest.mock import Mock
        >>> validator = FieldStorageBlob()
        >>> value = Mock(file_extension='bla')
        >>> validator._validate_python(value, None)

        >>> validator2 = FieldStorageBlob(whitelist=['bla', 'jpeg'])
        >>> validator2._validate_python(value, None)

        >>> validator3 = FieldStorageBlob(whitelist=['pdf', 'jpeg'])
        >>> validator3._validate_python(value, None)
        Traceback (most recent call last):
        ...
        formencode.api.Invalid: Please upload a valid file type.
        """
        if self.whitelist is None:
            return

        if value.file_extension not in self.whitelist:
            raise Invalid(self.message('badExtension', state), value, state)
