from django.conf import settings
from django.db import models

from django_tenants.models import DomainMixin


class Domain(DomainMixin):
    """ Tenant Domain Model"""

    def __str__(self):
        return f'{self.domain} [{self.tenant.schema_name}]'


class BulkDeactivationLog(models.Model):
    """
    Generic model for tracking bulk deactivation operations.

    This model can log bulk deactivations for any model type.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="User who performed the bulk deactivation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    affected_count = models.IntegerField(help_text="Number of records deactivated")

    # Information about what was deactivated
    model_name = models.CharField(
        max_length=100,
        help_text="Name of the model that was bulk deactivated"
    )
    app_label = models.CharField(
        max_length=100,
        help_text="App label of the model that was bulk deactivated"
    )
    affected_ids = models.JSONField(
        default=list,
        help_text="List of IDs of the records that were deactivated"
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Bulk Deactivation Log"
        verbose_name_plural = "Bulk Deactivation Logs"

    def __str__(self):
        return (
            f"Bulk deactivated {self.affected_count} {self.model_name} "
            f"records on {self.created_at:%Y-%m-%d %H:%M}"
        )
