from abc import ABC, abstractmethod
import requests
from requests.auth import HTTPBasicAuth
from typing import List

from .types import (
    JiraIssue, IssueMetrics, Sprint,
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
    return (
        (issue.type_ == ISSUE_TYPES.subtask or
         (issue.type_ == ISSUE_TYPES.story and not issue.subtasks)))


def create_issue_if_done(issue_json: dict) -> Optional[JiraIssue]:
    issue = JiraIssue.from_json(issue_json)
    if measurable_issue(issue):
        if issue.status == STATUS_TYPES.done:
            issue.metrics = IssueMetrics.from_json(issue_json)
            return issue
def fetch_all_completed_issues() -> List[JiraIssue]:
    pager = CheckTotalPager(
        url=(
            JIRA_BASEURL +
            f'/1.0/board/{TRADING_BOARD}/issue/?expand=changelog&maxResults=50'),
        items_key='issues',
        data_constructor=create_issue_if_done)
    return pager.fetch_all()


def fetch_sprints() -> List[Sprint]:
    pager = CheckLastPager(
        url=JIRA_BASEURL + (
            f'/1.0/board/{TRADING_BOARD}/sprint?maxResults=50'),
        items_key='values',
        data_constructor=Sprint.from_json)
    return pager.fetch_all()
