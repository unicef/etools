from django import forms

from etools.applications.audit.models import EngagementActionPoint


class EngagementActionPointAdminForm(forms.ModelForm):
    model = EngagementActionPoint
    fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["engagement"].required = True
