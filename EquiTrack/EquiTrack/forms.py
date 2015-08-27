__author__ = 'unicef-leb-inn'

from django import forms
from suit.widgets import AutosizedTextarea
from django.forms.models import BaseInlineFormSet


class AutoSizeTextForm(forms.ModelForm):
    """
    Adds large text boxes to name and description fields
    """
    class Meta:
        widgets = {
            'name':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
            'description':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
        }


class RequiredInlineFormSet(BaseInlineFormSet):
    """
    Generates an inline formset that is required
    """

    def _construct_form(self, i, **kwargs):
        """
        Override the method to change the form attribute empty_permitted
        """
        form = super(RequiredInlineFormSet, self)._construct_form(i, **kwargs)
        form.empty_permitted = False
        return form
