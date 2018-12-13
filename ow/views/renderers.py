from datetime import datetime, date
from webhelpers2.html import tags
from pyramid_simpleform.renderers import FormRenderer


class OWFormRenderer(FormRenderer):
    """
    Subclass FormRenderer to add a custom renderer for date fields.

    Such renderer already exist in newer (devel) versions of pyramid_simpleform
    but they had not been released yet.
    """

    def date(self, name, value=None, id=None, date_format=None, **attrs):
        """
        Outputs text input with an optionally formatted datetime.
        """
        value = self.value(name, value)
        id = id or name
        is_date = isinstance(value, date)
        is_datetime = isinstance(value, datetime)

        if (is_date or is_datetime) and date_format:
            value = value.strftime(date_format)

        return tags.text(name, value, id, **attrs)
