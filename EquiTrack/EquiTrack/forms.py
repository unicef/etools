
from django import forms
from django.forms import Textarea


class AutoSizeTextForm(forms.ModelForm):
    """
    Use textarea for name and description fields
    """
    class Meta:
        widgets = {
            'name': Textarea(),
            'description': Textarea(),
        }
