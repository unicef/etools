
from EquiTrack.celery import app
from management.issues.checks import recheck_all_open_issues, run_all_checks


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
