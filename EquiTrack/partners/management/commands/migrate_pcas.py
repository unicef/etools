__author__ = 'jcranwellward'

from django.core.management.base import (
    BaseCommand,
    CommandError
)

from partners.models import (
    PCA,
    PCASectorOutput,
    PCASectorGoal,
    PCASectorActivity,
)


class Command(BaseCommand):
    """

    """
    can_import_settings = True

    def handle(self, *args, **options):

        for pca in PCA.objects.all():

            for pca_sector in pca.pcasector_set.all():

                for output in pca_sector.RRP5_outputs.all():
                    PCASectorOutput.objects.get_or_create(
                        pca_sector=pca_sector,
                        output=output
                    )
                    print "Created output: {}".format(output.name)

                for indicator in pca_sector.indicatorprogress_set.all():
                    PCASectorGoal.objects.get_or_create(
                        pca_sector=pca_sector,
                        goal=indicator.indicator.goal
                    )
                    print "Created goal: {}".format(indicator.indicator.goal.name)

                for activity in pca_sector.activities.all():
                    PCASectorActivity.objects.get_or_create(
                        pca_sector=pca_sector,
                        activity=activity
                    )
                    print "Created activity: {}".format(activity.name)
