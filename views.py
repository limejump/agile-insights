import dash_table
from functools import partial
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

from models import Sprint as SprintModel


class Sprint:
    empty_sub_pie = go.Pie(labels=[], values=[], scalegroup='one')
    empty_pie = go.Pie(labels=[], values=[])

    def __init__(self, team_name):
        self.model = SprintModel(team_name)

    def _mk_sub_pie_trace(self, df, groupby, df_filters):
        filtered = df[df_filters]

        if filtered.empty:
            return self.empty_sub_pie

        pie = px.pie(
            filtered.groupby(groupby).size().reset_index(
                name='issue_count'),
            values='issue_count',
            names=groupby)
        # can only make subplots from graph objects
        return go.Pie(
            labels=pie.data[0]['labels'],
            values=pie.data[0]['values'],
            scalegroup='one')

    def maybe_bau_breakdown(self):
        df = self.model.mk_bau_breakdown_df()
        if df.empty:
            return None
        fig = px.pie(
            df.groupby(0).size().reset_index(name='issue_count'),
            values='issue_count',
            names=0,
            height=300,
            width=300)
        fig.update_layout(
            margin=dict(t=0, b=0, l=5, r=0, pad=2),
            legend_y=0.5)
        return fig

    def mk_summary_table(self):
        df = self.model.mk_issues_summary_df()
        fig = dash_table.DataTable(
            columns=(
                [{'name': '', "id": 'planned'}] +
                [{'name': i, "id": i} for i in df.columns[1:]]),
            data=df.to_dict('records'),
            style_cell={'textAlign': 'left'},
            style_as_list_view=True,
            style_data_conditional=[
                {
                    'if': {
                        'filter_query': '{planned} = Total'
                    },
                    'fontWeight': 'bold',
                    'border-top': '2px solid black'
                },
            ]
        )
        return fig

    def mk_overview_trace(self):
        # FIXME: this 'view' manipulates the DataFrame
        # breaking separation of concerns. Need to think
        # about migrating some of this detail to the model
        # interface.
        mk_sub_pie = partial(
            self._mk_sub_pie_trace, self.model.issues_df, 'description')
        fig = make_subplots(
            1, 4, specs=[[
                {'type': 'domain'}, {'type': 'domain'},
                {'type': 'domain'}, {'type': 'domain'}]],
            subplot_titles=[
                'Planned', 'Planned Delivered',
                'Unplanned', 'Unplanned Delivered'])
        fig.add_trace(
            mk_sub_pie(
                df_filters=self.model.issues_df.planned.eq(True)),
            1, 1)
        fig.add_trace(
            mk_sub_pie(
                df_filters=(
                    self.model.issues_df.planned.eq(True) &
                    self.model.issues_df.finished_in_sprint.eq(True))),
            1, 2)
        fig.add_trace(
            mk_sub_pie(
                df_filters=self.model.issues_df.planned.eq(False)),
            1, 3)
        fig.add_trace(
            mk_sub_pie(
                df_filters=(
                    self.model.issues_df.planned.eq(False) &
                    self.model.issues_df.finished_in_sprint.eq(True))),
            1, 4)
        fig.update_layout(
            legend_x=1,
            legend_y=1)
        fig.update_traces(
            textinfo='percent', showlegend=True)
        fig.update_layout(transition_duration=500)
        return fig

    def render(self):
        bau_breakdown = self.maybe_bau_breakdown()
        dom_nodes = [
            html.H2(self.model.name),
            html.P([
                dbc.Badge("Sprint Goal", color="success", className="mr-1"),
                self.model.goal]),
            html.H4("Sprint Summary"),
            html.Div(
                id="planned-unplanned",
                children=[self.mk_summary_table()],
                style={'padding': 20}
                ),
        ]
        if bau_breakdown:
            dom_nodes.extend([
                html.H4("BAU Breakdown"),
                dcc.Graph(
                    id='bau-breakdown',
                    figure=bau_breakdown)
            ])
        dom_nodes.append(
            dcc.Graph(id="breakdown", figure=self.mk_overview_trace()))
        return dom_nodes
