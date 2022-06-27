def intervention_budgets_initialization_on_create(instance, created, **kwargs):
    if created:
        InterventionManagementBudget = instance._meta.get_field('management_budgets').related_model
        instance.management_budgets = InterventionManagementBudget.objects.create(intervention=instance)
        InterventionBudget = instance._meta.get_field('planned_budget').related_model
        instance.planned_budget = InterventionBudget.objects.create(intervention=instance)
