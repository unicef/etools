from etools.libraries.djangolib.models import GroupWrapper

FMUser = GroupWrapper(code='fm_user',
                      name='FM User')

MonitoringVisitApprover = GroupWrapper(code='monitoring_visit_approver',
                                       name='Monitoring Visit Approver')

ReportReviewer = GroupWrapper(code='report_reviewer',
                              name='Report Reviewer')
