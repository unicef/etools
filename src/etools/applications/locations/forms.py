
import logging

from django import forms
from django.core.exceptions import ValidationError

from carto.exceptions import CartoException
from carto.sql import SQLClient

from etools.applications.locations.auth import EtoolsCartoNoAuthClient
from etools.applications.locations.models import CartoDBTable

logger = logging.getLogger(__name__)


class CartoDBTableForm(forms.ModelForm):

    class Meta:
        model = CartoDBTable
        fields = '__all__'

    def clean(self):

        domain = self.cleaned_data['domain']
        table_name = self.cleaned_data['table_name']
        name_col = self.cleaned_data['name_col']
        pcode_col = self.cleaned_data['pcode_col']
        parent_code_col = self.cleaned_data['parent_code_col']
        auth_client = EtoolsCartoNoAuthClient(base_url="https://{}.carto.com/".format(str(domain)))

        sql_client = SQLClient(auth_client)
        try:
            sites = sql_client.send('select * from {} limit 1'.format(table_name))
        except CartoException:
            logger.exception("CartoDB exception occured")
            raise ValidationError("Couldn't connect to CartoDB table: {}".format(table_name))
        else:
            row = sites['rows'][0]
            if name_col not in row:
                raise ValidationError('The Name column ({}) is not in table: {}'.format(
                    name_col, table_name
                ))
            if pcode_col not in row:
                raise ValidationError('The PCode column ({}) is not in table: {}'.format(
                    pcode_col, table_name
                ))
            if parent_code_col and parent_code_col not in row:
                raise ValidationError('The Parent Code column ({}) is not in table: {}'.format(
                    parent_code_col, table_name
                ))

        return self.cleaned_data
