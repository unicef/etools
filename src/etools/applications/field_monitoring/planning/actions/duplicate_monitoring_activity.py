from dataclasses import dataclass


@dataclass
class DuplicateMonitoringActivityParams:
    monitoring_activity_id: int
    with_checklist: bool



class DuplicateMonitoringActivity:
    def execute(self, monitoring_activity_id: int, with_checklist: bool) -> None:
        pass
