import arrow
from os import environ
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random

from config import config
from database.mongo import Client


config.set(
    'db',
    environ.get('DB_HOST', 'localhost'),
    int(environ.get('DB_PORT', 27017)),
    environ.get('DB_USERNAME', 'root'),
    environ.get('DB_PASSWORD', 'rootpassword'),
    )


db_client = Client()


class Forecast:
    def __init__(self, team_name):
        self._data = db_client.get_historic_issues(team_name)
        df = pd.DataFrame.from_records(self._data)
        # FIXME:
        # 1) make the cap configurable?
        # 2) remove top 95%
        self.df = df[df.days_taken < df.days_taken.quantile(0.95)]

    def mk_story_point_scatter(self):
        return px.scatter(self.df, x="story_points", y="days_taken")

    def mk_time_per_issue_scatter(self):
        percent_80 = self.df['days_taken'].quantile(0.8)
        percent_50 = self.df['days_taken'].quantile(0.5)
        issue_min = self.df['end_time'].min(numeric_only=False)
        issue_max = self.df['end_time'].max(numeric_only=False)

        quantiles_df = pd.DataFrame({
            'x': [issue_min, issue_max, issue_min, issue_max],
            'y': [percent_50, percent_50, percent_80, percent_80],
            'name': [
                f"50% {round(percent_50)} days",
                f"50% {round(percent_50)} days",
                f"80% {round(percent_80)} days",
                f"80% {round(percent_80)} days"]
        })

        fig = px.scatter(
            self.df, x='end_time', y="days_taken", hover_name="name",
            hover_data={'end_time': False, 'days_taken': True})
        for trace in px.line(
                quantiles_df, x='x', y='y', color='name',
                color_discrete_sequence=px.colors.qualitative.Vivid).data:
            fig.add_trace(trace)
        return fig

    def _run_montecarlo(self, num_issues=5):
        records = []
        pool = list(self.df['days_taken'].dropna())
        for simulation in range(1000):
            days_taken = sum([
                random.choice(pool)
                for _ in range(num_issues)])
            records.append({
                "simulation": simulation,
                "days_taken": days_taken})
        df = pd.DataFrame.from_records(
            records).sort_values('days_taken').reset_index(drop=True)
        percent_80 = df['days_taken'].quantile(0.8)
        percent_70 = df['days_taken'].quantile(0.7)
        percent_60 = df['days_taken'].quantile(0.6)
        percent_50 = df['days_taken'].quantile(0.5)
        issue_min = df['simulation'].min(numeric_only=False)
        issue_max = df['simulation'].max(numeric_only=False)
        quantiles_df = pd.DataFrame({
            'x': [
                issue_min, issue_max,
                issue_min, issue_max,
                issue_min, issue_max,
                issue_min, issue_max
                ],
            'y': [
                percent_50, percent_50,
                percent_60, percent_60,
                percent_70, percent_70,
                percent_80, percent_80
            ],
            'name': [
                f"50% {round(percent_50)} days",
                f"50% {round(percent_50)} days",
                f"60% {round(percent_60)} days",
                f"60% {round(percent_60)} days",
                f"70% {round(percent_70)} days",
                f"70% {round(percent_70)} days",
                f"80% {round(percent_80)} days",
                f"80% {round(percent_80)} days"]
        })

        fig = px.bar(df, x=df.index, y='days_taken')
        for trace in px.line(
                quantiles_df, x='x', y='y', color='name',
                color_discrete_sequence=px.colors.qualitative.Vivid).data:
            fig.add_trace(trace)
        return fig


class Sprint:
    empty_pie = go.Pie(labels=[], values=[], scalegroup='one')

    def __init__(self, sprint_id):
        self._data = db_client.get_sprint(sprint_id)
        self._auxillary_data = db_client.get_sprint_auxillary_data(sprint_id)
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

    def update_goal_completion(self, goal_completion_val):
        db_client.update_sprint_auxillary_data(
            self._data['_id'],
            {'goal_completed': goal_completion_val}
        )
        sprint = Sprint(self._data['_id'])
        return sprint

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
        six_sprints_ago = arrow.utcnow().shift(weeks=-12).datetime
        self.refs = {
            s['_id']: s['name']
            for s in db_client.get_sprints(team_name, six_sprints_ago)
        }
