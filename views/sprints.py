import dash_table
from dash_table.Format import Format, Scheme, Symbol
from itertools import chain
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dash_daq as daq
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

from .colours import WARNING, GOOD, BAD
from models import Sprints as SprintsModel
from models import SprintReadWrite as SprintModel
from models import Metrics as MetricsModel


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
        df = df[[
            'planned',
            'issues_count', 'delivered_issues_count', 'bau_issues_count',
            'delivered_issues_percentage', 'bau_issues_percentage'
            ]]
        cols = []
        for i in df.columns[1:]:
            col_spec = {
                "name": self.prettify_header(i),
                "id": i,
                "type": "numeric"
            }
            if i.endswith('percentage'):
                col_spec["format"] = Format(
                    precision=0,
                    scheme=Scheme.fixed,
                    symbol=Symbol.yes,
                    symbol_suffix='%')
            cols.append(col_spec)
        fig = dash_table.DataTable(
            columns=([{'name': '', "id": 'planned'}] + cols),
            data=df.to_dict('records'),
            style_cell={'textAlign': 'right'},
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

    @staticmethod
    def prettify_header(header_name):
        prefix, *_, suffix = header_name.split('_')
        if suffix == 'count':
            return f'# {prefix}'
        elif suffix == 'percentage':
            return f'% {prefix}'
        else:
            return header_name

    @staticmethod
    def editable_notes(notes):
        form_children = []
        if notes:
            form_children.append(
                dbc.FormGroup(dbc.Textarea(
                    className='markdown',
                    id='notes-content', value=notes,
                    style={'min-height': 250})))
        else:
            form_children.append(
                dbc.FormGroup(dbc.Textarea(
                    className='markdown',
                    id='notes-content',
                    placeholder='Write notes here in markdown format...',
                    style={'min-height': 250})))
        form_children.append(
            dbc.Button("Save", id="submit-notes", color="primary"))
        return dbc.Form(form_children)

    @staticmethod
    def read_only_notes(notes):
        return html.Div([
            dcc.Markdown(
                notes,
                className='markdown rounded border-secondary',
                dedent=True,
                style={
                    'font-size': '10px',
                    'min-height': 250,
                    'padding': '10px',
                    'border-style': 'solid',
                    'border-width': '1px'
                     }),
            dbc.Button(
                    "Edit",
                    id="edit-notes",
                    color="primary",
                    style={'margin-top': 10}),
            ],

        )

    def details_table(self):
        df = self.model.issues_df[[
            'name', 'description',
            'planned', 'finished_in_sprint', 'bau']]
        df = df.rename(columns={
            'finished_in_sprint': 'delivered',
            })

        fig = dash_table.DataTable(
            columns=(
                [{'name': i, "id": i} for i in df.columns]),
            data=df.to_dict('records'),
            sort_action='native',
            filter_action='native',
            # fixed_rows={'headers': True},
            # style_as_list_view=True,
            style_table={
                'height': 400,
                'overflowY': 'scroll',
                'overflowX': 'scroll'},
            style_cell={'textAlign': 'left'},
            style_data={
                'maxWidth': '150px',
                'whiteSpace': 'normal'
            },
            style_data_conditional=[
                {
                    'if': {
                        'column_id': 'planned',
                        'filter_query': '{planned} contains true'
                    },
                    'backgroundColor': GOOD,
                    'color': 'white'
                },
                {
                    'if': {
                        'column_id': 'delivered',
                        'filter_query': '{delivered} contains true'
                    },
                    'backgroundColor': GOOD,
                    'color': 'white'
                },
                {
                    'if': {
                        'column_id': 'planned',
                        'filter_query': '{planned} contains false'
                    },
                    'backgroundColor': BAD,
                    'color': 'white'
                },
                {
                    'if': {
                        'column_id': 'delivered',
                        'filter_query': '{delivered} contains false'
                    },
                    'backgroundColor': BAD,
                    'color': 'white'
                },
                {
                    'if': {
                        'column_id': 'bau',
                        'filter_query': '{bau} contains true'
                    },
                    'backgroundColor': WARNING,
                },
            ]
            )
        return fig

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
                style={'padding-top': 20, 'padding-bottom': 20}
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
        dom_nodes.extend([
            singleColRow(html.H4("Details", style={'padding-top': 20})),
            singleColRow(
                html.Div(
                    self.details_table(),
                    style={'padding-bottom': 20}
                    ))])
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


def _mk_sub_pie_trace(series):
    empty_sub_pie = go.Pie(
        labels=[], values=[], scalegroup='one')
    if series.empty:
        return empty_sub_pie

    df = series.value_counts().to_frame('issue_count')
    pie = px.pie(
        df,
        values='issue_count',
        names=df.index)
    # can only make subplots from graph objects
    return go.Pie(
        labels=pie.data[0]['labels'],
        values=pie.data[0]['values'],
        scalegroup='one')


def _mk_sub_bar_trace(
        df, name, x_col, y_col, color='blue', show_legend=False):
    fig = go.Bar(
        x=df[x_col].tolist(),
        y=df[y_col].tolist(),
        name=name,
        marker={'color': color},
        showlegend=show_legend,
        legendgroup=name)
    return fig


def _mk_sub_line_trace(
        df, name, x_col, y_col, color='blue', show_legend=False):
    fig = go.Scatter(
        x=df[x_col].tolist(),
        y=df[y_col].tolist(),
        name=name,
        marker={'color': color},
        showlegend=show_legend,
        legendgroup=name)
    return fig


def mk_gauge_trace(df):
    val = int(df.goal_completed.mean().round(0))
    if val < 60:
        color = 'red'
    elif val < 80:
        color = 'orange'
    else:
        color = 'green'
    fig = go.Indicator(
        value=val,
        number={'font': {'color': color}},
        title={
            'text': "Goal Completion %",
            'font': {'size': 12}}
    )
    return fig


def chunk(iterable, chunk_size=1):
    iterator = iter(iterable)

    while True:
        chunks = []
        try:
            for _ in range(chunk_size):
                chunks.append(next(iterator))
        except StopIteration:
            yield chunks
            break
        else:
            yield chunks


class Metrics:
    def __init__(self, team_names):
        self.model = MetricsModel()

    def mk_bau_overview_figure(self):
        df = self.model.sprint_bau_report_df()
        df = df.sort_values(['team_name', 'start_date'])
        team_names = df.team_name.unique()

        plots = len(team_names)
        cols = 3
        rows, rem = divmod(plots, cols)
        rows += rem

        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=[name for name in team_names],
            specs=[
                [{'type': 'domain'} for _ in range(cols)]
                for _ in range(rows)])

        for i, (_, group) in enumerate(df.groupby("team_name")):
            div, rem = divmod(i, cols)
            fig.add_trace(
                _mk_sub_pie_trace(
                    group.bau_summary.explode("bau_summary").dropna()
                ),
                row=div + 1, col=rem + 1)

        fig.update_layout(
            legend_x=1,
            legend_y=1,
            margin=dict(t=0, b=0, r=0, l=0))
        fig.update_traces(
            textinfo='percent', showlegend=True)
        fig.update_layout(transition_duration=500)
        return fig

    @staticmethod
    def add_sprint_delivery_traces(df, row, col, show_legend, fig):
        fig.add_trace(
            _mk_sub_line_trace(
                df,
                name='BAU %',
                x_col='end_date',
                y_col='bau_issues_percentage',
                color='orange',
                show_legend=show_legend),
            row=row, col=col)
        fig.add_trace(
            _mk_sub_line_trace(
                df,
                name='Delivery %',
                x_col='end_date',
                y_col='roadmap_delivered_issues_percentage',
                color=GOOD,
                show_legend=show_legend),
            row=row, col=col)
        fig.add_trace(
            _mk_sub_bar_trace(
                df,
                name='Goal completed',
                x_col='end_date',
                y_col='goal_completed',
                color='#90ee90',
                show_legend=show_legend),
            row=row, col=col)

    @staticmethod
    def add_gauge_trace(df, row, col, fig):
        fig.add_trace(mk_gauge_trace(df), row, col)

    @staticmethod
    def _gen_titles(df, cols):
        teams = df['team_name'].unique()
        for i in range(0, len(teams), cols):
            yield list(teams[i: i + 3])
            yield [None] * cols

    @staticmethod
    def _gen_specs(df, cols):
        teams = df['team_name'].unique()
        for _ in range(0, len(teams), cols):
            yield [{}] * cols
            yield [{'type': 'indicator'}] * cols

    @staticmethod
    def _gen_heights(df, cols):
        teams = df['team_name'].unique()
        for _ in range(0, len(teams), cols):
            yield 0.7
            yield 0.3

    def mk_delivery_summary_figure(self):
        df = self.model.sprint_performance_report_df()
        df = df.sort_values(['team_name', 'start_date'])
        cols = 3

        titles = list(self._gen_titles(df, cols))
        specs = list(self._gen_specs(df, cols))
        heights = list(self._gen_heights(df, cols))

        fig = make_subplots(
            rows=len(specs), cols=cols,
            subplot_titles=list(chain.from_iterable(titles)),
            specs=specs,
            row_heights=heights)

        for row_base, groups_chunk in enumerate(
               chunk(df.groupby('team_name'), cols),
               start=1):
            row_above = row_base + row_base - 1
            row_below = row_above + 1

            for col, (_, group_df) in enumerate(groups_chunk, start=1):
                if row_above == 1 and col == 1:
                    show_legend = True
                else:
                    show_legend = False

                self.add_sprint_delivery_traces(
                    group_df, row_above, col, show_legend, fig)
                self.add_gauge_trace(group_df, row_below, col, fig)

        fig.update_layout(
            legend_x=1,
            legend_y=1,
            height=600,
            margin=dict(t=20, b=20, r=0, l=0),
            )
        fig.update_layout(transition_duration=500)
        for ax in fig['layout']:
            if ax.startswith('yaxis'):
                fig['layout'][ax]['ticksuffix'] = '%'
        return fig

    def render(self):
        return dbc.Col([
            singleColRow(html.H2('KPIs')),
            singleColRow(dcc.Graph(figure=self.mk_delivery_summary_figure())),
            singleColRow(html.H2('BAU overview')),
            singleColRow(dcc.Graph(figure=self.mk_bau_overview_figure()))
            ])
