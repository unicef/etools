__author__ = 'jcranwellward'

from django import forms
from django.contrib.auth import get_user_model

from registration.forms import EmailRegistrationForm

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

    def clean_email(self):

        cleaned_data = super(
            UnicefEmailRegistrationForm, self).clean_email()

        email = cleaned_data.split('@')[1]
        if 'unicef.org' not in email:
            raise forms.ValidationError(
                "You must register with a UNICEF email address"
            )

        return cleaned_data