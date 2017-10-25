from __future__ import absolute_import

from django import forms
from django.db import connection
from django.db.models import Q
from django.contrib.auth.models import Group
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
