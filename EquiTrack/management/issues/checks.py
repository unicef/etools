from abc import ABCMeta, abstractmethod
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from django.utils.module_loading import import_string
from EquiTrack.util_scripts import run
from .exceptions import IssueFoundException
from management.models import FlaggedIssue


class BaseIssueCheck(object):
    """
    Base class for all Issue Checks
    """
    __metaclass__ = ABCMeta
    model = None
    issue_id = None

    def __init__(self):
        if self.model is None or not issubclass(self.model, Model):
            raise ImproperlyConfigured('Issue checks must define a model class that subclasses models.Model!')
        if not self.issue_id:
            raise ImproperlyConfigured('Issue checks must define a unique ID!')

    def check_all(self):
        """
        Check all objects for issues.
        """
        def _inner():
            for model_instance in self.get_queryset():
                try:
                    self.run_check(model_instance)
                except IssueFoundException as e:
                    issue = FlaggedIssue.get_or_new(content_object=model_instance, issue_id=self.issue_id)
                    issue.message = unicode(e)
                    issue.save()
        # todo: is it always valid to run all checks against all tenants?
        run(_inner)

    def get_queryset(self):
        """
        The queryset over which this check should be performed.
        Defaults to all matching models.
        """
        return self.model.objects.all()

    @abstractmethod
    def run_check(self, model_instance):
        """
        This method should raise an IssueFoundException if the check fails.
        """
        raise ImproperlyConfigured('Issue checks must override the run_check function!')


def get_issue_checks():
    for check_path in settings.ISSUE_CHECKS:
        yield get_issue_check(check_path)


# todo: should probably cache this with something like lru_cache
def get_issue_check(import_path):
    """
    Import the issue check class described by import_path, where
    import_path is the full Python path to the class.
    """
    IssueCheck = import_string(import_path)
    if not issubclass(IssueCheck, BaseIssueCheck):
        raise ImproperlyConfigured('Issue Check "%s" is not a subclass of "%s"' %
                                   (IssueCheck, BaseIssueCheck))
    return IssueCheck()
