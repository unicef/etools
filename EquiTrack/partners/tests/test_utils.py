import datetime
from EquiTrack.factories import UserFactory, GroupFactory, PartnerFactory, AgreementFactory, InterventionFactory, \
    ResultFactory, FundsReservationHeaderFactory, LocationFactory, GatewayTypeFactory
from partners.models import Intervention, InterventionBudget, InterventionResultLink
from reports.models import ResultType, LowerResult, IndicatorBlueprint, AppliedIndicator


def setup_intervention_test_data(test_case, include_results_and_indicators=False):
    today = datetime.date.today()
    test_case.unicef_staff = UserFactory(is_staff=True)
    test_case.partnership_manager_user = UserFactory(is_staff=True)
    test_case.partnership_manager_user.groups.add(GroupFactory())
    test_case.partner = PartnerFactory(name='Partner 1')
    test_case.partner1 = PartnerFactory(name='Partner 2')
    test_case.agreement = AgreementFactory(partner=test_case.partner, signed_by_unicef_date=datetime.date.today())

    test_case.active_agreement = AgreementFactory(
        partner=test_case.partner1,
        status='active',
        signed_by_unicef_date=datetime.date.today(),
        signed_by_partner_date=datetime.date.today()
    )

    test_case.intervention = InterventionFactory(agreement=test_case.agreement, title='Intervention 1')
    test_case.intervention_2 = InterventionFactory(agreement=test_case.agreement, title='Intervention 2',
                                                   document_type=Intervention.PD)
    test_case.active_intervention = InterventionFactory(
        agreement=test_case.active_agreement,
        title='Active Intervention',
        document_type=Intervention.PD,
        start=today - datetime.timedelta(days=1),
        end=today + datetime.timedelta(days=90),
        status='active',
        signed_by_unicef_date=today - datetime.timedelta(days=1),
        signed_by_partner_date=today - datetime.timedelta(days=1),
        unicef_signatory=test_case.unicef_staff,
        partner_authorized_officer_signatory=test_case.partner1.staff_members.all().first()
    )

    test_case.result_type = ResultType.objects.get_or_create(name=ResultType.OUTPUT)[0]
    test_case.result = ResultFactory(result_type=test_case.result_type)

    test_case.partnership_budget = InterventionBudget.objects.create(
        intervention=test_case.intervention,
        unicef_cash=10,
        unicef_cash_local=100,
        partner_contribution=20,
        partner_contribution_local=200,
        in_kind_amount_local=10,
    )

    # set up two frs not connected to any interventions
    test_case.fr_1 = FundsReservationHeaderFactory(intervention=None, currency='USD')
    test_case.fr_2 = FundsReservationHeaderFactory(intervention=None, currency='USD')

    if include_results_and_indicators:
        # setup additional inicator/results
        test_case.result = ResultFactory(name='A Result')
        test_case.result_link = InterventionResultLink.objects.create(
            intervention=test_case.active_intervention, cp_output=test_case.result)
        test_case.lower_result = LowerResult.objects.create(result_link=test_case.result_link,
                                                            name='Lower Result 1')
        test_case.indicator_blueprint = IndicatorBlueprint.objects.create(
            title='The Blueprint'
        )
        test_case.applied_indicator = AppliedIndicator.objects.create(
            indicator=test_case.indicator_blueprint,
            lower_result=test_case.lower_result,
        )
        test_case.applied_indicator.locations.add(LocationFactory(
            name='A Location',
            gateway=GatewayTypeFactory(name='A Gateway'),
            p_code='a-p-code')
        )
        test_case.disaggregation = test_case.applied_indicator.disaggregation.create(name='A Disaggregation')
