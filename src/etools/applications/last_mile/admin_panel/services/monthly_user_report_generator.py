import calendar
from datetime import date

from dateutil.relativedelta import relativedelta

from etools.applications.last_mile.admin_panel.serializers import LastMileProfileReportSerializer
from etools.applications.last_mile.models import Profile


class MonthlyUsersReportGenerator:

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
