from __future__ import absolute_import

from django import forms
from django.db import connection
from django.db.models import Q
from django.contrib.auth.models import Group
from django.forms import Textarea
from django.forms.models import BaseInlineFormSet


class AutoSizeTextForm(forms.ModelForm):
    """
    Use textarea for name and description fields
    """
    class Meta:
        widgets = {
            'name': Textarea(),
            'description': Textarea(),
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


class UserGroupForm(forms.ModelForm):
    """
    A form that will mask a user field to a certain group.
    Set the field name and group to use on the instance
    """
    user_field = None
    group_name = None

    def __init__(self, *args, **kwargs):
        super(UserGroupForm, self).__init__(*args, **kwargs)

        if self.user_field and self.group_name:

            group, created = Group.objects.get_or_create(
                name=self.group_name
            )
            self.fields[self.user_field].queryset = group.user_set.filter(
                Q(profile__country__schema_name=connection.schema_name) &
                Q(Q(profile__partner_staff_member__isnull=True) | Q(profile__partner_staff_member=0))
            )
