import pandas as pd
import plotly.express as px
import random

from database.mongo import get_client


class Forecast:
    def __init__(self, team_name):
        self.db_client = get_client()
        self._data = self.db_client.get_historic_issues(team_name)
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
