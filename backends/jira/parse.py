from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import EnumMeta, Enum, auto
from functools import partial
from itertools import chain
from typing import Any, Callable, List, Optional, Tuple
from re import findall


TIMEFORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
DUMPFORMAT = "%Y-%m-%dT%H:%M:%S"


def parse_issue(
        issue_json: dict, subtask_fetcher: Optional[Callable] = None
        ) -> JiraIssue:
    return JiraIssue.from_parsed_json(
        intermediate_parse(issue_json), subtask_fetcher)


def intermediate_parse(issue_json):
    subtask_refs = [
        subtask['self'] for subtask in issue_json['fields']['subtasks']]
    status_history, sprint_history = _parse_changelog(
        issue_json['changelog'])
    parent = issue_json['fields'].get('parent')
    if parent and IssueTypes[
            parent['fields']['issuetype']['name']] == IssueTypes.epic:
        epic = parent['fields']['summary']
    else:
        epic = None
    intermediate = {
        "name": issue_json['key'],
        "summary": issue_json['fields']['summary'],
        "epic": epic,
        "type": IssueTypes[
            issue_json['fields']['issuetype']['name']],
        "status": StatusTypes[
            issue_json['fields']['status']['name']],
        "story_points": issue_json['fields']['customfield_11638'],
        "subtasks": subtask_refs,
        "status_history": status_history,
        "sprint_history": sprint_history}
    return intermediate


def _parse_changelog(history_json: dict) -> Tuple[List, List]:
    status_history = []
    sprint_history = []
    for h in history_json['histories']:
        sh: dict[str, Any] = {
            'timestamp': datetime.strptime(h['created'], TIMEFORMAT)}
        sp: dict[str, Any] = {
            'timestamp': datetime.strptime(h['created'], TIMEFORMAT)}
        for i in h['items']:
            if 'fieldId' in i and i['fieldId'] == 'status':
                sh['from'] = maybe_status(i['fromString'])
                sh['to'] = maybe_status(i['toString'])
                status_history.append(sh)
            if i['field'] == 'Sprint':
                sp.update(_parse_sprint_change(i))
                sprint_history.append(sp)
    status_history.sort(key=lambda x: x['timestamp'])
    sprint_history.sort(key=lambda x: x['timestamp'])
    return status_history, sprint_history


def _parse_sprint_change(sprint_field: dict) -> dict:
    # some muppet thought that it would be a good ideas to store the
    # sprint change lists as comma separated strings.
    items_re = partial(findall, r'[^,\s][^\,]*[^,\s]*')
    return {
        "from": set(map(int, items_re(sprint_field['from']))),
        "to": set(map(int, items_re(sprint_field['to'])))}


def maybe_status(json_val: str) -> Optional[StatusTypes]:
    try:
        status = StatusTypes[json_val]
    except KeyError:
        print(f"Rejected Status Val: {json_val}")
    else:
        return status


def maybe_timestring(time: Optional[datetime]) -> Optional[str]:
    if time is not None:
        return datetime.strftime(time, TIMEFORMAT)


def maybe_datetime(time: Optional[str]) -> Optional[datetime]:
    if time is not None:
        return datetime.strptime(time, TIMEFORMAT)


class JiraEnumMeta(EnumMeta):
    def __getitem__(cls, name):
        return super().__getitem__(cls.canonicalize_name(name))

    @staticmethod
    def canonicalize_name(name: str) -> str:
        # FIXME: this caters for both Status and Issue types
        # they ought to be separated to reduce confusion
        mappings = {
            'underreview': 'codereview',
            'refactor': 'techdebt'
        }
        lower_no_spaces = name.replace(' ', '').replace('-', '').lower()
        mapped = mappings.get(lower_no_spaces)
        # a cx specific column
        if 'qa' in lower_no_spaces:
            lower_no_spaces = 'qa'
        if 'inmaster' in lower_no_spaces:
            lower_no_spaces = 'qa'  # FIXME: ??
        if 'techdebt' in lower_no_spaces:
            lower_no_spaces = 'techdebt'
        if 'done' in lower_no_spaces:
            lower_no_spaces = 'done'
        return mapped or lower_no_spaces


class JiraEnum(Enum, metaclass=JiraEnumMeta):
    pass


class IssueTypes(JiraEnum):
    epic = auto()
    bug = auto()
    story = auto()
    task = auto()
    subtask = auto()
    spike = auto()
    userstory = auto()
    adhoc = auto()
    documentation = auto()
    techdebt = auto()
    feature = auto()


class StatusTypes(JiraEnum):
    todo = auto()
    inprogress = auto()
    done = auto()
    codereview = auto()
    blocked = auto()
    qa = auto()


@dataclass
class StatusMetrics:
    started: bool
    finished: bool
    start: Optional[datetime]
    end: Optional[datetime]
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
            if status_change['to'] == StatusTypes.inprogress:
                return status_change['timestamp']

    @staticmethod
    def _final_done_timestamp(status_changes):
        for status_change in reversed(status_changes):
            if status_change['to'] == StatusTypes.done:
                return status_change['timestamp']

    @staticmethod
    def _round_seconds(seconds):
        return seconds if seconds == 0 else 1


