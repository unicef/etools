__author__ = 'jcranwellward'

from django.db import models
from django.db.models.signals import post_save
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group

from post_office import mail
from post_office.models import EmailTemplate
from filer.fields.file import FilerFileField

from EquiTrack.utils import AdminURLMixin


class TPMVisit(AdminURLMixin, models.Model):

    PLANNED = u'planned'
    COMPLETED = u'completed'
    RESCHEDULED = u'rescheduled'
    TPM_STATUS = (
        (PLANNED, u"Planned"),
        (COMPLETED, u"Completed"),
        (RESCHEDULED, u"Rescheduled"),
    )

    pca = models.ForeignKey('partners.PCA')
    status = models.CharField(
        max_length=32L,
        choices=TPM_STATUS,
        default=PLANNED,
    )
    cycle_number = models.PositiveIntegerField(
        blank=True, null=True
    )
    pca_location = models.ForeignKey(
        'partners.GwPCALocation',
        blank=True, null=True
    )
    tentative_date = models.DateField(
        blank=True, null=True
    )
    completed_date = models.DateField(
        blank=True, null=True
    )
    comments = models.TextField(
        blank=True, null=True
    )
    assigned_by = models.ForeignKey(
        'auth.User'
    )
    created_date = models.DateTimeField(
        auto_now_add=True
    )
    report = FilerFileField(
        blank=True, null=True
    )

    class Meta:
        verbose_name = u'TPM Visit'
        verbose_name_plural = u'TPM Visits'

    def save(self, **kwargs):
        if self.completed_date:
            self.status = self.COMPLETED
            location = self.pca_location
            location.tpm_visit = False
            location.save()
        super(TPMVisit, self).save(**kwargs)

    def download_url(self):
        if self.report:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" >Download</a>'.format(self.report.file.url)
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'Download Report'

    @classmethod
    def send_emails(cls, sender, instance, created, **kwargs):

        current_site = Site.objects.get_current()

        if created:

            email_name = 'tpm/visit/created'
            try:
                template = EmailTemplate.objects.get(
                    name=email_name
                )
            except EmailTemplate.DoesNotExist:
                template = EmailTemplate.objects.create(
                    name=email_name,
                    description='The email that is sent to TPM company when a visit request is created',
                    subject="TPM Visit Created",
                    content="The following TPM Visit has been created:"
                            "\r\n\r\n{{url}}"
                            "\r\n\r\nThank you."
                )

            tpm_group, created = Group.objects.get_or_create(
                name='Third Party Monitor'
            )

            tpm_users = tpm_group.user_set.all()
            if tpm_users:
                mail.send(
                    [tpm.email for tpm in tpm_users],
                    instance.assigned_by.email,
                    template=template,
                    context={
                        'url': 'http://{}{}'.format(
                            current_site.domain,
                            instance.get_admin_url()
                        )
                    },
                )
        else:

            if instance.status == TPMVisit.COMPLETED:
                state = 'Completed'
            else:
                state = 'Updated'

            email_name = 'tpm/visit/updated/completed'
            try:
                template = EmailTemplate.objects.get(
                    name=email_name
                )
            except EmailTemplate.DoesNotExist:
                template = EmailTemplate.objects.create(
                    name=email_name,
                    description='The email that is sent to the user who created the TPM Visit',
                    subject="TPM Visit {{state}}",
                    content="The following TPM Visit has been {{state}}:"
                            "\r\n\r\n{{url}}"
                            "\r\n\r\nThank you."
                )

            mail.send(
                [instance.assigned_by.email],
                template=template,
                context={
                    'state': state,
                    'url': 'http://{}{}'.format(
                        current_site.domain,
                        instance.get_admin_url()
                    )
                },
            )


post_save.connect(TPMVisit.send_emails, sender=TPMVisit)
