__author__ = 'jcranwellward'

from autocomplete_light import forms

from partners.models import GwPcaLocation


class LocationForm(forms.ModelForm):

    class Media:
        """
        We're currently using Media here, but that forced to move the
        javascript from the footer to the extrahead block ...

        So that example might change when this situation annoys someone a lot.
        """
        js = ('dependant_autocomplete.js',)

    class Meta:
        model = GwPcaLocation
