import traceback

from django.conf import settings
from django.db import transaction
from django.contrib.sites.models import Site

from post_office import mail
from post_office.models import EmailTemplate


def send_mail(sender, recipients, template, variables,
              attachments=None, cc_list=None, bcc_list=None, notification_obj=None):
    """
    Single mail send hook that is reused across the project
    """
    try:
        mail.send(
            recipients,
            sender,
            template=template,
            context=variables,
            attachments=attachments,
            cc=cc_list,
            bcc=bcc_list
        )
    except Exception as exp:
        print exp.message
        print traceback.format_exc()
    else:
        with transaction.atomic():
            if notification_obj:
                notification_obj.sent_recipients = recipients
                notification_obj.save()


class BaseEmail(object):
    """
    Base class for providing email templates in code
    that can be overridden in the django admin
    """
    template_name = None
    description = None
    subject = None
    content = None

    def __init__(self, object):
        self.object = object

    @classmethod
    def get_environment(cls):
        return settings.ENVIRONMENT

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
        """
        Provides context variables for the email template.
        Must be implemented in inheriting class
        """
        raise NotImplemented()

    def send(self, sender, *recipients):

        send_mail(
            sender,
            *recipients,
            template=self.get_email_template(),
            variables=self.get_context()
        )
