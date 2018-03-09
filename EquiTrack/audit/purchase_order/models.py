from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from EquiTrack.utils import get_environment
from firms.models import BaseFirm, BaseStaffMember
from notification.models import Notification


class AuditorFirm(BaseFirm):
    pass


@python_2_unicode_compatible
class AuditorStaffMember(BaseStaffMember):
    auditor_firm = models.ForeignKey(AuditorFirm, verbose_name=_('Auditor'), related_name='staff_members')

    def __str__(self):
        auditor_firm_name = ' ({})'.format(self.auditor_firm.name) if hasattr(self, 'auditor_firm') else ''
        return self.get_full_name() + auditor_firm_name

    def send_user_appointed_email(self, engagement):
        context = {
            'environment': get_environment(),
            'engagement': engagement.get_mail_context(),
            'staff_member': self.user.get_full_name(),
        }

        notification = Notification.objects.create(
            sender=self,
            recipients=[self.user.email], template_name='audit/engagement/submit_to_auditor',
            template_data=context
        )
        notification.send_notification()


class PurchaseOrderManager(models.Manager):
    def get_by_natural_key(self, order_number):
        return self.get(order_number=order_number)


@python_2_unicode_compatible
class PurchaseOrder(TimeStampedModel, models.Model):
    order_number = models.CharField(
        verbose_name=_('Purchase Order Number'),
        blank=True,
        null=True,
        unique=True,
        max_length=30
    )
    auditor_firm = models.ForeignKey(AuditorFirm, verbose_name=_('Auditor'), related_name='purchase_orders')
    contract_start_date = models.DateField(verbose_name=_('PO Date'), null=True, blank=True)
    contract_end_date = models.DateField(verbose_name=_('Contract Expiry Date'), null=True, blank=True)

    objects = PurchaseOrderManager()

    def __str__(self):
        return self.order_number

    def natural_key(self):
        return (self.order_number, )


class PurchaseOrderItemManager(models.Manager):
    def get_by_natural_key(self, purchase_order, number):
        return self.get(purchase_order=purchase_order, number=number)


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, related_name='items', verbose_name=_('Purchase Order'))
    number = models.IntegerField(verbose_name=_('PO Item Number'))

    objects = PurchaseOrderItemManager()

    class Meta:
        unique_together = ('purchase_order', 'number')

    def natural_key(self):
        return (self.purchase_order, self.number)
