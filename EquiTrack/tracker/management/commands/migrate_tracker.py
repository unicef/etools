__author__ = 'jcranwellward'

from decimal import Decimal

from django.utils.encoding import force_unicode
from django.core.management.base import (
    BaseCommand,
    CommandError
)
from django.contrib.gis.geos import Point

from reports import models as report_models
from locations import models as loc_models
from funds import models as fund_models
from partners import models as partner_models
from tracker import models as old_models


class Command(BaseCommand):
    """

    """
    can_import_settings = True

    def handle(self, *args, **options):
        """

        """

        ## Gateways
        #for gateway in old_models.Gateway.objects.all():
        #    new_gateway, created = loc_models.GatewayType.objects.get_or_create(
        #        name=gateway.name
        #    )
        #    if created:
        #        print "Gateway Created: {}".format(new_gateway.name)
        #
        ## Geography
        #for location in old_models.Location.objects.all():
        #
        #    new_governorate, created = loc_models.Governorate.objects.get_or_create(
        #        name=location.locality.region.governorate.name
        #    )
        #    if created:
        #        print "Governorate Created: {}".format(new_governorate.name)
        #
        #    new_region, created = loc_models.Region.objects.get_or_create(
        #        name=location.locality.region.name,
        #        governorate=new_governorate
        #    )
        #    if created:
        #        print "   Region Created: {}".format(new_region.name)
        #
        #    new_locality, created = loc_models.Locality.objects.get_or_create(
        #        name=force_unicode(location.locality.name),
        #        region=new_region,
        #        cad_code=location.locality.cad_code,
        #        cas_code=location.locality.cas_code,
        #        cas_code_un=location.locality.cas_code_un,
        #        cas_village_name=location.locality.cas_village_name
        #    )
        #    if created:
        #        print "      Locality Created: {}".format(new_locality.name)
        #
        #    new_location, created = loc_models.Location.objects.get_or_create(
        #        name=location.name,
        #        locality=new_locality,
        #        p_code=location.p_code,
        #    )
        #    if location.latitude and location.longitude:
        #        long, lat = float(location.longitude), float(location.latitude)
        #        #new_location.latitude = float(lat),
        #        #new_location.longitude = float(long),
        #        new_location.point = Point(long, lat)
        #        new_location.save()
        #
        #    if created:
        #        print "         Location Created: {}".format(new_location.name)
        #
        ## Donors
        #for grant in old_models.Grant.objects.all():
        #    new_donor, created = fund_models.Donor.objects.get_or_create(
        #        name=grant.donor.name
        #    )
        #    if created:
        #        print "Donor Created: {}".format(new_donor.name)
        #
        #    new_grant, created = fund_models.Grant.objects.get_or_create(
        #        donor=new_donor,
        #        name=grant.name
        #    )
        #    if created:
        #        print "   Grant Created: {}".format(new_grant.name)
        #
        ## Sectors
        #sectors = old_models.Sector.objects.all()
        #for sector in sectors:
        #
        #    sector, created = report_models.Sector.objects.get_or_create(
        #        name=sector.name.rstrip().lstrip(),
        #    )
        #    if created:
        #        sector.description = sector.description
        #        sector.save()
        #        print "Sector Created: {}".format(sector.name)
        #
        ## Outputs
        #rrp5_outputs = old_models.Rrp5Output.objects.filter()
        #
        #for rrp5 in rrp5_outputs:
        #    new_rrp5_output, created = report_models.Rrp5Output.objects.get_or_create(
        #        sector=report_models.Sector.objects.get(name=rrp5.sector.name),
        #        code=rrp5.code,
        #        name=rrp5.name.rstrip().lstrip()
        #    )
        #    if created:
        #        print "      RRP5 Output Created: {}".format(new_rrp5_output.name)
        #
        #for goal in old_models.Goal.objects.all():
        #    new_goal, created = report_models.Goal.objects.get_or_create(
        #        sector=report_models.Sector.objects.get(name=goal.sector.name),
        #        name=goal.name.rstrip().lstrip(),
        #        description=goal.description.rstrip().lstrip(),
        #    )
        #    if created:
        #        print "      Goal Created: {}".format(new_goal.name)
        #
        #for unit in old_models.Unit.objects.all():
        #    new_unit, created = report_models.Unit.objects.get_or_create(
        #        type=unit.type.rstrip().lstrip()
        #    )
        #    if created:
        #        print "      Unit Created: {}".format(new_unit.type)

        for ir in old_models.IntermediateResult.objects.all():

            if not report_models.IntermediateResult.objects.filter(name=ir.name.rstrip().lstrip()).count() == 1:
                new_itermeidate_result, created = report_models.IntermediateResult.objects.get_or_create(
                    sector=report_models.Sector.objects.get(name=ir.sector.name.rstrip().lstrip()),
                    ir_wbs_reference=ir.ir_wbs_reference.rstrip().lstrip(),
                    name=ir.name.rstrip().lstrip()
                )
                if created:
                    print "      IR Created: {}".format(new_itermeidate_result.name)

        for wbs in old_models.WBS.objects.all():
            if not report_models.WBS.objects.filter(name=wbs.name.rstrip().lstrip()).count() == 1:
                new_wbs, created = report_models.WBS.objects.get_or_create(
                    Intermediate_result=report_models.IntermediateResult.objects.get(name=wbs.ir.name.rstrip().lstrip()),
                    name=wbs.name.rstrip().lstrip(),
                    code=wbs.code.rstrip().lstrip()
                )
                if created:
                    print "      WBS Created: {}".format(new_wbs.name)

        # PCAs
        current_pcas = old_models.PCA.objects.all()
        for pca in current_pcas:

            new_partner, created = partner_models.PartnerOrganization.objects.get_or_create(
                name=pca.partner.name,
                description=pca.partner.description,
                email=pca.partner.email,
                contact_person=pca.partner.contact_person,
                phone_number=pca.partner.phone_number
            )
            if created:
                print "Partner Created: {}".format(new_partner.name)

            new_pca, created = partner_models.PCA.objects.get_or_create(
                number=pca.number,
                partner=new_partner,
            )
            if created:
                print "PCA Created: {}".format(new_pca.number)

            new_pca.title = pca.title
            new_pca.status = pca.status
            new_pca.start_date = pca.start_date
            new_pca.end_date = pca.end_date
            new_pca.initiation_date = pca.initiation_date
            new_pca.signed_by_unicef_date = pca.signed_by_unicef_date
            new_pca.unicef_mng_first_name = pca.unicef_mng_first_name
            new_pca.unicef_mng_last_name = pca.unicef_mng_last_name
            new_pca.unicef_mng_email = pca.unicef_mng_email
            new_pca.signed_by_partner_date = pca.signed_by_partner_date
            new_pca.partner_mng_first_name = pca.partner_mng_first_name
            new_pca.partner_mng_last_name = pca.partner_mng_last_name
            new_pca.partner_mng_email = pca.partner_mng_email
            new_pca.partner_contribution_budget = pca.partner_contribution_budget
            new_pca.unicef_cash_budget = pca.unicef_cash_budget
            new_pca.in_kind_amount_budget = pca.in_kind_amount_budget
            new_pca.cash_for_supply_budget = pca.cash_for_supply_budget
            new_pca.total_cash = pca.total_cash
            new_pca.received_date = pca.received_date
            new_pca.is_approved = pca.is_approved
            new_pca.save()

            for grant in old_models.PcaGrant.objects.filter(pca=pca):
                pca_grant, created = partner_models.PcaGrant.objects.get_or_create(
                    pca=new_pca,
                    grant=partner_models.Grant.objects.get(name=grant.grant.name),
                    funds=grant.funds
                )
                if created:
                    print "   PCA Grant Created: {} | Funds {}".format(
                        pca_grant.grant.name,
                        pca_grant.funds
                    )

            for old_pac_loc in old_models.GwPcaLoc.objects.filter(pca=pca):
                location = loc_models.Location.objects.get(
                    name=old_pac_loc.location.name,
                    p_code=old_pac_loc.location.p_code,
                )

                new_pca_loc, created = partner_models.GwPcaLocation.objects.get_or_create(
                    pca=new_pca,
                    name=old_pac_loc.name,
                    governorate=location.locality.region.governorate,
                    region=location.locality.region,
                    locality=location.locality,
                    gateway=loc_models.GatewayType.objects.get(
                        name=old_pac_loc.gateway.name
                    ),
                    location=location
                )
                if created:
                    print "   PCA Location Created: {}".format(new_pca_loc.name)

            # Sectors
            pca_sectors = old_models.PcaSector.objects.filter(pca=pca)
            for pca_sector in pca_sectors:
                sector=report_models.Sector.objects.get(name=pca_sector.sector.name)
                new_pca_sector, created = partner_models.PCASector.objects.get_or_create(
                    pca=new_pca,
                    sector=sector
                )
                if created:
                    print "   PCA Sector Created: {}".format(new_pca_sector.sector.name)

                # Outputs
                pca_rrp5_outputs = old_models.PcaRrp5Output.objects.filter(
                    pca=pca,
                    rrp5_output__sector__name=sector.name
                )
                for pca_rrp5 in pca_rrp5_outputs:
                    new_rrp5_output = report_models.Rrp5Output.objects.get(name=pca_rrp5.rrp5_output.name)
                    new_pca_sector.RRP5_outputs.add(new_rrp5_output)

                # Indicators
                pca_targets = old_models.PcaTargetProgress.objects.filter(pca=pca)
                for pca_target in pca_targets:
                    target_progress = old_models.TargetProgress.objects.filter(
                        target_id=pca_target.target_id
                    )[0]

                    new_indicator, created = report_models.Indicator.objects.get_or_create(
                        goal=report_models.Goal.objects.get(name=target_progress.target.goal.name.rstrip().lstrip()),
                        unit=report_models.Unit.objects.get(type=target_progress.unit.type),
                        name=target_progress.target.name.rstrip().lstrip(),
                        total=target_progress.total
                    )
                    if created:
                        print "      Indicator Created: {} | Total: {}".format(new_indicator.name,
                                                                               new_indicator.total)

                    new_indicator_progress, created = partner_models.IndicatorProgress.objects.get_or_create(
                        pca_sector=new_pca_sector,
                        indicator=new_indicator,
                        programmed=pca_target.total,
                        current=pca_target.current
                    )
                    if created:
                        print "      Indicator Progress Created: {} | Programmed: {} | Current: {}".format(
                            new_indicator_progress.indicator.name,
                            new_indicator_progress.programmed,
                            new_indicator_progress.current
                        )

                # WBS
                old_wbs = old_models.PcaWbs.objects.filter(pca=pca)
                for pca_wbs in old_wbs:
                    ir = report_models.IntermediateResult.objects.get(name=pca_wbs.wbs.ir.name.lstrip().rstrip())
                    wbs = report_models.WBS.objects.get(name=pca_wbs.wbs.name.lstrip().rstrip())

                    new_pca_ir, created = partner_models.PCASectorImmediateResult.objects.get_or_create(
                        pca_sector=new_pca_sector,
                        Intermediate_result=ir
                    )
                    new_pca_ir.wbs_activities.add(wbs)


                # Activites
                old_activities = old_models.PcaActivity.objects.filter(
                    pca=pca,
                    activity__sector__name=new_pca_sector.sector.name.rstrip().lstrip())
                for pca_activity in old_activities:
                    new_activity, created = report_models.Activity.objects.get_or_create(
                        sector=report_models.Sector.objects.get(name=pca_activity.activity.sector.name),
                        name=pca_activity.activity.name.rstrip().lstrip(),
                        type=pca_activity.activity.type
                    )
                    if created:
                        print "      Activity Created: {}".format(new_activity.name)

                    new_pca_sector.activities.add(new_activity)