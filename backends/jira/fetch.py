from abc import ABC, abstractmethod
from functools import partial
from itertools import groupby
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Optional

from .types import (
    IssueTypes, JiraIssue, Sprint,
    StatusTypes, IntermediateParser
)
from config import TRADING_BOARD

JIRA_BASEURL = 'https://limejump.atlassian.net/rest/agile'
MY_TOKEN = 'eVDgTL8kVgdXFaiJtbCF4001'
DUMPFORMAT = "%Y-%m-%dT%H:%M:%S"
ALL_ISSUES_FILENAME = 'jira-all-issues.json'


class JiraPager(ABC):
    auth = HTTPBasicAuth("grahame.gardiner@limejump.com", MY_TOKEN)

    def __init__(self, url, items_key, data_constructor):
        self.url = url
        self.items_key = items_key
        self.data_constructor = data_constructor

    def fetch_batch(self, start_at):
        # FIXME: use some url constructor lib
        return requests.get(
            self.url + f"&startAt={start_at}", auth=self.auth).json()

    @abstractmethod
    def fetch_all(self):
        pass


class CheckTotalPager(JiraPager):
    def fetch_all(self):
        data = []

        def extract_batch(batch_json):
            for item_json in batch_json[self.items_key]:
                item = self.data_constructor(item_json)
                if item is not None:
                    data.append(item)

        processed = 0
        first_batch = self.fetch_batch(processed)
        total = first_batch['total']
        extract_batch(first_batch)
        processed += len(first_batch[self.items_key])

        while processed < total:
            batch = self.fetch_batch(processed)
            extract_batch(batch)
            processed += len(batch[self.items_key])

        return data


class CheckTotalPagerWithSubRequests(JiraPager):
    def fetch_all(self):
        data = []

        def fetcher(url):
            return requests.get(url, auth=self.auth).json()

        def extract_batch(batch_json):
            for item_json in batch_json[self.items_key]:
                item = self.data_constructor(item_json, fetcher)
                if item is not None:
                    data.append(item)

        processed = 0
        first_batch = self.fetch_batch(processed)
        total = first_batch['total']
        extract_batch(first_batch)
        processed += len(first_batch[self.items_key])

        while processed < total:
            batch = self.fetch_batch(processed)
            extract_batch(batch)
            processed += len(batch[self.items_key])

        return data


class CheckLastPager(JiraPager):
    def fetch_all(self):
        data = []

        def extract_batch(batch_json):
            for item_json in batch_json[self.items_key]:
                item = self.data_constructor(item_json)
                if item is not None:
                    data.append(item)

        processed = 0
        first_batch = self.fetch_batch(processed)
        final = first_batch['isLast']
        extract_batch(first_batch)
        processed += len(first_batch)

        while not final:
            batch = self.fetch_batch(processed)
            extract_batch(batch)
            final = batch['isLast']
            processed += len(batch)

        return data


def measurable_issue(issue: JiraIssue) -> bool:
    stand_alone_issue = not issue.subtasks
    epic = issue.type_ == IssueTypes.epic
    return stand_alone_issue and not epic


def issues_with_full_metrics(board_id, issue_json: dict) -> Optional[JiraIssue]:
    issue = JiraIssue.from_parsed_json(
        IntermediateParser(
            from_status_id=make_from_status_id(board_id),
            from_issue_id=make_from_issue_id()).parse(issue_json))
    if measurable_issue(issue) and issue.status == StatusTypes.done:
        return issue


def fetch_all_completed_issues() -> List[JiraIssue]:
    pager = CheckTotalPager(
        url=(
            JIRA_BASEURL +
            f'/1.0/board/{TRADING_BOARD}/issue/?expand=changelog&maxResults=50'),
        items_key='issues',
        data_constructor=issues_with_full_metrics)
    return pager.fetch_all()


def make_from_issue_id():
    issue_types = requests.get(
        'https://limejump.atlassian.net/rest/api/3/issuetype',
        auth=HTTPBasicAuth(
            "grahame.gardiner@limejump.com", MY_TOKEN)).json()

    name_key = lambda x: x[0]

    issue_type_groups = groupby(sorted([
        (i['name'], i['id']) for i in issue_types],
        key=name_key), key=name_key)

    id_to_issue_type = {}
    for name, ids in issue_type_groups:
        try:
            issue_type = IssueTypes[name]
        # We only care about some issue types
        except KeyError:
            # FIXME: logging??
            print("Discarding issue type:", name)
            continue
        for _, issue_id in ids:
            existing_type = id_to_issue_type.get(issue_id)
            if existing_type and existing_type != issue_type:
                raise KeyError(
                    f"Overlapping issue id's: {issue_type}, {existing_type}")
            # Err yup, multiple id's for the same issue type
            id_to_issue_type[issue_id] = issue_type
    return id_to_issue_type.get


def make_from_status_id(board_id):
    config = requests.get(
        f'{JIRA_BASEURL}/1.0/board/{board_id}/configuration',
        auth=HTTPBasicAuth(
            "grahame.gardiner@limejump.com", MY_TOKEN)).json()
    status_types = config['columnConfig']['columns']
    id_to_status_type = {}
    for status_record in status_types:
        name = status_record['name']
        try:
            status_type = StatusTypes[name]
        except KeyError:
            # FIXME: logging
            print("Discarding status type:", name)
            continue
        statuses = status_record['statuses']
        for status in statuses:
            id_to_status_type[status['id']] = status_type
    return id_to_status_type.get


def fetch_closed_sprint_urls(board_id) -> List[str]:
    # The sprint endpoint doesn't respect the maxResults param.
    # We rarely want to construct sprint object with full issue lists
    # for every sprint, so just fetch the urls as an optimisation
    def constructor(sprint_json: dict) -> Optional[str]:
        print(sprint_json['name'])
        if sprint_json['state'] == 'closed':
            return sprint_json['self']

    pager = CheckLastPager(
        url=JIRA_BASEURL + (
            f'/1.0/board/{board_id}/sprint?maxResults=50'),
        items_key='values',
        data_constructor=constructor)
    all = pager.fetch_all()
    return all


def fetch_sprints(board_id, past: int = 3) -> List[dict]:
    closed_sprint_urls = fetch_closed_sprint_urls(board_id)
    all_ = [
        Sprint.from_parsed_json(
            requests.get(
                url, auth=HTTPBasicAuth(
                    "grahame.gardiner@limejump.com", MY_TOKEN)
            ).json(), issues_fetcher=partial(
                fetch_sprint_issues, board_id))
        for url in closed_sprint_urls[-past:]
    ]
    return [sprint.to_json() for sprint in all_]


def fetch_sprint_issues(board_id, sprint_id):
    parser = IntermediateParser(
        from_issue_id=make_from_issue_id(),
        from_status_id=make_from_status_id(board_id))

    def constructor(issue_json, fetch_func):
        parsed_json = parser.parse(issue_json)
        return JiraIssue.from_parsed_json(parsed_json, parser, fetch_func)

    pager = CheckTotalPagerWithSubRequests(
        url=JIRA_BASEURL + (
            f'/1.0/board/{TRADING_BOARD}/sprint/{sprint_id}/issue?maxResults=50&expand=changelog'),
        items_key='issues',
        data_constructor=constructor)
    return pager.fetch_all()


def get_latest_completed_sprint(sprints: List[Sprint]) -> Optional[Sprint]:
    # FIXME: What about new teams tha that haven't completed a sprint??
    while sprint := sprints.pop():
        if sprint.state == 'closed':
            break
    return sprint
