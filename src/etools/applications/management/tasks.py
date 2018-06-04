import logging

from django.core.mail import send_mail

from etools.applications.management.issues.checks import recheck_all_open_issues, run_all_checks
from etools.config.celery import app

logger = logging.getLogger(__name__)


@app.task
def run_all_checks_task():
    """
    Run all configured IssueChecks against the entire database.
    """
    run_all_checks()


@app.task
def recheck_all_open_issues_task():
    """
    Recheck all unresolved FlaggedIssue objects for resolution.
    """
    recheck_all_open_issues()


@app.task
def send_test_email(*args, **kwargs):
    """Task which send a test email"""

    logger.info('Test send email task started')

    subject = kwargs.get('subject', ['Test Subject'])[0]
    message = kwargs.get('message', ['Test Message'])[0]
    from_email = kwargs.get('from_email', ['from_email@unicef.org'])[0]
    user_email = kwargs.get('user_email', [])
    recipient_list = kwargs.get('recipient_list', [])
    if recipient_list:
        recipient_list = recipient_list[0].split(',')

    recipient_list.extend(user_email)

    send_mail(subject, message, from_email, recipient_list)

    logger.info('Test send email task finished')
