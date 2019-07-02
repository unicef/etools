from django import forms

from etools.applications.t2f.models import T2FActionPoint


class T2FActionPointAdminForm(forms.ModelForm):
    model = T2FActionPoint
    fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["travel_activity"].required = True
