from django import forms
from django.db import connection

from etools.applications.organizations.models import Organization
from etools.applications.users.models import Realm


class RealmForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None) is None:
            initial = kwargs.get('initial', {})
            unicef_org = Organization.objects.filter(name='UNICEF').first()
            if unicef_org:
                initial['organization'] = unicef_org
                kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    class Meta:
        model = Realm
        exclude = ('country',)

    def save(self, commit=True):
        if not self.instance.pk:
            self.instance.country = connection.tenant
        return super().save(commit=commit)
