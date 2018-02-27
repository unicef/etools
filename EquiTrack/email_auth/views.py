from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib.auth import REDIRECT_FIELD_NAME, login
from django.shortcuts import redirect
from django.views.generic import FormView
from django.utils.translation import ugettext_lazy as _

from drfpasswordless.utils import authenticate_by_token

from email_auth.forms import EmailLoginForm
from email_auth.utils import get_token_auth_link
from notification.models import Notification


class TokenAuthView(FormView):
    form_class = EmailLoginForm
    redirect_field_name = REDIRECT_FIELD_NAME
    template_name = 'email_auth/login.html'

    def get(self, request, *args, **kwargs):
        if 'token' in request.GET:
            user = authenticate_by_token(request.GET['token'])
            if user:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                return redirect('dashboard')

        return super(TokenAuthView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TokenAuthView, self).get_context_data(**kwargs)
        if 'token' in self.request.GET:
            context['form'].errors['__all__'] = [_('Couldn\'t log you in. Invalid token.')]

        return context

    def form_valid(self, form):
        email_context = {
            'recipient': form.get_user().get_full_name(),
            'login_link': get_token_auth_link(form.get_user()),
        }

        notification = Notification.objects.create(
            sender=form.get_user(),
            recipients=[form.get_user().email, ], template_name='email_auth/token/login',
            template_data=email_context
        )
        notification.send_notification()

        return self.render_to_response(self.get_context_data(email=form.get_user().email))
