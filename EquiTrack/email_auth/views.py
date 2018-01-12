from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.views.generic import FormView
from post_office import mail

from email_auth.forms import LoginForm
from email_auth.utils import update_url_with_token
from utils.common.urlresolvers import site_url


class TokenAuthView(FormView):
    form_class = LoginForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'email_auth/login.html'

    def form_valid(self, form):
        context = {
            'recipient': form.get_user(),
            'login_link': update_url_with_token(site_url(), form.get_user()),
        }

        mail.send(
            [form.get_user().email, ],
            settings.DEFAULT_FROM_EMAIL,
            template='email_auth/token/login',
            context=context,
        )

        return self.render_to_response(self.get_context_data())


login = TokenAuthView.as_view()
