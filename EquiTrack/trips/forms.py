__author__ = 'jcranwellward'

from datetime import datetime

from django.forms import ModelForm, fields
from django.core.exceptions import ValidationError

from suit_ckeditor.widgets import CKEditorWidget
from datetimewidget.widgets import DateTimeWidget

from .models import Trip


class TravelRoutesForm(ModelForm):

    depart = fields.DateTimeField(label='Depart', widget=DateTimeWidget(bootstrap_version=3))
    arrive = fields.DateTimeField(label='Arrive', widget=DateTimeWidget(bootstrap_version=3))

    def clean(self):
        cleaned_data = super(TravelRoutesForm, self).clean()
        depart = cleaned_data.get('depart')
        arrive = cleaned_data.get('arrive')

        if arrive < depart:
            raise ValidationError(
                'Departure must be greater than arrival'
            )

        # if self.instance:
        #     from_date = self.instance.trip.from_date
        #     to_date = self.instance.trip.to_date
        #     depart = depart.date()
        #     arrive = arrive.date()
        #
        #     if depart < from_date or to_date < arrive:
        #         raise ValidationError(
        #             'Travel dates must be within overall trip dates'
        #         )

        return cleaned_data


class TripForm(ModelForm):

    def clean(self):
        cleaned_data = super(TripForm, self).clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        owner = cleaned_data.get('owner')
        supervisor = cleaned_data.get('supervisor')
        budget_owner = cleaned_data.get('budget_owner')
        ta_required = cleaned_data.get('ta_required')
        pcas = cleaned_data.get('pcas')
        no_pca = cleaned_data.get('no_pca')
        programme_assistant = cleaned_data.get(u'programme_assistant')
        approved_by_supervisor = cleaned_data.get(u'approved_by_supervisor')
        date_supervisor_approved = cleaned_data.get(u'date_supervisor_approved')
        approved_by_budget_owner = cleaned_data.get(u'approved_by_budget_owner')
        date_budget_owner_approved = cleaned_data.get(u'date_budget_owner_approved')

        if to_date < from_date:
            raise ValidationError('The to date must be greater than the from date')

        if owner == supervisor:
            raise ValidationError('You can\'t supervise your own trips')

        if not pcas and not no_pca:
            raise ValidationError(
                'You must select the PCAs related to this trip'
                ' or select the "Not related to a PCA" option'
            )

        if ta_required and not programme_assistant:
            raise ValidationError(
                'This trip needs a programme assistant '
                'to create a Travel Authorisation (TA)'
            )

        if approved_by_supervisor and not date_supervisor_approved:
            raise ValidationError(
                'Please put the date the supervisor approved this Trip'
            )

        if approved_by_budget_owner and not date_budget_owner_approved:
            raise ValidationError(
                'Please put the date the budget owner approved this Trip'
            )

        #TODO: this can be removed once we upgrade to 1.7
        return cleaned_data

    class Meta:
        model = Trip
        widgets = {
            'main_observations':
                CKEditorWidget(editor_options={'startupFocus': False}),
        }