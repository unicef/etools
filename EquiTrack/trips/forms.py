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

    # cannot change the following fields: (if other fields are rigid add them in the list)
    PROTECTED_FIELDS = ['to_date', 'from_date']

    ERROR_MESSAGES = {
        'to_date_less_than_from': 'The to date must be greater than the from date',
        'owner_is_supervisor': 'You can\'t supervise your own trips',
        'not_approved_by_supervisor': 'As a traveller you cannot approve your own trips',
        'protected_field_changed': 'This field cannot be changed after approval',
        'trip_submitted_in_past': 'This trip\'s dates happened in the past and therefore cannot be submitted',
        'no_linked_interventions': 'You must select the interventions related to this trip or change the Travel Type',
        'no_assistant_for_TA': 'This trip needs a programme assistant to create a Travel Authorisation (TA)',
        'no_rep_for_int_travel': 'You must select the Representative for international travel trips',
        'no_date_supervisor_approve': 'Please put the date the supervisor approved this Trip',
        'no_date_budget_owner_approve': 'Please put the date the budget owner approved this Trip',
        'no_vision_user_for_TA': 'For TA Drafted trip you must select a Vision Approver',
        'no_driver_supervisor': 'You must enter a supervisor for the selected driver',
        'no_trip_report': 'You must provide a narrative report before the trip can be completed',
        'cant_manually_approve': 'Approved Status is automatically set, can\'t be manually set',
        'ta_needs_amending': 'Due to trip having a pending amendment to the TA, '
                             'only the travel focal point can complete the trip'
    }

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

        # PLANNING
        if (to_date and from_date) and to_date < from_date:
            raise ValidationError({'to_date': self.ERROR_MESSAGES['to_date_less_than_from']})

        if owner == supervisor:
            raise ValidationError({'owner': self.ERROR_MESSAGES['owner_is_supervisor']})

        if status == Trip.APPROVED and \
                not self.instance.status == Trip.APPROVED:
            raise ValidationError({'status': self.ERROR_MESSAGES['cant_manually_approve']})

        if ta_required and not programme_assistant:
            raise ValidationError({'programme_assistant': self.ERROR_MESSAGES['no_assistant_for_TA']})

        if international_travel and not representative:
            raise ValidationError({'representative': self.ERROR_MESSAGES['no_rep_for_int_travel']})

        # SUBMISSION
        if status == Trip.SUBMITTED and to_date < datetime.date(datetime.now()):
            raise ValidationError({'to_date': self.ERROR_MESSAGES['trip_submitted_in_past']})

        # APPROVAL
        if status == Trip.APPROVED and ta_drafted and not vision_approver:
            raise ValidationError({'vision_approver': self.ERROR_MESSAGES['no_vision_user_for_TA']})

        if driver and driver_supervisor is None:
            raise ValidationError({'driver_supervisor': self.ERROR_MESSAGES['no_driver_supervisor']})

        if self.instance.supervisor_id is not None and self.request.user != self.instance.supervisor:
            # only the supervisor can approve the trip
            if not self.instance.approved_by_supervisor and approved_by_supervisor:
                raise ValidationError({'approved_by_supervisor': self.ERROR_MESSAGES['not_approved_by_supervisor']})

        if approved_by_supervisor and not date_supervisor_approved:
            raise ValidationError({'date_supervisor_approved': self.ERROR_MESSAGES['no_date_supervisor_approve']})

        if approved_by_budget_owner and not date_budget_owner_approved:
            raise ValidationError({'date_budget_owner_approved': self.ERROR_MESSAGES['no_date_budget_owner_approve']})

        # If trip has been previously approved and approved tick has not been removed
        if self.instance.approved_by_supervisor:
            # Error if Trip was approved by supervisor and certain fields change
            for u_field in self.PROTECTED_FIELDS:
                if cleaned_data.get(u_field) != getattr(self.instance, u_field):
                    raise ValidationError({u_field: self.ERROR_MESSAGES['protected_field_changed']})

        # COMPLETION
        if status == Trip.COMPLETED:
            if not trip_report and travel_type != Trip.STAFF_ENTITLEMENT:
                raise ValidationError(self.ERROR_MESSAGES['no_trip_report'])

            if ta_required and pending_ta_amendment is True \
                    and self.request.user != programme_assistant \
                    and self.request.user != travel_assistant:
                raise ValidationError(self.ERROR_MESSAGES['ta_needs_amending'])


class RequireOneLocationFormSet(BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return

        # Locations cannot be changed if trip was approved by supervisor
        new_locations = set([f.instance for f in self.forms if f.cleaned_data])
        if self.instance.approved_by_supervisor:
            old_locations = set(self.instance.triplocation_set.all())
            print old_locations, new_locations
            if old_locations != new_locations:
                raise ValidationError('You cannot modify the location after the trip has been approved')

        form_count = len(new_locations)
        if form_count < 1 and self.instance.international_travel is False and self.instance.status == Trip.PLANNED:
            if self.instance.travel_type in [
                Trip.PROGRAMME_MONITORING,
                Trip.SPOT_CHECK
            ]:
                raise ValidationError('At least one location is required for this trip type. (Admin Level 1 or below)')


class TripFundsForm(BaseInlineFormSet):
    def clean(self):
        if any(self.errors):
            return

        total = sum([f.cleaned_data.get('amount') for f in self.forms if f.cleaned_data])
        if total and total != 100:
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