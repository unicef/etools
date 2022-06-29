from django.apps import apps

Intervention = apps.get_model('partners', 'Intervention')
InterventionBudget = apps.get_model('partners', 'InterventionBudget')
InterventionManagementBudget = apps.get_model('partners', 'InterventionManagementBudget')


def initialize_intervention_budgets(instance, created: bool, **kwargs):
    if created:
        instance.management_budgets = InterventionManagementBudget.objects.create(intervention=instance)
        instance.planned_budget = InterventionBudget.objects.create(intervention=instance)


def calc_totals_on_delete(instance, **kwargs):
    try:
        intervention = Intervention.objects.get(pk=instance.intervention.pk)
    except Intervention.DoesNotExist:
        pass
    else:
        try:
            intervention.planned_budget.calc_totals()
        except InterventionBudget.DoesNotExist:
            pass
