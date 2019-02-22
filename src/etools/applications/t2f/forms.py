from django import forms
from django.db.transaction import atomic

from etools.applications.t2f.models import Travel

class TravelForm(forms.ModelForm):

    class Meta:
        model = Travel
        fields = '__all__'

    @atomic
    def get_initial_for_field(self, field, field_name):
        super().get_initial_for_field(field, field_name)
