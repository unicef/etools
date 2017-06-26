from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from audit.transitions.conditions import BaseTransitionCheck, BaseRequiredFieldsCheck


class TPMVisitSubmitRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'tpm_partner',
    ]


class TPMVisitReportRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'tpm_report',
    ]


class TPMVisitReportValidations(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = {}
        report = getattr(instance, 'tpm_report', None)

        if not report or report.report.all().count() <= 0:
            errors["tpm_report"] = _('This field required')
        return errors


class ValidateTPMVisitActivities(BaseTransitionCheck):
    def _get_tpm_locations_errors(self, tpm_locations):
        tpm_locations_errors = []

        if not tpm_locations:
            return _('This field is required')

    def _get_tpm_low_results_errors(self, tpm_low_results):
        tpm_low_results_errors = []

        if not tpm_low_results:
            return _('This field required')

        for tpm_low_result in tpm_low_results:
            tpm_locations_errors = self._get_tpm_locations_errors(tpm_low_result.tpm_locations.all())

            if tpm_locations_errors:
                tpm_low_results_errors.append({
                    'id': tpm_low_result.id,
                    'tpm_locations': tpm_locations_errors
                })
        return tpm_low_results_errors

    def _get_sectors_errors(self, sectors):
        sectors_errors = []

        if not sectors:
            return _('This field is required')

        for sector in sectors:
            tpm_low_result_errors = self._get_tpm_low_results_errors(sector.tpm_low_results.all())

            if tpm_low_result_errors:
                sectors_errors.append({
                    'id': sector.id,
                    'tpm_low_results': tpm_low_result_errors,
                })
        return sectors_errors

    def _get_activities_errors(self, activities):
        activities_errors = []

        if not activities:
            return _('This field is required')

        for activity in activities:
            sectors_errors = self._get_sectors_errors(activity.tpm_sectors.all())

            if sectors_errors:
                activities_errors.append({
                    'id': activity.id,
                    'tpm_sectors': sectors_errors,
                })
        return activities_errors

    def get_errors(self, instance, *args, **kwargs):
        errors = {}
        activities = instance.tpm_activities.all()

        activities_errors = self._get_activities_errors(activities)

        if activities_errors:
            errors['tpm_activities'] = activities_errors
        return errors
