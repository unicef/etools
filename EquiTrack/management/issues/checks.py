from abc import ABCMeta, abstractmethod
from collections import namedtuple
import logging
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from django.utils.module_loading import import_string
from EquiTrack.util_scripts import run
from .exceptions import IssueFoundException, IssueCheckNotFoundException
from management.models import FlaggedIssue, ISSUE_STATUS_RESOLVED


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

    def get_object_metadata(self, model_instance):
        """
        Return any necessary metadata associated with an object. Necessary during rechecks.
        """
        return {}

    @abstractmethod
    def run_check(self, model_instance, metadata):
        """
        This method should raise an IssueFoundException if the check fails.
        """
        raise ImproperlyConfigured('Issue checks must override the run_check function!')


def get_issue_checks():
    check_ids = set()
    for check_path in settings.ISSUE_CHECKS:
        check = get_issue_check(check_path)
        if check.issue_id in check_ids:
            raise ImproperlyConfigured(
                'Duplicate Issue Check ID {} is not allowed! See settings.ISSUE_CHECKS'.format(check.issue_id)
            )
        check_ids.add(check.issue_id)
        yield get_issue_check(check_path)


def get_issue_check_by_id(issue_id):
    # todo: might make sense to cache this if it's going to be called frequently
    for check in get_issue_checks():
        if check.issue_id == issue_id:
            return check
    raise IssueCheckNotFoundException('No issue check with ID {} found.'.format(issue_id))


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


def run_all_checks():
    """
    Run all configured issue checks. Note that this function might take a long time to complete on a large
    database.
    """
    for issue_check in get_issue_checks():
        issue_check.check_all()


def recheck_all_open_issues():
    """
    Recheck all unresolved FlaggedIssue objects for resolution.
    """
    def _check():
        for issue in FlaggedIssue.objects.exclude(issue_status=ISSUE_STATUS_RESOLVED):
            try:
                issue.recheck()
            except IssueCheckNotFoundException as e:
                # todo: should this fail hard?
                logging.error(unicode(e))

    # todo: is it always valid to run all checks against all tenants?
    run(_check)
