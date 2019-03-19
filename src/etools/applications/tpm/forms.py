from django import forms

from etools.applications.tpm.models import TPMActionPoint


class TPMActionPointForm(forms.ModelForm):
    model = TPMActionPoint
    fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tpm_activity"].required = True
