__author__ = 'jcranwellward'

import datetime

from django.db import transaction
from django.core.management.base import (
    BaseCommand,
    CommandError
)
from django.contrib.auth.models import User
import reversion

from partners.models import (
    PCA,
    PartnershipBudget,
    PartnerStaffMember,
    AuthorizedOfficer,
    Agreement,
    AmendmentLog
)


class Command(BaseCommand):

    def handle(self, *args, **options):

        # create agreements
        for partnership in PCA.objects.filter(amendment=False, partnership_type=u'pca'):

            partner_staff, created = PartnerStaffMember.objects.get_or_create(
                partner=partnership.partner,
                email=partnership.partner_mng_email,
                first_name=partnership.partner_mng_first_name,
                last_name=partnership.partner_mng_last_name,
            )
            if created:
                print(u'Created partner staff: {}'.format(partner_staff))

            pca, created = Agreement.objects.get_or_create(
                partner=partnership.partner,
                agreement_type=Agreement.PCA,
                agreement_number=partnership.number,
            )
            if created:
                print(u'Created new PCA: {}'.format(pca))

            officer, created = AuthorizedOfficer.objects.get_or_create(
                agreement=pca,
                officer=partner_staff
            )
            if created:
                print(u'Created authorized officer {} for {}'.format(officer, pca))

            print(u'Get user for email: {}'.format(partnership.unicef_mng_email))
            pca.signed_by_unicef_date = datetime.datetime.combine(partnership.signed_by_unicef_date, datetime.time(00, 00))
            pca.signed_by = User.objects.get(email=partnership.unicef_mng_email)

            pca.signed_by_partner_date = datetime.datetime.combine(partnership.signed_by_partner_date, datetime.time(00, 00))
            pca.partner_manager = partner_staff

            pca.save()

            PartnershipBudget.objects.create(
                partnership=partnership,
                partner_contribution=partnership.partner_contribution_budget,
                unicef_cash=partnership.unicef_cash_budget,
                in_kind_amount=partnership.in_kind_amount_budget,
            )

            partnership.agreement = pca
            partnership.save()

            # merge amendments
            amendments = PCA.objects.filter(number=partnership.number, amendment=True).order_by('amendment_number')

            with transaction.atomic(), reversion.create_revision():

                for amendment in amendments:

                    amendment_log, created = AmendmentLog.objects.get_or_create(
                        partnership=partnership,
                        type='Other',
                        amended_at=amendment.amended_at,
                        amendment_number=amendment.amendment_number
                    )
                    if created:
                        print(u'New amendment log entry for {}: {}'.format(partnership, amendment_log))

                    if amendment.unicef_cash_budget:
                        budget = PartnershipBudget.objects.create(
                            partnership=partnership,
                            partner_contribution=amendment.partner_contribution_budget,
                            unicef_cash=amendment.unicef_cash_budget,
                            in_kind_amount=amendment.in_kind_amount_budget,
                            amendment=amendment_log
                        )
                        print(u'Amended budget: {}'.format(budget))

                    # migrate grants
                    for grant in amendment.pcagrant_set.all():
                        grant.partnership = partnership
                        grant.amendment = amendment_log
                        grant.save()

                    # migrate sectors
                    for sector in amendment.pcasector_set.all():
                        sector.pca = partnership
                        sector.amendment = amendment_log
                        sector.save()

                    for file in partnership.pcafile_set.all():
                        file.pca = partnership
                        file.save()

                    for location in partnership.locations.all():
                        location.pca = partnership
                        location.save()

                    partnership.agreement = pca
                    partnership.end_date = amendment.end_date
                    partnership.signed_by_partner_date = amendment.signed_by_partner_date
                    partnership.signed_by_unicef_date = amendment.signed_by_unicef_date
                    partnership.save()

                # make manual revision point
                reversion.set_comment("Merged amendments for partnership: {}".format(
                    partnership.number)
                )
