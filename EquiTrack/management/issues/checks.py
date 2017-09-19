from abc import ABCMeta, abstractmethod
from collections import namedtuple
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from django.utils.module_loading import import_string
from EquiTrack.util_scripts import run
from .exceptions import IssueFoundException
from management.models import FlaggedIssue


ModelCheckData = namedtuple('ModelCheckData', 'object metadata')


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
            for model_instance, metadata in self.get_objects_to_check():
                try:
                    self.run_check(model_instance, metadata)
                except IssueFoundException as e:
                    issue = FlaggedIssue.get_or_new(content_object=model_instance, issue_id=self.issue_id)
                    issue.message = unicode(e)
                    issue.save()
        # todo: is it always valid to run all checks against all tenants?
        run(_inner)

    def get_queryset(self):
        """
        The default queryset of data to be checked.
        """
        return self.model.objects.all()

    def get_objects_to_check(self):
        """
        An iterable returning the ModelCheckData objects over which this check should be performed.
        Should return an iterable/queryset of ModelCheckData with object being an instance of self.model
        and metadata being an optional dictionary of additional data needed by the check.

        The default just returns the results of self.get_queryset with empty metadata
        """
        for object in self.get_queryset():
            yield ModelCheckData(object, {})

    @abstractmethod
    def run_check(self, model_instance, metadata):
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
