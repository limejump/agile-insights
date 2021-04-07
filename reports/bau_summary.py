
import pandas as pd

from .utils import SprintsAggregate


def create_reports(teams, num_sprints=6):
    summaries = []
    for team in teams:
        agg = SprintsAggregate(team.name, num_sprints)
        summaries.append(agg.summarise_bau())
    return pd.concat(summaries).reset_index(drop=True)