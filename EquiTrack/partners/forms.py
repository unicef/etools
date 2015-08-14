__author__ = 'jcranwellward'

from suit.widgets import AutosizedTextarea
from django import forms
#from autocomplete_light import forms

from reports.models import Sector
from partners.models import (
    PCA,
    GwPCALocation,
    IndicatorProgress
)


# class LocationForm(forms.ModelForm):
#
#     class Media:
#         """
#         We're currently using Media here, but that forced to move the
#         javascript from the footer to the extrahead block ...
#
#         So that example might change when this situation annoys someone a lot.
#         """
#         js = ('dependant_autocomplete.js',)
#
#     class Meta:
#         model = GwPCALocation


class IndicatorAdminModelForm(forms.ModelForm):

    class Meta:
        model = IndicatorProgress

    def __init__(self, *args, **kwargs):
        super(IndicatorAdminModelForm, self).__init__(*args, **kwargs)
        self.fields['indicator'].queryset = []


class PCAForm(forms.ModelForm):

    p_codes = forms.CharField(widget=forms.Textarea, required=False)
    location_sector = forms.ModelChoiceField(
        queryset=Sector.objects.all(),
        required=False
    )

    class Meta:
        model = PCA
        widgets = {
            'title':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
        }
