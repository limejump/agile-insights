import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
