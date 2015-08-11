__author__ = 'jcranwellward'

from datetime import datetime

from django.forms import ModelForm, fields, Form
from django.core.exceptions import ValidationError

from suit.widgets import AutosizedTextarea
from suit_ckeditor.widgets import CKEditorWidget
from datetimewidget.widgets import DateTimeWidget, DateWidget

from partners.models import PCA
from .models import Trip, TravelRoutes


class TravelRoutesForm(ModelForm):

    class Meta:
        model = TravelRoutes

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
                from_date = datetime.strptime(self.data.get('from_date'), '%Y-%m-%d').date()
                to_date = datetime.strptime(self.data.get('to_date'), '%Y-%m-%d').date()
                depart = depart.date()
                arrive = arrive.date()

                #check if itinerary dates are outside the entire trip date range
                if to_date < depart or depart < from_date or to_date < arrive or arrive < from_date:
                    raise ValidationError(
                        'Travel dates must be within overall trip dates'
                    )
        return cleaned_data


class TripForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(TripForm, self).__init__(*args, **kwargs)

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
        international_travel = cleaned_data.get('international_travel')
        representative = cleaned_data.get('representative')
        ta_drafted = cleaned_data.get(u'ta_drafted')
        vision_approver = cleaned_data.get(u'vision_approver')
        programme_assistant = cleaned_data.get(u'programme_assistant')
        approved_by_supervisor = cleaned_data.get(u'approved_by_supervisor')
        date_supervisor_approved = cleaned_data.get(u'date_supervisor_approved')
        approved_by_budget_owner = cleaned_data.get(u'approved_by_budget_owner')
        date_budget_owner_approved = cleaned_data.get(u'date_budget_owner_approved')
        approved_by_human_resources = cleaned_data.get(u'approved_by_human_resources')
        trip_report = cleaned_data.get(u'main_observations')
        ta_trip_took_place_as_planned = cleaned_data.get(u'ta_trip_took_place_as_planned')


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

        if international_travel and not representative:
            raise ValidationError('You must select the Representative for international travel trips')

        if approved_by_supervisor and not date_supervisor_approved:
            raise ValidationError(
                'Please put the date the supervisor approved this Trip'
            )

        if approved_by_budget_owner and not date_budget_owner_approved:
            raise ValidationError(
                'Please put the date the budget owner approved this Trip'
            )

        #TODO: Debug this
        if status == Trip.APPROVED and not approved_by_supervisor:
            raise ValidationError(
                'Only the supervisor can approve this trip'
            )

        if status == Trip.APPROVED and ta_drafted:
            if not vision_approver:
                raise ValidationError(
                    'For TA Drafted trip you must select a Vision Approver'
                )
            if not programme_assistant:
                raise ValidationError(
                    'For TA Drafted trip you must select a Staff Responsible for TA'
                )

        if status == Trip.COMPLETED:
            if not trip_report:
                raise ValidationError(
                    'You must provide a narrative report before the trip can be completed'
                )

            if ta_required and ta_trip_took_place_as_planned is False:
                raise ValidationError(
                    'Only the TA travel assistant can complete the trip'
                )

            # if not approved_by_human_resources and travel_type == Trip.STAFF_DEVELOPMENT:
            #     raise ValidationError(
            #         'STAFF DEVELOPMENT trip must be certified by Human Resources before it can be completed'
            #     )

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
