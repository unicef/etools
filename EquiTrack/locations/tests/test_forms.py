from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from carto.exceptions import CartoException
from mock import patch, Mock

from EquiTrack.factories import GatewayTypeFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from locations import forms


class TestCartoDBTableForm(FastTenantTestCase):
    def setUp(self):
        super(TestCartoDBTableForm, self).setUp()
        self.mock_sql = Mock()
        gateway = GatewayTypeFactory()
        self.data = {
            "api_key": "123",
            "domain": "example.com",
            "table_name": "test",
            "name_col": "name",
            "pcode_col": "pcode",
            "parent_code_col": "parent",
            "location_type": gateway.pk,
        }

    def _test_clean(self, form):
        with patch("locations.forms.SQLClient.send", self.mock_sql):
            return form.is_valid()

    def test_no_connection(self):
        """Check that validation fails when SQLClient request fails"""
        self.mock_sql.side_effect = CartoException
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].args[0],
            "Couldn't connect to CartoDB table: test"
        )

    def test_no_name_col(self):
        """Check that validation fails when `name_col` is missing"""
        self.mock_sql.return_value = {"rows": [{
            "pcode": "",
            "parent": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].args[0],
            "The Name column (name) is not in table: test"
        )

    def test_no_pcode_col(self):
        """Check that validation fails when `pcode_col` is missing"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "parent": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].args[0],
            "The PCode column (pcode) is not in table: test"
        )

    def test_no_parent_code_col(self):
        """Check that validation fails when `parent_code_col` is missing"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].args[0],
            "The Parent Code column (parent) is not in table: test"
        )

    def test_clean(self):
        """Check that validation passes"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertTrue(self._test_clean(form))
        self.assertEqual(form.errors.as_data(), {})
