import dash_core_components as dcc
import pandas as pd
import plotly.express as px

from models import Forecast as ForecastModel


class Forecast:
    def __init__(self, team_name):
        self.model = ForecastModel(team_name)

    def mk_story_point_scatter(self):
        return px.scatter(self.model.df, x="story_points", y="days_taken")

    def mk_time_per_issue_scatter(self):
        percent_80 = self.model.df['days_taken'].quantile(0.8)
        percent_50 = self.model.df['days_taken'].quantile(0.5)
        issue_min = self.model.df['end_time'].min(numeric_only=False)
        issue_max = self.model.df['end_time'].max(numeric_only=False)

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
            self.model.df, x='end_time', y="days_taken", hover_name="name",
            hover_data={'end_time': False, 'days_taken': True})
        for trace in px.line(
                quantiles_df, x='x', y='y', color='name',
                color_discrete_sequence=px.colors.qualitative.Vivid).data:
            fig.add_trace(trace)
        return fig

    def mk_montecarlo_plot(self, num_issues=5):
        df = self.model.run_montecarlo(num_issues)
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

    def render(self):
        return [
            dcc.Graph(
                id="story-points",
                figure=self.mk_story_point_scatter()),
            dcc.Graph(
                id="overview",
                figure=self.mk_time_per_issue_scatter())
        ]
