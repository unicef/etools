__author__ = 'jcranwellward'

from django import forms
from django.db import connection
from django.contrib.auth import get_user_model

from .models import UserProfile, Country, Section

User = get_user_model()


class ProfileForm(forms.ModelForm):
    section = forms.ModelChoiceField(
        connection.tenant.sections.all(),
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
