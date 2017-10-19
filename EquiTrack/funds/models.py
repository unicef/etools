from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Donor(models.Model):
    """
    Represents Donor for a Grant.
    """

    name = models.CharField(max_length=45, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class GrantManager(models.Manager):
    def get_queryset(self):
        return super(GrantManager, self).get_queryset().select_related('donor')


@python_2_unicode_compatible
class Grant(models.Model):
    """
    Represents the name of a Grant with expiration date, and Donor name.

    Relates to :model:`funds.Donor`
    """

    donor = models.ForeignKey(Donor)
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    expiry = models.DateField(null=True, blank=True)

    objects = GrantManager()

    class Meta:
        ordering = ['donor']

    def __str__(self):
        return u"{}: {}".format(
            self.donor.name,
            self.name
        )


@python_2_unicode_compatible
class FundsReservationHeader(models.Model):
    intervention = models.ForeignKey('partners.Intervention', related_name='frs', blank=True, null=True)
    vendor_code = models.CharField(max_length=20)
    fr_number = models.CharField(max_length=20, unique=True)
    document_date = models.DateField(null=True, blank=True)
    fr_type = models.CharField(max_length=50, null=True, blank=True)
    currency = models.CharField(max_length=50, null=True, blank=True)
    document_text = models.CharField(max_length=255, null=True, blank=True)

    # this is the field required for validation, this is the 'current_amount'
    intervention_amt = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Current FR Amount')
    # overall_amount
    total_amt = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='FR Overall Amount')
    # actual is also referred to as "disbursment"
    actual_amt = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Actual Cash Transfer')
    outstanding_amt = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Outstanding DCT')

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return u'{}'.format(
            self.fr_number
        )

    class Meta:
        ordering = ['fr_number']
        unique_together = ('vendor_code', 'fr_number')

    @property
    def expired(self):
        today = timezone.now().date()
        return self.end_date < today


@python_2_unicode_compatible
class FundsReservationItem(models.Model):
    fund_reservation = models.ForeignKey(FundsReservationHeader, related_name="fr_items")
    fr_ref_number = models.CharField(max_length=30, null=True, blank=True)
    line_item = models.CharField(max_length=5)

    # grant and fund will be needed for filtering in the future
    wbs = models.CharField(max_length=30, null=True, blank=True)
    grant_number = models.CharField(max_length=20, null=True, blank=True)
    fund = models.CharField(max_length=10, null=True, blank=True)
    overall_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    overall_amount_dc = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    line_item_text = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return u'{}'.format(
            self.fr_ref_number
        )

    class Meta:
        unique_together = ('fund_reservation', 'line_item')

    def save(self, **kwargs):
        if not self.fr_ref_number:
            self.fr_ref_number = '{}-{}'.format(self.fund_reservation.fr_number, self.line_item)
        return super(FundsReservationItem, self).save(**kwargs)


@python_2_unicode_compatible
class FundsCommitmentHeader(models.Model):
    vendor_code = models.CharField(max_length=20)
    fc_number = models.CharField(max_length=20, unique=True)
    document_date = models.DateField(null=True, blank=True)
    fc_type = models.CharField(max_length=50, null=True, blank=True)
    currency = models.CharField(max_length=50, null=True, blank=True)
    document_text = models.CharField(max_length=255, null=True, blank=True)
    exchange_rate = models.CharField(max_length=20, null=True, blank=True)
    responsible_person = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return u'{}'.format(
            self.fc_number
        )


@python_2_unicode_compatible
class FundsCommitmentItem(models.Model):
    fund_commitment = models.ForeignKey(FundsCommitmentHeader, related_name='fc_items')
    fc_ref_number = models.CharField(max_length=30, null=True, blank=True)
    line_item = models.CharField(max_length=5)
    wbs = models.CharField(max_length=30, null=True, blank=True)
    grant_number = models.CharField(max_length=20, null=True, blank=True)
    fund = models.CharField(max_length=10, null=True, blank=True)
    gl_account = models.CharField(max_length=15, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    fr_number = models.CharField(max_length=20, blank=True, null=True)
    commitment_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    commitment_amount_dc = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    amount_changed = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    line_item_text = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return u'{}'.format(
            self.fc_ref_number
        )

    class Meta:
        unique_together = ('fund_commitment', 'line_item')

    def save(self, **kwargs):
        if not self.fc_ref_number:
            self.fc_ref_number = '{}-{}'.format(self.fund_commitment.fc_number, self.line_item)
        return super(FundsCommitmentItem, self).save(**kwargs)
