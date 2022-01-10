from django.db import models
from django.utils.translation import gettext as _

from unicef_attachments.models import Attachment as NewAttachment


class AttachmentFlatManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(source="Trips")


class AttachmentFlat(models.Model):
    attachment = models.ForeignKey(
        NewAttachment,
        related_name="denormalized",
        on_delete=models.CASCADE,
    )
    partner = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Partner')
    )
    partner_type = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Partner Type')
    )
    vendor_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Vendor Number')
    )
    pd_ssfa = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('PD SSFA ID')
    )
    pd_ssfa_number = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('PD SSFA Number')
    )
    agreement_reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Agreement Reference Number')
    )
    object_link = models.URLField(
        blank=True,
        verbose_name=_('Object Link')
    )
    file_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('File Type')
    )
    file_link = models.CharField(
        max_length=1024,
        blank=True,
        verbose_name=_('File Link')
    )
    filename = models.CharField(
        max_length=1024,
        blank=True,
        verbose_name=_('File Name')
    )
    source = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Source'),
    )
    uploaded_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Uploaded by')
    )
    created = models.DateTimeField(
        verbose_name=_('Created'),
        null=True,
    )
    ip_address = models.GenericIPAddressField(default='0.0.0.0')

    objects = AttachmentFlatManager()

    def __str__(self):
        return str(self.attachment)

    @classmethod
    def get_file_types(cls):
        return cls.objects.exclude(file_type="").values_list(
            "file_type",
            flat=True
        ).distinct("file_type").order_by("file_type")
