__author__ = 'jcranwellward'

from import_export import resources

from partners.models import PCA


class PCAResource(resources.ModelResource):

    class Meta:
        model = PCA