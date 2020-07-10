import collections
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json
from os.path import abspath, dirname, join


class Sprint:
    def __init__(self, data_filepath):
        with open(data_filepath) as f:
            data = json.load(f)
        self._data = data

    @property
    def name(self):
        return self._data['name']

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

    @staticmethod
    def _mk_sub_pie_trace(collection, key,):
        data = [i[key] for i in collection]
        counts = Counter(data)
        names = []
        vals = []
        for k, v in counts.items():
            names.append(k)
            vals.append(v)
        pie = px.pie(
            pd.DataFrame(dict(names=names, values=vals)),
            values='values',
            names='names')
        # can only make subplots from graph objects
        return go.Pie(
            labels=pie.data[0]['labels'],
            values=pie.data[0]['values'],
            scalegroup='one')

    def mk_summary_table(self):
        planned_count = len(self.planned_issues)
        planned_delivered = len([
            i for i in self.planned_issues
            if i['finished_in_sprint']])
        unplanned_count = len(self.unplanned_issues)
        unplanned_delivered = len([
            i for i in self.unplanned_issues
            if i['finished_in_sprint']])
        df = pd.DataFrame({
            "state": ['planned', 'planned', 'unplanned', 'unplanned'],
            'status': ['committed', 'delivered', 'committed', 'delivered'],
            "issue_count": [
                planned_count, planned_delivered,
                unplanned_count, unplanned_delivered]
        })
        return px.bar(df, x='status', y='issue_count', color='state')
        # return dash_table.DataTable(
        #     columns=[{'name': i, 'id': i} for i in df.columns],
        #     data=df.to_dict('record'))

    def mk_overview_trace(self):
        fig = make_subplots(
            1, 4, specs=[[
                {'type': 'domain'}, {'type': 'domain'},
                {'type': 'domain'}, {'type': 'domain'}]],
            subplot_titles=['Planned','Planned Delivered', 'Unplanned', 'Unplanned Delivered'])
        fig.add_trace(
            self._mk_sub_pie_trace(
                self.planned_issues, 'label'),
            1, 1)
        fig.add_trace(
            self._mk_sub_pie_trace([
                    i for i in self.planned_issues
                    if i['started_in_sprint'] and i['finished_in_sprint']
                ],
                'label'),
            1, 2)
        fig.add_trace(
            self._mk_sub_pie_trace(
                self.unplanned_issues, 'label'),
            1, 3)
        fig.add_trace(
            self._mk_sub_pie_trace([
                    i for i in self.unplanned_issues
                    if i['started_in_sprint'] and i['finished_in_sprint']
                ],
                'label'),
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