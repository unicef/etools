import calendar
from datetime import date

from django.conf import settings

from dateutil.relativedelta import relativedelta
from unicef_notification.utils import send_notification

from etools.applications.last_mile.admin_panel.serializers import LastMileProfileReportSerializer
from etools.applications.last_mile.models import Profile
from etools.applications.users.models import User


class LastMileAdminPanelUtils:

    def generate_data_for_monthly_users_created_report(self, tenant_name):
        today = date.today()
        first_day_of_last_month = (today.replace(day=1) - relativedelta(months=1))
        year, month = first_day_of_last_month.year, first_day_of_last_month.month
        last_day = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)

        filter_data = Profile.objects.filter(
            created_on__date__range=[start_date, end_date], user__realms__country__schema_name=tenant_name
        ).distinct()

        return LastMileProfileReportSerializer(filter_data, many=True).data

    def send_email_notification(self, tenant_name):
        monthly_data = self.generate_data_for_monthly_users_created_report(tenant_name)
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
