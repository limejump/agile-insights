from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple, List, Optional


JIRA_BASEURL = 'https://limejump.atlassian.net/rest/agile'
TRADING_BOARD = 140
TIMEFORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
DUMPFORMAT = "%Y-%m-%dT%H:%M:%S"

IssueTypes = NamedTuple("IssueTypes", [("story", int), ("subtask", int)])
ISSUE_TYPES = IssueTypes(story=10350, subtask=10354)

StatusTypes = NamedTuple(
    "StatusTypes", [
        ('todo', int),
        ('inprogress', int),
        ('done', int),
        ('codereview', int),
    ])

STATUS_TYPES = StatusTypes(
    todo=11490, inprogress=11491, done=11492, codereview=11493)


@dataclass
class IssueMetrics:
    storypoints: float
    resolution_date: datetime
    status_history: List[dict]
    days_taken: int = field(init=False)
    sprint_history: List[dict]

    def __post_init__(self):
        status_history = self._parse_status_history()
        start = self._first_inprogress_timestamp(status_history)
        end = self._final_done_timestamp(status_history)
        # FIXME:
        # Some tickets have no status history and move straight done.
        # We default such cases to 1 day of work.
        # This is a terrible approach to capture this, but will do for now.
        # really we should parse the status history up front and not create
        # an IssueMetrics record if we ar unable to determine a duration
        try:
            delta = end - start
            self.days_taken = delta.days + self._round_seconds(delta.seconds)
        except TypeError:
            self.days_taken = 1

    def _parse_status_history(self):
        ''' return the status history in chronological order
        '''
        status_history = []
        for i in self.status_history:
            s = {
                "from": i['from'],
                "to": i['to'],
                "timestamp": datetime.strptime(
                    i['timestamp'], TIMEFORMAT)}
            status_history.append(s)
        return sorted(status_history, key=lambda x: x['timestamp'])

    @staticmethod
    def _first_inprogress_timestamp(status_changes):
        for status_change in status_changes:
            if status_change['to'] == STATUS_TYPES.inprogress:
                return status_change['timestamp']

    @staticmethod
    def _final_done_timestamp(status_changes):
        for status_change in reversed(status_changes):
            if status_change['to'] == STATUS_TYPES.done:
                return status_change['timestamp']

    @staticmethod
    def _round_seconds(seconds):
        return seconds if seconds == 0 else 1

    @classmethod
    def from_json(cls, issue_json):
        histories = issue_json['changelog']['histories']
        status_changes = []
        sprint_changes = []
        for h in histories:
            st = {'timestamp': h['created']}
            sp = {'timestamp': h['created']}
            for i in h['items']:
                if 'fieldId' in i and i['fieldId'] == 'status':
                    st['from'] = int(i['from'])
                    st['to'] = int(i['to'])
                    status_changes.append(st)
                if 'field' in i and i['field'] == 'Sprint':
                    sprint_added = (
                        set(i['to'].split(', ')) - set(i['from'].split(', ')))
                    if sprint_added:
                        sprint_id = sprint_added.pop()
                        if sprint_id:
                            sp['sprint_id'] = int(sprint_id)
                            sp['operation'] = 'add'
                    sprint_changes.append(sp)
        return cls(
            storypoints=issue_json['fields']['customfield_11638'],
            resolution_date=datetime.strptime(
                issue_json['fields']['resolutiondate'],
                TIMEFORMAT),
            status_history=status_changes,
            sprint_history=sprint_changes)

    def to_json(self):
        return {
            'storypoints': self.storypoints,
            'days_taken': self.days_taken,
            'resolution_date': datetime.strftime(
                self.resolution_date, DUMPFORMAT)
        }


@dataclass
class JiraIssue:
    name: str
    type_: int
    status: int
    has_subtasks: bool
    parent_name: Optional[str]
    metrics: Optional[IssueMetrics] = None

    @classmethod
    def from_json(cls, issue_json: dict) -> JiraIssue:
        parent_name_record = issue_json['fields'].get('parent')
        if parent_name_record is not None:
            parent_name = parent_name_record['fields']['summary']
        else:
            parent_name = None
        return cls(
            name=issue_json['key'],
            parent_name=parent_name,
            type_=int(issue_json['fields']['issuetype']['id']),
            has_subtasks=bool(issue_json['fields']['subtasks']),
            status=int(issue_json['fields']['status']['id']))

    def to_json(self):
        metrics = self.metrics.to_json() if self.metrics else None
        return {
            "type": self.type_,
            "name": self.name,
            "status": self.status,
            "metrics": metrics
        }

    @property
    def label(self):
        self.parent_name or "No Label"


@dataclass
class Sprint:
    id_: int
    name: str
    state: str
    start: datetime
    end: datetime
    issues: List[JiraIssue] = field(init=False)

    @classmethod
    def from_json(cls, sprint_json: dict) -> Sprint:
        return cls(
            id_=sprint_json['id'],
            name=sprint_json['name'],
            state=sprint_json['state'],
            start=sprint_json['startDate'],
            end=sprint_json.get('completeDate') or sprint_json['endDate'])
