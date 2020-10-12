import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd

from config import config
from models import Forecast, Sprint


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
        dbc.NavItem(dbc.NavLink('Sprints Metrics', href='/sprints')),
        dbc.NavItem(dbc.NavLink('Forecasts', href='/forecasts')),
    ], pills=True)
])


layout_sprints = html.Div(children=[
    layout_index,
    html.Div(id='sprints'),
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
    Output('sprints', 'children'),
    [Input(component_id="team-picker", component_property="value")])
def change_planned_graph(team_name):
    sprint = Sprint(team_name)
    return sprint.render()


@app.callback(
    Output("forecasts", "children"),
    [Input(component_id="team-picker", component_property="value")])
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
     Input(component_id="team-picker", component_property="value")])
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
