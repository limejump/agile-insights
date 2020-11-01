import arrow
from datetime import datetime
from math import floor, ceil
import pandas as pd
import random

from database.mongo import get_client


class Forecast:
    def __init__(self, team_name):
        self.db_client = get_client()
        six_sprints_ago = arrow.utcnow().shift(weeks=-12).datetime
        self._sprints_data = self.db_client.get_sprints(
            team_name, six_sprints_ago)

        self._historic_data = self.db_client.get_historic_issues(team_name)
        df = pd.DataFrame.from_records(self._historic_data)
        # FIXME:
        # 1) make the cap configurable?
        # 2) remove top 95%
        self.historic_df = df[df.days_taken < df.days_taken.quantile(0.95)]

    def run_montecarlo(self, num_issues):
        records = []
        pool = list(self.historic_df['days_taken'].dropna())
        for simulation in range(1000):
            days_taken = sum([
                random.choice(pool)
                for _ in range(num_issues)])
            records.append({
                "simulation": simulation,
                "days_taken": days_taken})
        df = pd.DataFrame.from_records(
            records).sort_values('days_taken').reset_index(drop=True)
        return df

    def throughput_df(self):
        df = pd.DataFrame()
        throughput = 0
        for sprint in reversed(self._sprints_data):
            throughput += len(
                [i for i in sprint['issues']
                 if i['finished_in_sprint']])
            df = df.append(
                {
                    'name': sprint['name'],
                    'start': sprint['start'],
                    'start_ordinal': sprint['start'].toordinal(),
                    'throughput': throughput
                },
                ignore_index=True)
        return df

    @staticmethod
    def gradient(start_y, end_y, start_x, end_x):
        return (end_y - start_y) / (end_x - start_x)

    def minmax_gradients(self, df):
        origin_time = df.at[0, 'start_ordinal']
        origin_throughput = df.at[0, 'throughput']

        grads = []
        for index, row, in df.iterrows():
            if index == 0:
                continue
            grad = self.gradient(
                origin_throughput, row['throughput'],
                origin_time, row['start_ordinal']
            )
            grads.append(grad)
        return min(grads), max(grads)

    def uncertainty_cone_coords(self):
        df = self.throughput_df()
        min_g, max_g = self.minmax_gradients(df)
        end_y = df.iloc[-1]['throughput']
        start_x = df.iloc[0]['start']
        start_y = df.iloc[0]['throughput']
        start_x_ord = df.iloc[0]['start_ordinal']
        x1 = floor(
            start_x_ord + ((end_y - start_y) / min_g))
        x2 = floor(
            start_x_ord + ((end_y - start_y) / max_g))
        return (
            (start_x, start_y, datetime.fromordinal(x2), end_y),
            (start_x, start_y, datetime.fromordinal(x1), end_y))
