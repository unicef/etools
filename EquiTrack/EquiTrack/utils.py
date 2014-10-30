__author__ = 'jcranwellward'

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site

from post_office.models import EmailTemplate
from post_office import mail

admin_url_name = 'admin:{app_label}_{model_name}_{action}'


def send_mail(sender, template, variables, *recipients):
    mail.send(
        [recp for recp in recipients],
        sender,
        template=template,
        context=variables,
    )


class BaseEmail(object):

    template_name = None
    description = None
    subject = None
    content = None

    def __init__(self, object):
        self.object = object

    @classmethod
    def get_current_site(cls):
        return Site.objects.get_current()

    @classmethod
    def get_email_template(cls):
        if cls.template_name is None:
            raise NotImplemented()
        try:
            template = EmailTemplate.objects.get(
                name=cls.template_name
            )
        except EmailTemplate.DoesNotExist:
            template = EmailTemplate.objects.create(
                name=cls.template_name,
                description=cls.description,
                subject=cls.subject,
                content=cls.content
            )
        return template

    def get_context(self):
        raise NotImplemented()

    def send(self, sender, *recipients):

        send_mail(
            sender,
            self.get_email_template(),
            self.get_context(),
            *recipients
        )


class AdminURLMixin(object):
    def get_admin_url(self):
        content_type = ContentType \
            .objects \
            .get_for_model(self.__class__)
        return reverse(admin_url_name.format(
            app_label=content_type.app_label,
            model_name=content_type.model,
            action='change'
        ), args=(self.id,))


def get_changeform_link(model, link_name='View', action='change'):
    if model.id:
        url_name = admin_url_name.format(
            app_label=model._meta.app_label,
            model_name=model._meta.model_name,
            action=action
        )
        changeform_url = reverse(url_name, args=(model.id,))
        return u'<a class="btn btn-primary default" ' \
               u'onclick="return showAddAnotherPopup(this);" ' \
               u'href="{}" target="_blank">{}</a>'.format(changeform_url, link_name)
    return u''
