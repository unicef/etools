from abc import ABCMeta, abstractmethod
from collections import namedtuple
import logging
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from django.utils.module_loading import import_string
from EquiTrack.util_scripts import run
from environment.models import IssueCheckConfig
from .exceptions import IssueFoundException, IssueCheckNotFoundException
from management.models import FlaggedIssue, ISSUE_STATUS_RESOLVED


ModelCheckData = namedtuple('ModelCheckData', 'object metadata')


class BaseIssueCheck(object):
    """
    Base class for all Issue Checks
    """
    __metaclass__ = ABCMeta
    model = None  # the model class that this check runs against.
    check_id = None  # a unique id for the issue check type.

    def __init__(self):
        if self.model is None or not issubclass(self.model, Model):
            raise ImproperlyConfigured('Issue checks must define a model class that subclasses models.Model!')
        if not self.check_id:
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
                    issue = FlaggedIssue.get_or_new(content_object=model_instance, issue_id=self.check_id)
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


def get_available_issue_checks():
    """
    Get all issue checks from the configured settings.
    """
    check_ids = set()
    for check_path in settings.ISSUE_CHECKS:
        check = get_issue_check(check_path)
        if check.check_id in check_ids:
            raise ImproperlyConfigured(
                'Duplicate Issue Check ID {} is not allowed! See settings.ISSUE_CHECKS'.format(check.check_id)
            )
        check_ids.add(check.check_id)
        yield get_issue_check(check_path)


def get_active_issue_checks():
    """
    Get all *active* issue checks from the configured settings / database.
    """
    bootstrap_checks(default_is_active=False)
    active_checks = set(IssueCheckConfig.objects.filter(is_active=True).values_list('check_id', flat=True))
    for check in get_available_issue_checks():
        if check.check_id in active_checks:
            yield check


def get_issue_check_by_id(check_id):
    # todo: might make sense to cache this if it's going to be called frequently
    for check in get_available_issue_checks():
        if check.check_id == check_id:
            return check
    raise IssueCheckNotFoundException('No issue check with ID {} found.'.format(check_id))


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
    for issue_check in get_active_issue_checks():
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


def bootstrap_checks(default_is_active=False):
    """
    Bootstraps the IssueCheckConfig objects for all IssueChecks in the database.
    """
    for issue_check in get_available_issue_checks():
        if not IssueCheckConfig.objects.filter(check_id=issue_check.check_id).exists():
            IssueCheckConfig.objects.create(check_id=issue_check.check_id, is_active=default_is_active)
