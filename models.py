import dash_table
from os import WCOREDUMP, environ
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

    def __init__(self, team_name):
        self._data = db_client.get_latest_sprint(team_name)
        self.issues_df = pd.DataFrame.from_records(
            self._data['issues'])

    @property
    def name(self):
        return self._data['name']

    @property
    def goal(self):
        return self._data['goal']

    def _mk_sub_pie_trace(self, df_filters):
        filtered = self.issues_df[df_filters]

        if filtered.empty:
            return self.empty_pie

        pie = px.pie(
            filtered.groupby('description').size().reset_index(
                name='issue_count'),
            values='issue_count',
            names='description')
        # can only make subplots from graph objects
        return go.Pie(
            labels=pie.data[0]['labels'],
            values=pie.data[0]['values'],
            scalegroup='one')

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

    def mk_summary_table(self):
        df = self.mk_issues_summary_df()
        fig = dash_table.DataTable(
            columns=(
                [{'name': '', "id": 'planned'}] +
                [{'name': i, "id": i} for i in df.columns[1:]]),
            data=df.to_dict('records'),
            style_cell={'textAlign': 'left'},
            style_as_list_view=True,
            style_data_conditional=[
                {
                    'if': {
                        'filter_query': '{planned} = Total'
                    },
                    'fontWeight': 'bold'
                },
            ]
        )
        return fig

    @staticmethod
    def percent(df, col_a, col_b):
        df = df[col_a] / df[col_b]
        df = df.map('{:.0%}'.format)
        return df

    def mk_overview_trace(self):
        fig = make_subplots(
            1, 4, specs=[[
                {'type': 'domain'}, {'type': 'domain'},
                {'type': 'domain'}, {'type': 'domain'}]],
            subplot_titles=[
                'Planned', 'Planned Delivered',
                'Unplanned', 'Unplanned Delivered'])
        fig.add_trace(
            self._mk_sub_pie_trace(
                df_filters=self.issues_df.planned.eq(True)),
            1, 1)
        fig.add_trace(
            self._mk_sub_pie_trace(
                df_filters=(
                    self.issues_df.planned.eq(True) &
                    self.issues_df.finished_in_sprint.eq(True))),
            1, 2)
        fig.add_trace(
            self._mk_sub_pie_trace(
                df_filters=self.issues_df.planned.eq(False)),
            1, 3)
        fig.add_trace(
            self._mk_sub_pie_trace(
                df_filters=(
                    self.issues_df.planned.eq(False) &
                    self.issues_df.finished_in_sprint.eq(True))),
            1, 4)
        fig.update_layout(
            title_text='Sprint at a Glance',
            legend_x=1,
            legend_y=1)
        fig.update_traces(
            textinfo='percent', showlegend=True)
        return fig
