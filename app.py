import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import json
from os import listdir
from os.path import abspath, dirname, join, isfile, split
import pandas as pd
import plotly.express as px

from config import JIRA_SPRINTS_SOURCE_SINK
from models import Sprint

pd.options.mode.chained_assignment = None


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

app = dash.Dash(
    'Limejump Tech Metrics',
    external_stylesheets=[dbc.themes.BOOTSTRAP])

team_data_options = []
for _, folder in JIRA_SPRINTS_SOURCE_SINK:
    _, team_name = split(folder)
    files = [f for f in listdir(folder) if isfile]
    team_data_options.append({
        "label": team_name,
        "value": join(folder, files[0])})


url_bar_and_content_div = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


layout_index = html.Div([
    dbc.Nav([
        dbc.NavItem(dbc.NavLink('Sprints Metrics', href='/sprints')),
        dbc.NavItem(dbc.NavLink('Forecasts', href='/forecasts')),
    ], pills=True)
])


layout_sprints = html.Div(children=[
    layout_index,
    html.H1('Limejump Tech Latest Sprint Breakdown'),
    html.Div(id='headers'),
    dcc.Graph(id="planned-unplanned"),
    dcc.Graph(id="breakdown"),
    dcc.RadioItems(
        id="team-picker",
        options=team_data_options,
        value=team_data_options[0]['value'])
])


layout_forecasting = html.Div([
    layout_index,
    html.H2('Forecasting')
])


app.layout = url_bar_and_content_div


app.validation_layout = html.Div([
    url_bar_and_content_div,
    layout_index,
    layout_sprints,
    layout_forecasting
])


@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == "/sprints":
        return layout_sprints
    elif pathname == "/forecasts":
        return layout_forecasting
    else:
        return layout_index


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
