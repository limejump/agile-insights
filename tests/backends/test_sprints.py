import pytest

from datetime import datetime, timedelta, timezone
from lenses import lens

from backends.jira.parse import IssueTypes, JiraIssue, Sprint, SprintMetrics, StatusMetrics, StatusTypes


@pytest.fixture
def basic_scenario():
    return (
        {
            "id": 1,
            "goal": "Achieve Something",
            "name": "Usain",
            "state": "closed",
            "startDate": "2020-01-01T09:00:00.000+0100",
            "endDate": "2020-01-14T09:00:00.000+0100",
            "completeDate": "2020-01-14T09:00:00.000+0100"
        },
        Sprint(
            id_=1,
            goal="Achieve Something",
            name="Usain",
            state="closed",
            start=datetime(
                2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            end=datetime(
                2020, 1, 14, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))))
    )


def test_basic_parsing(basic_scenario):
    raw_json, result = basic_scenario
    assert Sprint.from_parsed_json(raw_json) == result


@pytest.fixture
def sprint_issues_lens():
    return lens.issues


@pytest.fixture
def base_issue():
    return JiraIssue(
        name="An Issue",
        summary="Issue for sprint",
        epic=None,
        type_=IssueTypes.story,
        status=StatusTypes.todo,
        story_points=5.0,
        subtasks=[],
        status_metrics=StatusMetrics(
            started=False,
            finished=False,
            start=None,
            end=None,
            days_taken=None),
        sprint_metrics=SprintMetrics(sprint_additions=[]))


def test_sprint_with_issue(
        basic_scenario, base_issue, sprint_issues_lens):
    raw_json, result = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issue)
    result = sprint_issues_lens.set(base_issue)(result)
    assert sprint == result
