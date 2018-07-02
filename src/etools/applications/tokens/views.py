from django.conf import settings
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView

from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_notification.utils import send_notification_with_template

from etools.applications.tokens.forms import EmailLoginForm
from etools.applications.tokens.utils import get_token_auth_link, update_url_with_kwargs


class TokenEmailAuthView(FormView):
    form_class = EmailLoginForm
    template_name = 'tokens/login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(request.GET.get('next', 'dashboard'))

        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.update({'next': self.request.GET.get('next')})
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if settings.EMAIL_AUTH_TOKEN_NAME in self.request.GET:
            context['form'].errors['__all__'] = [_('Couldn\'t log you in. Invalid token.')]

        return context

    def form_valid(self, form):
        login_link = get_token_auth_link(form.get_user())

        redirect_to = form.data.get('next', self.request.GET.get('next'))
        if redirect_to:
            login_link = update_url_with_kwargs(login_link, next=redirect_to)

        email_context = {
            'recipient': form.get_user().get_full_name(),
            'login_link': login_link,
        }

        send_notification_with_template(
            recipients=[form.get_user().email],
            template_name='email_auth/token/login',
            context=email_context
        )

        return self.render_to_response(self.get_context_data(email=form.get_user().email))


class TokenGetView(APIView):
    """Expects user to be logged in already"""
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(request.GET.get('next', 'dashboard'))
        token, _ = Token.objects.get_or_create(user=request.user)
        return Response({"token": token.key})


class TokenResetView(APIView):
    """Reset users token"""
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(request.GET.get('next', 'dashboard'))
        token, created = Token.objects.get_or_create(user=request.user)
        if not created:
            token.delete()
            token = Token.objects.create(user=request.user)
        return Response({"token": token.key})


class TokenDeleteView(APIView):
    """Delete users token"""
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(request.GET.get('next', 'dashboard'))
        try:
            Token.objects.get(user=request.user).delete()
        except Token.DoesNotExist:
            pass
        return Response({"message": "Token has been deleted."})
