from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, NamedTuple, List, Optional

from click.types import DateTime


JIRA_BASEURL = 'https://limejump.atlassian.net/rest/agile'
TRADING_BOARD = 140
TIMEFORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
DUMPFORMAT = "%Y-%m-%dT%H:%M:%S"

IssueTypes = NamedTuple(
    "IssueTypes", [
        ("epic", int),
        ("story", int),
        ("subtask", int), ('task', int),
        ('bug', int),
        ('spike', int)
        ])
ISSUE_TYPES = IssueTypes(
    story=10350, task=10351, bug=10352, epic=10353, subtask=10354, spike=10364)
TYPE_NAMES = {v: k for k, v in ISSUE_TYPES._asdict().items()}

StatusTypes = NamedTuple(
    "StatusTypes", [
        ('todo', int),
        ('inprogress', int),
        ('done', int),
        ('codereview', int),
    ])

STATUS_TYPES = StatusTypes(
    todo=11490, inprogress=11491, done=11492, codereview=11493)
STATUS_NAMES = {v: k for k, v in STATUS_TYPES._asdict().items()}


@dataclass
class StatusMetrics:
    started: bool
    finished: bool
    start: Optional[DateTime]
    end: Optional[DateTime]
    days_taken: Optional[int]

    @classmethod
    def from_json(cls, history_json: dict) -> StatusMetrics:
        status_history = []
        for h in history_json:
            st = {'timestamp': datetime.strptime(h['created'], TIMEFORMAT)}
            for i in h['items']:
                if 'fieldId' in i and i['fieldId'] == 'status':
                    st['from'] = int(i['from'])
                    st['to'] = int(i['to'])
                    status_history.append(st)
        status_history.sort(key=lambda x: x['timestamp'])

        start_time = cls._first_inprogress_timestamp(status_history)
        end_time = cls._final_done_timestamp(status_history)
        started = bool(start_time)
        finished = bool(end_time)
        if started and finished:
            delta = end_time - start_time
            days_taken = delta.days + cls._round_seconds(delta.seconds)
        else:
            days_taken = None
        return cls(
            started=started, finished=finished, start=start_time, end=end_time,
            days_taken=days_taken)

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


@dataclass
class SprintMetrics:
    sprint_additions: List[dict]

    @classmethod
    def from_json(cls, history_json: List[dict]) -> SprintMetrics:
        sprint_additions = []
        for h in history_json:
            sp = {'timestamp': datetime.strptime(h['created'], TIMEFORMAT)}
            for i in h['items']:
                if i['field'] == 'Sprint':
                    sprint_id = cls._parse_sprint_change(i)
                    sp['sprint_id'] = sprint_id
                    sprint_additions.append(sp)
        sprint_additions.sort(key=lambda x: x['timestamp'])
        return cls(sprint_additions=sprint_additions)

    @staticmethod
    def _parse_sprint_change(sprint_field: dict) -> Optional[int]:
        # some muppet thought that it would be a good ideas to store the
        # sprint change lists as comma separated strings. So we're trying to
        # convert ('<sprint id1>', '<sprint_id1>, <sprint_id2>')  -> 'sprint_id2'
        # i.e. the sprint this issue got added too.
        # issues can also get removed from sprints, hence this being an optional type
        from_ = set(sprint_field['from'].split(', '))
        to = set(sprint_field['to'].split(', '))
        sprint_added = to - from_
        if sprint_added:
            sprint_id = sprint_added.pop()
            # ('<sprint_id>', '') -> {''}    :/
            if sprint_id:
                return int(sprint_id)


@dataclass
class JiraIssue:
    name: str
    summary: str
    type_: int
    status: int
    story_points: Optional[float]
    subtasks: List[JiraSubTask]
    status_metrics: StatusMetrics
    sprint_metrics: SprintMetrics

    @classmethod
    def from_json(
            cls, issue_json: dict,
            fetch_subtask: Callable = None) -> JiraIssue:
        subtask_refs = issue_json['fields']['subtasks']
        subtasks = []
        if subtask_refs and fetch_subtask:
            for subtask_ref in subtask_refs:
                subtasks.append(
                    JiraSubTask.from_json(
                        fetch_subtask(subtask_ref['self'] + '?expand=changelog')))

        return cls(
            name=issue_json['key'],
            summary=issue_json['fields']['summary'],
            type_=int(issue_json['fields']['issuetype']['id']),
            status=int(issue_json['fields']['status']['id']),
            story_points=issue_json['fields']['customfield_11638'],
            subtasks=subtasks,
            status_metrics=StatusMetrics.from_json(
                issue_json['changelog']['histories']),
            sprint_metrics=SprintMetrics.from_json(
                issue_json['changelog']['histories'])
            )

    def to_json(self) -> List[dict]:
        if self.subtasks:
            return [
                subt.to_json() for subt in self.subtasks]
        return [{
            "type": TYPE_NAMES[self.type_],
            "name": self.name,
            "status": STATUS_NAMES[self.status],
            "story_points": self.story_points,
            "started": self.status_metrics.started,
            "finished": self.status_metrics.finished,
            "days_taken": self.status_metrics.days_taken,
        }]

    @property
    def label(self):
        self.summary or "No Label"


@dataclass
class JiraSubTask:
    name: str
    summary: str
    status: int
    story_points: Optional[float]
    status_metrics: StatusMetrics
    sprint_metrics: SprintMetrics
    type_: int = ISSUE_TYPES.subtask
    parent: JiraIssue = field(init=False)

    @classmethod
    def from_json(cls, issue_json: dict) -> JiraSubTask:
        empty_sprint_metrics: List[dict] = []
        return cls(
            name=issue_json['key'],
            summary=issue_json['fields']['summary'],
            type_=int(issue_json['fields']['issuetype']['id']),
            status=int(issue_json['fields']['status']['id']),
            story_points=issue_json['fields']['customfield_11638'],
            status_metrics=StatusMetrics.from_json(
                issue_json['changelog']['histories']),
            sprint_metrics=SprintMetrics.from_json(empty_sprint_metrics))

    def to_json(self) -> dict:
        return {
            "type": TYPE_NAMES[self.type_],
            "name": self.name,
            "status": STATUS_NAMES[self.status],
            "story_points": self.story_points,
            "started": self.status_metrics.started,
            "finished": self.status_metrics.finished,
            "days_taken": self.status_metrics.days_taken,
        }


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
