__author__ = 'jcranwellward'

from django import forms
from suit.widgets import AutosizedTextarea

from .models import Indicator, Result


class IndicatorAdminForm(forms.ModelForm):

    class Meta:
        model = Indicator
        fields = '__all__'
        widgets = {
            'name':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Filter linked results by sector and result structure
        """
        super(IndicatorAdminForm, self).__init__(*args, **kwargs)
        if self.instance.sector_id:
            results = Result.objects.filter(
                sector=self.instance.sector
            )
            if self.instance.hrp:
                results = results.filter(
                    hrp=self.instance.hrp
                )
            self.fields['result'].queryset = results
