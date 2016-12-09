__author__ = 'unicef'

import logging
from django import forms
from django.core.exceptions import ValidationError

from cartodb import CartoDBAPIKey, CartoDBException

from .models import CartoDBTable

logger = logging.getLogger('locations.models')


class CartoDBTableForm(forms.ModelForm):

    class Meta:
        model = CartoDBTable
        fields = '__all__'

    def clean(self):

        api_key = self.cleaned_data['api_key']
        domain = self.cleaned_data['domain']
        table_name = self.cleaned_data['table_name']
        name_col = self.cleaned_data['name_col']
        pcode_col = self.cleaned_data['pcode_col']
        parent_code_col = self.cleaned_data['parent_code_col']

        client = CartoDBAPIKey(api_key, domain)
        try:
            sites = client.sql(
                'select * from {} limit 1'.format(table_name)
            )
        except CartoDBException as e:
            logging.exception("CartoDB exception occured", exc_info=True)
            raise ValidationError("Couldn't connect to CartoDB table: "+table_name)
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