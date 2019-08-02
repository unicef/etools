from etools.applications.core.util_scripts import set_country
from etools.applications.reports.models import Indicator, Result
from etools.applications.users.models import Country

model = Result
for workspace in Country.objects.exclude(schema_name='public'):
    set_country(workspace.name)
    if model.objects.filter(sector__isnull=False).exists():
        print(model.objects.filter(sector__isnull=False).count(), workspace)

# 5 China
# 21 FRG
# 2 Sierra Leone
# 55 UAT

model = Indicator
for workspace in Country.objects.exclude(schema_name='public'):
    set_country(workspace.name)
    if model.objects.filter(sector__isnull=False).exists():
        print(model.objects.filter(sector__isnull=False).count(), workspace)

# 2 Cambodia
# 1 China
# 8 FRG
# 16 Sierra Leone
# 27 UAT
