__author__ = 'jcranwellward'

import datetime

from django.db import transaction
from django.core.management.base import (
    BaseCommand,
    CommandError
)
from django.contrib.auth.models import User, Group
import reversion

from partners.models import (
    PCA,
    PartnershipBudget,
    PartnerStaffMember,
    Agreement,
    AmendmentLog
)


class Command(BaseCommand):

    def handle(self, *args, **options):

        # create agreements
        for partnership in PCA.objects.filter(amendment=False, partnership_type=u'pca', status__in=[
            PCA.IMPLEMENTED, PCA.IN_PROCESS, PCA.ACTIVE
        ]):

            partner_staff, created = PartnerStaffMember.objects.get_or_create(
                partner=partnership.partner,
                email=partnership.partner_mng_email,
                first_name=partnership.partner_mng_first_name,
                last_name=partnership.partner_mng_last_name,
            )
            if created:
                print(u'1. Created partner staff: {}'.format(partner_staff))

            pca, created = Agreement.objects.get_or_create(
                partner=partnership.partner,
                agreement_type=Agreement.PCA,
                agreement_number=partnership.number,
            )
            if created:
                print(u'2. Created new PCA: {}'.format(pca))

            pca.signed_by_unicef_date = partnership.signed_by_unicef_date
            try:
                print(u'3. Get user for email: {}'.format(partnership.unicef_mng_email))
                pca.signed_by = User.objects.get(email=partnership.unicef_mng_email)
                group, created = Group.objects.get_or_create(
                    name=u'Senior Management Team'
                )
                group.user_set.add(pca.signed_by)
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                print(u'User {} does not exist (check email address on {}) or many users with same email'.format(
                    partnership.unicef_mng_email, partnership)
                )

            pca.signed_by_partner_date = partnership.signed_by_partner_date
            pca.partner_manager = partner_staff

            if partnership.start_date and partnership.end_date:
                pca.start = datetime.datetime.combine(
                    partnership.start_date,
                    datetime.time(00, 00)
                )
                pca.end = datetime.datetime.combine(
                    partnership.end_date,
                    datetime.time(00, 00)
                )
            pca.partner_staff_members.add(partner_staff)
            pca.save()

            PartnershipBudget.objects.create(
                partnership=partnership,
                partner_contribution=partnership.partner_contribution_budget,
                unicef_cash=partnership.unicef_cash_budget,
                in_kind_amount=partnership.in_kind_amount_budget,
            )

            partnership.agreement = pca
            partnership.partnership_type = PCA.PD
            partnership.partner_manager = partner_staff
            partnership.unicef_manager = pca.signed_by

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
                        print(u'5. New amendment log entry for {}: {}'.format(partnership, amendment_log))

                    if not partnership.budget_log.filter(amendment=amendment_log).exists():
                            budget = PartnershipBudget.objects.create(
                                partnership=partnership,
                                partner_contribution=amendment.partner_contribution_budget or 0,
                                unicef_cash=amendment.unicef_cash_budget or 0,
                                in_kind_amount=amendment.in_kind_amount_budget or 0,
                                amendment=amendment_log
                            )
                            print(u'6. Amended budget: {}'.format(budget))

                    # migrate grants
                    for grant in amendment.grants.all():
                        if grant not in partnership.grants.all():
                            grant.partnership = partnership
                            grant.amendment = amendment_log
                            grant.save()

                    # migrate sectors
                    for sector in amendment.pcasector_set.all():
                        if sector not in partnership.pcasector_set.all():
                            sector.pca = partnership
                            sector.amendment = amendment_log
                            sector.save()

                    for file in partnership.pcafile_set.all():
                        file.pca = partnership
                        file.save()

                    for location in partnership.locations.all():
                        location.pca = partnership
                        location.save()

                    if amendment.end_date:
                        partnership.end_date = amendment.end_date

                    if amendment.signed_by_partner_date:
                        partnership.signed_by_partner_date = amendment.signed_by_partner_date

                    if amendment.signed_by_unicef_date:
                        partnership.signed_by_unicef_date = amendment.signed_by_unicef_date

                    for manager in amendment.unicef_managers.all():
                        partnership.unicef_managers.add(manager)

                    partnership.save()

                    if partnership.end_date:
                        pca.end = datetime.datetime.combine(
                            partnership.end_date,
                            datetime.time(00, 00)
                        )
                        pca.save()

                # make manual revision point
                reversion.set_comment("Merged amendments for partnership: {}".format(
                    partnership.number)
                )
