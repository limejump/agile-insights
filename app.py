import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import json
from os.path import abspath, dirname, join


app = dash.Dash('Limejump Tech Metrics')

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

pie_chart_data = {}
for sprint_file in [
    join(abspath(dirname(__file__)), 'datasets', filename)
    for filename in [
        'TRAD-Sprint-308.json',
        'TRAD-Sprint-313.json',
        'TRAD-Sprint-319.json']]:
    with open(sprint_file) as f:
        data = json.load(f)
    name = data['name']
    issues = data['issues']
    pie_chart_data[name] = {
        'issue': [i['label'] for i in issues],
        'type': [i['type'] for i in issues],
        'days_taken': [i['days_taken'] for i in issues]}

children = []
for k, v in pie_chart_data.items():
    children.append(html.Div(children=k))
    children.append(
        dcc.Graph(
            id=k,
            figure=px.sunburst(
                v, path=['type', 'issue'])))

app.layout = html.Div(children=[
    html.H1(children='LimeJump Tech Metrics'),

    html.Div(children='''
        Almost no correlation whatsoever
    '''),

    dcc.Graph(
        id='Story Points vs Time Taken',
        figure=fig
    ),

    html.Div(children='''
       How long does a ticket take to get from in progress to done?
    '''),

    dcc.Graph(
        id='Duration vs end date',
        figure=fig2
    ),
] + children)

if __name__ == '__main__':
    app.run_server(debug=True)