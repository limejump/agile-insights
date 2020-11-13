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
def base_issues():
    return [
        JiraIssue(
            name="An Issue",
            summary="Issue for sprint",
            epic=None,
            type_=IssueTypes.story,
            status=StatusTypes.todo,
            story_points=5.0,
            labels=set(),
            subtasks=[],
            status_metrics=StatusMetrics(
                started=False,
                finished=False,
                start=None,
                end=None,
                days_taken=None),
            sprint_metrics=SprintMetrics(sprint_additions=[]))
    ]


def test_sprint_with_issue(
        basic_scenario, base_issues, sprint_issues_lens):
    raw_json, result = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issues)
    result = sprint_issues_lens.set(base_issues)(result)
    assert sprint == result


def test_no_sprint_metrics_means_unplanned(basic_scenario, base_issues):
    raw_json, _ = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issues)
    assert sprint.planned_issue(sprint.issues[0]) is False


def test_planned_issue_added_at_sprint_start(
        basic_scenario, base_issues, sprint_issues_lens):
    raw_json, _ = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issues)
    sprint = sprint_issues_lens[0].sprint_metrics.set(
        SprintMetrics(
            sprint_additions=[{
                "timestamp": datetime(
                    2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
                "sprint_id": 1
            }]
        )
    )(sprint)
    assert sprint.planned_issue(sprint.issues[0]) is True


def test_planned_issue_added_before_sprint_start(
        basic_scenario, base_issues, sprint_issues_lens):
    raw_json, _ = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issues)
    sprint = sprint_issues_lens[0].sprint_metrics.set(
        SprintMetrics(
            sprint_additions=[{
                "timestamp": datetime(
                    2020, 1, 1, 8, 59, 0, tzinfo=timezone(timedelta(hours=1))),
                "sprint_id": 1
            }]
        )
    )(sprint)
    assert sprint.planned_issue(sprint.issues[0]) is True


def test_unplanned_issue_added_after_sprint_start(
        basic_scenario, base_issues, sprint_issues_lens):
    raw_json, _ = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issues)
    sprint = sprint_issues_lens[0].sprint_metrics.set(
        SprintMetrics(
            sprint_additions=[{
                "timestamp": datetime(
                    2020, 1, 1, 9, 1, 0, tzinfo=timezone(timedelta(hours=1))),
                "sprint_id": 1
            }]
        )
    )(sprint)
    assert sprint.planned_issue(sprint.issues[0]) is False


def test_started_in_sprint(
        basic_scenario, base_issues, sprint_issues_lens):
    raw_json, _ = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issues)
    sprint = sprint_issues_lens[0].status_metrics.set(
        StatusMetrics(
            started=False,
            finished=True,
            start=datetime(
                2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            end=datetime(
                2020, 1, 2, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            days_taken=1),
    )(sprint)


def test_started_because_finished_in_sprint(
        basic_scenario, base_issues, sprint_issues_lens):
    raw_json, _ = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issues)
    sprint = sprint_issues_lens[0].status_metrics.set(
        StatusMetrics(
            started=False,
            finished=True,
            start=None,
            end=datetime(
                2020, 1, 2, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            days_taken=1),
    )(sprint)
    assert sprint.started_in_sprint(sprint.issues[0]) is True


def test_not_started_in_sprint(
        basic_scenario, base_issues, sprint_issues_lens):
    raw_json, _ = basic_scenario
    sprint = Sprint.from_parsed_json(raw_json, lambda x: base_issues)
    sprint = sprint_issues_lens[0].status_metrics.set(
        StatusMetrics(
            started=False,
            finished=True,
            start=datetime(
                2019, 12, 30, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            end=datetime(
                2020, 1, 1, 8, 59, 0, tzinfo=timezone(timedelta(hours=1))),
            days_taken=1),
    )(sprint)
    assert sprint.started_in_sprint(sprint.issues[0]) is False
