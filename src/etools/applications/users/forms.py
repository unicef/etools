from django import forms
from django.db import connection

from etools.applications.users.models import Office, Section, UserProfile


class ProfileForm(forms.ModelForm):
    office = forms.ModelChoiceField(
        Office.objects.all(),
        empty_label='Office',
        widget=forms.Select(attrs={'class': 'form-control input-sm'})
    )
    section = forms.ModelChoiceField(
        Section.objects.all(),
        empty_label='Section',
        widget=forms.Select(attrs={'class': 'form-control input-sm'})
    )
    job_title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserProfile
        exclude = ['user', ]

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['office'].queryset = connection.tenant.offices.all()
        self.fields['section'].queryset = connection.tenant.sections.all()
