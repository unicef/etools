from django import forms

from etools.applications.reports.models import Indicator, Result


class IndicatorAdminForm(forms.ModelForm):

    class Meta:
        model = Indicator
        fields = '__all__'
        widgets = {
            'name': forms.Textarea(),
        }

    def __init__(self, *args, **kwargs):
        """
        Filter linked results by sector and result structure
        """
        super().__init__(*args, **kwargs)
        if self.instance.sector_id:
            results = Result.objects.filter(
                sector=self.instance.sector
            )
            self.fields['result'].queryset = results
