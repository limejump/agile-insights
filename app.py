import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from functools import lru_cache
from os import environ
import pandas as pd

from config import config
from models import Forecast
from views import Sprints, Sprint, Metrics


config.set(
    'db',
    environ.get('DB_HOST', 'localhost'),
    int(environ.get('DB_PORT', 27017)),
    environ.get('DB_USERNAME', 'root'),
    environ.get('DB_PASSWORD', 'rootpassword'),
    )

pd.options.mode.chained_assignment = None


app = dash.Dash(
    'Limejump Tech Metrics',
    external_stylesheets=[dbc.themes.BOOTSTRAP])


team_data_options = [
    {"label": team.name, "value": team.name}
    for team in config.get('static').teams]

url_bar_and_content_div = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


layout_index = html.Div([
    dbc.Nav([
        dbc.NavItem(dbc.NavLink('Sprints', href='/sprints')),
        dbc.NavItem(dbc.NavLink('Forecasts', href='/forecasts')),
        dbc.NavItem(dbc.NavLink('Metrics', href='/metrics')),
    ], pills=True)
])


layout_sprints = html.Div(children=[
    html.Div([
        html.Div(children=False, id='notes-editability', hidden=True),
        dbc.Row([dbc.Col([layout_index])]),
        dbc.Row([dbc.Col([
            html.Div([html.Label([
                'Team',
                dcc.Dropdown(
                    id="teams-dropdown",
                    options=team_data_options,
                    value=team_data_options[0]['value'])
                ], style={'width': '100%', 'font-size': '12px'})]),
            html.Div([html.Label([
                'Sprint',
                dcc.Dropdown(
                    id="sprint-dropdown",
                    options=[],
                    value=0)
                ], style={'width': '100%', 'font-size': '12px'})]),
            ], width=3, className='bg-info'),
            dbc.Col(
                html.Div(
                    id='sprints',
                    children=Sprint.callback_elements(),
                    className='container-fluid'),
                width=9)
        ])], className='container-fluid')
])


layout_forecasting = html.Div([
    layout_index,
    html.Div(
        children=[
            html.Label([
                'Select Team',
                dcc.Dropdown(
                    id="teams-dropdown",
                    options=team_data_options,
                    value=team_data_options[0]['value'])],
                style={'display': 'inline-block', 'width': '30%'}),
        ]),
    html.H2('Forecasting'),
    html.Div(id='forecasts'),
    dcc.Input(
        id='num-issues',
        type='number'),
    html.Div(id='actual-forecast'),
])


@lru_cache(maxsize=32)
def layout_metrics():
    return html.Div([
        layout_index,
        html.Div(
            Metrics(
                team.name
                for team in config.get('static').teams
            ).render())
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
    if pathname != '/metrics':
        layout_metrics.cache_clear()
    if pathname == "/sprints":
        return layout_sprints
    elif pathname == "/forecasts":
        return layout_forecasting
    elif pathname == "/metrics":
        return layout_metrics()
    else:
        return layout_index


@app.callback(
    [
        Output('sprints', 'children'),
        Output('sprint-dropdown', 'options'),
        Output('notes-editability', 'children')
    ],
    [
        # Sprint selectors
        Input(component_id='teams-dropdown', component_property="value"),
        Input(component_id='sprint-dropdown', component_property="value"),
        # Sprint modifiers, accessible via users
        Input(component_id='goal-completion-toggle', component_property="on"),
        Input(component_id='edit-notes', component_property="n_clicks"),
        Input(component_id='submit-notes', component_property="n_clicks"),
    ],
    [
        State('notes-editability', 'children'),
        State('notes-content', 'value')
    ])
def change_sprint(
        team_name, sprint_id,
        goal_complete, edit_notes, submit_notes,
        notes_editability, notes_content):
    # if someone deletes the team selection we'll recieve None
    if team_name is None:
        team_name = team_data_options[0]['value']

    if edit_notes:
        notes_editability = True
    if submit_notes:
        notes_editability = False

    sprints = Sprints(team_name)
    # sprint_id can alreaedy be set when we select a new team
    # so we may need to override it to the teams' default.
    if sprint_id in sprints.sprint_ids:
        sprint = Sprint(sprint_id, notes_editability)
    else:
        sprint = Sprint(sprints.default_select, notes_editability)

    triggers = dash.callback_context.triggered
    if triggers:
        param = triggers.pop()['prop_id']
        if param == 'goal-completion-toggle.on':
            sprint.update_goal_completion(goal_complete)
        elif param == 'submit-notes.n_clicks':
            sprint.save_notes(notes_content)

    return sprint.render(), sprints.select_options, notes_editability


@app.callback(
    Output("forecasts", "children"),
    [Input(component_id="teams-dropdown", component_property="value")])
def update_estimate_graph(team_name):
    forecast = Forecast(team_name)
    return [
        dcc.Graph(
            id="story-points",
            figure=forecast.mk_story_point_scatter()),
        dcc.Graph(
            id="overview",
            figure=forecast.mk_time_per_issue_scatter())
    ]


@app.callback(
    Output('actual-forecast', 'children'),
    [Input("num-issues", "value"),
     Input(component_id="teams-dropdown", component_property="value")])
def run_simulation(num_issues, team_name):
    forecast = Forecast(team_name)
    if num_issues:
        return dcc.Graph(
            id="monte-carlo",
            figure=forecast._run_montecarlo(num_issues))
    else:
        return "..."


if __name__ == '__main__':
    app.run_server(debug=True)
