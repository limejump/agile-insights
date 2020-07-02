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


def measurable_issue(issue: JiraIssue) -> bool:
    return (
        (issue.type_ == ISSUE_TYPES.subtask or
         (issue.type_ == ISSUE_TYPES.story and not issue.has_subtasks)) and
        issue.status == STATUS_TYPES.done)


def fetch_batch(start_at):
    return requests.get(
        JIRA_BASEURL + (
            f'/1.0/board/{TRADING_BOARD}/issue/?expand=changelog&maxResults=50&startAt={start_at}'),
        auth=HTTPBasicAuth("grahame.gardiner@limejump.com", MY_TOKEN)).json()


def fetch_all_issues() -> List[JiraIssue]:
    data = []

    def extract_batch(issues):
        for issue_json in issues['issues']:
            issue = JiraIssue.from_json(issue_json)
            if measurable_issue(issue):
                issue.metrics = IssueMetrics.from_json(issue_json)
                data.append(issue)

    processed = 0
    first_batch = fetch_batch(processed)
    total = first_batch['total']
    extract_batch(first_batch)
    processed += len(first_batch['issues'])

    while processed < total:
        batch = fetch_batch(processed)
        extract_batch(batch)
        processed += len(first_batch['issues'])

    return data
