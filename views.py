import dash_table
from functools import partial
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dash_daq as daq
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

from models import Sprints as SprintsModel
from models import Sprint as SprintModel


def singleColRow(item):
    return dbc.Row([dbc.Col([item])])


class Sprints:
    def __init__(self, team_name):
        self.sprints = SprintsModel(team_name)
        self.select_options = [
            {'label': name, 'value': id_}
            for id_, name in self.sprints.refs.items()]
        self.default_select = self.select_options[0]['value']

    @property
    def sprint_ids(self):
        return list(self.sprints.refs.keys())


class Sprint:
    empty_sub_pie = go.Pie(labels=[], values=[], scalegroup='one')
    empty_pie = go.Pie(labels=[], values=[])

    def __init__(self, sprint_id, edit_notes):
        self.model = SprintModel(sprint_id)
        if not self.model.notes:
            self.edit_notes = True
        else:
            self.edit_notes = edit_notes

    def update_goal_completion(self, goal_completion_val):
        self.model = self.model.update_goal_completion(goal_completion_val)

    def save_notes(self, notes):
        if notes:
            self.model = self.model.save_notes(notes)
        else:
            # FIXME: may want to handle this using validation using
            # FormFeedback
            self.edit_notes = True

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
            height=220,
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

    @staticmethod
    def editable_notes(notes):
        form_children = []
        if notes:
            form_children.append(
                dbc.FormGroup(dbc.Textarea(
                    className='markdown',
                    id='notes-content', value=notes,
                    style={'height': 250})))
        else:
            form_children.append(
                dbc.FormGroup(dbc.Textarea(
                    className='markdown',
                    id='notes-content',
                    placeholder='Write notes here in markdown format...',
                    style={'height': 250})))
        form_children.append(
            dbc.Button("Save", id="submit-notes", color="primary"))
        return dbc.Form(form_children)

    @staticmethod
    def read_only_notes(notes):
        return html.Div([
            dcc.Markdown(
                notes,
                className='markdown',
                dedent=True,
                style={'font-size': '10px', 'height': 250}),
            ],
            className='rounded border-secondary',
            style={
                'border-style': 'solid',
                # 'border-color': 'border-light',
                'border-width': '1px',
                'padding': '10px'}
        )

    def render(self):
        bau_breakdown = self.maybe_bau_breakdown()
        dom_nodes = [
            singleColRow(html.H2(self.model.name)),
            dbc.Row([
                dbc.Col([html.P([
                    dbc.Badge("Sprint Goal", color="success", className="mr-1"),
                    self.model.goal])], width=9),
                dbc.Col([daq.BooleanSwitch(
                    id='goal-completion-toggle',
                    label='Goal Achieved',
                    color='#008000',
                    on=self.model.goal_completed
                )], width=3)
            ]),
            singleColRow(html.H4("Sprint Summary")),
            singleColRow(html.Div(
                id="planned-unplanned",
                children=[self.mk_summary_table()],
                style={'padding': 20}
                )),
        ]
        # FIXME: When in edit mode we have to add a hidden Div representing
        # the edit button from read only mode, and visa versa.
        # If we don't we get callback errors for which ever button doesn't
        # exist. There should be a better way to account for conditionally
        # rendered dom nodes.
        if self.edit_notes:
            row_children = [
                dbc.Col([
                    html.H4("Notes"),
                    self.editable_notes(self.model.notes),
                    html.Div(id="edit-notes", hidden=True)],
                    width=6
                )]
        else:
            row_children = [
                dbc.Col([
                    html.H4("Notes"),
                    self.read_only_notes(self.model.notes),
                    dbc.Button(
                            "Edit",
                            id="edit-notes",
                            color="primary"),
                    html.Div(id="submit-notes", hidden=True),
                    html.Div(id="notes-content", hidden=True)],
                    width=6
                )]

        if bau_breakdown:
            row_children.append(
                dbc.Col([
                    singleColRow(html.H4("BAU Breakdown")),
                    singleColRow(
                        dcc.Graph(
                            id='bau-breakdown',
                            figure=bau_breakdown,
                            config={
                                'displayModeBar': False,
                                'fillFrame': True,
                                'frameMargins': 0
                            })
                        )
                ], width=6))
        dom_nodes.append(dbc.Row(row_children))
        # dom_nodes.append(
        #     dcc.Graph(id="breakdown", figure=self.mk_overview_trace()))
        return dom_nodes

    @classmethod
    def callback_elements(cls):
        ''' List of DOM elements that will be manipulated by
            callbacks in the main app, to pass layout validation
        '''
        return [
            daq.BooleanSwitch(id='goal-completion-toggle'),
            dbc.Button(id='edit-notes'),
            dbc.Button(id='submit-notes'),
            dbc.Textarea(id='notes-content')
        ]
