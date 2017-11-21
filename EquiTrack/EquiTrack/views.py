from django.views.generic import TemplateView
from django.db import connection


class MainView(TemplateView):
    template_name = 'choose_login.html'


class OutdatedBrowserView(TemplateView):
    template_name = 'outdated_browser.html'


class PublicTenantMixin(object):

    def get_queryset(self):
        if connection.schema_name == 'public':
            return self.serializer_class.Meta.model.objects.none()
        else:
            return self.serializer_class.Meta.model.objects.all()