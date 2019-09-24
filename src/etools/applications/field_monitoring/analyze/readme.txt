# monitoring activity
/analyze/overall/
overall_data = {
    "activities_completed": 120,
    "activities_planned": 180,
}


# coverage by active partnerships
/analyze/coverate/partners/
coverage_partners = [
    {
        "name": "AKKAR NETWORK",
        "completed": 5,
        "planned": 10,
        "minimum_required_visits": 2,
        "days_since_visit": 40,
    },
]

/analyze/coverage/interventions/
coverage_interventions = [
    {
        "name": "PD201823",
        "days_since_visit": 90,
        "avg_days": 30,
    }
]

/analyze/coverage/cp-outputs/
coverage_cp_outputs = [
    {
        "name": "1.3 ACCESS TO IMMUN...",
        "days_since_visit": 90,
        "avg_days": 30,
    }
]


# geographic coverage
/analyze/coverage/geographic/?sections__in=1,2,3
filter by parent = country
filter by sections
coverage_locations = [
    {
        "name": "location.name",
        "completed": 5 "number of visits filtered by sections",
        "geom": "GEOMETRY",
    }
]


# visits eligible for hact programmatic visit
/analyze/hact/
hact = [
    {
        "partner": "AKKAR NETWORK",
        "activities": [
            {
                "name": "first activity",
                "cp_outputs": [],
                "interventions": [],
                "end_date": "2019-12-12",
            }
        ]
    }
]


# open issues and action points
/analyze/issues/partners/
issues_partners = [
    {
        "name": "AKKAR NETWORK",
        "log_issues": 4,
        "action_points": 2,
    }
]

/analyze/issues/interventions/
issues_interventions = [
    {
        "name": "PD201823",
        "log_issues": 4,
        "action_points": 2,
    }
]

/analyze/issues/locations/ # todo: filters should be applied here, locations list is really huge
issues_locations = [
    {
        "name": "Katmandu",
        "log_issues": 4,
        "action_points": 2,
    }
]
