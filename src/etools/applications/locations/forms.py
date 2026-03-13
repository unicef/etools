from django import forms
from django.utils.translation import gettext_lazy as _


class LocationImportUploadForm(forms.Form):
    """Form for uploading Excel/CSV file for Location import."""

    import_file = forms.FileField(
        label=_('Excel or CSV file'),
        help_text=_('Required headers: Name, Admin Level, Admin Level Name, P Code, Active, Parent'),
    )

    def clean_import_file(self):
        data = self.cleaned_data['import_file']
        name = (data.name or '').lower()
        if not (name.endswith('.csv') or name.endswith('.xlsx') or name.endswith('.xls')):
            raise forms.ValidationError(
                _('File must be CSV (.csv) or Excel (.xlsx, .xls).')
            )
        return data
