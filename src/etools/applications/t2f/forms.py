from django import forms
from django.db import transaction

from etools.applications.t2f.models import make_travel_reference_number, Travel

class TravelForm(forms.ModelForm):

    class Meta:
        model = Travel
        fields = '__all__'

    def get_initial_for_field(self, field, field_name):
        if self.initial.get(field_name, field.initial) == make_travel_reference_number:
            with transaction.atomic():
                return super().get_initial_for_field(field, field_name)

        return super().get_initial_for_field(field, field_name)