@dataclass
class SprintMetrics:
    sprint_additions: List[dict]

    @classmethod
    def from_parsed_json(
            cls, sprint_history_json: List[dict]) -> SprintMetrics:
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
    epic: Optional[str]
    type_: IssueTypes
    status: StatusTypes
    story_points: Optional[float]
    subtasks: List[JiraIssue]
    status_metrics: StatusMetrics
    sprint_metrics: SprintMetrics
    parent_issue: Optional[JiraIssue] = None

    @classmethod
    def from_parsed_json(
            cls, intermediate: dict,
            subtask_fetcher: Callable = None) -> JiraIssue:
        if subtask_fetcher:
            subtasks = cls.fetch_subtasks(
                subtask_fetcher, intermediate['subtasks'])
        else:
            subtasks = []
        issue = cls(
            name=intermediate['name'],
            summary=intermediate['summary'],
            epic=intermediate['epic'],
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
                subtask.epic = issue.epic
                subtask.sprint_metrics = issue.sprint_metrics
        return issue

    @staticmethod
    def fetch_subtasks(
            fetcher: Callable, subtask_refs: List[str]) -> List[JiraIssue]:
        return [
            parse_issue(fetcher(ref + '?expand=changelog'))
            for ref in subtask_refs]

    def to_json(self) -> List[dict]:
        if self.subtasks:
            return list(chain(*[subt.to_json() for subt in self.subtasks]))
        return [{
            "type": self.type_.name,
            "name": self.name,
            "status": self.status.name,
            "story_points": self.story_points,
            "started": self.status_metrics.started,
            "finished": self.status_metrics.finished,
            "start_time": maybe_timestring(self.status_metrics.start),
            "end_time": maybe_timestring(self.status_metrics.end),
            "days_taken": self.status_metrics.days_taken,
            "label": self.label
        }]

    @property
    def label(self):
        if self.parent_issue:
            parent_label = self.parent_issue.label
        else:
            parent_label = None
        return self.epic or parent_label or self.summary or "No Label"


@dataclass
class Sprint:
    id_: int
    name: str
    goal: str
    state: str
    start: datetime
    # FIXME: could be None for 'active' sprints
    end: datetime
    issues: Optional[List[JiraIssue]] = None

    @classmethod
    def from_parsed_json(
            cls, sprint_json: dict, issues_fetcher: Callable = None) -> Sprint:
        sprint = cls(
            id_=sprint_json['id'],
            goal=sprint_json['goal'],
            name=sprint_json['name'],
            state=sprint_json['state'],
            start=datetime.strptime(
                sprint_json['startDate'], TIMEFORMAT),
            end=(
                maybe_datetime(sprint_json.get('completeDate')) or
                datetime.strptime(sprint_json['endDate'], TIMEFORMAT)))

        if issues_fetcher:
            issues = issues_fetcher(sprint.id_)
            sprint.issues = issues
        return sprint

    def to_json(self):
        issues = list(
            chain(*[self._issue_to_json(i) for i in self.issues]))
        return {
            "id": self.id_,
            "name": self.name,
            "goal": self.goal,
            "state": self.state,
            "start": maybe_timestring(self.start),
            "end": maybe_timestring(self.end),
            "issues": issues}

    def _issue_to_json(self, issue: JiraIssue) -> List[dict]:
        # Due to the Jira heirachy the issue_json is either a singleton
        # list containing 'The' Issue or this list of subtasks.
        issues = issue.subtasks or [issue]
        issues_json = issue.to_json()
        filtered_issues = []
        for json_record, issue in zip(issues_json, issues):
            json_record['planned'] = self.planned_issue(issue)
            json_record['started_in_sprint'] = self.started_in_sprint(issue)
            json_record['finished_in_sprint'] = self.finished_in_sprint(issue)
            if not self.finished_before_sprint_start(issue):
                filtered_issues.append(json_record)
        return filtered_issues

    #
    # -------- Issue predicates and filters ----------
    #
    def planned_issue(self, issue: JiraIssue) -> bool:
        added_to_this_sprint = list(filter(
                lambda x: x['sprint_id'] == self.id_,
                issue.sprint_metrics.sprint_additions))
        if added_to_this_sprint:
            time_added = added_to_this_sprint.pop()['timestamp']
            return time_added <= self.start
        else:
            # TODO: assume unplanned if we have no sprint metrics
            return False

    def started_in_sprint(self, issue: JiraIssue) -> bool:
        started = issue.status_metrics.started
        start_time = issue.status_metrics.start
        started_in_sprint = (
            started and bool(start_time) and
            self.start <= start_time <= self.end)
        # FIXME: Sometimes tockets move straight from ToDo to Done
        # i.e. finished before they started
        return started_in_sprint or self.finished_in_sprint(issue)

    def finished_in_sprint(self, issue: JiraIssue) -> bool:
        finished = issue.status_metrics.finished
        end_time = issue.status_metrics.end

        return (
            finished and bool(end_time) and
            self.start <= end_time <= self.end
        )

    def finished_before_sprint_start(self, issue: JiraIssue) -> bool:
        finished = issue.status_metrics.finished
        end_time = issue.status_metrics.end

        return (
            finished and bool(end_time) and
            end_time < self.start)
