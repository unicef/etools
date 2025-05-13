from django.conf import settings

from unicef_notification.utils import send_notification

from etools.applications.last_mile.admin_panel.services.MonthlyUsersReportGenerator import MonthlyUsersReportGenerator
from etools.applications.users.models import User


class MonthlyUsersReportNotificator:

    def send_email_notification(self, tenant_name):
        monthly_data = MonthlyUsersReportGenerator().generate_data_for_monthly_users_created_report(tenant_name)
        users_to_send_email = User.objects \
            .filter(realms__country__schema_name=tenant_name,
                    realms__is_active=True,
                    realms__group__name='LMSM User Creation Report') \
            .values_list('email', flat=True) \
            .distinct()
        send_notification(
            recipients=list(users_to_send_email),
            from_address=settings.DEFAULT_FROM_EMAIL,
            subject='LMSM : Monthly User Creation Report',
            html_content_filename='emails/last_mile_users.html',
            context={"monthly_data": monthly_data}
        )
