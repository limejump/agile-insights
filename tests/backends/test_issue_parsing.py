import pytest

from collections import namedtuple
from datetime import datetime, timedelta, timezone
from lenses import lens

from backends.jira.parse import (
    ParentGetter,
    JiraIssue, SprintMetrics, StatusMetrics, StatusTypes, IssueTypes,
    intermediate_parse, parse_issue)


LensCollection = namedtuple(
    'LensCollection', ('raw', 'intermediate', 'final'))


@pytest.fixture
def status_history_lenses():
    status_history = LensCollection(
        lens['changelog']['histories'],
        lens['status_history'],
        lens.status_metrics)
    return status_history


@pytest.fixture
def status_lenses():
    status = LensCollection(
        lens['fields']['status']['name'],
        lens['status'],
        lens.status)
    return status


@pytest.fixture
def sprint_history_lenses():
    sprint = LensCollection(
        lens['changelog']['histories'],
        lens['sprint_history'],
        lens.sprint_metrics
    )
    return sprint


@pytest.fixture
def basic_scenario():
    return (
        {
            "id": "1",
            "key": "EXAMPLE-1",
            "changelog": {"histories": []},
            "fields": {
                "labels": [],
                "status": {"name": "To Do"},
                "subtasks": [],
                "issuetype": {"name": "Task"},
                "customfield_11638": 5.0,
                "summary": "Test all the things"
            }
        },
        {
            "name": "EXAMPLE-1",
            "summary": "Test all the things",
            "epic": None,
            "type": IssueTypes.task,
            "status": StatusTypes.todo,
            "story_points": 5.0,
            "subtasks": [],
            "status_history": [],
            "sprint_history": []
        },
        JiraIssue(
            name="EXAMPLE-1",
            summary="Test all the things",
            epic=None,
            type_=IssueTypes.task,
            status=StatusTypes.todo,
            story_points=5.0,
            subtasks=[],
            status_metrics=StatusMetrics(
                started=False,
                finished=False,
                start=None,
                end=None,
                days_taken=None),
            sprint_metrics=SprintMetrics(sprint_additions=[]),
            get_parent_issue=None)
    )


def test_basic_parsing(basic_scenario):
    raw_json, intermediate, final = basic_scenario
    assert intermediate_parse(raw_json) == intermediate
    assert parse_issue(raw_json) == final


