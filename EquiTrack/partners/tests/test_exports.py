__author__ = 'jcranwellward'

from django.test import TestCase

from partners.models import GwPCALocation, PCA, PartnerOrganization
from partners.utils import generate_kml


class TestKMLExport(TestCase):

    def test_kml_generation(self):


        self.assertTrue(False)