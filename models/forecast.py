import pandas as pd
import random

from database.mongo import get_client


class Forecast:
    def __init__(self, team_name):
        self.db_client = get_client()
        self._data = self.db_client.get_historic_issues(team_name)
        df = pd.DataFrame.from_records(self._data)
        # FIXME:
        # 1) make the cap configurable?
        # 2) remove top 95%
        self.df = df[df.days_taken < df.days_taken.quantile(0.95)]

    def run_montecarlo(self, num_issues):
        records = []
        pool = list(self.df['days_taken'].dropna())
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
