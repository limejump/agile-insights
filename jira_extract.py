from __future__ import annotations
import click
from click.types import DateTime
from datetime import datetime
from dataclasses import dataclass, field
import json
from requests import get
from requests.auth import HTTPBasicAuth
from typing import NamedTuple, List, Optional

MY_TOKEN = 'eVDgTL8kVgdXFaiJtbCF4001'
JIRA_BASEURL = 'https://limejump.atlassian.net/rest/agile'
TRADING_BOARD = 140
TIMEFORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
DUMPFORMAT = "%Y-%m-%dT%H:%M:%S"
FULL_DATASET_FILEPATH = 'full-jira-dataset.json'

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
        for h in histories:
            s = {'timestamp': h['created']}
            for i in h['items']:
                if 'fieldId' in i and i['fieldId'] == 'status':
                    s['from'] = int(i['from'])
                    s['to'] = int(i['to'])
                    status_changes.append(s)
        return cls(
            storypoints=issue_json['fields']['customfield_11638'],
            resolution_date=datetime.strptime(
                issue_json['fields']['resolutiondate'],
                TIMEFORMAT),
            status_history=status_changes)

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
    metrics: Optional[IssueMetrics] = None

    @classmethod
    def from_json(cls, issue_json: dict) -> JiraIssue:
        return cls(
            name=issue_json['key'],
            type_=int(issue_json['fields']['issuetype']['id']),
            status=int(issue_json['fields']['status']['id']),
            has_subtasks=bool(issue_json['fields']['subtasks']))

    def to_json(self):
        return {
            "name": self.name,
            "status": self.status,
            "metrices": self.metrics.to_json()
        }


def measurable_issue(issue: JiraIssue) -> bool:
    return (issue.type_ == ISSUE_TYPES.subtask or
            (issue.type_ == ISSUE_TYPES.story and not issue.has_subtasks))


def fetch(start_at):
    return get(
        JIRA_BASEURL + (
            f'/1.0/board/{TRADING_BOARD}/issue/?expand=changelog&maxResults=50&startAt={start_at}'),
        auth=HTTPBasicAuth("grahame.gardiner@limejump.com", MY_TOKEN)).json()


@click.group()
def cli():
    pass


@cli.command()
def extract():
    data = []

    def extract_batch(issues):
        for issue_json in issues['issues']:
            issue = JiraIssue.from_json(issue_json)
            if measurable_issue(issue):
                issue.metrics = IssueMetrics.from_json(issue_json)
                data.append(issue)

    processed = 0
    first_batch = fetch(processed)
    total = first_batch['total']
    extract_batch(first_batch)
    processed += len(first_batch['issues'])

    while processed < total:
        batch = fetch(processed)
        extract_batch(batch)
        processed += len(first_batch['issues'])

    with open(FULL_DATASET_FILEPATH, 'w') as f:
        json.dump([d.to_json() for d in data], f, indent=2)


@cli.group()
def dump():
    pass


@dump.command()
def full():
    try:
        with open(FULL_DATASET_FILEPATH, 'r'):
            pass
    except FileNotFoundError:
        raise click.ClickException("please run `extract`")
    else:
        click.echo(f'file dumped at: ./{FULL_DATASET_FILEPATH}')


@dump.command(help="If neither --start or --end is specified return all")
@click.option('--start', type=DateTime())
@click.option('--end', type=DateTime())
def range(start, end):
    # FIXME: Repitition
    try:
        with open(FULL_DATASET_FILEPATH, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise click.ClickException("please run `extract`")
    if start and end:
        with open(f'jira-dataset-from-{start}-to-{end}.json', 'w') as f:
            json.dump(
                [d for d in data
                 if start <= datetime.strptime(d['resolution_date'], DUMPFORMAT) <= end],
                f, indent=2)
        click.echo(f'file dumped at: ./jira-dataset-from-{start}-to-{end}.json')
    elif start:
        with open(f'jira-dataset-from-{start}.json', 'w') as f:
            json.dump(
                [d for d in data
                 if start <= datetime.strptime(d['resolution_date'], DUMPFORMAT)],
                f, indent=2)
        click.echo(f'file dumped at: ./jira-dataset-from-{start}.json')
    elif end:
        with open(f'jira-dataset-to-{end}.json', 'w') as f:
            json.dump(
                [d for d in data
                 if datetime.strptime(d['resolution_date'], DUMPFORMAT) <= end],
                f, indent=2)
        click.echo(f'file dumped at: ./jira-dataset-to-{end}.json')
    else:
        click.echo(f'file dumped at: ./{FULL_DATASET_FILEPATH}')


if __name__ == '__main__':
    cli()