def test_status_history_rounds_up_to_nearest_day(
        basic_scenario, status_lenses, status_history_lenses):
    ''' We only capture days_taken, and we always round up.
        This is subject to change. But finer grained time measures
        are likely not useful for forecasting.
    '''
    raw_json, intermediate, final = basic_scenario
    issue = status_lenses.raw.set('Done')(raw_json)
    issue = status_history_lenses.raw.set(
        [
            {
                "created": "2020-01-01T09:01:00.000+0100",
                "items": [
                    {
                        "field": "status",
                        "fieldId": "status",
                        "fromString": "In Progress",
                        "toString": "Done"
                    }
                ]
            },
            {
                "created": "2020-01-01T09:00:00.000+0100",
                "items": [
                    {
                        "field": "status",
                        "fieldId": "status",
                        "fromString": "To Do",
                        "toString": "In Progress"
                    }
                ]
            },
        ])(issue)
    intermediate = status_lenses.intermediate.set(
        StatusTypes.done)(intermediate)
    intermediate = status_history_lenses.intermediate.set([
        {
            "timestamp": datetime(
                2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            "from": StatusTypes.todo,
            "to": StatusTypes.inprogress
        },
        {
            "timestamp": datetime(
                2020, 1, 1, 9, 1, 0, tzinfo=timezone(timedelta(hours=1))),
            "from": StatusTypes.inprogress,
            "to": StatusTypes.done
        }
    ])(intermediate)
    final = status_lenses.final.set(StatusTypes.done)(final)
    final = status_history_lenses.final.set(
        StatusMetrics(
            started=True, finished=True,
            start=datetime(
                2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            end=datetime(
                2020, 1, 1, 9, 1, 0, tzinfo=timezone(timedelta(hours=1))),
            days_taken=1))(final)
    assert intermediate_parse(issue) == intermediate
    assert parse_issue(issue) == final


def test_status_history_no_done_date_no_end(
        basic_scenario, status_lenses, status_history_lenses):
    ''' If a ticket hasn't been moved to done it has no
        days_taken metric or end date.
    '''
    raw_json, intermediate, final = basic_scenario
    raw_json = status_lenses.raw.set('In Progress')(raw_json)
    raw_json = status_history_lenses.raw.set(
        [
            {
                "created": "2020-01-01T09:00:00.000+0100",
                "items": [
                    {
                        "field": "status",
                        "fieldId": "status",
                        "fromString": "To Do",
                        "toString": "In Progress"
                    }
                ]
            },
        ])(raw_json)
    intermediate = status_lenses.intermediate.set(
        StatusTypes.inprogress)(intermediate)
    intermediate = status_history_lenses.intermediate.set([
        {
            "timestamp": datetime(
                2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            "from": StatusTypes.todo,
            "to": StatusTypes.inprogress
        },
    ])(intermediate)
    final = status_lenses.final.set(StatusTypes.inprogress)(final)
    final = status_history_lenses.final.set(
        StatusMetrics(
            started=True, finished=False,
            start=datetime(
                2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            end=None,
            days_taken=None))(final)
    assert intermediate_parse(raw_json) == intermediate
    assert parse_issue(raw_json) == final


def test_status_history_straight_to_done(
        basic_scenario, status_lenses, status_history_lenses):
    # TODO: do we artificially set days_taken to 1?
    raw_json, intermediate, final = basic_scenario
    raw_json = status_lenses.raw.set('Done')(raw_json)
    raw_json = status_history_lenses.raw.set(
        [
            {
                "created": "2020-01-01T09:00:00.000+0100",
                "items": [
                    {
                        "field": "status",
                        "fieldId": "status",
                        "fromString": "To Do",
                        "toString": "Done"
                    }
                ]
            },
        ])(raw_json)
    intermediate = status_lenses.intermediate.set(
        StatusTypes.done)(intermediate)
    intermediate = status_history_lenses.intermediate.set([
        {
            "timestamp": datetime(
                2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            "from": StatusTypes.todo,
            "to": StatusTypes.done
        },
    ])(intermediate)
    final = status_lenses.final.set(StatusTypes.done)(final)
    final = status_history_lenses.final.set(
        StatusMetrics(
            started=False, finished=True,
            start=None,
            end=datetime(
                2020, 1, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            days_taken=None))(final)
    assert intermediate_parse(raw_json) == intermediate
    assert parse_issue(raw_json) == final


def test_sprint_history_addition(basic_scenario, sprint_history_lenses):
    raw_json, intermediate, final = basic_scenario
    raw_json = sprint_history_lenses.raw.set([
        {
            "created": "2020-01-01T11:00:00.000+0100",
            "items": [
                {
                    "field": "Sprint",
                    "from": "1",
                    "to": "1, 2",
                }
            ]
        },
    ])(raw_json)
    intermediate = sprint_history_lenses.intermediate.set([
        {
            "timestamp": datetime(
                2020, 1, 1, 11, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            "from": {1},
            "to": {1, 2}
        }
    ])(intermediate)
    assert intermediate_parse(raw_json) == intermediate
    final = sprint_history_lenses.final.set(
        SprintMetrics(sprint_additions=[
            {
                "timestamp": datetime(
                    2020, 1, 1, 11, 0, 0, tzinfo=timezone(timedelta(hours=1))),
                "sprint_id": 2
            }
        ])
    )(final)
    assert parse_issue(raw_json) == final


def test_sprint_history_removal(basic_scenario, sprint_history_lenses):
    raw_json, intermediate, final = basic_scenario
    raw_json = sprint_history_lenses.raw.set([
        {
            "created": "2020-01-01T11:00:00.000+0100",
            "items": [
                {
                    "field": "Sprint",
                    "from": "1, 2",
                    "to": "1",
                }
            ]
        },
    ])(raw_json)
    intermediate = sprint_history_lenses.intermediate.set([
        {
            "timestamp": datetime(
                2020, 1, 1, 11, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            "from": {1, 2},
            "to": {1}
        }
    ])(intermediate)
    assert intermediate_parse(raw_json) == intermediate
    final = sprint_history_lenses.final.set(
        SprintMetrics(sprint_additions=[])
    )(final)
    assert parse_issue(raw_json) == final


def mock_subtask_fetcher(url):
    # id_ = url.split('/')[-1]
    return {
            # "id": id_,
            "key": "A subtask",
            "changelog": {"histories": []},
            "fields": {
                "labels": [],
                "status": {"name": "To Do"},
                "subtasks": [],
                "issuetype": {"name": "Subtask"},
                "customfield_11638": 2.0,
                "summary": "Test some of the things"
            }
        }


@pytest.fixture
def subtask_scenario():
    task = JiraIssue(
        name="EXAMPLE-1",
        summary="Test all the things",
        epic="An Epic",
        type_=IssueTypes.task,
        status=StatusTypes.todo,
        story_points=5.0,
        subtasks=[],
        status_metrics=StatusMetrics(
            started=False,
            finished=False,
            start=None,
            end=None,
            days_taken=None),
        sprint_metrics=SprintMetrics(sprint_additions=[]),
        get_parent_issue=None)
    task.subtasks = [
        JiraIssue(
            name="A subtask",
            summary="Test some of the things",
            epic="An Epic",
            type_=IssueTypes.subtask,
            status=StatusTypes.todo,
            story_points=2.0,
            subtasks=[],
            status_metrics=StatusMetrics(
                started=False,
                finished=False,
                start=None,
                end=None,
                days_taken=None),
            sprint_metrics=SprintMetrics(sprint_additions=[]),
            get_parent_issue=ParentGetter(task)),
        JiraIssue(
            name="A subtask",
            summary="Test some of the things",
            epic="An Epic",
            type_=IssueTypes.subtask,
            status=StatusTypes.todo,
            story_points=2.0,
            subtasks=[],
            status_metrics=StatusMetrics(
                started=False,
                finished=False,
                start=None,
                end=None,
                days_taken=None),
            sprint_metrics=SprintMetrics(sprint_additions=[]),
            get_parent_issue=ParentGetter(task)),
    ]
    return (
        {
            "id": "1",
            "key": "EXAMPLE-1",
            "changelog": {"histories": []},
            "fields": {
                "parent": {
                    "fields": {
                        "issuetype": {"name": "epic"},
                        "summary": "An Epic"
                    }
                },
                "labels": [],
                "status": {"name": "To Do"},
                "subtasks": [
                    {
                        "id": 2,
                        "self": "https://path/to/issue/2"
                    },
                    {
                        "id": 3,
                        "self": "https://path/to/issue/3"
                    },
                ],
                "issuetype": {"name": "Task"},
                "customfield_11638": 5.0,
                "summary": "Test all the things"
            }
        },
        {
            "name": "EXAMPLE-1",
            "summary": "Test all the things",
            "epic": "An Epic",
            "type": IssueTypes.task,
            "status": StatusTypes.todo,
            "story_points": 5.0,
            "subtasks": [
                "https://path/to/issue/2",
                "https://path/to/issue/3",
            ],
            "status_history": [],
            "sprint_history": []
        },
        task
    )


def test_issue_with_subtasks(subtask_scenario):
    raw_json, intermediate, final = subtask_scenario
    assert intermediate_parse(raw_json) == intermediate
    assert parse_issue(raw_json, mock_subtask_fetcher) == final


@pytest.fixture
def subtask_lenses():
    return LensCollection(
        None,
        None,
        lens.subtasks)


def test_subtasks_inherit_from_parent(
        subtask_scenario, subtask_lenses, sprint_history_lenses):
    raw_json, intermediate, final = subtask_scenario
    raw_json = sprint_history_lenses.raw.set([
        {
            "created": "2020-01-01T11:00:00.000+0100",
            "items": [
                {
                    "field": "Sprint",
                    "from": "1",
                    "to": "1, 2",
                }
            ]
        },
    ])(raw_json)
    intermediate = sprint_history_lenses.intermediate.set([
        {
            "timestamp": datetime(
                2020, 1, 1, 11, 0, 0, tzinfo=timezone(timedelta(hours=1))),
            "from": {1},
            "to": {1, 2}
        }
    ])(intermediate)
    sprint_metrics = SprintMetrics(sprint_additions=[
            {
                "timestamp": datetime(
                    2020, 1, 1, 11, 0, 0, tzinfo=timezone(timedelta(hours=1))),
                "sprint_id": 2
            }
        ])
    final = sprint_history_lenses.final.set(sprint_metrics)(final)
    # Subtasks inherit their SprintMetrics from their parent
    # because the parent is the entity that you can physical move between
    # sprints.
    final = subtask_lenses.final.Each().modify(
        lambda subtask: sprint_history_lenses.final.set(
            sprint_metrics)(subtask))(final)
    assert parse_issue(raw_json, mock_subtask_fetcher) == final
    assert final.subtasks[0].label == final.label != None
    assert final.subtasks[0].epic == final.epic != None
