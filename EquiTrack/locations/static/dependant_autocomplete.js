/**
 * Created by jcranwellward on 02/12/2013.
 */

$(document).ready(function() {
    $('body').on('change', '.autocomplete-light-widget select[name$=governorate]', function() {
        var governorateSelectElement = $(this);
        var regionSelectElement = $('#' + $(this).attr('id').replace('governorate', 'region'));
        var regionWidgetElement = regionSelectElement.parents('.autocomplete-light-widget');

        // When the country select changes
        value = $(this).val();

        if (value) {
            // If value is contains something, add it to autocomplete.data
            regionWidgetElement.yourlabsWidget().autocomplete.data = {
                'governorate_id': value[0]
            };
        } else {
            // If value is empty, empty autocomplete.data
            regionWidgetElement.yourlabsWidget().autocomplete.data = {}
        }

        //example debug statements, that does not replace using breakbpoints and a proper debugger but can hel
        console.log($(this), 'changed to', value);
        console.log(regionWidgetElement, 'data is', regionWidgetElement.yourlabsWidget().autocomplete.data)
    });

    $('body').on('change', '.autocomplete-light-widget select[name$=region]', function() {
        var regionSelectElement = $(this);
        var localitySelectElement = $('#' + $(this).attr('id').replace('region', 'locality'));
        var localityWidgetElement = localitySelectElement.parents('.autocomplete-light-widget');

        // When the country select changes
        value = $(this).val();

        if (value) {
            // If value is contains something, add it to autocomplete.data
            localityWidgetElement.yourlabsWidget().autocomplete.data = {
                'region_id': value[0]
            };
        } else {
            // If value is empty, empty autocomplete.data
            localityWidgetElement.yourlabsWidget().autocomplete.data = {}
        }

        // example debug statements, that does not replace using breakbpoints and a proper debugger but can hel
        console.log($(this), 'changed to', value);
        console.log(localityWidgetElement, 'data is', localityWidgetElement.yourlabsWidget().autocomplete.data)
    });
});