from __future__ import absolute_import

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.six import text_type

from management.issues.exceptions import IssueFoundException

ISSUE_CATEGORY_DATA = 'data'
ISSUE_CATEGORY_COMPLIANCE = 'compliance'
ISSUE_CATEGORY_CHOICES = (
    (ISSUE_CATEGORY_DATA, 'Data Issue'),
    (ISSUE_CATEGORY_COMPLIANCE, 'Compliance Issue'),
)

ISSUE_STATUS_NEW = 'new'
ISSUE_STATUS_PENDING = 'pending'
ISSUE_STATUS_REACTIVATED = 'reactivated'
ISSUE_STATUS_RESOLVED = 'resolved'
ISSUE_STATUS_CHOICES = (
    (ISSUE_STATUS_NEW, 'New (untriaged)'),
    (ISSUE_STATUS_PENDING, 'Pending (triaged, not resolved)'),
    (ISSUE_STATUS_REACTIVATED, 'Reactivated (was resolved but not fixed)'),
    (ISSUE_STATUS_RESOLVED, 'Resolved'),
)


@python_2_unicode_compatible
class FlaggedIssue(models.Model):
    # generic foreign key to any object in the DB
    # https://docs.djangoproject.com/en/1.11/ref/contrib/contenttypes/#generic-relations
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    issue_category = models.CharField(max_length=32, choices=ISSUE_CATEGORY_CHOICES, default=ISSUE_CATEGORY_DATA,
                                      db_index=True)
    issue_status = models.CharField(max_length=32, choices=ISSUE_STATUS_CHOICES, default=ISSUE_STATUS_NEW,
                                    db_index=True)
    issue_id = models.CharField(
        max_length=100,
        help_text='A readable ID associated with the specific issue, e.g. "pca-no-attachment"',
        db_index=True,
    )
    message = models.TextField()

    def recheck(self):
        from management.issues.checks import get_issue_check_by_id  # noqa
        check = get_issue_check_by_id(self.issue_id)
        try:
            check.run_check(self.content_object, metadata=check.get_object_metadata(self.content_object))
        except IssueFoundException as e:
            # don't change status unless it was marked resolved
            if self.issue_status == ISSUE_STATUS_RESOLVED:
                self.issue_status = ISSUE_STATUS_REACTIVATED
            self.message = text_type(e)
            self.save()
        else:
            self.issue_status = ISSUE_STATUS_RESOLVED
            self.save()

    @classmethod
    def get_or_new(cls, content_object, issue_id):
        """
        Like get_or_create except doesn't actually create the object in the database, and only
        allows for a limited set of fields.
        """
        try:
            # we can't query on content_object directly without defining a GenericRelation on every
            # model, so just do it manually from the content type and id
            ct = ContentType.objects.get_for_model(content_object)
            return cls.objects.get(content_type=ct, object_id=content_object.pk, issue_id=issue_id)
        except FlaggedIssue.DoesNotExist:
            return cls(content_object=content_object, issue_id=issue_id)

    def __str__(self):
        return self.message
