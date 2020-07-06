from abc import ABC, abstractmethod
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Optional

from .types import (
    JiraIssue, Sprint,
    ISSUE_TYPES, STATUS_TYPES
)

JIRA_BASEURL = 'https://limejump.atlassian.net/rest/agile'
TRADING_BOARD = 140
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
    epic = issue.type_ == ISSUE_TYPES.epic
    return stand_alone_issue and not epic


def issues_with_full_metrics(issue_json: dict) -> Optional[JiraIssue]:
    issue = JiraIssue.from_json(issue_json)
    if measurable_issue(issue) and issue.status == STATUS_TYPES.done:
        return issue


def fetch_all_completed_issues() -> List[JiraIssue]:
    pager = CheckTotalPager(
        url=(
            JIRA_BASEURL +
            f'/1.0/board/{TRADING_BOARD}/issue/?expand=changelog&maxResults=50'),
        items_key='issues',
        data_constructor=issues_with_full_metrics)
    return pager.fetch_all()


def fetch_sprints() -> List[Sprint]:
    pager = CheckLastPager(
        url=JIRA_BASEURL + (
            f'/1.0/board/{TRADING_BOARD}/sprint?maxResults=50'),
        items_key='values',
        data_constructor=Sprint.from_json)
    latest = get_latest_completed_sprint(pager.fetch_all())
    return fetch_sprint_issues(latest.id_)


def fetch_sprint_issues(sprint_id):
    pager = CheckTotalPagerWithSubRequests(
        url=JIRA_BASEURL + (
            f'/1.0/board/{TRADING_BOARD}/sprint/{sprint_id}/issue?maxResults=50&expand=changelog'),
        items_key='issues',
        data_constructor=JiraIssue.from_json)
    return pager.fetch_all()


def get_latest_completed_sprint(sprints: List[Sprint]) -> Optional[Sprint]:
    # FIXME: What about new teams tha that haven't completed a sprint??
    while sprint := sprints.pop():
        if sprint.state == 'closed':
            break
    return sprint
