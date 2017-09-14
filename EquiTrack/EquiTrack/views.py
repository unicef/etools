from django.views.generic import TemplateView


class MainView(TemplateView):
    template_name = 'choose_login.html'


class OutdatedBrowserView(TemplateView):
    template_name = 'outdated_browser.html'
