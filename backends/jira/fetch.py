import requests
from requests.auth import HTTPBasicAuth
from typing import List

from .types import (
    JiraIssue, IssueMetrics,
    ISSUE_TYPES, STATUS_TYPES
)

JIRA_BASEURL = 'https://limejump.atlassian.net/rest/agile'
TRADING_BOARD = 140
MY_TOKEN = 'eVDgTL8kVgdXFaiJtbCF4001'
DUMPFORMAT = "%Y-%m-%dT%H:%M:%S"
ALL_ISSUES_FILENAME = 'jira-all-issues.json'


class CheckTotalPager:
    auth = HTTPBasicAuth("grahame.gardiner@limejump.com", MY_TOKEN)

    def __init__(self, url, items_key, data_constructor):
        self.url = url
        self.items_key = items_key
        self.data_constructor = data_constructor

    def fetch_batch(self, start_at):
        # FIXME: use some url constructor lib
        return requests.get(
            self.url + f"&startAt={start_at}", auth=self.auth).json()

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


def measurable_issue(issue: JiraIssue) -> bool:
    return (
        (issue.type_ == ISSUE_TYPES.subtask or
         (issue.type_ == ISSUE_TYPES.story and not issue.has_subtasks)) and
        issue.status == STATUS_TYPES.done)


def create_issue(issue_json):
    issue = JiraIssue.from_json(issue_json)
    if measurable_issue(issue):
        issue.metrics = IssueMetrics.from_json(issue_json)
        return issue


def fetch_all_issues() -> List[JiraIssue]:
    pager = CheckTotalPager(
        url=(
            JIRA_BASEURL +
            f'/1.0/board/{TRADING_BOARD}/issue/?expand=changelog&maxResults=50'),
        items_key='issues',
        data_constructor=create_issue)
    return pager.fetch_all()


def fetch_sprints(start_at):
    requests.get(
        JIRA_BASEURL + (
            f'/1.0/board/{TRADING_BOARD}/sprint'),
        auth=HTTPBasicAuth("grahame.gardiner@limejump.com", MY_TOKEN)).json()
