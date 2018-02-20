from rest_framework_csv import renderers as r


class AppliedIndicatorLocationCSVRenderer(r.CSVRenderer):
    header = ['partner', 'vendor',
              'status', 'start', 'end', 'country_programme', 'pd_ref_number',
              'pd_title', 'cp_output', 'ram_indicators', 'lower_result',
              'indicator', 'location', 'section', 'cluster_name',
              'baseline', 'target', 'means_of_verification', ]

    labels = {
        "partner": "Name of the Partner",
        "vendor": "Vendor Number",
        "status": "Status",
        "start": "Start Date",
        "end": "End Date",
        "country_programme": "Country Programme",
        "pd_ref_number": "PD Reference Number",
        "pd_title": "Title of the PD",
        "cp_output": "CP Outputs - related to the PD Indicator",
        "ram_indicators": "RAM Indicators related to the PD Indicator",
        "lower_result": "PD/SSFA Output - related to the PD Indicator",
        "indicator": "PD/SSFA Indicator - related to the PD Indicator Location",
        "location": "Location",
        "section": " Indicator Level Sections",
        "cluster_name": "Cluster",
        "baseline": "Basseline - related to the indicator",
        "target": "Target - related to the indicator",
        "means_of_verification": "MoV - related to the indicator"
    }