from abc import ABC, abstractmethod
from functools import partial
from dataclasses import dataclass
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Optional

from .parse import (
    IssueTypes, JiraIssue, Sprint,
    StatusTypes, parse_issue)

from config import config, configclass


@configclass
@dataclass
class JiraConfig:
    base_url: str
    email: str
    access_token: str


config.register('jira', JiraConfig)


def request_with_auth_check(url):
    jira_config = config.get('jira')
    auth = HTTPBasicAuth(jira_config.email, jira_config.access_token)
    resp = requests.get(url, auth=auth)
    resp.raise_for_status()
    return resp


class JiraPager(ABC):
    def __init__(self, url, items_key, data_constructor):
        jiraconfig = config.get('jira')
        self.base_url = jiraconfig.base_url
        self.url = self.base_url + url
        self.items_key = items_key
        self.data_constructor = data_constructor

    def fetch_batch(self, start_at):
        # FIXME: use some url constructor lib
        return request_with_auth_check(
            self.url + f"&startAt={start_at}").json()

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
            return request_with_auth_check(url).json()

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


def issues_with_full_metrics(issue_json: dict) -> Optional[JiraIssue]:
    issue = parse_issue(issue_json)
    if measurable_issue(issue) and issue.status == StatusTypes.done:
        return issue


def fetch_all_completed_issues(board_id) -> List[JiraIssue]:
    pager = CheckTotalPager(
        url=(
            f'/1.0/board/{board_id}/issue/?expand=changelog&maxResults=50'),
        items_key='issues',
        data_constructor=issues_with_full_metrics)
    return pager.fetch_all()


def fetch_closed_sprint_urls(board_id) -> List[str]:
    # The sprint endpoint doesn't respect the maxResults param.
    # We rarely want to construct sprint object with full issue lists
    # for every sprint, so just fetch the urls as an optimisation
    def constructor(sprint_json: dict) -> Optional[str]:
        if sprint_json['state'] == 'closed':
            return sprint_json['self']

    pager = CheckLastPager(
        url=(
            f'/1.0/board/{board_id}/sprint?maxResults=50'),
        items_key='values',
        data_constructor=constructor)
    all = pager.fetch_all()
    return all


def fetch_sprints(board_id, past: int = 3) -> List[dict]:
    closed_sprint_urls = fetch_closed_sprint_urls(board_id)
    all_ = [
        Sprint.from_parsed_json(
            request_with_auth_check(url).json(),
            issues_fetcher=partial(fetch_sprint_issues, board_id))
        for url in closed_sprint_urls[-past:]
    ]
    return [sprint.to_mongo() for sprint in all_]


def fetch_sprint_issues(board_id, sprint_id):
    pager = CheckTotalPagerWithSubRequests(
        url=(
            f'/1.0/board/{board_id}/sprint/{sprint_id}'
            '/issue?maxResults=50&expand=changelog'),
        items_key='issues',
        data_constructor=parse_issue)
    return pager.fetch_all()


def get_latest_completed_sprint(sprints: List[Sprint]) -> Optional[Sprint]:
    # FIXME: What about new teams tha that haven't completed a sprint??
    while sprint := sprints.pop():
        if sprint.state == 'closed':
            break
    return sprint
