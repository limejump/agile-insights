import arrow
from datetime import datetime
from dataclasses import dataclass, field
from requests import get
from requests.auth import HTTPBasicAuth
from typing import NamedTuple, List

MY_TOKEN = 'eVDgTL8kVgdXFaiJtbCF4001'
JIRA_BASEURL = 'https://limejump.atlassian.net/rest/agile'
TRADING_BOARD = 140
TIMEFORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"

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
    name: str
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
        # this is a terrible approach to capture this, but will do for now.
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


def fetch(start_at):
    return get(
        JIRA_BASEURL + (
            f'/1.0/board/{TRADING_BOARD}/issue/?expand=changelog&maxResults=50&startAt={start_at}'),
        auth=HTTPBasicAuth("grahame.gardiner@limejump.com", MY_TOKEN)).json()


def extract():
    data = []

    def extract_batch(issues):
        for issue in issues['issues']:
            if (
                    int(issue['fields']['status']['id']) == STATUS_TYPES.done and
                    int(issue['fields']['issuetype']['id']) in ISSUE_TYPES):
                if not issue['fields']['subtasks']:
                    histories = issue['changelog']['histories']
                    status_changes = []
                    for h in histories:
                        s = {'timestamp': h['created']}
                        for i in h['items']:
                            if 'fieldId' in i and i['fieldId'] == 'status':
                                s['from'] = int(i['from'])
                                s['to'] = int(i['to'])
                                status_changes.append(s)
                    data.append(
                        IssueMetrics(
                            name=issue['key'],
                            storypoints=issue['fields']['customfield_11638'],
                            resolution_date=datetime.strptime(
                                issue['fields']['resolutiondate'],
                                TIMEFORMAT),
                            status_history=status_changes))

    processed = 0
    first_batch = fetch(processed)
    total = first_batch['total']
    extract_batch(first_batch)
    processed += len(first_batch['issues'])

    while processed < total:
        batch = fetch(processed)
        extract_batch(batch)
        processed += len(first_batch['issues'])

    return data


data = extract()
two_months_worth = [
    i for i in data if i.resolution_date > arrow.now().shift(months=-2)
]
from pprint import pprint
pprint(two_months_worth)
print(len(data))
print(len(two_months_worth))
