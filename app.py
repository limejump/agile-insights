import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from os import listdir
from os.path import join, isfile, split
import pandas as pd

from config import FOLDERS
from models import Forecast, Sprint

pd.options.mode.chained_assignment = None


app = dash.Dash(
    'Limejump Tech Metrics',
    external_stylesheets=[dbc.themes.BOOTSTRAP])


team_data_options = [
    {"label": team, "value": team}
    for team in ['cx', 'billing', 'trading']]

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
    html.Div(id='sprints'),
    dcc.Graph(id="planned-unplanned"),
    dcc.Graph(id="breakdown"),
    dcc.RadioItems(
        id="team-picker",
        options=team_data_options,
        value=team_data_options[0]['value'])
    ])


layout_forecasting = html.Div([
    layout_index,
    html.H2('Forecasting'),
    html.Div(id='forecasts'),
    dcc.Input(
        id='num-issues',
        type='number'),
    html.Div(id='actual-forecast'),
    dcc.RadioItems(
        id="team-picker",
        options=team_data_options,
        value=team_data_options[0]['value'])
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
def change_planned_graph(team_name):
    sprint = Sprint(latest_sprint_file(team_name))
    fig = sprint.mk_summary_table()
    # fig.update_layout(transition_duration=500)
    return fig


@app.callback(
    Output('breakdown', 'figure'),
    [Input(component_id="team-picker", component_property="value")])
def change_breakdown_graph(team_name):
    sprint = Sprint(latest_sprint_file(team_name))
    fig = sprint.mk_overview_trace()
    fig.update_layout(transition_duration=500)
    return fig


@app.callback(
    Output("forecasts", "children"),
    [Input(component_id="team-picker", component_property="value")])
def update_estimate_graph(team_name):
    folder = FOLDERS[team_name]['historic']
    forecast = Forecast(
        join(folder, 'all-issues.json'))
    return [
        dcc.Graph(
            id="story-points",
            figure=forecast.mk_story_point_scatter()),
        dcc.Graph(
            id="overview",
            figure=forecast.mk_time_per_issue_scatter())
    ]


@app.callback(
    Output('sprints', 'children'),
    [Input(component_id="team-picker", component_property="value")])
def change_heading(team_name):
    sprint = Sprint(latest_sprint_file(team_name))
    return [
        html.H2(sprint.name),
        html.H4(sprint.goal)
    ]


@app.callback(
    Output('actual-forecast', 'children'),
    [Input("num-issues", "value"),
     Input(component_id="team-picker", component_property="value")])
def run_simulation(num_issues, team_name):
    folder = FOLDERS[team_name]['historic']
    forecast = Forecast(
        join(folder, 'all-issues.json'))
    if num_issues:
        return dcc.Graph(
            id="monte-carlo",
            figure=forecast._run_montecarlo(num_issues))
    else:
        return "..."


def latest_sprint_file(team_name):
    folder = FOLDERS[team_name]['sprint']
    latest, *_ = reversed(sorted(listdir(folder)))
    print(listdir(folder))
    print(latest)
    return join(folder, latest)


if __name__ == '__main__':
    app.run_server(debug=True)
