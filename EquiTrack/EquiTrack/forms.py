__author__ = 'unicef-leb-inn'

from django import forms
from suit.widgets import AutosizedTextarea


class AutoSizeTextForm(forms.ModelForm):
    class Meta:
        widgets = {
            'name':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
            'description':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
        }
