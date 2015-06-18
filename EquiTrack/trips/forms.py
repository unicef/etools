__author__ = 'jcranwellward'

from datetime import datetime

from django.forms import ModelForm, fields, Form
from django.core.exceptions import ValidationError

from suit.widgets import AutosizedTextarea
from suit_ckeditor.widgets import CKEditorWidget
from datetimewidget.widgets import DateTimeWidget, DateWidget

from partners.models import PCA
from .models import Trip


class TravelRoutesForm(ModelForm):

    depart = fields.DateTimeField(label='Depart', widget=DateTimeWidget(bootstrap_version=3),
                                  input_formats=['%d/%m/%Y %H:%M'])
    arrive = fields.DateTimeField(label='Arrive', widget=DateTimeWidget(bootstrap_version=3),
                                  input_formats=['%d/%m/%Y %H:%M'])

    def clean(self):
        cleaned_data = super(TravelRoutesForm, self).clean()
        depart = cleaned_data.get('depart')
        arrive = cleaned_data.get('arrive')

        if arrive and depart:
            if arrive < depart:
                raise ValidationError(
                    'Arrival must be greater than departure'
                )

            if self.instance and self.instance.trip_id is not None:
                from_date = self.instance.trip.from_date
                to_date = self.instance.trip.to_date
                depart = depart.date()
                arrive = arrive.date()

                #check if itinerary dates are outside the entire trip date range
                if to_date < depart or depart < from_date or to_date < arrive or arrive < from_date:
                    raise ValidationError(
                        'Travel dates must be within overall trip dates'
                    )


            # obj = Trip.objects.get(pk=self.instance.trip.pk)
            # model_instance = self.save(commit=False)
            # print(obj.status)
            # obj.status = Trip.PLANNED
            # obj.save()

        return cleaned_data


class TripForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(TripForm, self).__init__(*args, **kwargs)
        #self.fields['pcas'].queryset = PCA.get_active_partnerships()

    class Meta:
        model = Trip
        widgets = {
            'purpose_of_travel':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
            'main_observations':
                CKEditorWidget(editor_options={'startupFocus': False}),
        }

    def clean(self):
        cleaned_data = super(TripForm, self).clean()
        status = cleaned_data.get('status')
        travel_type = cleaned_data.get('travel_type')
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
        trip_report = cleaned_data.get(u'main_observations')


        if to_date < from_date:
            raise ValidationError('The to date must be greater than the from date')

        if owner == supervisor:
            raise ValidationError('You can\'t supervise your own trips')

        if not pcas and travel_type == Trip.PROGRAMME_MONITORING:
            raise ValidationError(
                'You must select the PCAs related to this trip'
                ' or change the Travel Type'
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

        if status == Trip.COMPLETED:
            if not approved_by_supervisor:
                raise ValidationError(
                    'The trip must be approved before it can be completed'
                )

            if not trip_report:
                raise ValidationError(
                    'You must provide a narrative report before the trip can be completed'
                )

        #TODO: Debug this
        # if status == Trip.APPROVED and not approved_by_supervisor:
        #     raise ValidationError(
        #         'Only the supervisor can approve this trip'
        #     )

        #TODO: this can be removed once we upgrade to 1.7
        return cleaned_data




class TripFilterByDateForm(Form):

    depart = fields.DateField(
        label='From',
        widget=DateWidget(
            bootstrap_version=3,
            attrs={}
        )
    )
    arrive = fields.DateField(
        label='To',
        widget=DateWidget(
            bootstrap_version=3,
            attrs={}
        )
    )
