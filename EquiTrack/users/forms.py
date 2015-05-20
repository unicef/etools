__author__ = 'jcranwellward'

from django import forms
from django.contrib.auth import get_user_model

from registration.forms import EmailRegistrationForm, RegistrationForm
from trips.models import Office
from reports.models import Sector
from users.models import UserProfile

User = get_user_model()


class UnicefEmailRegistrationForm(EmailRegistrationForm):

    username = forms.RegexField(
        regex=r'^[\w.@+-]+$',
        max_length=30,
        label="Username",
        error_messages={
            'invalid':
            "This value may contain only letters, "
            "numbers and @/./+/-/_ characters."})

    first_name = forms.CharField(max_length=254)
    last_name = forms.CharField(max_length=254)
    office = forms.ModelChoiceField(
        Office.objects.all(),
        empty_label='Office',
        widget=forms.Select(attrs={'class': 'form-control input-sm'})
    )
    section = forms.ModelChoiceField(
        Sector.objects.all(),
        empty_label='Section',
        widget=forms.Select(attrs={'class': 'form-control input-sm'})
    )
    job_title = forms.CharField(max_length=255)
    phone_number = forms.CharField(max_length=255)

    def clean_email(self):

        cleaned_data = super(
            UnicefEmailRegistrationForm, self).clean_email()

        email = cleaned_data.split('@')[1]
        if 'unicef.org' not in email:
            raise forms.ValidationError(
                "You must register with a UNICEF email address"
            )

        return cleaned_data


class ProfileForm(forms.ModelForm):
    office = forms.ModelChoiceField(
        Office.objects.all(),
        empty_label='Office',
        widget=forms.Select(attrs={'class': 'form-control input-sm'})
    )
    section = forms.ModelChoiceField(
        Sector.objects.all(),
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
