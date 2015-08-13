from __future__ import absolute_import

__author__ = 'jcranwellward'

import pandas

from django import forms
from django.forms.models import BaseInlineFormSet
from django.contrib import messages
#from autocomplete_light import forms
from django.core.exceptions import ValidationError

from locations.models import Location
from reports.models import Sector, Result, Indicator
from .models import (
    PCA,
    GwPCALocation,
    ResultChain,
    IndicatorProgress
)


# class LocationForm(forms.ModelForm):
#
#     class Media:
#         """
#         We're currently using Media here, but that forced to move the
#         javascript from the footer to the extrahead block ...
#
#         So that example might change when this situation annoys someone a lot.
#         """
#         js = ('dependant_autocomplete.js',)
#
#     class Meta:
#         model = GwPCALocation


class IndicatorAdminModelForm(forms.ModelForm):

    class Meta:
        model = IndicatorProgress

    def __init__(self, *args, **kwargs):
        super(IndicatorAdminModelForm, self).__init__(*args, **kwargs)
        self.fields['indicator'].queryset = []


class ResultInlineAdminFormSet(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        kwargs['parent_object'] = self.instance
        return super(ResultInlineAdminFormSet, self)._construct_form(i, **kwargs)


class ResultChainAdminForm(forms.ModelForm):

    class Meta:
        model = ResultChain

    def __init__(self, *args, **kwargs):
        """
        Filter linked results by sector and result structure
        """
        if 'parent_object' in kwargs:
            self.parent_partnership = kwargs.pop('parent_object')

        super(ResultChainAdminForm, self).__init__(*args, **kwargs)

        if hasattr(self, 'parent_partnership'):

            results = Result.objects.filter(
                result_structure=self.parent_partnership.result_structure
            )
            indicators = Indicator.objects.filter(
                result_structure=self.parent_partnership.result_structure
            )
            for sector in self.parent_partnership.sector_children:
                results = results.filter(sector=sector)
                indicators = indicators.filter(sector=sector)

            if self.instance.result_id:
                self.fields['result'].queryset = results.filter(id=self.instance.result_id)
                self.fields['indicator'].queryset = indicators.filter(result_id=self.instance.result_id)

            print 'Name: {}'.format(self.instance.result.name)
        print 'Result: {}'.format(self.fields['result'].queryset.count())
        print 'Ind: {}'.format(self.fields['indicator'].queryset.count())


class PCAForm(forms.ModelForm):

    # fields needed to assign locations from p_codes
    p_codes = forms.CharField(widget=forms.Textarea, required=False)
    location_sector = forms.ModelChoiceField(
        required=False,
        queryset=Sector.objects.all()
    )

    # fields needed to import log frames/work plans from excel
    log_frame = forms.FileField(required=False)
    log_frame_sector = forms.ModelChoiceField(
        required=False,
        queryset=Sector.objects.all()
    )

    class Meta:
        model = PCA

    def add_locations(self, p_codes, sector):
        """
        Adds locations to the partnership based
        on the passed in list and the relevant sector
        """
        p_codes_list = p_codes.split()
        created, notfound = 0, 0
        for p_code in p_codes_list:
            try:
                location = Location.objects.get(
                    p_code=p_code
                )
                loc, new = GwPCALocation.objects.get_or_create(
                    sector=sector,
                    governorate=location.locality.region.governorate,
                    region=location.locality.region,
                    locality=location.locality,
                    location=location,
                    pca=self.obj
                )
                if new:
                    created += 1
            except Location.DoesNotExist:
                notfound += 1

        messages.info(
            self.request,
            u'Assigned {} locations, {} were not found'.format(
                created, notfound
            ))

    def import_results_from_log_frame(self, log_frame, sector):
        """
        Matches results from the log frame to country result structure
        """
        try:  # first try to grab the excel as a table...
            data = pandas.read_excel(log_frame, index_col=0)
        except Exception as exp:
            raise ValidationError(exp.message)

        imported = found = not_found = 0
        for code in data.index.values:
            try:
                result = Result.objects.get(
                    sector=sector,
                    code=code
                )
            except (Result.DoesNotExist, Result.MultipleObjectsReturned) as exp:
                not_found += 1
                #TODO: Log this
            else:
                result_chain, new = ResultChain.objects.get_or_create(
                    partnership=self.obj,
                    result_type=result.result_type,
                    result=result,
                )
                if new:
                    imported += 1
                else:
                    found += 1

        messages.info(
            self.request,
            u'Imported {} results, {} were not found'.format(
                found, not_found
            ))

    def clean(self):
        """
        Add elements to the partnership based on imports
        """
        cleaned_data = super(PCAForm, self).clean()
        p_codes =cleaned_data[u'p_codes']
        location_sector = cleaned_data[u'location_sector']

        log_frame = self.cleaned_data[u'log_frame']
        log_frame_sector = self.cleaned_data[u'log_frame_sector']

        if p_codes and not location_sector:
            raise ValidationError(
                u'Please select a sector to assign the locations against'
            )

        if p_codes and location_sector:
            self.add_locations(p_codes, location_sector)

        if log_frame and not log_frame_sector:
            raise ValidationError(
                u'Please select a sector to import results against'
            )

        if log_frame and log_frame_sector:
            self.import_results_from_log_frame(log_frame, log_frame_sector)

        return cleaned_data
