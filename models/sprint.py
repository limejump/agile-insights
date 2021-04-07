import arrow
import pandas as pd
import plotly.graph_objects as go

from database.mongo import get_client
from reports.utils import mk_issues_summary_df


class SprintReadOnly:
    empty_pie = go.Pie(labels=[], values=[], scalegroup='one')

    def __init__(self, data, auxillary_data):
        self._data = data
        self._auxillary_data = auxillary_data
        self.issues_df = pd.DataFrame.from_records(
            self._data['issues'])

    @property
    def name(self):
        return self._data['name']

    @property
    def goal(self):
        return self._data['goal']

    @property
    def goal_completed(self):
        return bool(self._auxillary_data.get('goal_completed'))

    @property
    def notes(self):
        return self._auxillary_data.get('notes')

    def mk_issues_summary_df(self):
        return mk_issues_summary_df(self._data)

    def mk_bau_breakdown_df(self):
        bau = []
        for bau_category in self.issues_df[
                self.issues_df.bau.eq(True)].bau_breakdown.values:
            bau.extend(bau_category)
        df = pd.DataFrame(bau)
        return df


class SprintReadWrite(SprintReadOnly):
    def __init__(self, sprint_id):
        self.db_client = get_client()
        super().__init__(
            self.db_client.get_sprint(sprint_id),
            self.db_client.get_sprint_auxillary_data(sprint_id)
        )

    def update_goal_completion(self, goal_completion_val):
        # FIXME: potential data-race under load.
        # Updating two documents outside of transaction.
        # Highly unlikely to be a problem with current usage.
        # Symptoms: sprint and performance_reports have inconsistent
        # goal completion values.
        self.db_client.update_sprint_auxillary_data(
            self._data['_id'],
            {
                'goal_completed': goal_completion_val,
                'notes': self.notes
            }
        )
        self.db_client.update_performance_report(
            self._data['_id'],
            {'goal_completed': self.goal_completion_as_int(
                goal_completion_val)})
        sprint = SprintReadWrite(self._data['_id'])
        return sprint

    @staticmethod
    def goal_completion_as_int(goal_completed):
        return 100 if goal_completed else 0

    def save_notes(self, notes):
        self.db_client.update_sprint_auxillary_data(
            self._data['_id'],
            {
                'goal_completed': self.goal_completed,
                'notes': notes
            }
        )
        return SprintReadWrite(self._data['_id'])


class Sprints:
    def __init__(self, team_name):
        self.db_client = get_client()
        six_sprints_ago = arrow.utcnow().shift(weeks=-12).datetime
        self.refs = {
            s['_id']: s['name']
            for s in self.db_client.get_sprints(
                team_name, six_sprints_ago)
        }


class Metrics:
    def __init__(self):
        self.db_client = get_client()
        six_sprints_ago = arrow.utcnow().shift(weeks=-12).datetime
        self.sprint_reports = self.db_client.get_performance_reports(
            ending_after=six_sprints_ago)
        self.bau_reports = self.db_client.get_bau_reports(
            ending_after=six_sprints_ago)

    def sprint_performance_report_df(self):
        return pd.DataFrame.from_records(self.sprint_reports)

    def sprint_bau_report_df(self):
        return pd.DataFrame.from_records(self.bau_reports)
