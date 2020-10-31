import arrow
import pandas as pd
import plotly.graph_objects as go

from database.mongo import get_client


class Sprint:
    empty_pie = go.Pie(labels=[], values=[], scalegroup='one')

    def __init__(self, sprint_id):
        self.db_client = get_client()
        self._data = self.db_client.get_sprint(sprint_id)
        self._auxillary_data = self.db_client.get_sprint_auxillary_data(
            sprint_id)
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

    def update_goal_completion(self, goal_completion_val):
        self.db_client.update_sprint_auxillary_data(
            self._data['_id'],
            {
                'goal_completed': goal_completion_val,
                'notes': self.notes
            }
        )
        sprint = Sprint(self._data['_id'])
        return sprint

    def save_notes(self, notes):
        self.db_client.update_sprint_auxillary_data(
            self._data['_id'],
            {
                'goal_completed': self.goal_completed,
                'notes': notes
            }
        )
        return Sprint(self._data['_id'])

    def mk_issues_summary_df(self):
        df = self._summarise(self.issues_df)
        df = df.set_index('planned')
        df.loc['Total'] = df.sum()
        df['% delivered'] = self.percent(df, '# delivered', '# issues')
        df['% bau'] = self.percent(df, '# bau', '# issues')
        df = df.round().reset_index()
        return df

    @staticmethod
    def _summarise(df):
        summary_df = df.groupby(
            ['planned', 'finished_in_sprint', 'bau']).size().reset_index(
                name="# issues")
        summary_df['planned'].replace({
            True: "planned", False: "unplanned"}, inplace=True)
        transformed_df = summary_df[["planned", "# issues"]].groupby(
            ['planned'], as_index=False).sum()
        delivered_df = summary_df[summary_df.finished_in_sprint.eq(True)][
            ["planned", "# issues"]].groupby(
                ['planned'], as_index=False).sum()
        transformed_df['# delivered'] = pd.Series(
            delivered_df['# issues'].values)
        bau_df = summary_df[summary_df.bau.eq(True)][
            ["planned", "# issues"]].groupby(['planned'], as_index=False).sum()
        transformed_df['# bau'] = pd.Series(bau_df['# issues'].values)
        transformed_df = transformed_df.fillna(0)
        return transformed_df

    @staticmethod
    def percent(df, col_a, col_b):
        df = df[col_a] / df[col_b]
        df = df.map('{:.0%}'.format)
        return df

    def mk_bau_breakdown_df(self):
        bau = []
        for bau_category in self.issues_df[
                self.issues_df.bau.eq(True)].bau_breakdown.values:
            bau.extend(bau_category)
        df = pd.DataFrame(bau)
        return df


class Sprints:
    def __init__(self, team_name):
        self.db_client = get_client()
        six_sprints_ago = arrow.utcnow().shift(weeks=-12).datetime
        self.refs = {
            s['_id']: s['name']
            for s in self.db_client.get_sprints(
                team_name, six_sprints_ago)
        }


class SprintsAggregate:
    def __init__(self, team_name):
        self.db_client = get_client()
        six_sprints_ago = arrow.utcnow().shift(weeks=-12).datetime
        self.refs = [s['_id'] for s in self.db_client.get_sprints(
            team_name, six_sprints_ago)]
        self.sprints = [Sprint(sprint_id) for sprint_id in self.refs]

    def bau_breakdown_df(self):
        bau_agg_df = pd.concat(
            sprint.mk_bau_breakdown_df() for sprint in self.sprints
        )
        return bau_agg_df

    def sprint_summary_df(self):
        dfs = []
        for sprint in self.sprints:
            summary_df = sprint.mk_issues_summary_df().tail(1)
            summary_df['sprint_start_date'] = sprint._data['start']
            goal_completed = (
                100 if sprint.goal_completed else 0)
            summary_df['goal_completed'] = goal_completed
            dfs.append(summary_df)
        return pd.concat(dfs)
