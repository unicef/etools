from rest_framework_csv import renderers as r


class AppliedIndicatorLocationCSVRenderer(r.CSVRenderer):
    header = ['partner', 'vendor',
              'status', 'start', 'end', 'country_programme', 'pd_ref_number',
              'pd_title', 'cp_output', 'ram_indicators', 'lower_result',
              'indicator', 'location', 'section', 'cluster_name',
              'baseline', 'target', 'means_of_verification', ]

    labels = {
        "partner": "Partner",
        "vendor": "Vendor Number",
        "status": "Status",
        "start": "Start Date",
        "end": "End Date",
        "country_programme": "Country Programme",
        "pd_ref_number": "Reference Number",
        "pd_title": "Title",
        "cp_output": "CP Outputs",
        "ram_indicators": "RAM Indicators",
        "lower_result": "PD/SPD Output",
        "indicator": "PD/SPD Indicator",
        "location": "Locations",
        "section": " Sections",
        "cluster_name": "Cluster",
        "baseline": "Basseline",
        "target": "Target",
        "means_of_verification": "MoV"
    }
