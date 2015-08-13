__author__ = 'unicef-leb-inn'

from django import forms
from suit.widgets import AutosizedTextarea


class IndicatorForm(forms.ModelForm):
    class Meta:
        widgets = {
            'name':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
        }
