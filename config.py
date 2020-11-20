from dataclasses import dataclass
import json
from typing import List


class ConfigClass:
    def __init__(self, dataclass):
        self.config_class = dataclass
        self.config = None

    def set(self, *a, **kw):
        if self.config is not None:
            raise ValueError(
                f'config for {self.config_class.__name__} already set')
        self.config = self.config_class(*a, **kw)

    def get(self):
        if self.config is not None:
            return self.config
        else:
            raise ValueError(
                f'config for {self.config_class.__name__} not set')


def configclass(dataclass):
    return ConfigClass(dataclass)


class Config:
    def __init__(self):
        self.config_store = {}

    def register(self, name, configclass):
        self.config_store[name] = configclass

    def get(self, name):
        return self.config_store[name].get()

    def set(self, name, *a, **kw):
        self.config_store[name].set(*a, **kw)


# The motivation for these config helpers is to enable the definition
# of config to be done near the usage site, but allow the setting of
# the actual config values to be done higher up as command line options,
# environment variables, or config files.
# Near the usage site you define a dataclass which captures the relevant
# config. Then call config.register, passing in the dataclass, to add it
# to the global store.
config = Config()


@dataclass
class TeamInfo:
    name: str
    board_id: int


@configclass
@dataclass
class TeamsConfig:
    teams: List[TeamInfo]


def get_teams_from_file():
    with open('./config_files/config.json') as f:
        content = json.load(f)
    return [
        TeamInfo(team['name'], team['board_id'])
        for team in content['teams']
    ]


config.register('teams', TeamsConfig)


def parse_teams_input(teams):
    return [TeamInfo(name, board_id) for name, board_id in teams]


def json_provider(file_path, cmd_name):
    with open(file_path) as f:
        content = json.load(f)
    teams = tuple(
        (d['name'], d['board_id']) for d in content['teams'])
    jira_email = content['jira']['email']
    url = content['jira']['base_url']
    return {
        'team': teams,
        'jira_user_email': jira_email,
        'jira_url': url
    }
