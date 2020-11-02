import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from models import Forecast as ForecastModel


class Forecast:
    def __init__(self, team_name, remaining_issues=None):
        self.model = ForecastModel(team_name)
        self.remaining_issues = remaining_issues

    def mk_throughput_line(self):
        df = self.model.throughput_df()
        fig = go.Figure(data=go.Scatter(
            x=df['end'].tolist(),
            y=df['throughput'].tolist(),
            name='throughput'
        ))
        if self.remaining_issues:
            self.add_uncertaintity_cone(df, fig)
        return fig

    def add_uncertaintity_cone(self, throughput_df, fig):
        current_throughput = throughput_df.iloc[-1]['throughput']
        target = current_throughput + self.remaining_issues
        quick, slow = self.model.uncertainty_cone_coords(target)

        x_a, y_a, x_b, y_b = quick
        fig.add_trace(go.Scatter(
            x=[x_a, x_b],
            y=[y_a, y_b],
            name='optimistic',
            mode='lines',
            line={
                'color': 'green',
                'dash': 'dash',
                'width': 1
            },
            legendgroup='optimistic'
        ))
        fig.add_trace(go.Scatter(
            x=[x_b, x_b],
            y=[y_b, 0],
            mode='lines',
            line={
                'color': 'green',
                'dash': 'dash',
                'width': 1
            },
            showlegend=False,
            legendgroup='optimistic'
        ))
        x_a, y_a, x_b, y_b = slow
        fig.add_trace(go.Scatter(
            x=[x_a, x_b],
            y=[y_a, y_b],
            name='pesimistic',
            mode='lines',
            line={
                'color': 'red',
                'dash': 'dash',
                'width': 1
            },
            legendgroup='optimistic'
        ))
        fig.add_trace(go.Scatter(
            x=[x_b, x_b],
            y=[y_b, 0],
            mode='lines',
            line={
                'color': 'red',
                'dash': 'dash',
                'width': 1
            },
            showlegend=False,
            legendgroup='pesimistic'
        ))

    def mk_story_point_scatter(self):
        self.model.throughput_df()
        return px.scatter(
            self.model.historic_df, x="story_points", y="days_taken")

    def mk_time_per_issue_scatter(self):
        percent_80 = self.model.historic_df['days_taken'].quantile(0.8)
        percent_50 = self.model.historic_df['days_taken'].quantile(0.5)
        issue_min = self.model.historic_df['end_time'].min(numeric_only=False)
        issue_max = self.model.historic_df['end_time'].max(numeric_only=False)

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
            self.model.historic_df, x='end_time', y="days_taken",
            hover_name="name",
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
            html.P("Input the number of remaining issues to reach your goal."),
            dbc.Input(
                id="issues-input", type="number",
                min=0, step=1,
                value=self.remaining_issues),
            dcc.Graph(
                id='throuput',
                figure=self.mk_throughput_line()
            ),
            # dcc.Graph(
            #     id="story-points",
            #     figure=self.mk_story_point_scatter()),
            # dcc.Graph(
            #     id="overview",
            #     figure=self.mk_time_per_issue_scatter())
        ]

    @classmethod
    def callback_elements(cls):
        return [
            dbc.Input(id='issues-input')
        ]
