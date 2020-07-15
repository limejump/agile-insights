from backends.jira.types import SprintMetrics
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json
from os import listdir
from os.path import abspath, dirname, join, isfile, split

from config import JIRA_SPRINTS_SOURCE_SINK, TRADING_SPRINT_FOLDER

pd.options.mode.chained_assignment = None


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

    @property
    def unplanned_issues(self):
        return [
            i for i in self._data['issues']
            if not i['planned']]

    @property
    def planned_issues(self):
        return [
            i for i in self._data['issues']
            if i['planned']]

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


with open(
    join(
        abspath(dirname(__file__)),
        'datasets', 'jira-all-issues.json'), 'r') as f:
    issues = json.load(f)

df = pd.DataFrame({
    'story_points':  [i['story_points'] for i in issues],
    'days_taken': [i['days_taken'] for i in issues]
    })
fig = px.scatter(df, x="story_points", y="days_taken")


df2 = pd.DataFrame({
    'days_taken': [i['days_taken'] for i in issues],
    'end_date': [i['end_time'] for i in issues],
    'name': [i['name'] for i in issues]
    })

percent_85 = df2.quantile(0.85).days_taken
percent_50 = df2.quantile(0.5).days_taken
issue_max = df2.max(numeric_only=False)
issue_min = df2.min(numeric_only=False)

df_quants = pd.DataFrame({
    'x': [issue_min.end_date, issue_max.end_date,
          issue_min.end_date, issue_max.end_date],
    'y': [percent_50, percent_50, percent_85, percent_85],
    'name': [
        f"50% {round(percent_50)} days",
        f"50% {round(percent_50)} days",
        f"85% {round(percent_85)} days",
        f"85% {round(percent_85)} days"]
})

fig2 = px.scatter(
    df2, x='end_date', y="days_taken", hover_name="name",
    hover_data={'end_date': False, 'days_taken': True})
for trace in px.line(
        df_quants, x='x', y='y', color='name',
        color_discrete_sequence=px.colors.qualitative.Vivid).data:
    fig2.add_trace(trace)

children = []
for filepath in [
    join(abspath(dirname(__file__)), 'datasets', filename)
    for filename in reversed([
        'TRAD-Sprint-308.json',
        'TRAD-Sprint-313.json',
        'TRAD-Sprint-319.json',
        'TRAD-Sprint-334.json'])]:
    sprint = Sprint(filepath)
    children.extend(
        [html.Div(children=sprint.name),
         html.Div(dcc.Graph(
             figure=sprint.mk_summary_table())),
         html.Div(dcc.Graph(
             figure=sprint.mk_overview_trace()))
        ])

app = dash.Dash('Limejump Tech Metrics')

team_data_options = []
for _, folder in JIRA_SPRINTS_SOURCE_SINK:
    _, team_name = split(folder)
    files = [f for f in listdir(folder) if isfile]
    team_data_options.append({
        "label": team_name,
        "value": join(folder, files[0])})


app.layout = html.Div(children=[
    html.H1('Limejump Tech Latest Sprint Breakdown'),
    html.Div(id='headers'),
    dcc.Graph(id="planned-unplanned"),
    dcc.Graph(id="breakdown"),
    dcc.RadioItems(
        id="team-picker",
        options=team_data_options,
        value=team_data_options[0]['value'])
])


@app.callback(
    Output('planned-unplanned', 'figure'),
    [Input(component_id="team-picker", component_property="value")])
def change_planned_graph(team_data_file):
    fig = Sprint(team_data_file).mk_summary_table()
    # fig.update_layout(transition_duration=500)
    return fig


@app.callback(
    Output('breakdown', 'figure'),
    [Input(component_id="team-picker", component_property="value")])
def change_breakdown_graph(team_data_file):
    fig = Sprint(team_data_file).mk_overview_trace()
    fig.update_layout(transition_duration=500)
    return fig

@app.callback(
    Output('headers', 'children'),
    [Input(component_id="team-picker", component_property="value")])
def change_heading(team_data_file):
    sprint = Sprint(team_data_file)
    return [
        html.H2(sprint.name),
        html.H4(sprint.goal)
    ]

if __name__ == '__main__':
    app.run_server(debug=True)