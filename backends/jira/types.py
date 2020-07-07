from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from typing import Callable, NamedTuple, List, Optional, Tuple
from re import findall

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


class IntermediateParser:
    def parse(self, issue_json):
        subtask_refs = [
            subtask['self'] for subtask in issue_json['fields']['subtasks']]
        status_history, sprint_history = self._parse_changelog(
            issue_json['changelog'])
        intermediate = {
            "name": issue_json['key'],
            "summary": issue_json['fields']['summary'],
            "type": int(issue_json['fields']['issuetype']['id']),
            "status": int(issue_json['fields']['status']['id']),
            "story_points": issue_json['fields']['customfield_11638'],
            "subtasks": subtask_refs,
            "status_history": status_history,
            "sprint_history": sprint_history}
        return intermediate

    def _parse_changelog(self, history_json: dict) -> Tuple[List, List]:
        status_history = []
        sprint_history = []
        for h in history_json['histories']:
            sh = {'timestamp': datetime.strptime(h['created'], TIMEFORMAT)}
            sp = {'timestamp': datetime.strptime(h['created'], TIMEFORMAT)}
            for i in h['items']:
                if 'fieldId' in i and i['fieldId'] == 'status':
                    sh['from'] = int(i['from'])
                    sh['to'] = int(i['to'])
                    status_history.append(sh)
                if i['field'] == 'Sprint':
                    sp.update(self._parse_sprint_change(i))
                    sprint_history.append(sp)
        status_history.sort(key=lambda x: x['timestamp'])
        sprint_history.sort(key=lambda x: x['timestamp'])
        return status_history, sprint_history

    @staticmethod
    def _parse_sprint_change(sprint_field: dict) -> dict:
        # some muppet thought that it would be a good ideas to store the
        # sprint change lists as comma separated strings.
        items_re = partial(findall, r'[^,\s][^\,]*[^,\s]*')
        return {
            "from": set(items_re(sprint_field['from'])),
            "to": set(items_re(sprint_field['to']))}


@dataclass
class StatusMetrics:
    started: bool
    finished: bool
    start: Optional[DateTime]
    end: Optional[DateTime]
    days_taken: Optional[int]

    @classmethod
    def from_parsed_json(cls, status_history: dict) -> StatusMetrics:
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
    def from_parsed_json(cls, sprint_history_json: List[dict]) -> SprintMetrics:
        sprint_additions = []
        for sprint_changes in sprint_history_json:
            sprint_added = sprint_changes['to'] - sprint_changes['from']
            if sprint_added:
                sprint_additions.append({
                    "timestamp": sprint_changes['timestamp'],
                    "sprint_id": sprint_added.pop()
                })
        return cls(sprint_additions)


@dataclass
class JiraIssue:
    name: str
    summary: str
    type_: int
    status: int
    story_points: Optional[float]
    subtasks: List[JiraIssue]
    status_metrics: StatusMetrics
    sprint_metrics: SprintMetrics
    parent_issue: Optional[JiraIssue] = None

    @classmethod
    def from_parsed_json(
            cls, intermediate: dict, subtask_fetcher=None) -> JiraIssue:
        if subtask_fetcher:
            subtasks = cls.fetch_subtasks(
                subtask_fetcher, intermediate['subtasks'])
        else:
            subtasks = []
        issue = cls(
            name=intermediate['name'],
            summary=intermediate['summary'],
            type_=intermediate['type'],
            status=intermediate['status'],
            story_points=intermediate['story_points'],
            subtasks=subtasks,
            status_metrics=StatusMetrics.from_parsed_json(
                intermediate['status_history']),
            sprint_metrics=SprintMetrics.from_parsed_json(
                intermediate['sprint_history']))
        if issue.subtasks:
            for subtask in issue.subtasks:
                subtask.parent_issue = issue
        return issue

    @staticmethod
    def fetch_subtasks(
            fetcher: Callable, subtask_refs: List[str]) -> List[JiraIssue]:
        parser = IntermediateParser()
        return [
            JiraIssue.from_parsed_json(
                parser.parse(
                    fetcher(ref + '?expand=changelog')))
            for ref in subtask_refs]

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
            "label": self.label
        }]

    @property
    def label(self):
        if self.parent_issue:
            parent_label = self.parent_issue.label
        else:
            parent_label = None
        return parent_label or self.summary or "No Label"


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
