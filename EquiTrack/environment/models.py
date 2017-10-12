from django.utils.encoding import python_2_unicode_compatible
from django.db import models


@python_2_unicode_compatible
class IssueCheckConfig(models.Model):
    """
    Used to enable/disable issue checks at runtime.
    """
    check_id = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return '{}: {}'.format(self.check_id, self.is_active)
