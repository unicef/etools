from django.db import connection
from django.utils import timezone

from etools.applications.partners.models import Intervention
from etools.applications.users.models import Country
from etools.config.celery import app


@app.task
def transfer_active_pds_to_new_cp():
    today = timezone.now().date()

    original_tenant = connection.tenant
    try:
        for country in Country.objects.exclude(name='Global'):
            connection.set_tenant(country)

            outdated_active_pds = Intervention.objects.filter(
                status__in=[
                    Intervention.DRAFT,
                    Intervention.SIGNED,
                    Intervention.ACTIVE,
                ],
                end__gt=today,
                agreement__country_programme__invalid=False,
                agreement__country_programme__to_date__lte=today,
            ).prefetch_related(
                'agreement__partner'
            )

            for pd in outdated_active_pds:
                partner = pd.agreement.partner
                active_pca = partner.agreements.filter(
                    country_programme__to_date__gt=today,
                    country_programme__invalid=False
                ).first()
                if not active_pca:
                    continue

                pd.agreement = active_pca
                pd.save()
    finally:
        connection.set_tenant(original_tenant)
