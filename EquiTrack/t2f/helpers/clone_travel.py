from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist


class CloneTravelHelper(object):
    def __init__(self, travel):
        self.travel = travel

    def clone_for_secondary_traveler(self, new_traveler):
        fk_related = ['itinerary', 'expenses', 'deductions', 'cost_assignments']
        o2o_related = ['clearances']
        new_travel = self._do_the_cloning(new_traveler, fk_related, o2o_related)
        new_travel.activities = self.travel.activities.all()

        return new_travel

    def clone_for_driver(self, new_traveler):
        fk_related = ['itinerary']
        o2o_related = ['clearances']
        new_travel = self._do_the_cloning(new_traveler, fk_related, o2o_related)
        new_travel.is_driver = True
        new_travel.save()
        return new_travel

    def _do_the_cloning(self, new_traveler, fk_related, o2o_related):
        new_travel = self._clone_model(self.travel)
        new_travel.traveler = new_traveler
        new_travel.reset_status()
        new_travel.save()

        cloned_models = self._clone_related(fk_related, o2o_related)
        for new_related in cloned_models:
            new_related.travel = new_travel
            new_related.save()

        return new_travel

    def _clone_related(self, fk_related=None, o2o_related=None):
        fk_related = fk_related or []
        o2o_related = o2o_related or []
        cloned_models = []

        for relation_name in fk_related:
            related_qs = getattr(self.travel, relation_name).all()
            new_models = self._clone_model_list(related_qs)
            cloned_models.extend(new_models)

        for relation_name in o2o_related:
            try:
                related = getattr(self.travel, relation_name)
            except ObjectDoesNotExist:
                continue
            new_related = self._clone_model(related)
            cloned_models.append(new_related)

        return cloned_models

    def _clone_model_list(self, model_list):
        return map(self._clone_model, model_list)

    def _clone_model(self, model):
        from t2f.models import make_travel_reference_number

        new_instance = model.__class__.objects.get(pk=model.pk)
        new_instance.pk = None
        new_instance.id = None

        new_instance.reference_number = make_travel_reference_number()
        return new_instance
