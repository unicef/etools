import datetime
from EquiTrack.factories import UserFactory, GroupFactory, PartnerFactory, AgreementFactory, InterventionFactory, \
    ResultFactory, FundsReservationHeaderFactory
# TODO intervention sector locations cleanup
from partners.models import Intervention, InterventionSectorLocationLink, InterventionBudget
from reports.models import ResultType, Sector


def setup_intervention_test_data(test_case):
    today = datetime.date.today()
    test_case.unicef_staff = UserFactory(is_staff=True)
    test_case.partnership_manager_user = UserFactory(is_staff=True)
    test_case.partnership_manager_user.groups.add(GroupFactory())
    test_case.partner = PartnerFactory(name='Partner 1')
    test_case.partner1 = PartnerFactory(name='Partner 2')
    test_case.agreement = AgreementFactory(partner=test_case.partner, signed_by_unicef_date=datetime.date.today())

    test_case.active_agreement = AgreementFactory(partner=test_case.partner1,
                                                  status='active',
                                                  signed_by_unicef_date=datetime.date.today(),
                                                  signed_by_partner_date=datetime.date.today())

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

    test_case.result_type = ResultType.objects.get(name=ResultType.OUTPUT)
    test_case.result = ResultFactory(result_type=test_case.result_type)

    # TODO intervention sector locations cleanup
    test_case.pcasector = InterventionSectorLocationLink.objects.create(
        intervention=test_case.intervention,
        sector=Sector.objects.create(name="Sector 1")
    )
    test_case.partnership_budget = InterventionBudget.objects.create(
        intervention=test_case.intervention,
        unicef_cash=100,
        unicef_cash_local=10,
        partner_contribution=200,
        partner_contribution_local=20,
        in_kind_amount_local=10,
    )

    # TODO intervention sector locations cleanup
    test_case.location = InterventionSectorLocationLink.objects.create(
        intervention=test_case.intervention,
        sector=Sector.objects.create(name="Sector 2")
    )
    # set up two frs not connected to any interventions
    test_case.fr_1 = FundsReservationHeaderFactory(intervention=None)
    test_case.fr_2 = FundsReservationHeaderFactory(intervention=None)
