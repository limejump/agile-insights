import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random


class Forecast:
    def __init__(self, data_filepath):
        with open(data_filepath) as f:
            data = json.load(f)
        df = pd.DataFrame.from_records(data)
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
    def __init__(self, data_filepath):
        with open(data_filepath) as f:
            data = json.load(f)
        self._data = data
        self.issues_df = pd.DataFrame.from_records(data['issues'])

    @property
    def name(self):
        return self._data['name']

    @property
    def goal(self):
        return self._data['goal']

    def _mk_sub_pie_trace(self, df_filters):
        filtered = self.issues_df[df_filters]
        pie = px.pie(
            filtered.groupby('label').size().reset_index(
                name='issue_count'),
            values='issue_count',
            names='label')
        # can only make subplots from graph objects
        return go.Pie(
            labels=pie.data[0]['labels'],
            values=pie.data[0]['values'],
            scalegroup='one')

    def mk_summary_table(self):
        summary_df = self.issues_df.groupby(
            ['planned', 'finished_in_sprint']).size().reset_index(
                    name="issue_count")
        summary_df['planned'].replace({
            True: "planned", False: "unplanned"}, inplace=True)
        committed_df = summary_df[["planned", "issue_count"]].groupby(
            ['planned'], as_index=False).sum()
        delivered_df = summary_df[summary_df.finished_in_sprint.eq(True)]
        fig = {
            'data': [
                go.Bar(
                    x=committed_df.planned,
                    y=committed_df.issue_count,
                    name="committed"),
                go.Bar(
                    x=delivered_df.planned,
                    y=delivered_df.issue_count,
                    name="delivered")],
            'layout': go.Layout(
                barmode='overlay', yaxis_title="issue count")
        }
        return fig

    def mk_overview_trace(self):
        fig = make_subplots(
            1, 4, specs=[[
                {'type': 'domain'}, {'type': 'domain'},
                {'type': 'domain'}, {'type': 'domain'}]],
            subplot_titles=['Planned','Planned Delivered', 'Unplanned', 'Unplanned Delivered'])
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
