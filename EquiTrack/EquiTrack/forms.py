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


class ParentInlineAdminFormSet(BaseInlineFormSet):
    """
    Passes the parent instance to the form constructor for easy
    access by child inline forms to use for conditional filtering
    """
    def _construct_form(self, i, **kwargs):
        kwargs['parent_object'] = self.instance
        return super(ParentInlineAdminFormSet, self)._construct_form(i, **kwargs)


class RequireOneFormSet(ParentInlineAdminFormSet):
    """
    Require at least one form in the formset to be completed.
    """
    required = True

    def clean(self):
        """Check that at least one form has been completed."""
        super(RequireOneFormSet, self).clean()
        for error in self.errors:
            if error:
                return
        completed = 0
        for cleaned_data in self.cleaned_data:
            # form has data and we aren't deleting it.
            if cleaned_data and not cleaned_data.get('DELETE', False):
                completed += 1

        if completed < 1 and self.required:
            raise forms.ValidationError("At least one %s is required." %
                self.model._meta.object_name.lower())
