from __future__ import absolute_import, division, print_function, unicode_literals

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _


class EmailLoginForm(forms.Form):
    email = forms.EmailField(label=_("Your Email"))

    error_messages = {
        'no_such_user': _("User with such email does not exists."),
        'inactive': _("This account is inactive."),
    }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.user_cache = None
        super(EmailLoginForm, self).__init__(*args, **kwargs)

    def clean(self):
        if self.errors:
            return

        self.user_cache = get_user_model().objects.filter(email=self.cleaned_data['email']).first()
        if not self.user_cache:
            raise forms.ValidationError(
                self.error_messages['no_such_user'],
                code='no_such_user',
            )
        else:
            self.confirm_login_allowed(self.user_cache)

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )

    def get_user(self):
        return self.user_cache
