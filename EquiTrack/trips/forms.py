__author__ = 'jcranwellward'

from datetime import datetime

from django.forms import ModelForm, fields, Form
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from suit.widgets import AutosizedTextarea
from suit_ckeditor.widgets import CKEditorWidget
from datetimewidget.widgets import DateTimeWidget, DateWidget
from autocomplete_light import forms as auto_forms

from partners.models import PCA
from .models import Trip, TravelRoutes, TripLocation


class TravelRoutesForm(ModelForm):

    class Meta:
        model = TravelRoutes
        fields = '__all__'

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

                # check if itinerary dates are outside the entire trip date range
                if to_date < depart or depart < from_date or to_date < arrive or arrive < from_date:
                    raise ValidationError(
                        'Travel dates must be within overall trip dates'
                    )
        return cleaned_data


class TripLocationForm(auto_forms.ModelForm):

    class Meta:
        model = TripLocation
        fields = ('location',)
        autocomplete_fields = ('location',)


class TripForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(TripForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Trip
        fields = '__all__'
        widgets = {
            'purpose_of_travel':
                AutosizedTextarea(attrs={'class': 'input-xlarge'}),
            'main_observations':
                CKEditorWidget(editor_options={'startupFocus': False}),
        }

    def clean(self):
        cleaned_data = super(TripForm, self).clean()
        status = cleaned_data.get(u'status')
        travel_type = cleaned_data.get(u'travel_type')
        from_date = cleaned_data.get(u'from_date')
        to_date = cleaned_data.get(u'to_date')
        owner = cleaned_data.get(u'owner')
        supervisor = cleaned_data.get(u'supervisor')
        travel_assistant = cleaned_data.get(u'travel_assistant')
        budget_owner = cleaned_data.get(u'budget_owner')
        ta_required = cleaned_data.get(u'ta_required')
        pcas = cleaned_data.get(u'pcas')
        no_pca = cleaned_data.get(u'no_pca')
        international_travel = cleaned_data.get(u'international_travel')
        representative = cleaned_data.get(u'representative')
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
        pending_ta_amendment = cleaned_data.get(u'pending_ta_amendment')
        driver = cleaned_data.get(u'driver')
        driver_supervisor = cleaned_data.get(u'driver_supervisor')

        if to_date < from_date:
            raise ValidationError('The to date must be greater than the from date')

        if owner == supervisor:
            raise ValidationError('You can\'t supervise your own trips')

        if not pcas and travel_type == Trip.PROGRAMME_MONITORING:
            raise ValidationError(
                'You must select the interventions related to this trip'
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

        if status == Trip.SUBMITTED and to_date < datetime.date(datetime.now()):
            raise ValidationError(
                'This trip\'s dates happened in the past and therefore cannot be submitted'
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

        if status == Trip.APPROVED and not self.instance.approved_by_supervisor:
            raise ValidationError(
                'Only the supervisor can approve this trip'
            )

        if driver and driver_supervisor is None:
                raise ValidationError('You must enter a supervisor for the selected driver')

        if status == Trip.COMPLETED:
            if not trip_report and travel_type != Trip.STAFF_ENTITLEMENT:
                raise ValidationError(
                    'You must provide a narrative report before the trip can be completed'
                )

            if ta_required and pending_ta_amendment is True \
                    and self.request.user != programme_assistant \
                    and self.request.user != travel_assistant:
                raise ValidationError(
                    'Due to trip having a pending amendment to the TA, '
                    ' only the travel focal point can complete the trip'
                )

            # if not approved_by_human_resources and travel_type == Trip.STAFF_DEVELOPMENT:
            #     raise ValidationError(
            #         'STAFF DEVELOPMENT trip must be certified by Human Resources before it can be completed'
            #     )

        #TODO: this can be removed once we upgrade to 1.7
        return cleaned_data


class RequireOneLocationFormSet(BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return

        form_count = len([f for f in self.forms if f.cleaned_data])
        if form_count < 1 and self.instance.international_travel is False and self.instance.status != Trip.CANCELLED:
            raise ValidationError('At least one Trip location is required. (governorate and region)')


class TripFundsForm(BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return

        total = sum([f.cleaned_data.get('amount') for f in self.forms if f.cleaned_data])
        if total != 100:
            raise ValidationError('The total funds for the trip needs to equal to 100%')


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