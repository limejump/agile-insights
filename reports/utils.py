import arrow
import pandas as pd

from database.mongo import get_client


def percent(df, col_a, col_b):
    df = (df[col_a] / df[col_b]) * 100
    return df


def goal_complete(sprint_aux_data):
    return bool(sprint_aux_data.get('goal_completed'))


def summarise_sprint(team_name, sprint_data, sprint_aux_data):
    sprint_summary_df = mk_issues_summary_df(sprint_data).tail(1)
    sprint_summary_df['start_date'] = sprint_data['start']
    sprint_summary_df['end_date'] = sprint_data['end']
    goal_completed = (
        100 if goal_complete(sprint_aux_data) else 0)
    sprint_summary_df['goal_completed'] = goal_completed
    sprint_summary_df['_id'] = sprint_data['_id']
    sprint_summary_df['team_name'] = team_name
    sprint_summary_df = sprint_summary_df.drop(columns=['planned'])
    return sprint_summary_df


def mk_issues_summary_df(sprint_data):
    issues_df = pd.DataFrame.from_records(
        sprint_data['issues']
    )
    df = _summarise(issues_df)
    df = df.set_index('planned')
    df.loc['Total'] = df.sum()
    df['delivered_issues_percentage'] = percent(
        df, 'delivered_issues_count', 'issues_count')
    df['bau_issues_percentage'] = percent(
        df, 'bau_issues_count', 'issues_count')
    df['roadmap_delivered_issues_percentage'] = percent(
        df, 'roadmap_delivered_issues_count', 'roadmap_issues_count')
    df = df.round().reset_index()
    return df


def _summarise(df):
    summary_df = df.groupby(
        ['planned', 'finished_in_sprint', 'bau']).size().reset_index(
            name="issues_count")
    summary_df['planned'].replace({
        True: "planned", False: "unplanned"}, inplace=True)
    transformed_df = summary_df[["planned", "issues_count"]].groupby(
        ['planned'], as_index=False).sum()
    delivered_df = summary_df[summary_df.finished_in_sprint.eq(True)][
        ["planned", "issues_count"]].groupby(
            ['planned'], as_index=False).sum()
    transformed_df['delivered_issues_count'] = pd.Series(
        delivered_df['issues_count'].values)
    bau_df = summary_df[summary_df.bau.eq(True)][
        ["planned", "issues_count"]].groupby(['planned'], as_index=False).sum()

    non_bau_df = summary_df[summary_df.bau.eq(False)][
        ["planned", "issues_count"]].groupby(['planned'], as_index=False).sum()
    non_bau_delivered_df = summary_df[
        summary_df.bau.eq(False) & summary_df.finished_in_sprint.eq(True)
        ][["planned", "issues_count"]].groupby(
            ['planned'], as_index=False).sum()

    transformed_df['bau_issues_count'] = pd.Series(bau_df['issues_count'].values)
    transformed_df['roadmap_issues_count'] = pd.Series(
        non_bau_df['issues_count'].values)
    transformed_df['roadmap_delivered_issues_count'] = pd.Series(
        non_bau_delivered_df['issues_count'].values)
    transformed_df = transformed_df.fillna(0)
    return transformed_df


def mk_bau_summary_df(team_name, sprint_data):
    issues_df = pd.DataFrame.from_records(
        sprint_data['issues'])
    bau_summary = [
        bau_category
        for row in issues_df[issues_df.bau.eq(True)].bau_breakdown
        for bau_category in row
    ]
    record = {
        '_id': sprint_data['_id'],
        'team_name': team_name,
        'start_date': sprint_data['start'],
        'end_date': sprint_data['end'],
        'bau_summary': bau_summary}
    df = pd.DataFrame.from_records([record])
    return df


class SprintsAggregate:
    def __init__(self, team_name, num_sprints):
        self.db = get_client()
        self.team_name = team_name
        self.sprints_data = self.db.get_sprints_and_aux(
            team_name,
            arrow.utcnow().shift(weeks=-(num_sprints * 2)).datetime
        )

    def summarise_sprints(self):
        sprint_summaries = []
        for sprint_data in self.sprints_data:
            aux = sprint_data.pop("auxillary_data")
            aux_doc = aux.pop() if aux else {}
            sprint_summaries.append(
                summarise_sprint(self.team_name, sprint_data, aux_doc))
        return pd.concat(sprint_summaries).reset_index(drop=True)

    def summarise_bau(self):
        bau_summaries = []
        for sprint_data in self.sprints_data:
            sprint_data.pop("auxillary_data")
            bau_summaries.append(
                mk_bau_summary_df(self.team_name, sprint_data))
        return pd.concat(bau_summaries)
